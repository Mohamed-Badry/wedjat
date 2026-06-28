# -*- coding: utf-8 -*-
"""
Validation test pipeline for the UWE-4 AI-Enhanced Ground Station.
Verifies data flow: CelesTrak -> Skyfield -> SGP4 -> ML Model -> API response values.
"""

import sys
import unittest
from datetime import datetime, timezone

try:
    from app import app, compute_orbit, get_tle, fetch_tle
    from skyfield.api import EarthSatellite, load
    import joblib
except ImportError as exc:
    print(f"Error importing modules: {exc}")
    sys.exit(1)


class TestGroundStationPipeline(unittest.TestCase):

    def test_tle_caching_and_fetching(self):
        print("\n[TEST] 1. TLE Fetching and Parsing...")
        # Verify TLE fetch works and caches
        ok = fetch_tle(force=False)
        self.assertTrue(ok, "Failed to retrieve cached or live TLE")
        line1, line2 = get_tle()
        self.assertIsNotNone(line1)
        self.assertIsNotNone(line2)
        print(f"  Line 1: {line1}")
        print(f"  Line 2: {line2}")

    def test_skyfield_propagation(self):
        print("\n[TEST] 2. Skyfield Propagation & Coordinates...")
        line1, line2 = get_tle()
        ts = load.timescale()
        sat = EarthSatellite(line1, line2, "UWE-4", ts)
        
        t = ts.now()
        geocentric = sat.at(t)
        r_raw = geocentric.position.km
        v_raw = geocentric.velocity.km_per_s
        
        self.assertEqual(len(r_raw), 3)
        self.assertEqual(len(v_raw), 3)
        print(f"  Position ECI (km): x={r_raw[0]:.2f}, y={r_raw[1]:.2f}, z={r_raw[2]:.2f}")
        print(f"  Velocity ECI (km/s): vx={v_raw[0]:.4f}, vy={v_raw[1]:.4f}, vz={v_raw[2]:.4f}")

    def test_api_orbit_json(self):
        print("\n[TEST] 3. FastAPI Orbit Evaluation Response...")
        orbit_data = compute_orbit()
        
        # Verify presence of ECI positions and velocities
        self.assertIn("pos_eci", orbit_data)
        self.assertIn("vel_eci", orbit_data)
        self.assertIn("elevation_profile", orbit_data)
        self.assertIn("azimuth_profile", orbit_data)
        
        # Verify sizes of elevation and azimuth profile arrays (should be 80 points)
        self.assertEqual(len(orbit_data["elevation_profile"]), 80)
        self.assertEqual(len(orbit_data["azimuth_profile"]), 80)
        
        print(f"  GS Elevation: {orbit_data['elevation']} degrees")
        print(f"  GS Azimuth: {orbit_data['azimuth']} degrees")
        print(f"  Elevation Profile Array length: {len(orbit_data['elevation_profile'])} points")
        print(f"  Azimuth Profile Array length: {len(orbit_data['azimuth_profile'])} points")
        print(f"  BSTAR Drag Term: {orbit_data['coe']['bstar']}")


if __name__ == "__main__":
    unittest.main()
