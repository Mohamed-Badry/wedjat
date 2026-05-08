import tempfile
import unittest
from pathlib import Path

import httpx
import pandas as pd

from api.dashboard_data import DashboardDataRepository
from api.main import create_app
from gr_sat.model_artifacts import ModelArtifactMetadata, model_artifact_paths, save_model_metadata

class MlApiTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.processed_dir = self.root / "data" / "processed"
        self.models_dir = self.root / "models"
        self.processed_dir.mkdir(parents=True)
        self.models_dir.mkdir(parents=True)

        pd.DataFrame([
            {"timestamp": "2026-01-01T00:00:00Z", "anomaly_score": 0.10, "is_anomaly": False},
            {"timestamp": "2026-01-01T00:01:00Z", "anomaly_score": 0.40, "is_anomaly": True},
        ]).to_csv(self.processed_dir / "43880.csv", index=False)

        metadata = ModelArtifactMetadata(
            version=2,
            norad_id="43880",
            feature_names=["batt_voltage"],
            hidden_dim=12,
            latent_dim=3,
            kld_weight=0.05,
            threshold=0.30,
            threshold_percentile=95.0,
            inference_mode="deterministic",
            train_rows=10,
            validation_rows=2,
            test_rows=2,
            train_start="2026-01-01T00:00:00+00:00",
            train_end="2026-01-01T00:01:00+00:00",
            validation_start="2026-01-02T00:00:00+00:00",
            validation_end="2026-01-02T00:00:00+00:00",
            test_start="2026-01-02T00:02:00+00:00",
            test_end="2026-01-02T00:02:00+00:00",
            feature_contract_version=3,
            diagnosis_feature_names=["batt_voltage"],
        )
        save_model_metadata(model_artifact_paths(self.models_dir, "43880").metadata, metadata)

        repository = DashboardDataRepository(root=self.root)
        self.app = create_app(repository)

    def tearDown(self):
        self.tmpdir.cleanup()

    async def _get(self, path: str, params: dict | None = None):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(path, params=params)

    async def test_sensitivity_sweep_returns_curve_data(self):
        response = await self._get("/api/ml/sensitivity", params={"norad_id": 43880})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        
        self.assertIn("sweep", payload)
        self.assertIn("roc", payload)
        self.assertIn("current_threshold", payload)
        
        # Verify sweep points
        sweep = payload["sweep"]
        self.assertTrue(len(sweep) > 0)
        self.assertIn("threshold", sweep[0])
        self.assertIn("f1_score", sweep[0])
        self.assertIn("precision", sweep[0])
        self.assertIn("recall", sweep[0])

    async def test_sensitivity_sweep_404_for_unknown_satellite(self):
        response = await self._get("/api/ml/sensitivity", params={"norad_id": 99999})
        self.assertEqual(response.status_code, 404)

if __name__ == "__main__":
    unittest.main()
