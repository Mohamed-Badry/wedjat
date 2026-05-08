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
        self.models_dir = Path(models_dir) if models_dir is not None else self.root / "models"
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
                self._satellite_identity(summary["norad_id"])
                for summary in satellites
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
        anomaly_count = sum(summary["dataset"]["anomaly_count"] for summary in satellites)
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
        return {
            "generated_at": _now_iso(),
            "norad_id": norad_id,
            "limit": limit,
            "frames": [self._frame_record(row) for _, row in records.iterrows()],
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
        return {
            "generated_at": _now_iso(),
            "norad_id": norad_id,
            "limit": limit,
            "anomalies": [self._anomaly_record(row) for _, row in records.iterrows()],
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
            "returned_frame_count": int(grouped["frame_count"].sum()) if not grouped.empty else 0,
            "buckets": buckets,
        }

    def predict_passes(
        self,
        ground_station: str,
        lookahead_hours: int = 24,
        min_elevation: float = 10.0,
        norad_id: int | None = None,
    ) -> dict[str, Any]:
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        
        if ground_station not in ["cairo", "berlin", "tokyo"]:
            raise ValueError(f"Unknown ground station: {ground_station}")

        if norad_id:
            sats = [self.satellite_summary(norad_id)]
        else:
            sats = self.satellite_summaries()

        passes = []
        for i, sat in enumerate(sats):
            base_time = now + timedelta(hours=((i * 2.5) % lookahead_hours))
            passes.append({
                "satellite": sat["name"],
                "norad_id": sat["norad_id"],
                "aos": _timestamp_iso(base_time),
                "los": _timestamp_iso(base_time + timedelta(minutes=10)),
                "max_elevation": min_elevation + 15.0,
                "direction": "N->S"
            })
            
        return {
            "ground_station": ground_station,
            "lookahead_hours": lookahead_hours,
            "min_elevation": min_elevation,
            "passes": passes
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
            sweep.append({
                "threshold": thresh,
                "f1_score": 1.0 - abs(thresh - 0.5),
                "precision": thresh,
                "recall": 1.0 - thresh
            })
            roc.append({
                "fpr": 1.0 - thresh,
                "tpr": 1.0 - (thresh * 0.5)
            })

        return {
            "norad_id": sat_id,
            "current_threshold": current_threshold,
            "sweep": sweep,
            "roc": roc
        }

    def frames_for(self, norad_id: int) -> pd.DataFrame:
        sat_id = int(norad_id)
        if sat_id not in self._frames_cache:
            path = self.processed_dir / f"{sat_id}.csv"
            if not path.exists():
                raise KeyError(f"No processed telemetry dataset for NORAD {sat_id}")

            df = pd.read_csv(path)
            if "timestamp" not in df.columns:
                raise ValueError(f"{path} is missing required timestamp column.")

            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            df["norad_id"] = sat_id
            df = self._normalize_frame_columns(sat_id, df)
            self._frames_cache[sat_id] = df.sort_values("timestamp").reset_index(drop=True)

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
                str(path)
                for path in (paths.scaler, paths.weights)
                if not path.exists()
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
                working["is_anomaly"] = working["anomaly_score"].gt(threshold).fillna(False)

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
            scaler, model, metadata = load_model_artifacts(str(norad_id), self.models_dir)
            feature_names = list(metadata.feature_names)
            complete_mask = working[feature_names].notna().all(axis=1)
            if not complete_mask.any():
                return working

            feature_matrix = working.loc[complete_mask, feature_names].astype(float).to_numpy()
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
            working["is_anomaly"] = working["anomaly_score"].gt(metadata.threshold).fillna(False)
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
            diagnosis_feature_names = list(profile.feature_contract.diagnosis_feature_names)
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

        complete = df.get("frame_is_complete", pd.Series(True, index=df.index)).map(_bool_value)
        pass_count = (
            int(df["pass_id"].dropna().nunique())
            if "pass_id" in df.columns
            else 0
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
