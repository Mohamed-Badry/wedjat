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
import httpx
import os
import time

# Resolve the root data/cache directory safely
PROJECT_ROOT = Path(__file__).resolve().parents[3]
CACHE_DIR = PROJECT_ROOT / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

class SpaceWeatherObservation(BaseModel):
    date: datetime
    f107_obs: float
    f107a_obs: float
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

def download_with_cache(url: str, filename: str, ttl_seconds: int = 3600) -> Path:
    """Helper method to fetch and cache files cleanly"""
    cache_file = CACHE_DIR / filename
    
    needs_fetch = True
    if cache_file.exists():
        age = time.time() - cache_file.stat().st_mtime
        if age < ttl_seconds:
            needs_fetch = False
            
    if needs_fetch:
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(url)
                response.raise_for_status()
                with open(cache_file, "wb") as f:
                    f.write(response.content)
        except Exception as e:
            print(f"Failed to fetch {url} (falling back to cache if available): {e}")
            
    return cache_file

def fetch_latest_space_weather() -> SpaceWeatherObservation:
    """Fetch latest space weather from CelesTrak SW-All.csv with persistent file caching"""
    url = "https://celestrak.org/SpaceData/SW-All.csv"
    cache_file = download_with_cache(url, "SW-All.csv")
    
    try:
        if cache_file.exists():
            df = pd.read_csv(cache_file)
            valid = df.dropna(subset=["AP_AVG", "F10.7_OBS"])
            latest = valid.iloc[-1]
            
            def safe_float(val, default):
                try:
                    if pd.isna(val): return default
                    return float(val)
                except:
                    return default

            f107 = safe_float(latest.get("F10.7_OBS", None), -999.0)
            f107a = safe_float(latest.get("F10.7_81_OBS", latest.get("F10.7_CTR81_OBS", f107)), f107)
            ap_avg = safe_float(latest.get("AP_AVG", None), -999.0)
            kp_cols = [safe_float(latest.get(f"KP{i}", -999.0), -999.0) for i in range(1, 9)]
            kp_cols = [k for k in kp_cols if k != -999.0]
            kp_max = max(kp_cols) if kp_cols else -999.0
            
            return SpaceWeatherObservation(
                date=datetime.now(), f107_obs=f107, f107a_obs=f107a, kp_max=kp_max, ap_avg=ap_avg
            )
            
        # Offline Fallback
        fallback_file = PROJECT_ROOT / "data" / "04_daily_orbit_space_weather_uwe4.csv"
        if fallback_file.exists():
            df = pd.read_csv(fallback_file)
            valid = df.dropna(subset=["ap_avg", "f107_obs"])
            latest = valid.iloc[-1]
            
            f107 = float(latest["f107_obs"]) if not pd.isna(latest["f107_obs"]) else -999.0
            f107a = float(latest.get("f107_obs_rolling_81d", f107)) if not pd.isna(latest.get("f107_obs_rolling_81d", f107)) else f107
            ap_avg = float(latest["ap_avg"]) if not pd.isna(latest["ap_avg"]) else -999.0
            kp_max = float(latest["kp_max"]) if not pd.isna(latest["kp_max"]) else -999.0
            
            return SpaceWeatherObservation(
                date=datetime.now(), f107_obs=f107, f107a_obs=f107a, kp_max=kp_max, ap_avg=ap_avg
            )
            
    except Exception as e:
        print(f"Error parsing space weather: {e}")
        
    return SpaceWeatherObservation(
        date=datetime.now(), f107_obs=-999.0, f107a_obs=-999.0, kp_max=-999.0, ap_avg=-999.0
    )

def get_satellite(norad_id: int) -> Optional['EarthSatellite']:
    from skyfield.api import Loader
    cache_dir = PROJECT_ROOT / "data" / "tle"
    cache_dir.mkdir(parents=True, exist_ok=True)
    custom_loader = Loader(str(cache_dir))
    
    # 1. Try to load from the centralized active TLE list first
    active_filename = "celestrak_active.tle"
    active_url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"
    
    reload = True
    active_path = cache_dir / active_filename
    if active_path.exists():
        if custom_loader.days_old(active_filename) < 0.25:
            reload = False
            
    try:
        tle_file = custom_loader.tle_file(active_url, filename=active_filename, reload=reload)
    except Exception as e:
        print(f"Failed to fetch active TLEs: {e}")
        tle_file = None
        if active_path.exists():
            print(f"Falling back to stale active TLE cache")
            tle_file = custom_loader.tle_file(active_url, filename=active_filename, reload=False)
            
    if tle_file:
        for sat in tle_file:
            if sat.model.satnum == norad_id:
                return sat
        
    # 2. If not found in active (or banned), try fetching the specific TLE
    specific_filename = f"tle_{norad_id}.txt"
    specific_url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={norad_id}&FORMAT=tle"
    
    reload = True
    specific_path = cache_dir / specific_filename
    if specific_path.exists():
        if custom_loader.days_old(specific_filename) < 0.25:
            reload = False
            
    try:
        tle_file = custom_loader.tle_file(specific_url, filename=specific_filename, reload=reload)
    except Exception as e:
        print(f"Failed to fetch specific TLE for {norad_id}: {e}")
        tle_file = None
        if specific_path.exists():
            print(f"Falling back to stale specific TLE cache")
            tle_file = custom_loader.tle_file(specific_url, filename=specific_filename, reload=False)
            
    if tle_file:
        return tle_file[0]
        
    return None

def compute_atmospheric_state(norad_id: int, weather: SpaceWeatherObservation) -> AtmosphericState:
    from skyfield.api import load
    sat = get_satellite(norad_id)
    if not sat:
        return AtmosphericState(
            exospheric_temp_k=-999.0,
            density_kg_m3=-999.0,
            bstar=-999.0,
            drag_coeff=-999.0,
            altitude_km=-999.0
        )
        
    ts = load.timescale()
    t = ts.now()
    
    # Calculate exact geodetic coordinates (WGS84)
    geocentric = sat.at(t)
    subpoint = geocentric.subpoint()
    lat = subpoint.latitude.degrees
    lon = subpoint.longitude.degrees
    alt_km = subpoint.elevation.km
        
    f107 = weather.f107_obs
    f107a = weather.f107a_obs
    ap = weather.ap_avg
    
    if f107 == -999.0 or ap == -999.0:
        density_kg_m3 = -999.0
        exo_temp = -999.0
    else:
        try:
            # msise_model(time, alt_km, lat, lon, f107A, f107, ap)
            ds = nrlmsise00.msise_model(t.utc_datetime(), alt_km, lat, lon, f107a, f107, ap)
            # Total mass density is ds[0][5] in g/cm3. 1 g/cm3 = 1000 kg/m3.
            density_kg_m3 = ds[0][5] * 1000.0
            exo_temp = ds[1][0]
        except Exception:
            density_kg_m3 = -999.0
            exo_temp = -999.0
        
    return AtmosphericState(
        exospheric_temp_k=exo_temp,
        density_kg_m3=density_kg_m3,
        bstar=sat.model.bstar,
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
