from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd
import torch

from gr_sat.model_artifacts import (
    ModelArtifactMetadata,
    load_model_artifacts,
    load_model_metadata,
    model_artifact_paths,
)
from gr_sat.models import compute_anomaly_scores
from gr_sat.satellite_profiles import get_satellite_profile
from gr_sat.telemetry import DecoderRegistry

import gr_sat.decoders  # noqa: F401 - registers available decoders

try:
    from .database import database_status
except ImportError:  # pragma: no cover - used when uvicorn runs from src/api
    from database import database_status


FEATURE_FIELDS = (
    "batt_voltage",
    "batt_current",
    "batt_a_voltage",
    "batt_b_voltage",
    "batt_a_current",
    "batt_b_current",
    "power_consumption",
    "temp_obc",
    "temp_batt_a",
    "temp_batt_b",
    "temp_panel_z",
    "uptime",
)


QUALITY_FIELDS = (
    "frame_is_complete",
    "missing_raw_fields",
    "missing_raw_field_count",
    "sampling_irregular",
    "dropped_packet_suspect",
    "same_timestamp_collision",
    "seconds_since_prev",
    "seconds_to_next",
    "pass_id",
    "pass_frame_index",
    "pass_frame_count",
    "pass_duration_sec",
    "pass_median_cadence_sec",
    "cadence_reference_sec",
)


@dataclass(frozen=True)
class ModelStatus:
    status: str
    detail: str
    metadata: ModelArtifactMetadata | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        if self.metadata is None:
            return {
                "status": self.status,
                "detail": self.detail,
                "error": self.error,
                "threshold": None,
                "inference_mode": None,
                "artifact_version": None,
                "feature_names": [],
                "feature_contract_version": None,
                "train_rows": 0,
                "validation_rows": 0,
                "test_rows": 0,
            }

        return {
            "status": self.status,
            "detail": self.detail,
            "error": self.error,
            "threshold": _json_value(self.metadata.threshold),
            "inference_mode": self.metadata.inference_mode,
            "artifact_version": self.metadata.version,
            "feature_names": list(self.metadata.feature_names),
            "diagnosis_feature_names": list(
                self.metadata.diagnosis_feature_names or self.metadata.feature_names
            ),
            "feature_contract_version": self.metadata.feature_contract_version,
            "train_rows": self.metadata.train_rows,
            "validation_rows": self.metadata.validation_rows,
            "test_rows": self.metadata.test_rows,
            "train_start": self.metadata.train_start,
            "train_end": self.metadata.train_end,
            "validation_start": self.metadata.validation_start,
            "validation_end": self.metadata.validation_end,
            "test_start": self.metadata.test_start,
            "test_end": self.metadata.test_end,
        }


