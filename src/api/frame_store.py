"""Data access layer: loads telemetry frames from CSV and/or database.

Owns caching, deduplication, and satellite discovery.  Has no ML
or HTTP knowledge — pure data retrieval.
"""

from __future__ import annotations

from loguru import logger
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from gr_sat.core.telemetry import DecoderRegistry

if TYPE_CHECKING:
    from .scoring import ScoringService




class FrameStore:
    """Loads, caches, and serves telemetry DataFrames.

    Optionally accepts a :class:`ScoringService` to apply anomaly
    scores transparently when frames are first loaded.
    """

    def __init__(
        self,
        processed_dir: Path,
        models_dir: Path,
        scoring: ScoringService | None = None,
    ):
        self.processed_dir = processed_dir
        self.models_dir = models_dir
        self._scoring = scoring
        self._cache: dict[int, pd.DataFrame] = {}

    # ── Public API ───────────────────────────────────────────────────

    def frames_for(self, norad_id: int) -> pd.DataFrame:
        """Return (and cache) all telemetry frames for *norad_id*."""
        sat_id = int(norad_id)

        if sat_id not in self._cache:
            dfs: list[pd.DataFrame] = []

            # 1. Try to load from live database first
            db_dfs = self._load_from_database(sat_id)
            if db_dfs:
                dfs.extend(db_dfs)
                logger.info(f"Loaded {len(dfs[0])} telemetry frames from database for NORAD {sat_id}")
            else:
                # 2. Offline Fallback to Historical CSV
                logger.info(f"Database empty or offline. Falling back to local processed CSV for NORAD {sat_id}")
                path = self.processed_dir / f"{sat_id}.csv"
                if path.exists():
                    try:
                        csv_df = pd.read_csv(path)
                        if "timestamp" in csv_df.columns:
                            csv_df["timestamp"] = pd.to_datetime(
                                csv_df["timestamp"], utc=True
                            )
                            csv_df["norad_id"] = sat_id
                            dfs.append(csv_df)
                    except Exception as exc:
                        logger.warning("Failed to load CSV for %d: %s", sat_id, exc)

            if not dfs:
                raise KeyError(
                    f"No telemetry data found for NORAD {sat_id} in Database or CSV."
                )

            df = dfs[0]
            df = df.drop_duplicates(subset=["timestamp"], keep="last")



            # Apply anomaly scores if a scoring service is wired in
            if self._scoring is not None:
                df = self._scoring.ensure_scores(sat_id, df)

            self._cache[sat_id] = df.sort_values("timestamp").reset_index(drop=True)

        return self._cache[sat_id].copy()

    def combined_frames(self, norad_id: int | None) -> pd.DataFrame:
        """Return frames for a single satellite, or all satellites combined."""
        if norad_id is not None:
            return self.frames_for(norad_id)

        ids = sorted(self.discover_dataset_ids())
        if not ids:
            return pd.DataFrame()
        return pd.concat([self.frames_for(sat_id) for sat_id in ids], ignore_index=True)

    def discover_satellite_ids(self) -> set[int]:
        """Union of dataset IDs, decoder-supported IDs, and model IDs."""
        return (
            self.discover_dataset_ids()
            | set(DecoderRegistry.list_supported().keys())
            | self.discover_model_ids()
        )

    def discover_dataset_ids(self) -> set[int]:
        """NORAD IDs that have a processed CSV on disk."""
        if not self.processed_dir.exists():
            return set()
        ids: set[int] = set()
        for path in self.processed_dir.glob("*.csv"):
            try:
                ids.add(int(path.stem))
            except ValueError:
                continue
        return ids

    def discover_model_ids(self) -> set[int]:
        """NORAD IDs that have a model metadata file on disk."""
        if not self.models_dir.exists():
            return set()
        ids: set[int] = set()
        for path in self.models_dir.glob("*_metadata.json"):
            try:
                ids.add(int(path.name.removesuffix("_metadata.json")))
            except ValueError:
                continue
        return ids

    @staticmethod
    def sort_recent(df: pd.DataFrame) -> pd.DataFrame:
        """Sort *df* by timestamp (newest first), breaking ties by anomaly score."""
        if df.empty:
            return df
        sort_columns = ["timestamp"]
        ascending = [False]
        if "anomaly_score" in df.columns:
            sort_columns.append("anomaly_score")
            ascending.append(False)
        return df.sort_values(sort_columns, ascending=ascending)

    # ── Private helpers ──────────────────────────────────────────────

    @staticmethod
    def _load_from_database(sat_id: int) -> list[pd.DataFrame]:
        """Attempt to load live telemetry from TimescaleDB."""
        dfs: list[pd.DataFrame] = []
        try:
            try:
                from .database import get_engine
                from .db_models import TelemetryRow, RawFrame
            except ImportError:
                from database import get_engine  # type: ignore[no-redef]
                from db_models import TelemetryRow, RawFrame  # type: ignore[no-redef]
            from sqlmodel import Session, select

            engine = get_engine()
            if engine:
                with Session(engine) as session:
                    statement = (
                        select(TelemetryRow, RawFrame)
                        .join(RawFrame, TelemetryRow.raw_frame_id == RawFrame.id)
                        .where(TelemetryRow.norad_id == sat_id)
                        .order_by(TelemetryRow.timestamp.asc())
                    )
                    results = session.exec(statement).all()

                if results:
                    rows = []
                    for tf, rf in results:
                        if not tf.features:
                            continue
                        row: dict = {
                            "timestamp": tf.timestamp,
                            "norad_id": tf.norad_id,
                            "station_id": rf.station_id,
                            "raw_frame": rf.raw_frame,
                            "snr": rf.snr,
                            "anomaly_score": tf.anomaly_score,
                            "is_anomaly": tf.is_anomaly or False,
                            "missing_fields": tf.missing_fields,
                            "missing_raw_fields": tf.missing_raw_fields,
                            "frame_is_complete": tf.frame_is_complete,
                            "dropped_packet_suspect": tf.dropped_packet_suspect,
                            "sampling_irregular": tf.sampling_irregular,
                            "pass_id": tf.pass_id,
                            "pass_duration_sec": tf.pass_duration_sec,
                            "pass_frame_count": tf.pass_frame_count,
                        }
                        if isinstance(tf.features, dict):
                            row.update(tf.features)
                        rows.append(row)

                    db_df = pd.DataFrame(rows)
                    db_df["timestamp"] = pd.to_datetime(db_df["timestamp"], utc=True)
                    dfs.append(db_df)
        except Exception as exc:
            try:
                from sqlalchemy.exc import SQLAlchemyError

                if isinstance(exc, SQLAlchemyError):
                    logger.error(
                        "Critical database query failure for %d: %s", sat_id, exc
                    )
                    raise RuntimeError(f"Database query failed: {exc}") from exc
            except ImportError:
                pass

            logger.warning("Failed to query DB for %d: %s", sat_id, exc)

        return dfs
