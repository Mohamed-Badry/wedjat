"""Response-dict formatters for the dashboard API.

Pure functions that convert internal data structures (DataFrames, rows,
ModelStatus, etc.) into the JSON-serialisable dicts that FastAPI returns.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from gr_sat.core.satellite_profiles import get_satellite_profile
from gr_sat.core.telemetry import DecoderRegistry

try:
    from .serialization import (
        FEATURE_FIELDS,
        QUALITY_FIELDS,
        bool_value,
        json_value,
        missing_fields_value,
        timestamp_iso,
    )
except ImportError:
    from serialization import (
        FEATURE_FIELDS,
        QUALITY_FIELDS,
        bool_value,
        json_value,
        missing_fields_value,
        timestamp_iso,
    )


# ── Identity & dataset helpers ───────────────────────────────────────


def satellite_identity(norad_id: int) -> dict[str, Any]:
    """Build the satellite identity dict from profiles and decoder registry."""
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


def dataset_summary(df: pd.DataFrame) -> dict[str, Any]:
    """Compute high-level statistics for a telemetry DataFrame."""
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
        bool_value
    )
    pass_count = int(df["pass_id"].dropna().nunique()) if "pass_id" in df.columns else 0
    return {
        "status": "available",
        "row_count": int(len(df)),
        "anomaly_count": int(df["is_anomaly"].fillna(False).astype(bool).sum()),
        "complete_frame_count": int(complete.fillna(False).sum()),
        "partial_frame_count": int((~complete.fillna(False)).sum()),
        "pass_count": pass_count,
        "start": timestamp_iso(df["timestamp"].min()),
        "end": timestamp_iso(df["timestamp"].max()),
        "latest_timestamp": timestamp_iso(df["timestamp"].max()),
    }


def dataset_window(satellites: list[dict[str, Any]]) -> dict[str, Any]:
    """Derive the overall time window across all satellite datasets."""
    starts = [
        s["dataset"]["start"] for s in satellites if s["dataset"]["start"] is not None
    ]
    ends = [s["dataset"]["end"] for s in satellites if s["dataset"]["end"] is not None]
    return {
        "label": "historical_processed_dataset",
        "start": min(starts) if starts else None,
        "end": max(ends) if ends else None,
    }


# ── Frame / anomaly record formatting ───────────────────────────────


def format_frame_record(
    row: dict[str, Any],
    threshold: float | None,
    *,
    kaitai_decoded: dict | None = None,
) -> dict[str, Any]:
    """Build a JSON-ready dict for a single telemetry frame."""
    features = {
        field: json_value(row.get(field)) for field in FEATURE_FIELDS if field in row
    }
    quality = {
        field: json_value(row.get(field)) for field in QUALITY_FIELDS if field in row
    }
    if "missing_raw_fields" in quality:
        quality["missing_raw_fields"] = missing_fields_value(
            quality["missing_raw_fields"]
        )

    raw_frame_hex = json_value(row.get("raw_frame"))

    return {
        "timestamp": timestamp_iso(row["timestamp"]),
        "norad_id": int(row["norad_id"]),
        "source": "historical_processed_csv",
        "raw_frame": raw_frame_hex,
        "kaitai_decoded": kaitai_decoded,
        "features": features,
        "quality": quality,
        "model": {
            "anomaly_score": json_value(row.get("anomaly_score")),
            "threshold": threshold,
            "is_anomaly": bool(bool_value(row.get("is_anomaly"))),
        },
    }


def format_anomaly_record(
    row: dict[str, Any],
    threshold: float | None,
    reconstruction: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a JSON-ready dict for a single anomaly event."""
    features = {
        field: json_value(row.get(field)) for field in FEATURE_FIELDS if field in row
    }
    quality = {
        field: json_value(row.get(field)) for field in QUALITY_FIELDS if field in row
    }
    if "missing_raw_fields" in quality:
        quality["missing_raw_fields"] = missing_fields_value(
            quality["missing_raw_fields"]
        )

    record: dict[str, Any] = {
        "timestamp": timestamp_iso(row["timestamp"]),
        "norad_id": int(row["norad_id"]),
        "score": json_value(row.get("anomaly_score")),
        "threshold": threshold,
        "features": features,
        "quality": quality,
    }

    if reconstruction is not None:
        record.update(
            {
                "reconstructed_features": reconstruction.get("reconstructed_features"),
                "scaled_features": reconstruction.get("scaled_features"),
                "scaled_reconstructed_features": reconstruction.get(
                    "scaled_reconstructed_features"
                ),
                "feature_contributions": reconstruction.get("feature_contributions"),
            }
        )
    else:
        record.update(
            {
                "reconstructed_features": None,
                "scaled_features": None,
                "scaled_reconstructed_features": None,
                "feature_contributions": None,
            }
        )

    return record


# ── Status components ────────────────────────────────────────────────


def status_components(
    dataset_ids: set[int],
    model_ids: set[int],
    processed_dir: str,
    models_dir: str,
) -> list[dict[str, Any]]:
    """Build the list of component-health dicts for ``/api/status``."""
    try:
        from .database import database_status
    except ImportError:
        from database import database_status  # type: ignore[no-redef]

    return [
        {
            "name": "api",
            "status": "online",
            "detail": "FastAPI process is responding.",
            "metadata": {"title": "gr_sat Wedjat API"},
        },
        database_status(),
        _processed_data_component(dataset_ids, processed_dir),
        _model_artifacts_component(model_ids, models_dir),
    ]


def overall_status(components: list[dict[str, Any]]) -> str:
    """Derive a top-level status string from a list of component dicts."""
    severe = {"error", "offline"}
    if any(c["status"] in severe for c in components):
        return "degraded"
    return "online"


# ── Private helpers ──────────────────────────────────────────────────


def _processed_data_component(
    dataset_ids: set[int], processed_dir: str
) -> dict[str, Any]:
    status = "online" if dataset_ids else "degraded"
    return {
        "name": "processed_data",
        "status": status,
        "detail": f"{len(dataset_ids)} processed satellite dataset(s) available.",
        "metadata": {
            "processed_dir": processed_dir,
            "satellite_ids": sorted(dataset_ids),
        },
    }


def _model_artifacts_component(model_ids: set[int], models_dir: str) -> dict[str, Any]:
    status = "online" if model_ids else "degraded"
    return {
        "name": "model_artifacts",
        "status": status,
        "detail": f"{len(model_ids)} model metadata artifact(s) available.",
        "metadata": {
            "models_dir": models_dir,
            "satellite_ids": sorted(model_ids),
        },
    }
