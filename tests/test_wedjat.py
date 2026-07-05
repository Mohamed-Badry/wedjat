import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from datetime import datetime, timedelta, timezone

import joblib
import numpy as np
from sklearn.preprocessing import StandardScaler
import torch

from gr_sat.core.satellite_profiles import DEFAULT_PROFILE
ALL_FEATURES = list(DEFAULT_PROFILE.feature_contract.feature_names)
from gr_sat.ml.model_artifacts import ModelArtifactMetadata, model_artifact_paths, save_model_metadata
from gr_sat.ml.vae import TelemetryVAE
from gr_sat.core.telemetry import FrameProcessingResult, TelemetryFrame
from gr_sat.ml.wedjat import (
    OnlineWedjat,
    STATE_ALERTING,
    STATE_DEGRADED,
    STATE_GAP,
    STATE_IDLE,
    STATE_RECEIVING,
)

_DEFAULT_PANEL_TEMP = object()


def _build_frame(
    timestamp: datetime,
    feature_value: float,
    temp_panel_z: float | None | object = _DEFAULT_PANEL_TEMP,
) -> TelemetryFrame:
    return TelemetryFrame(
        timestamp=timestamp,
        norad_id=43880,
        source="live_station",
        batt_a_voltage=feature_value,
        batt_b_voltage=feature_value,
        batt_a_current=feature_value,
        batt_b_current=feature_value,
        batt_voltage=feature_value,
        batt_current=feature_value,
        power_consumption=feature_value,
        temp_obc=feature_value,
        temp_batt_a=feature_value,
        temp_batt_b=feature_value,
        temp_panel_z=feature_value if temp_panel_z is _DEFAULT_PANEL_TEMP else temp_panel_z,
        uptime=1,
    )


class OnlineWedjatTests(unittest.TestCase):
    def _build_wedjat(self, threshold: float = 1.0):
        tmpdir = tempfile.TemporaryDirectory()
        models_dir = Path(tmpdir.name)
        paths = model_artifact_paths(models_dir, "43880")
        n_features = len(ALL_FEATURES)

        scaler = StandardScaler().fit(np.array([[-1.0] * n_features, [1.0] * n_features]))
        joblib.dump(scaler, paths.scaler)

        model = TelemetryVAE(input_dim=n_features, hidden_dim=4, latent_dim=2)
        for parameter in model.parameters():
            parameter.data.zero_()
        torch.save(model.state_dict(), paths.weights)

        metadata = ModelArtifactMetadata(
            version=1,
            norad_id="43880",
            feature_names=list(ALL_FEATURES),
            hidden_dim=4,
            latent_dim=2,
            kld_weight=0.05,
            threshold=threshold,
            threshold_percentile=95.0,
            inference_mode="deterministic",
            train_rows=8,
            validation_rows=1,
            test_rows=1,
            train_start=None,
            train_end=None,
            validation_start=None,
            validation_end=None,
            test_start=None,
            test_end=None,
            feature_contract_version=3,
            diagnosis_feature_names=list(ALL_FEATURES),
        )
        save_model_metadata(paths.metadata, metadata)
        return tmpdir, OnlineWedjat.from_artifacts("43880", models_dir=models_dir, gap_timeout_seconds=60)

    def test_wedjat_starts_idle_and_transitions_to_receiving(self):
        tmpdir, wedjat = self._build_wedjat(threshold=1.0)
        self.addCleanup(tmpdir.cleanup)

        packet_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
        with patch(
            "gr_sat.ml.wedjat.process_frame_result",
            return_value=FrameProcessingResult(frame=_build_frame(packet_time, 0.0)),
        ):
            result = wedjat.process_packet(b"\x00", packet_time)

        self.assertEqual(wedjat.state, STATE_RECEIVING)
        self.assertEqual(result.status, "ok")
        self.assertFalse(result.is_anomaly)
        self.assertEqual(result.state, STATE_RECEIVING)

    def test_wedjat_alerts_on_high_score(self):
        tmpdir, wedjat = self._build_wedjat(threshold=1.0)
        self.addCleanup(tmpdir.cleanup)

        alerts = []
        wedjat.alert_sink = alerts.append
        packet_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
        with patch(
            "gr_sat.ml.wedjat.process_frame_result",
            return_value=FrameProcessingResult(frame=_build_frame(packet_time, 2.0)),
        ):
            result = wedjat.process_packet(b"\x00", packet_time)

        self.assertEqual(result.state, STATE_ALERTING)
        self.assertTrue(result.is_anomaly)
        self.assertEqual(len(alerts), 1)

    def test_wedjat_reports_gap_after_timeout(self):
        tmpdir, wedjat = self._build_wedjat(threshold=1.0)
        self.addCleanup(tmpdir.cleanup)

        packet_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
        with patch(
            "gr_sat.ml.wedjat.process_frame_result",
            return_value=FrameProcessingResult(frame=_build_frame(packet_time, 0.0)),
        ):
            wedjat.process_packet(b"\x00", packet_time)

        state = wedjat.check_gap(packet_time + timedelta(seconds=61))
        self.assertEqual(state, STATE_GAP)

    def test_wedjat_enters_degraded_state_on_inference_error(self):
        tmpdir, wedjat = self._build_wedjat(threshold=1.0)
        self.addCleanup(tmpdir.cleanup)

        packet_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
        broken_frame = _build_frame(packet_time, 0.0, temp_panel_z=None)
        with patch(
            "gr_sat.ml.wedjat.process_frame_result",
            return_value=FrameProcessingResult(frame=broken_frame),
        ):
            result = wedjat.process_packet(b"\x00", packet_time)

        self.assertEqual(result.state, STATE_DEGRADED)
        self.assertEqual(result.status, "error")
        self.assertIn("Missing required feature", result.error)
        self.assertEqual(result.failure_code, "inference_error")

    def test_wedjat_reports_idle_before_any_packets(self):
        tmpdir, wedjat = self._build_wedjat(threshold=1.0)
        self.addCleanup(tmpdir.cleanup)

        self.assertEqual(wedjat.check_gap(datetime(2026, 1, 1, tzinfo=timezone.utc)), STATE_IDLE)

    def test_wedjat_tracks_feature_contract_metadata(self):
        tmpdir, wedjat = self._build_wedjat(threshold=1.0)
        self.addCleanup(tmpdir.cleanup)

        status = wedjat.status()

        self.assertEqual(status["feature_contract_version"], 3)
        self.assertIn("batt_voltage", status["feature_names"])
        self.assertNotIn("volt_rolling_std", status["feature_names"])


if __name__ == "__main__":
    unittest.main()
