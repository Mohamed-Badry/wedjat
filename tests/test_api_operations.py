import unittest
import httpx
from unittest.mock import patch
from api.main import create_app
from api.dashboard_data import DashboardDataRepository

class OperationsApiTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.app = create_app()

    async def _get(self, path: str, params: dict | None = None):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(path, params=params)

    def test_pass_prediction_returns_valid_passes(self):
        pass # To be replaced by async test

    async def test_pass_prediction_endpoint(self):
        response = await self._get(
            "/api/operations/passes",
            params={
                "ground_station": "cairo",
                "lookahead_hours": 24,
                "min_elevation": 10.0,
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("passes", payload)
        
        passes = payload["passes"]
        # Can be empty if no sats, but we should assert structure if present
        if passes:
            first_pass = passes[0]
            self.assertIn("satellite", first_pass)
            self.assertIn("norad_id", first_pass)
            self.assertIn("aos", first_pass)
            self.assertIn("los", first_pass)
            self.assertIn("max_elevation", first_pass)
            self.assertIn("direction", first_pass)

    async def test_pass_prediction_invalid_station(self):
        response = await self._get(
            "/api/operations/passes",
            params={
                "ground_station": "unknown_station",
                "lookahead_hours": 24,
                "min_elevation": 10.0,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.json())

if __name__ == "__main__":
    unittest.main()
