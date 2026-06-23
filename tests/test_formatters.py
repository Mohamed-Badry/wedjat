import pytest
from datetime import datetime, timezone
from src.api.formatters import satellite_identity, dataset_window
from src.gr_sat.core.telemetry import TelemetryFrame

def test_satellite_identity_known():
    identity = satellite_identity(43880)
    assert identity["norad_id"] == 43880
    assert identity["name"] == "UWE-4"

def test_satellite_identity_unknown():
    identity = satellite_identity(99999)
    assert identity["norad_id"] == 99999
    assert identity["name"] == "NORAD 99999"
    assert identity["decoder"] is None

def test_dataset_window_empty():
    window = dataset_window([])
    assert window["start"] is None
    assert window["end"] is None

def test_dataset_window_populated():
    satellites = [
        {"dataset": {"start": "2024-01-01T00:00:00Z", "end": "2024-01-03T00:00:00Z"}},
        {"dataset": {"start": "2023-12-31T00:00:00Z", "end": "2024-01-05T00:00:00Z"}},
        {"dataset": {"start": None, "end": None}},
    ]
    window = dataset_window(satellites)
    assert window["start"] == "2023-12-31T00:00:00Z"
    assert window["end"] == "2024-01-05T00:00:00Z"
