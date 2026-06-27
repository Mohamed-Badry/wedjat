from datetime import datetime, timedelta
import joblib
import pandas as pd
from pydantic import BaseModel
from pathlib import Path
from typing import List, Optional
import urllib.request
import numpy as np
from sgp4.api import Satrec, jday
import nrlmsise00

class SpaceWeatherObservation(BaseModel):
    date: datetime
    f107_obs: float
    kp_max: float
    ap_avg: float

class AtmosphericState(BaseModel):
    exospheric_temp_k: float
    density_kg_m3: float
    bstar: float
    drag_coeff: float
    altitude_km: float

class OrbitDecayForecast(BaseModel):
    date: datetime
    satellite_id: int
    horizon: timedelta
    predicted_decay_km: float
    predicted_altitude_km: float
    model_version: str

def fetch_latest_space_weather() -> SpaceWeatherObservation:
    """Fetch latest space weather from CelesTrak SW-All.csv"""
    try:
        url = "https://celestrak.org/SpaceData/SW-All.csv"
        df = pd.read_csv(url)
        # Drop rows missing critical data and get the latest valid one
        valid = df.dropna(subset=["AP_AVG", "F10.7_OBS"])
        latest = valid.iloc[-1]
        
        def safe_float(val, default):
            try:
                if pd.isna(val):
                    return default
                return float(val)
            except:
                return default

        f107 = safe_float(latest.get("F10.7_OBS", None), -999.0)
        ap_avg = safe_float(latest.get("AP_AVG", None), -999.0)
        
        kp_cols = [latest.get(f"KP{i}", -999.0) for i in range(1, 9)]
        kp_cols = [safe_float(k, -999.0) for k in kp_cols if k != -999.0]
        kp_max = max(kp_cols) if kp_cols else -999.0
        
        return SpaceWeatherObservation(
            date=datetime.now(),
            f107_obs=f107,
            kp_max=kp_max,
            ap_avg=ap_avg
        )
    except Exception as e:
        print(f"Error fetching space weather: {e}")
        return SpaceWeatherObservation(
            date=datetime.now(),
            f107_obs=-999.0,
            kp_max=-999.0,
            ap_avg=-999.0
        )

def get_satellite(norad_id: int) -> Optional[Satrec]:
    try:
        url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={norad_id}&FORMAT=tle"
        with urllib.request.urlopen(url, timeout=10) as response:
            lines = response.read().decode('utf-8').strip().splitlines()
        if len(lines) >= 3:
            return Satrec.twoline2rv(lines[1], lines[2])
    except Exception as e:
        print(f"Failed to load TLE for {norad_id}: {e}")
    return None

def compute_atmospheric_state(norad_id: int, weather: SpaceWeatherObservation) -> AtmosphericState:
    sat = get_satellite(norad_id)
    if not sat:
        return AtmosphericState(
            exospheric_temp_k=-999.0,
            density_kg_m3=-999.0,
            bstar=-999.0,
            drag_coeff=-999.0,
            altitude_km=-999.0
        )
        
    now = datetime.utcnow()
    jd, fr = jday(now.year, now.month, now.day, now.hour, now.minute, now.second)
    e, r, v = sat.sgp4(jd, fr)
    
    if e != 0:
        alt_km = -999.0
    else:
        alt_km = np.linalg.norm(r) - 6371.0
        
    f107 = weather.f107_obs
    ap = weather.ap_avg
    
    if f107 == -999.0 or ap == -999.0:
        density_kg_m3 = -999.0
        exo_temp = -999.0
    else:
        try:
            # msise_model(time, alt_km, lat, lon, f107A, f107, ap)
            ds = nrlmsise00.msise_model(now, alt_km, 0.0, 0.0, f107, f107, ap)
            # Total mass density is ds[0][5] in g/cm3. 1 g/cm3 = 1000 kg/m3.
            density_kg_m3 = ds[0][5] * 1000.0
            exo_temp = ds[1][0]
        except Exception:
            density_kg_m3 = -999.0
            exo_temp = -999.0
        
    return AtmosphericState(
        exospheric_temp_k=exo_temp,
        density_kg_m3=density_kg_m3,
        bstar=sat.bstar,
        drag_coeff=2.20,
        altitude_km=alt_km
    )

def PredictOrbitDecay(satellite_id: int, weather: SpaceWeatherObservation, alt_km: float = 500.0) -> List[OrbitDecayForecast]:
    """
    Predict orbit decay using the pre-trained ML models over 7-day and 30-day horizons.
    """
    import json
    forecasts = []
    models_dir = Path("models")
    data_dir = Path("data")
    
    # Load dataset for feature extraction
    try:
        dataset_path = data_dir / "04_daily_orbit_space_weather_uwe4.csv"
        df = pd.read_csv(dataset_path)
        latest_row = df.tail(1).copy()
    except Exception as e:
        print(f"Failed to load ML dataset: {e}")
        latest_row = None
    
    for days in [7, 30]:
        model_path = models_dir / f"uwe4_production_model_{days}d.pkl"
        feature_path = models_dir / f"uwe4_production_features_{days}d.json"
        
        predicted_decay_km = -999.0  # Obvious failure value instead of fallback
        
        if model_path.exists() and feature_path.exists() and latest_row is not None:
            try:
                # Load features list
                with open(feature_path, "r") as f:
                    feature_cols = json.load(f)
                
                # Load model
                model = joblib.load(model_path)
                
                # Extract features for latest day
                X_latest = latest_row[feature_cols]
                
                # Predict
                predicted_decay_km = float(model.predict(X_latest)[0])
            except Exception as e:
                print(f"Inference failed for {days}d: {e}")
                
        forecasts.append(
            OrbitDecayForecast(
                date=datetime.now(),
                satellite_id=satellite_id,
                horizon=timedelta(days=days),
                predicted_decay_km=predicted_decay_km,
                predicted_altitude_km=alt_km - predicted_decay_km if alt_km != -999.0 and predicted_decay_km != -999.0 else -999.0,
                model_version=f"{days}d-production"
            )
        )
    return forecasts
