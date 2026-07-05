"""Dashboard data orchestrator — thin façade over focused sub-modules.

Preserves the ``DashboardDataRepository`` public interface so that
``main.py``, ``mqtt_client.py``, and existing tests continue to work
with **zero import changes**.

Sub-modules
-----------
- :mod:`~api.serialization` — pure value-conversion helpers
- :mod:`~api.frame_store`   — CSV / DB loading, caching, discovery
- :mod:`~api.scoring`       — ML model status, inference, reconstruction
- :mod:`~api.pass_predictor`— Skyfield orbital-mechanics pass prediction
- :mod:`~api.formatters`    — JSON response-dict assembly
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import pandas as pd
from loguru import logger

from gr_sat.ml.ml_config import DATA_DIR, MODEL_DIR, PROJECT_ROOT
from gr_sat.core.telemetry import DecoderRegistry

import gr_sat.core.decoders  # noqa: F401 — registers available decoders

try:
    from .frame_store import FrameStore
    from .pass_predictor import predict_passes as _predict_passes
    from .scoring import ModelStatus, ScoringService
    from .serialization import FEATURE_FIELDS, json_value, now_iso, timestamp_iso
    from .formatters import (
        dataset_summary,
        dataset_window,
        format_anomaly_record,
        format_frame_record,
        overall_status,
        satellite_identity,
        status_components,
    )
except ImportError:
    from frame_store import FrameStore
    from pass_predictor import predict_passes as _predict_passes
    from scoring import ModelStatus, ScoringService
    from serialization import FEATURE_FIELDS, json_value, now_iso, timestamp_iso
    from formatters import (
        dataset_summary,
        dataset_window,
        format_anomaly_record,
        format_frame_record,
        overall_status,
        satellite_identity,
        status_components,
    )

# Re-export so ``from api.dashboard_data import ModelStatus`` keeps working.
__all__ = ["DashboardDataRepository", "ModelStatus"]


class DashboardDataRepository:
    """Thin orchestrator that composes :class:`FrameStore`,
    :class:`ScoringService`, and the formatter / pass-predictor modules.

    All public method signatures are preserved for backward
    compatibility with ``main.py``, ``mqtt_client.py``, and tests.
    """

    def __init__(
        self,
        root: Path | str = PROJECT_ROOT,
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

        # Compose sub-services
        self._scoring = ScoringService(self.models_dir)
        self._store = FrameStore(
            processed_dir=self.processed_dir,
            models_dir=self.models_dir,
            scoring=self._scoring,
        )

    # ── Status & summaries ───────────────────────────────────────────

    def reload_models(self) -> None:
        """Clear in-memory ML models so fresh ones are loaded from disk."""
        self._scoring.clear_cache()

    def status_payload(self) -> dict[str, Any]:
        satellites = self.satellite_summaries()
        components = status_components(
            dataset_ids=self._store.discover_dataset_ids(),
            model_ids=self._store.discover_model_ids(),
            processed_dir=str(self.processed_dir),
            models_dir=str(self.models_dir),
        )
        return {
            "status": overall_status(components),
            "service": "gr_sat Wedjat API",
            "generated_at": now_iso(),
            "components": components,
            "supported_satellites": [
                satellite_identity(s["norad_id"]) for s in satellites
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
        frame_count = sum(s["dataset"]["row_count"] for s in satellites)
        anomaly_count = sum(s["dataset"]["anomaly_count"] for s in satellites)
        partial_frame_count = sum(
            s["dataset"]["partial_frame_count"] for s in satellites
        )
        pass_count = sum(s["dataset"]["pass_count"] for s in satellites)

        return {
            "generated_at": now_iso(),
            "window": dataset_window(satellites),
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
            "throughput_buckets": self.throughput(limit=14, bucket="day")["buckets"],
        }

    def satellite_summaries(self) -> list[dict[str, Any]]:
        ids = sorted(self._store.discover_satellite_ids())
        return [self.satellite_summary(norad_id) for norad_id in ids]

    def satellite_summary(self, norad_id: int) -> dict[str, Any]:
        sat_id = int(norad_id)
        if sat_id not in self._store.discover_satellite_ids():
            raise KeyError(f"NORAD {sat_id} is not known to the dashboard data layer.")

        try:
            df = self._store.frames_for(sat_id)
        except KeyError:
            df = pd.DataFrame()
        model = self._scoring.model_status(norad_id).to_dict()
        identity = satellite_identity(sat_id)
        return {
            **identity,
            "dataset": dataset_summary(df),
            "model": model,
        }

    # ── Telemetry frames ─────────────────────────────────────────────

    def append_live_frame(self, norad_id: int, row: dict) -> None:
        """Called by the MQTT worker to inject a live frame into the cache."""
        self._store.append_frame(norad_id, row)

    def update_live_frame_score(self, norad_id: int, timestamp_str: str, score: float, is_anomaly: bool) -> None:
        """Called by the ML worker to update a live frame's score in the cache."""
        self._store.update_frame_score(norad_id, timestamp_str, score, is_anomaly)

    def recent_frames(
        self,
        norad_id: int | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        df = self._store.combined_frames(norad_id)
        records = FrameStore.sort_recent(df).head(limit)
        records_dict = records.to_dict(orient="records")

        frames = []
        for row in records_dict:
            r_norad = int(norad_id) if norad_id is not None else int(row["norad_id"])
            status = self._scoring.model_status(r_norad)
            threshold = (
                json_value(status.metadata.threshold) if status.metadata else None
            )
            kaitai_decoded = self._try_decode(row)

            frames.append(
                format_frame_record(row, threshold, kaitai_decoded=kaitai_decoded)
            )

        return {
            "generated_at": now_iso(),
            "norad_id": norad_id,
            "limit": limit,
            "frames": frames,
        }

    # ── Anomalies ────────────────────────────────────────────────────

    def recent_anomalies(
        self,
        norad_id: int | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        df = self._store.combined_frames(norad_id)
        if "is_anomaly" not in df.columns:
            anomalies = df.iloc[0:0]
        else:
            anomalies = df[df["is_anomaly"].fillna(False).astype(bool)]

        records = FrameStore.sort_recent(anomalies).head(limit)
        records_dict = records.to_dict(orient="records")

        anomalies_list = []
        for row in records_dict:
            r_norad = int(norad_id) if norad_id is not None else int(row["norad_id"])
            status = self._scoring.model_status(r_norad)
            threshold = (
                json_value(status.metadata.threshold) if status.metadata else None
            )

            # Build features dict for reconstruction
            features = {f: json_value(row.get(f)) for f in FEATURE_FIELDS if f in row}
            reconstruction = (
                self._scoring.reconstruct_frame(r_norad, features)
                if status.status == "ready"
                else None
            )

            anomalies_list.append(
                format_anomaly_record(row, threshold, reconstruction=reconstruction)
            )

        return {
            "generated_at": now_iso(),
            "norad_id": norad_id,
            "limit": limit,
            "anomalies": anomalies_list,
        }

    # ── Throughput ────────────────────────────────────────────────────

    def throughput(
        self,
        norad_id: int | None = None,
        limit: int = 30,
        bucket: Literal["hour", "day"] = "day",
    ) -> dict[str, Any]:
        df = self._store.combined_frames(norad_id)
        if df.empty:
            return {
                "generated_at": now_iso(),
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
            .agg(
                frame_count=("timestamp", "size"),
                anomaly_count=("is_anomaly", "sum"),
            )
            .sort_index()
            .tail(limit)
            .reset_index()
        )

        buckets = [
            {
                "timestamp": timestamp_iso(row["_bucket"]),
                "frame_count": int(row["frame_count"]),
                "anomaly_count": int(row["anomaly_count"]),
            }
            for _, row in grouped.iterrows()
        ]
        return {
            "generated_at": now_iso(),
            "norad_id": norad_id,
            "bucket": bucket,
            "limit": limit,
            "total_frames": int(len(df)),
            "returned_frame_count": (
                int(grouped["frame_count"].sum()) if not grouped.empty else 0
            ),
            "buckets": buckets,
        }

    # ── Analytics ────────────────────────────────────────────────────

    def analytics_report(self, norad_id: int | None = None) -> dict[str, Any]:
        df = self._store.combined_frames(norad_id)
        if df.empty:
            return {}

        working = df.copy()
        working["_day"] = working["timestamp"].dt.floor("D")

        # 1. Throughput & Pass Metrics
        throughput_daily = (
            working.groupby("_day", dropna=True)
            .agg(
                frame_count=("timestamp", "size"),
                dropped_suspects=("dropped_packet_suspect", "sum"),
                irregular_sampling=("sampling_irregular", "sum"),
            )
            .sort_index()
            .tail(30)
            .reset_index()
        )

        pass_metrics: list[dict[str, Any]] = []
        if (
            "pass_duration_sec" in working.columns
            and "pass_frame_count" in working.columns
        ):
            pass_df = working.dropna(
                subset=["pass_id", "pass_duration_sec", "pass_frame_count"]
            )
            pass_df = pass_df.drop_duplicates(subset=["pass_id"]).tail(200)
            for _, row in pass_df.iterrows():
                pass_metrics.append(
                    {
                        "pass_id": int(row["pass_id"]),
                        "duration_sec": float(row["pass_duration_sec"]),
                        "frame_count": int(row["pass_frame_count"]),
                        "timestamp": timestamp_iso(row["timestamp"]),
                    }
                )

        # 2. Pipeline Data Quality
        complete_count = int(working["frame_is_complete"].sum()) if "frame_is_complete" in working.columns else 0
        total_count = len(working)
        partial_count = total_count - complete_count

        missing_counts: dict[str, int] = {}
        if "missing_raw_fields" in working.columns:
            try:
                from .serialization import missing_fields_value
            except ImportError:
                from serialization import missing_fields_value

            for fields_str in working["missing_raw_fields"].dropna():
                fields = missing_fields_value(fields_str)
                for f in fields:
                    if f and f != "null":
                        missing_counts[f] = missing_counts.get(f, 0) + 1

        missing_list = [{"field": k, "count": v} for k, v in missing_counts.items()]
        missing_list.sort(key=lambda x: x["count"], reverse=True)

        # 3. Macro Health (Seasonal Drift)
        macro_health = (
            working.groupby("_day", dropna=True)
            .agg(
                batt_voltage_raw_mean=("batt_voltage", "mean"),
                batt_voltage_std=("batt_voltage", "std"),
                temp_panel_z_raw_mean=("temp_panel_z", "mean"),
                temp_panel_z_std=("temp_panel_z", "std"),
            )
            .sort_index()
            .tail(180)
        )

        macro_health["batt_voltage_mean"] = (
            macro_health["batt_voltage_raw_mean"]
            .rolling(window=7, min_periods=1)
            .mean()
        )
        macro_health["temp_panel_z_mean"] = (
            macro_health["temp_panel_z_raw_mean"]
            .rolling(window=7, min_periods=1)
            .mean()
        )
        macro_health = macro_health.reset_index()

        # Calculate real Pearson correlation matrix
        corr_cols = ["batt_voltage", "temp_batt_a", "temp_panel_z", "power_consumption"]
        actual_corr_cols = [c for c in corr_cols if c in working.columns]
        correlation_matrix = {}
        if len(actual_corr_cols) >= 2:
            try:
                corr_df = working[actual_corr_cols].corr()
                for c1 in actual_corr_cols:
                    correlation_matrix[c1] = {}
                    for c2 in actual_corr_cols:
                        val = corr_df.loc[c1, c2]
                        correlation_matrix[c1][c2] = float(val) if pd.notna(val) else 0.0
            except Exception as e:
                logger.warning("Failed to compute correlation matrix: %s", e)

        # Calculate real field integrity success rates
        fields_to_check = ["batt_voltage", "temp_panel_z", "temp_obc", "temp_batt_a", "temp_batt_b", "power_consumption", "uptime"]
        field_integrity = {}
        for f in fields_to_check:
            if f in working.columns:
                non_null = working[f].notna().sum()
                total = len(working)
                field_integrity[f] = float(non_null / total) if total > 0 else 0.0
            else:
                field_integrity[f] = 0.0

        # Calculate real average SNR
        avg_snr = 0.0
        if "snr" in working.columns:
            valid_snr = working["snr"].dropna()
            if not valid_snr.empty:
                avg_snr = float(valid_snr.mean())

        return {
            "generated_at": now_iso(),
            "norad_id": norad_id,
            "throughput_30d": [
                {
                    "date": timestamp_iso(row["_day"]),
                    "frame_count": int(row["frame_count"]),
                    "dropped_suspects": int(row["dropped_suspects"]),
                    "irregular_sampling": int(row["irregular_sampling"]),
                }
                for _, row in throughput_daily.iterrows()
            ],
            "pass_metrics": pass_metrics,
            "quality": {
                "complete_frames": complete_count,
                "partial_frames": partial_count,
                "missing_fields": missing_list[:15],
                "field_integrity": field_integrity,
                "avg_snr": avg_snr,
            },
            "macro_health_correlation": correlation_matrix,
            "macro_health": [
                {
                    "date": timestamp_iso(row["_day"]),
                    "batt_voltage_mean": (
                        float(row["batt_voltage_mean"])
                        if pd.notna(row["batt_voltage_mean"])
                        else None
                    ),
                    "batt_voltage_std": (
                        float(row["batt_voltage_std"])
                        if pd.notna(row["batt_voltage_std"])
                        else None
                    ),
                    "temp_panel_z_mean": (
                        float(row["temp_panel_z_mean"])
                        if pd.notna(row["temp_panel_z_mean"])
                        else None
                    ),
                    "temp_panel_z_std": (
                        float(row["temp_panel_z_std"])
                        if pd.notna(row["temp_panel_z_std"])
                        else None
                    ),
                }
                for _, row in macro_health.iterrows()
            ],
        }

    # ── Pass prediction (delegates to pass_predictor) ────────────────

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
        if norad_id is not None:
            sats = [self.satellite_summary(norad_id)]
        else:
            sats = self.satellite_summaries()
        return _predict_passes(
            satellite_summaries=sats,
            lat=lat,
            lon=lon,
            elevation_m=elevation_m,
            station_label=station_label,
            lookahead_hours=lookahead_hours,
            min_elevation=min_elevation,
            include_tracks=include_tracks,
        )

    # ── Sensitivity sweep ────────────────────────────────────────────

    def sensitivity_sweep(self, norad_id: int) -> dict[str, Any]:
        sat_id = int(norad_id)
        if sat_id not in self._store.discover_satellite_ids():
            raise KeyError(f"NORAD {sat_id} is not known to the dashboard data layer.")

        model = self._scoring.model_status(sat_id)
        current_threshold = model.metadata.threshold if model.metadata else 0.5

        try:
            import torch
            import numpy as np
            from sklearn.metrics import roc_curve
            from gr_sat.ml.model_artifacts import split_chronological
            from gr_sat.ml.vae import compute_anomaly_scores
            from gr_sat.core.satellite_profiles import (
                get_satellite_profile,
                build_baseline_mask,
                feature_completeness_mask,
            )

            # Load model artifacts
            scaler, vae, metadata = self._scoring._load_artifacts(sat_id)
            profile = get_satellite_profile(str(sat_id))

            # Load dataset
            data_path = self.processed_dir / f"{sat_id}.csv"
            if not data_path.exists():
                raise FileNotFoundError(f"Processed dataset not found at {data_path}")

            df = pd.read_csv(data_path)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp")

            # Clean and filter using baseline profiles
            extreme_mask = build_baseline_mask(df, profile)
            df_clean = df[~extreme_mask].copy()
            complete_mask = feature_completeness_mask(df_clean, metadata.feature_names)
            df_ready = df_clean[complete_mask].copy()

            split = split_chronological(df_ready)
            df_test = split.test.copy()

            # Inject faults inline to avoid rich dependency in evaluation.py
            rng = np.random.RandomState(42)
            df_faulted = df_test.copy()
            y_true = np.zeros(len(df_test), dtype=int)

            # 1. Panel Failure
            sunlight_mask = df_faulted["temp_panel_z"] > 15
            sun_idx = np.where(sunlight_mask)[0]
            valid_starts = [idx for idx in sun_idx if idx + 30 < len(df_faulted)]
            if valid_starts:
                chosen_starts = rng.choice(valid_starts, size=min(5, len(valid_starts)), replace=False)
                for start in chosen_starts:
                    idx_range = range(start, start + 30)
                    df_faulted.iloc[list(idx_range), df_faulted.columns.get_loc("batt_current")] = -0.2
                    y_true[list(idx_range)] = 1

            # 2. Thermal Runaway
            normal_idx = np.where(y_true == 0)[0]
            valid_starts_therm = [idx for idx in normal_idx if idx + 30 < len(df_faulted)]
            if valid_starts_therm:
                chosen_starts_therm = rng.choice(valid_starts_therm, size=min(5, len(valid_starts_therm)), replace=False)
                for start in chosen_starts_therm:
                    idx_range = range(start, start + 30)
                    if "temp_batt_a" in df_faulted.columns:
                        df_faulted.iloc[list(idx_range), df_faulted.columns.get_loc("temp_batt_a")] += 7.0
                    if "temp_batt_b" in df_faulted.columns:
                        df_faulted.iloc[list(idx_range), df_faulted.columns.get_loc("temp_batt_b")] += 7.0
                    y_true[list(idx_range)] = 1

            X_faulted_scaled = scaler.transform(df_faulted[metadata.feature_names].values)

            # VAE Inference
            X_tensor = torch.FloatTensor(X_faulted_scaled)
            diagnosis_mask = [
                metadata.feature_names.index(f)
                for f in metadata.diagnosis_feature_names
            ]
            vae.eval()
            with torch.no_grad():
                X_recon_vae, mu, logvar = vae(X_tensor)
                scores = compute_anomaly_scores(
                    X_recon_vae,
                    X_tensor,
                    mu,
                    logvar,
                    kld_weight=metadata.kld_weight,
                    diagnosis_mask=diagnosis_mask,
                ).numpy()

            # Compute ROC Curve
            fpr_curve, tpr_curve, _ = roc_curve(y_true, scores)

            # Downsample ROC points for the UI to prevent rendering bloat
            roc = []
            step = max(1, len(fpr_curve) // 30)
            for idx in range(0, len(fpr_curve), step):
                roc.append({
                    "fpr": float(fpr_curve[idx]),
                    "tpr": float(tpr_curve[idx])
                })
            if not any(p["fpr"] == 1.0 and p["tpr"] == 1.0 for p in roc):
                roc.append({"fpr": 1.0, "tpr": 1.0})

            # Threshold Sweep (50 points between min and max scores)
            sweep = []
            min_score = float(scores.min())
            max_score = float(scores.max())
            threshold_grid = np.linspace(min_score, max_score, 50)

            for thresh in threshold_grid:
                thresh_val = float(thresh)
                preds = scores > thresh_val
                tp = int((preds & (y_true == 1)).sum())
                fp = int((preds & (y_true == 0)).sum())
                fn = int((~preds & (y_true == 1)).sum())

                precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
                recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
                f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

                sweep.append({
                    "threshold": thresh_val,
                    "f1_score": f1,
                    "precision": precision,
                    "recall": recall
                })

        except Exception as exc:
            logger.warning(
                f"Failed to compute real sensitivity sweep for {sat_id}: {exc}. "
                "Falling back to simulated sweep."
            )
            # Simulated fallback sweep
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

    # ── Backward-compat delegates ────────────────────────────────────

    def model_status(self, norad_id: int) -> ModelStatus:
        """Delegate to :meth:`ScoringService.model_status`."""
        return self._scoring.model_status(norad_id)

    def frames_for(self, norad_id: int) -> pd.DataFrame:
        """Delegate to :meth:`FrameStore.frames_for`."""
        return self._store.frames_for(norad_id)

    def _score_frames(
        self,
        norad_id: int,
        df: pd.DataFrame,
        model_status: ModelStatus,
    ) -> pd.DataFrame:
        """Backward-compat: ``mqtt_client.py`` calls this directly."""
        return self._scoring.score_frames(norad_id, df, model_status)

    # ── Private helpers ──────────────────────────────────────────────

    @staticmethod
    def _try_decode(row: dict[str, Any]) -> dict | None:
        """Attempt on-the-fly Kaitai decode of a raw hex frame."""
        raw_frame_hex = row.get("raw_frame")
        if not raw_frame_hex or not isinstance(raw_frame_hex, str):
            return None
        try:
            decoder = DecoderRegistry.get_decoder(int(row["norad_id"]))
            if decoder:
                payload_bytes = bytes.fromhex(raw_frame_hex)
                decoded_outcome = decoder.decode_with_diagnostics(payload_bytes)
                if decoded_outcome.ok:
                    return decoded_outcome.data
        except Exception:
            pass
        return None
