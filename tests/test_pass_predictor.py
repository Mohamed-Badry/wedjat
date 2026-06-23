import pytest
from src.api.pass_predictor import predict_passes

def test_predict_passes_validation():
    with pytest.raises(ValueError, match="Latitude must be between -90 and 90 degrees"):
        predict_passes([], lat=100.0, lon=0.0)

    with pytest.raises(ValueError, match="Longitude must be between -180 and 180 degrees"):
        predict_passes([], lat=0.0, lon=200.0)
        
    with pytest.raises(ValueError, match="Ground station elevation must be between -500 and 10000 meters"):
        predict_passes([], lat=0.0, lon=0.0, elevation_m=-1000.0)

def test_predict_passes_empty_satellites():
    result = predict_passes([], lat=29.0, lon=31.0, elevation_m=32.0, station_label="Test")
    assert result["ground_station"]["label"] == "Test"
    assert result["passes"] == []
    assert result["min_elevation"] == 10.0