class DashboardDataRepository:
    def __init__(
        self,
        root: Path | str = Path("."),
        processed_dir: Path | str | None = None,
        models_dir: Path | str | None = None,
    ):
        self.root = Path(root)
        self.processed_dir = (
            Path(processed_dir)
            if processed_dir is not None
            else self.root / "data" / "processed"
        )
        self.models_dir = (
            Path(models_dir) if models_dir is not None else self.root / "models"
        )
        self._frames_cache: dict[int, pd.DataFrame] = {}
        self._model_cache: dict[int, ModelStatus] = {}

    def status_payload(self) -> dict[str, Any]:
        satellites = self.satellite_summaries()
        components = [
            {
                "name": "api",
                "status": "online",
                "detail": "FastAPI process is responding.",
                "metadata": {"title": "gr_sat Watchdog API"},
            },
            database_status(),
            self._processed_data_component(),
            self._model_artifacts_component(),
        ]
        return {
            "status": self._overall_status(components),
            "service": "gr_sat Watchdog API",
            "generated_at": _now_iso(),
            "components": components,
            "supported_satellites": [
                self._satellite_identity(summary["norad_id"]) for summary in satellites
            ],
            "links": {
                "dashboard_summary": "/api/dashboard/summary",
                "satellites": "/api/satellites",
                "recent_telemetry": "/api/telemetry/recent",
                "recent_anomalies": "/api/anomalies/recent",
                "throughput": "/api/telemetry/throughput",
            },
        }

    def dashboard_summary(self) -> dict[str, Any]:
        satellites = self.satellite_summaries()
        frame_count = sum(summary["dataset"]["row_count"] for summary in satellites)
        anomaly_count = sum(
            summary["dataset"]["anomaly_count"] for summary in satellites
        )
        partial_frame_count = sum(
            summary["dataset"]["partial_frame_count"] for summary in satellites
        )
        pass_count = sum(summary["dataset"]["pass_count"] for summary in satellites)

        return {
            "generated_at": _now_iso(),
            "window": self._dataset_window(satellites),
            "service_status": self.status_payload()["components"],
            "totals": {
                "satellite_count": len(satellites),
                "frame_count": frame_count,
                "anomaly_count": anomaly_count,
                "partial_frame_count": partial_frame_count,
                "pass_count": pass_count,
            },
            "active_satellites": satellites,
            "recent_anomalies": self.recent_anomalies(limit=5)["anomalies"],
            "throughput": self.throughput(limit=14, bucket="day")["buckets"],
        }

    def satellite_summaries(self) -> list[dict[str, Any]]:
        ids = sorted(self._discover_satellite_ids())
        return [self.satellite_summary(norad_id) for norad_id in ids]

    def satellite_summary(self, norad_id: int) -> dict[str, Any]:
        sat_id = int(norad_id)
        if sat_id not in self._discover_satellite_ids():
            raise KeyError(f"NORAD {sat_id} is not known to the dashboard data layer.")

        try:
            df = self.frames_for(sat_id)
        except KeyError:
            df = pd.DataFrame()
        model = self.model_status(norad_id).to_dict()
        identity = self._satellite_identity(sat_id)
        return {
            **identity,
            "dataset": self._dataset_summary(df),
            "model": model,
        }

    def recent_frames(
        self,
        norad_id: int | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        df = self._combined_frames(norad_id)
        records = self._sort_recent(df).head(limit)
        
        # Optimize by avoiding iterrows
        records_dict = records.to_dict(orient="records")
        frames = []
        
        for row in records_dict:
            threshold = None
            if norad_id is not None:
                model_status = self.model_status(int(norad_id))
            else:
                model_status = self.model_status(int(row["norad_id"]))
                
            if model_status.metadata is not None:
                threshold = _json_value(model_status.metadata.threshold)

            features = {
                field: _json_value(row.get(field))
                for field in FEATURE_FIELDS
                if field in row
            }
            quality = {
                field: _json_value(row.get(field))
                for field in QUALITY_FIELDS
                if field in row
            }
            if "missing_raw_fields" in quality:
                quality["missing_raw_fields"] = _missing_fields_value(
                    quality["missing_raw_fields"]
                )

            frames.append({
                "timestamp": _timestamp_iso(row["timestamp"]),
                "norad_id": int(row["norad_id"]),
                "source": "historical_processed_csv",
                "features": features,
                "quality": quality,
                "model": {
                    "anomaly_score": _json_value(row.get("anomaly_score")),
                    "threshold": threshold,
                    "is_anomaly": bool(_bool_value(row.get("is_anomaly"))),
                },
            })

        return {
            "generated_at": _now_iso(),
            "norad_id": norad_id,
            "limit": limit,
            "frames": frames,
        }

    def recent_anomalies(
        self,
        norad_id: int | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        df = self._combined_frames(norad_id)
        if "is_anomaly" not in df.columns:
            anomalies = df.iloc[0:0]
        else:
            anomalies = df[df["is_anomaly"].fillna(False).astype(bool)]

        records = self._sort_recent(anomalies).head(limit)
        records_dict = records.to_dict(orient="records")
        anomalies_list = []
        
        for row in records_dict:
            threshold = None
            if norad_id is not None:
                model_status = self.model_status(int(norad_id))
            else:
                model_status = self.model_status(int(row["norad_id"]))
                
            if model_status.metadata is not None:
                threshold = _json_value(model_status.metadata.threshold)

            features = {
                field: _json_value(row.get(field))
                for field in FEATURE_FIELDS
                if field in row
            }
            quality = {
                field: _json_value(row.get(field))
                for field in QUALITY_FIELDS
                if field in row
            }
            if "missing_raw_fields" in quality:
                quality["missing_raw_fields"] = _missing_fields_value(
                    quality["missing_raw_fields"]
                )
                
            anomalies_list.append({
                "timestamp": _timestamp_iso(row["timestamp"]),
                "norad_id": int(row["norad_id"]),
                "score": _json_value(row.get("anomaly_score")),
                "threshold": threshold,
                "features": features,
                "quality": quality,
            })

        return {
            "generated_at": _now_iso(),
            "norad_id": norad_id,
            "limit": limit,
            "anomalies": anomalies_list,
        }

    def throughput(
        self,
        norad_id: int | None = None,
        limit: int = 30,
        bucket: Literal["hour", "day"] = "day",
    ) -> dict[str, Any]:
        df = self._combined_frames(norad_id)
        if df.empty:
            return {
                "generated_at": _now_iso(),
                "norad_id": norad_id,
                "bucket": bucket,
                "limit": limit,
                "total_frames": 0,
                "buckets": [],
            }

        freq = "h" if bucket == "hour" else "D"
        working = df.copy()
        working["_bucket"] = working["timestamp"].dt.floor(freq)
        grouped = (
            working.groupby("_bucket", dropna=True)
            .agg(frame_count=("timestamp", "size"), anomaly_count=("is_anomaly", "sum"))
            .sort_index()
            .tail(limit)
            .reset_index()
        )

        buckets = [
            {
                "timestamp": _timestamp_iso(row["_bucket"]),
                "frame_count": int(row["frame_count"]),
                "anomaly_count": int(row["anomaly_count"]),
            }
            for _, row in grouped.iterrows()
        ]
        return {
            "generated_at": _now_iso(),
            "norad_id": norad_id,
            "bucket": bucket,
            "limit": limit,
            "total_frames": int(len(df)),
            "returned_frame_count": int(grouped["frame_count"].sum())
            if not grouped.empty
            else 0,
            "buckets": buckets,
        }

    def predict_passes(
        self,
        lat: float,
        lon: float,
        elevation_m: float = 0.0,
        station_label: str | None = None,
        lookahead_hours: int = 24,
        min_elevation: float = 10.0,
        norad_id: int | None = None,
        include_tracks: bool = True,
    ) -> dict[str, Any]:
        from datetime import datetime, timedelta, timezone
        from skyfield.api import load, wgs84

        now = datetime.now(timezone.utc)

        if not -90.0 <= lat <= 90.0:
            raise ValueError("Latitude must be between -90 and 90 degrees.")
        if not -180.0 <= lon <= 180.0:
            raise ValueError("Longitude must be between -180 and 180 degrees.")
        if not -500.0 <= elevation_m <= 10000.0:
            raise ValueError(
                "Ground station elevation must be between -500 and 10000 meters."
            )

        st_data = {
            "id": "custom",
            "label": station_label or "Custom Ground Station",
            "lat": float(lat),
            "lon": float(lon),
            "elevation_m": float(elevation_m),
        }

        gs = wgs84.latlon(
            st_data["lat"],
            st_data["lon"],
            elevation_m=st_data["elevation_m"],
        )

        if norad_id is not None:
            sats = [self.satellite_summary(norad_id)]
        else:
            sats = self.satellite_summaries()

        ts = load.timescale()
        t0 = ts.from_datetime(now)
        t1 = ts.from_datetime(now + timedelta(hours=lookahead_hours))

        # Load Celestrak TLEs using skyfield
        url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"
        try:
            tle_file = load.tle_file(url)
            by_id = {sat.model.satnum: sat for sat in tle_file}
        except Exception:
            by_id = {}

        def sample_track(sat: Any, t_rise: Any, t_set: Any) -> list[dict[str, Any]]:
            if not include_tracks:
                return []

            start_dt = t_rise.utc_datetime()
            end_dt = t_set.utc_datetime()
            duration_seconds = (end_dt - start_dt).total_seconds()
            if duration_seconds <= 0:
                return []

            sample_count = 32
            track = []
            for sample_index in range(sample_count):
                offset = duration_seconds * sample_index / max(sample_count - 1, 1)
                sample_dt = start_dt + timedelta(seconds=offset)
                sample_t = ts.from_datetime(sample_dt)
                subpoint = sat.at(sample_t).subpoint()
                alt, az, distance = (sat - gs).at(sample_t).altaz()
                track.append(
                    {
                        "time": _timestamp_iso(sample_dt),
                        "lat": round(subpoint.latitude.degrees, 4),
                        "lon": round(subpoint.longitude.degrees, 4),
                        "elevation": round(alt.degrees, 1),
                        "azimuth": round(az.degrees, 1),
                        "range_km": round(distance.km, 1),
                    }
                )
            return track

        passes = []
        for sat_info in sats:
            sat_id = sat_info["norad_id"]
            if sat_id not in by_id:
                continue

            sat = by_id[sat_id]
            t, events = sat.find_events(gs, t0, t1, altitude_degrees=0.0)

            for i in range(len(events)):
                if events[i] == 1:  # culmination
                    t_peak = t[i]
                    alt, az, dist = (sat - gs).at(t_peak).altaz()

                    if alt.degrees >= min_elevation:
                        t_rise = None
                        for j in range(i, -1, -1):
                            if events[j] == 0:
                                t_rise = t[j]
                                break

                        t_set = None
                        for j in range(i, len(events)):
                            if events[j] == 2:
                                t_set = t[j]
                                break

                        if t_rise is not None and t_set is not None:
                            # Determine general direction
                            start_az = (sat - gs).at(t_rise).altaz()[1].degrees
                            end_az = (sat - gs).at(t_set).altaz()[1].degrees

                            # Simple heuristic for direction
                            direction = "N->S" if end_az > start_az else "S->N"
                            if abs(start_az - end_az) > 180:  # cross 360
                                direction = "S->N" if end_az < start_az else "N->S"

                            pass_record = {
                                "satellite": sat_info["name"],
                                "norad_id": sat_id,
                                "aos": _timestamp_iso(t_rise.utc_datetime()),
                                "los": _timestamp_iso(t_set.utc_datetime()),
                                "max_elevation": round(alt.degrees, 1),
                                "direction": direction,
                            }
                            if include_tracks:
                                pass_record["track"] = sample_track(sat, t_rise, t_set)
                            passes.append(pass_record)

        passes.sort(key=lambda p: p["aos"])

        return {
            "ground_station": {
                "id": st_data["id"],
                "label": st_data["label"],
                "lat": st_data["lat"],
                "lon": st_data["lon"],
                "elevation_m": st_data["elevation_m"],
            },
            "lookahead_hours": lookahead_hours,
            "min_elevation": min_elevation,
            "passes": passes,
        }

    def sensitivity_sweep(self, norad_id: int) -> dict[str, Any]:
        sat_id = int(norad_id)
        if sat_id not in self._discover_satellite_ids():
            raise KeyError(f"NORAD {sat_id} is not known to the dashboard data layer.")

        model = self.model_status(sat_id)
        current_threshold = model.metadata.threshold if model.metadata else 0.5

        # Simulated sweep data
        sweep = []
        roc = []
        for i in range(1, 100):
            thresh = i / 100.0
            sweep.append(
                {
                    "threshold": thresh,
                    "f1_score": 1.0 - abs(thresh - 0.5),
                    "precision": thresh,
                    "recall": 1.0 - thresh,
                }
            )
            roc.append({"fpr": 1.0 - thresh, "tpr": 1.0 - (thresh * 0.5)})

        return {
            "norad_id": sat_id,
            "current_threshold": current_threshold,
            "sweep": sweep,
            "roc": roc,
        }

    def frames_for(self, norad_id: int) -> pd.DataFrame:
        sat_id = int(norad_id)

        if sat_id not in self._frames_cache:
            dfs = []

            # 1. Load from Historical CSV
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
                except Exception as e:
                    import logging

                    logging.getLogger("DashboardDataRepository").warning(
                        f"Failed to load CSV for {sat_id}: {e}"
                    )

            # 2. Load from Live Database
            try:
                try:
                    from .database import get_engine
                    from .models import TelemetryFrame, RawFrame
                except ImportError:
                    from database import get_engine
                    from models import TelemetryFrame, RawFrame
                from sqlmodel import Session, select

                engine = get_engine()
                if engine:
                    with Session(engine) as session:
                        statement = (
                            select(TelemetryFrame, RawFrame)
                            .join(RawFrame, TelemetryFrame.raw_frame_id == RawFrame.id)
                            .where(TelemetryFrame.norad_id == sat_id)
                            .order_by(TelemetryFrame.timestamp.asc())
                        )
                        results = session.exec(statement).all()

                    if results:
                        rows = []
                        for tf, rf in results:
                            if not tf.features:
                                continue
                            row = {
                                "timestamp": tf.timestamp,
                                "norad_id": tf.norad_id,
                                "station_id": rf.station_id,
                                "raw_frame": rf.raw_frame,
                                "snr": rf.snr,
                                "anomaly_score": tf.anomaly_score,
                                "is_anomaly": tf.is_anomaly,
                                "missing_fields": tf.missing_fields,
                            }
                            if isinstance(tf.features, dict):
                                row.update(tf.features)
                            rows.append(row)

                        db_df = pd.DataFrame(rows)
                        db_df["timestamp"] = pd.to_datetime(
                            db_df["timestamp"], utc=True
                        )
                        dfs.append(db_df)
            except Exception as e:
                import logging
                
                try:
                    from sqlalchemy.exc import SQLAlchemyError
                    if isinstance(e, SQLAlchemyError):
                        logging.getLogger("DashboardDataRepository").error(
                            f"Critical database query failure for {sat_id}: {e}"
                        )
                        raise RuntimeError(f"Database query failed: {e}") from e
                except ImportError:
                    pass

                logging.getLogger("DashboardDataRepository").warning(
                    f"Failed to query DB for {sat_id}: {e}"
                )

            if not dfs:
                raise KeyError(
                    f"No telemetry data found for NORAD {sat_id} in CSV or Database."
                )

            # Combine, normalize, and cache
            df = pd.concat(dfs, ignore_index=True) if len(dfs) > 1 else dfs[0]
            df = df.drop_duplicates(subset=["timestamp"], keep="last")
            df = self._normalize_frame_columns(sat_id, df)
            self._frames_cache[sat_id] = df.sort_values("timestamp").reset_index(
                drop=True
            )

        return self._frames_cache[sat_id].copy()

    def model_status(self, norad_id: int) -> ModelStatus:
        sat_id = int(norad_id)
        if sat_id not in self._model_cache:
            paths = model_artifact_paths(self.models_dir, str(sat_id))
            if not paths.metadata.exists():
                self._model_cache[sat_id] = ModelStatus(
                    status="missing",
                    detail=f"No model metadata found at {paths.metadata}.",
                )
                return self._model_cache[sat_id]

            try:
                metadata = load_model_metadata(paths.metadata)
            except Exception as exc:
                self._model_cache[sat_id] = ModelStatus(
                    status="error",
                    detail="Model metadata could not be loaded.",
                    error=str(exc),
                )
                return self._model_cache[sat_id]

            missing = [
                str(path) for path in (paths.scaler, paths.weights) if not path.exists()
            ]
            if missing:
                self._model_cache[sat_id] = ModelStatus(
                    status="metadata_only",
                    detail="Model metadata is available, but inference artifacts are incomplete.",
                    metadata=metadata,
                    error=f"Missing artifacts: {', '.join(missing)}",
                )
            else:
                self._model_cache[sat_id] = ModelStatus(
                    status="ready",
                    detail="Scaler, VAE weights, and metadata are available.",
                    metadata=metadata,
                )

        return self._model_cache[sat_id]

    def _combined_frames(self, norad_id: int | None) -> pd.DataFrame:
        if norad_id is not None:
            return self.frames_for(norad_id)

        ids = sorted(self._discover_dataset_ids())
        if not ids:
            return pd.DataFrame()
        return pd.concat([self.frames_for(sat_id) for sat_id in ids], ignore_index=True)

    def _discover_satellite_ids(self) -> set[int]:
        return (
            self._discover_dataset_ids()
            | set(DecoderRegistry.list_supported().keys())
            | self._discover_model_ids()
        )

    def _discover_dataset_ids(self) -> set[int]:
        if not self.processed_dir.exists():
            return set()
        ids = set()
        for path in self.processed_dir.glob("*.csv"):
            try:
                ids.add(int(path.stem))
            except ValueError:
                continue
        return ids

    def _discover_model_ids(self) -> set[int]:
        if not self.models_dir.exists():
            return set()
        ids = set()
        for path in self.models_dir.glob("*_metadata.json"):
            try:
                ids.add(int(path.name.removesuffix("_metadata.json")))
            except ValueError:
                continue
        return ids

    def _normalize_frame_columns(self, norad_id: int, df: pd.DataFrame) -> pd.DataFrame:
        working = df.copy()

        if "is_anomaly" in working.columns:
            working["is_anomaly"] = working["is_anomaly"].map(_bool_value).fillna(False)
        else:
            working["is_anomaly"] = False

        if "anomaly_score" not in working.columns:
            working["anomaly_score"] = np.nan

        model_status = self.model_status(norad_id)
        if working["anomaly_score"].isna().all() and model_status.status == "ready":
            working = self._score_frames(norad_id, working, model_status)
        elif model_status.metadata is not None:
            threshold = model_status.metadata.threshold
            missing_anomaly_flags = (
                "is_anomaly" not in df.columns or working["is_anomaly"].isna().any()
            )
            if missing_anomaly_flags:
                working["is_anomaly"] = (
                    working["anomaly_score"].gt(threshold).fillna(False)
                )

        return working

    def _score_frames(
        self,
        norad_id: int,
        df: pd.DataFrame,
        model_status: ModelStatus,
    ) -> pd.DataFrame:
        assert model_status.metadata is not None
        working = df.copy()
        try:
            if not hasattr(self, "_loaded_models"):
                self._loaded_models = {}
            if norad_id not in self._loaded_models:
                self._loaded_models[norad_id] = load_model_artifacts(
                    str(norad_id), self.models_dir
                )
            scaler, model, metadata = self._loaded_models[norad_id]
            feature_names = list(metadata.feature_names)
            complete_mask = working[feature_names].notna().all(axis=1)
            if not complete_mask.any():
                return working

            feature_matrix = (
                working.loc[complete_mask, feature_names].astype(float).to_numpy()
            )
            scaled = scaler.transform(feature_matrix)
            x_tensor = torch.FloatTensor(scaled)
            model.eval()
            with torch.no_grad():
                recon_x, mu, logvar = model(x_tensor)
                scores = compute_anomaly_scores(
                    recon_x,
                    x_tensor,
                    mu,
                    logvar,
                    kld_weight=metadata.kld_weight,
                ).numpy()

            working.loc[complete_mask, "anomaly_score"] = scores
            working["is_anomaly"] = (
                working["anomaly_score"].gt(metadata.threshold).fillna(False)
            )
        except Exception as exc:
            self._model_cache[int(norad_id)] = ModelStatus(
                status="error",
                detail="Model artifacts exist, but dashboard scoring failed.",
                metadata=model_status.metadata,
                error=str(exc),
            )

        return working

    def _satellite_identity(self, norad_id: int) -> dict[str, Any]:
        sat_id = int(norad_id)
        supported = DecoderRegistry.list_supported()
        try:
            profile = get_satellite_profile(sat_id)
            name = profile.name
            feature_contract_version = profile.feature_contract.version
            feature_names = list(profile.feature_contract.feature_names)
            diagnosis_feature_names = list(
                profile.feature_contract.diagnosis_feature_names
            )
        except KeyError:
            name = f"NORAD {sat_id}"
            feature_contract_version = None
            feature_names = []
            diagnosis_feature_names = []

        return {
            "norad_id": sat_id,
            "name": name,
            "decoder": supported.get(sat_id),
            "feature_contract_version": feature_contract_version,
            "feature_names": feature_names,
            "diagnosis_feature_names": diagnosis_feature_names,
        }

    def _dataset_summary(self, df: pd.DataFrame) -> dict[str, Any]:
        if df.empty:
            return {
                "status": "missing",
                "row_count": 0,
                "anomaly_count": 0,
                "complete_frame_count": 0,
                "partial_frame_count": 0,
                "pass_count": 0,
                "start": None,
                "end": None,
                "latest_timestamp": None,
            }

        complete = df.get("frame_is_complete", pd.Series(True, index=df.index)).map(
            _bool_value
        )
        pass_count = (
            int(df["pass_id"].dropna().nunique()) if "pass_id" in df.columns else 0
        )
        return {
            "status": "available",
            "row_count": int(len(df)),
            "anomaly_count": int(df["is_anomaly"].fillna(False).astype(bool).sum()),
            "complete_frame_count": int(complete.fillna(False).sum()),
            "partial_frame_count": int((~complete.fillna(False)).sum()),
            "pass_count": pass_count,
            "start": _timestamp_iso(df["timestamp"].min()),
            "end": _timestamp_iso(df["timestamp"].max()),
            "latest_timestamp": _timestamp_iso(df["timestamp"].max()),
        }

    def _dataset_window(self, satellites: list[dict[str, Any]]) -> dict[str, Any]:
        starts = [
            summary["dataset"]["start"]
            for summary in satellites
            if summary["dataset"]["start"] is not None
        ]
        ends = [
            summary["dataset"]["end"]
            for summary in satellites
            if summary["dataset"]["end"] is not None
        ]
        return {
            "label": "historical_processed_dataset",
            "start": min(starts) if starts else None,
            "end": max(ends) if ends else None,
        }

    def _frame_record(self, row: pd.Series) -> dict[str, Any]:
        features = {
            field: _json_value(row.get(field))
            for field in FEATURE_FIELDS
            if field in row.index
        }
        quality = {
            field: _json_value(row.get(field))
            for field in QUALITY_FIELDS
            if field in row.index
        }
        if "missing_raw_fields" in quality:
            quality["missing_raw_fields"] = _missing_fields_value(
                quality["missing_raw_fields"]
            )

        threshold = None
        model_status = self.model_status(int(row["norad_id"]))
        if model_status.metadata is not None:
            threshold = _json_value(model_status.metadata.threshold)

        return {
            "timestamp": _timestamp_iso(row["timestamp"]),
            "norad_id": int(row["norad_id"]),
            "source": "historical_processed_csv",
            "features": features,
            "quality": quality,
            "model": {
                "anomaly_score": _json_value(row.get("anomaly_score")),
                "threshold": threshold,
                "is_anomaly": bool(_bool_value(row.get("is_anomaly"))),
            },
        }

    def _anomaly_record(self, row: pd.Series) -> dict[str, Any]:
        frame = self._frame_record(row)
        return {
            "timestamp": frame["timestamp"],
            "norad_id": frame["norad_id"],
            "score": frame["model"]["anomaly_score"],
            "threshold": frame["model"]["threshold"],
            "features": frame["features"],
            "quality": frame["quality"],
        }

    def _processed_data_component(self) -> dict[str, Any]:
        dataset_ids = self._discover_dataset_ids()
        status = "online" if dataset_ids else "degraded"
        return {
            "name": "processed_data",
            "status": status,
            "detail": f"{len(dataset_ids)} processed satellite dataset(s) available.",
            "metadata": {
                "processed_dir": str(self.processed_dir),
                "satellite_ids": sorted(dataset_ids),
            },
        }

    def _model_artifacts_component(self) -> dict[str, Any]:
        model_ids = self._discover_model_ids()
        status = "online" if model_ids else "degraded"
        return {
            "name": "model_artifacts",
            "status": status,
            "detail": f"{len(model_ids)} model metadata artifact(s) available.",
            "metadata": {
                "models_dir": str(self.models_dir),
                "satellite_ids": sorted(model_ids),
            },
        }

    def _overall_status(self, components: list[dict[str, Any]]) -> str:
        severe = {"error", "offline"}
        if any(component["status"] in severe for component in components):
            return "degraded"
        return "online"

    def _sort_recent(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        sort_columns = ["timestamp"]
        ascending = [False]
        if "anomaly_score" in df.columns:
            sort_columns.append("anomaly_score")
            ascending.append(False)
        return df.sort_values(sort_columns, ascending=ascending)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _timestamp_iso(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    return pd.Timestamp(value).isoformat()


def _json_value(value: Any) -> Any:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, pd.Timestamp):
        return _timestamp_iso(value)
    if isinstance(value, float):
        return float(value)
    return value


def _bool_value(value: Any) -> bool | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return bool(value)


def _missing_fields_value(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        if stripped.startswith("[") and stripped.endswith("]"):
            import json

            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
            except json.JSONDecodeError:
                pass
        return [part.strip() for part in stripped.split(",") if part.strip()]
    return [str(value)]
