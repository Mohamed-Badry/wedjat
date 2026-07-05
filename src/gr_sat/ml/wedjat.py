"""
Minimal online wedjat runtime for deterministic packet-by-packet inference.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
import torch

from gr_sat.ml.ml_config import MODEL_DIR
from gr_sat.ml.model_artifacts import ModelArtifactMetadata, load_model_artifacts
from gr_sat.ml.vae import compute_anomaly_scores
from gr_sat.core.satellite_profiles import DEFAULT_PROFILE, get_satellite_profile
from gr_sat.core.telemetry import TelemetryFrame, process_frame_result

STATE_IDLE = "idle"
STATE_RECEIVING = "receiving"
STATE_GAP = "gap"
STATE_DEGRADED = "degraded"
STATE_ALERTING = "alerting"


@dataclass(frozen=True)
class WedjatAlert:
    norad_id: str
    timestamp: datetime
    score: float
    threshold: float
    source: str
    features: dict[str, float]


@dataclass(frozen=True)
class WedjatResult:
    status: str
    state: str
    score: float | None = None
    threshold: float | None = None
    is_anomaly: bool = False
    error: str | None = None
    failure_code: str | None = None
    frame: TelemetryFrame | None = None


class OnlineWedjat:
    def __init__(
        self,
        norad_id: str,
        scaler,
        model,
        metadata: ModelArtifactMetadata,
        gap_timeout_seconds: float = 180.0,
        alert_sink: Callable[[WedjatAlert], None] | None = None,
    ):
        self.norad_id = int(norad_id)
        self.scaler = scaler
        self.model = model
        self.metadata = metadata
        self.gap_timeout_seconds = float(gap_timeout_seconds)
        self.alert_sink = alert_sink
        self.state = STATE_IDLE
        self.last_packet_at: datetime | None = None
        try:
            self.profile = get_satellite_profile(self.norad_id)
        except KeyError:
            self.profile = DEFAULT_PROFILE
        self._pass_gap_seconds = self.profile.pass_gap_seconds
        self._rolling_window = self.profile.rolling_window
        self._recent_frames: deque[TelemetryFrame] = deque(maxlen=self._rolling_window)
        self._diagnosis_mask = [
            self.metadata.feature_names.index(f)
            for f in (self.metadata.diagnosis_feature_names or self.metadata.feature_names)
        ]
        self._score_history: deque[float] = deque(maxlen=5)

    @classmethod
    def from_artifacts(
        cls,
        norad_id: str,
        models_dir: Path = MODEL_DIR,
        gap_timeout_seconds: float = 180.0,
        alert_sink: Callable[[WedjatAlert], None] | None = None,
    ) -> "OnlineWedjat":
        scaler, model, metadata = load_model_artifacts(norad_id, models_dir)
        return cls(
            norad_id=norad_id,
            scaler=scaler,
            model=model,
            metadata=metadata,
            gap_timeout_seconds=gap_timeout_seconds,
            alert_sink=alert_sink,
        )

    def _rolling_std(self, field_name: str, frame: TelemetryFrame) -> float:
        values = [
            float(getattr(previous_frame, field_name))
            for previous_frame in self._recent_frames
            if getattr(previous_frame, field_name, None) is not None
        ]
        current_value = getattr(frame, field_name, None)
        if current_value is None or pd.isna(current_value):
            raise ValueError(f"Missing required feature '{field_name}' for inference.")
        values.append(float(current_value))
        if len(values) < 2:
            return 0.0
        return float(np.std(values, ddof=1))

    def _resolve_feature_value(self, frame: TelemetryFrame, feature_name: str) -> float:
        if hasattr(frame, feature_name):
            value = getattr(frame, feature_name)
            if value is None or pd.isna(value):
                raise ValueError(
                    f"Missing required feature '{feature_name}' for inference."
                )
            return float(value)

        if feature_name == "volt_rolling_std":
            return self._rolling_std("batt_voltage", frame)
        if feature_name == "temp_rolling_std":
            return self._rolling_std("temp_batt_a", frame)

        raise ValueError(f"Unsupported feature '{feature_name}' for online inference.")

    def _feature_vector(self, frame: TelemetryFrame) -> np.ndarray:
        values = []
        for feature_name in self.metadata.feature_names:
            values.append(self._resolve_feature_value(frame, feature_name))
        return np.asarray(values, dtype=float)

    def _score_frame(self, frame: TelemetryFrame) -> float:
        feature_vector = self._feature_vector(frame)
        scaled_vector = self.scaler.transform([feature_vector])
        x_tensor = torch.FloatTensor(scaled_vector)
        self.model.eval()
        with torch.no_grad():
            recon_x, mu, logvar = self.model(x_tensor)
            score_tensor = compute_anomaly_scores(
                recon_x,
                x_tensor,
                mu,
                logvar,
                kld_weight=self.metadata.kld_weight,
                diagnosis_mask=self._diagnosis_mask,
            )
        return float(score_tensor.item())

    def process_packet(
        self,
        payload: bytes,
        timestamp: datetime,
        source: str = "live_station",
    ) -> WedjatResult:
        self.last_packet_at = timestamp

        try:
            frame_result = process_frame_result(
                self.norad_id, payload, source, timestamp
            )
            if not frame_result.ok:
                self.state = STATE_RECEIVING
                return WedjatResult(
                    status=frame_result.failure.code,
                    state=self.state,
                    error=frame_result.failure.message,
                    failure_code=frame_result.failure.code,
                )

            frame = frame_result.frame
            if self._recent_frames:
                elapsed = (
                    timestamp - self._recent_frames[-1].timestamp
                ).total_seconds()
                if elapsed > self._pass_gap_seconds:
                    self._recent_frames.clear()
            raw_score = self._score_frame(frame)
            self._score_history.append(raw_score)
            
            # Use median score for robust thresholding
            if len(self._score_history) == self._score_history.maxlen:
                score = float(np.median(self._score_history))
            else:
                score = raw_score
                
            is_anomaly = score > self.metadata.threshold
            self.state = STATE_ALERTING if is_anomaly else STATE_RECEIVING
            self._recent_frames.append(frame)

            if is_anomaly and self.alert_sink is not None:
                self.alert_sink(
                    WedjatAlert(
                        norad_id=str(self.norad_id),
                        timestamp=timestamp,
                        score=score,
                        threshold=self.metadata.threshold,
                        source=source,
                        features={
                            feature_name: self._resolve_feature_value(
                                frame, feature_name
                            )
                            for feature_name in self.metadata.feature_names
                        },
                    )
                )

            return WedjatResult(
                status="ok",
                state=self.state,
                score=score,
                threshold=self.metadata.threshold,
                is_anomaly=is_anomaly,
                failure_code=None,
                frame=frame,
            )
        except Exception as exc:
            self.state = STATE_DEGRADED
            return WedjatResult(
                status="error",
                state=self.state,
                error=str(exc),
                failure_code="inference_error",
            )

    def check_gap(self, now: datetime) -> str:
        if self.last_packet_at is None:
            self.state = STATE_IDLE
            return self.state

        elapsed = (now - self.last_packet_at).total_seconds()
        if elapsed > self.gap_timeout_seconds:
            self.state = STATE_GAP
        elif self.state != STATE_DEGRADED:
            self.state = STATE_RECEIVING
        return self.state

    def status(self) -> dict:
        return {
            "norad_id": str(self.norad_id),
            "state": self.state,
            "last_packet_at": self.last_packet_at.isoformat()
            if self.last_packet_at
            else None,
            "threshold": self.metadata.threshold,
            "inference_mode": self.metadata.inference_mode,
            "feature_names": list(self.metadata.feature_names),
            "feature_contract_version": self.metadata.feature_contract_version,
            "rolling_window": self._rolling_window,
        }
