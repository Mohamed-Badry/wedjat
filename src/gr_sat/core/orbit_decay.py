from datetime import datetime, timedelta
from functools import lru_cache, wraps
import joblib
import json
import pandas as pd
from pydantic import BaseModel
from pathlib import Path
from threading import Lock
from types import SimpleNamespace
from typing import Callable, List, Optional, TypeVar
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

config = SimpleNamespace(space_weather_source="CelesTrak")

T = TypeVar("T")


def ttl_cache(ttl_seconds: int) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Small process-local TTL cache for expensive-but-not-live orbital inputs."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        cache: dict[tuple[object, ...], tuple[T, float]] = {}
        lock = Lock()

        @wraps(func)
        def wrapper(*args, **kwargs):
            key = args + tuple(sorted(kwargs.items()))
            now = time.time()
            with lock:
                cached = cache.get(key)
                if cached and now - cached[1] < ttl_seconds:
                    return cached[0]

            value = func(*args, **kwargs)
            with lock:
                cache[key] = (value, now)
            return value

        def cache_clear() -> None:
            with lock:
                cache.clear()

        wrapper.cache_clear = cache_clear  # type: ignore[attr-defined]
        return wrapper

    return decorator

class SpaceWeatherObservation(BaseModel):
    date: datetime
    f107_obs: float
    f107a_obs: float = -999.0
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
    failure_file = CACHE_DIR / f"{filename}.failed"
    retry_after_seconds = int(os.getenv("CELESTRAK_RETRY_AFTER_SECONDS", "900"))
    timeout_seconds = float(os.getenv("CELESTRAK_HTTP_TIMEOUT_SECONDS", "1.5"))
    
    needs_fetch = True
    if cache_file.exists():
        age = time.time() - cache_file.stat().st_mtime
        if age < ttl_seconds:
            needs_fetch = False

    if needs_fetch and failure_file.exists():
        failure_age = time.time() - failure_file.stat().st_mtime
        if failure_age < retry_after_seconds:
            needs_fetch = False
            
    if needs_fetch:
        try:
            with httpx.Client(timeout=timeout_seconds) as client:
                response = client.get(url)
                response.raise_for_status()
                with open(cache_file, "wb") as f:
                    f.write(response.content)
            failure_file.unlink(missing_ok=True)
        except Exception as e:
            failure_file.touch()
            print(f"Failed to fetch {url} (falling back to cache if available): {e}")
            
    return cache_file

@ttl_cache(ttl_seconds=600)
def fetch_latest_space_weather() -> SpaceWeatherObservation:
    """Fetch latest space weather from DB cache, or CelesTrak SW-All.csv"""
    from datetime import datetime, timezone
    
    # 1. DB Cache Look-through
    try:
        from sqlmodel import Session, select
        try:
            from src.api.database import get_engine
            from src.api.db_models import SpaceWeatherRecord
        except ImportError:
            from api.database import get_engine  # type: ignore
            from api.db_models import SpaceWeatherRecord  # type: ignore

        engine = get_engine()
        if engine:
            with Session(engine) as session:
                stmt = select(SpaceWeatherRecord).order_by(SpaceWeatherRecord.fetched_at.desc())
                record = session.exec(stmt).first()
                if record:
                    age_hours = (datetime.now(timezone.utc) - record.fetched_at).total_seconds() / 3600.0
                    if age_hours < 12.0:
                        return SpaceWeatherObservation(
                            date=record.timestamp,
                            f107_obs=record.f107_index,
                            f107a_obs=record.f107_index, # Proxy
                            kp_max=record.kp_index,
                            ap_avg=record.ap_index
                        )
    except Exception as e:
        print(f"Database Space Weather fetch failed: {e}")

    url = "https://celestrak.org/SpaceData/SW-All.csv"
    
    try:
        import httpx
        import io
        resp = httpx.get(url, timeout=5.0)
        resp.raise_for_status()
        
        df = pd.read_csv(io.StringIO(resp.text))
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
        
        obs = SpaceWeatherObservation(
            date=datetime.now(timezone.utc), f107_obs=f107, f107a_obs=f107a, kp_max=kp_max, ap_avg=ap_avg
        )
        
        # Save to Database
        try:
            if engine:
                with Session(engine) as session:
                    rec = SpaceWeatherRecord(
                        timestamp=obs.date,
                        f107_index=obs.f107_obs,
                        kp_index=obs.kp_max,
                        ap_index=obs.ap_avg
                    )
                    session.add(rec)
                    session.commit()
        except Exception as e:
            print(f"Failed to save space weather to DB: {e}")
            
        return obs
            
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

@ttl_cache(ttl_seconds=3600)
def get_satellite(norad_id: int) -> Optional['EarthSatellite']:
    from skyfield.api import load, EarthSatellite
    from datetime import datetime, timezone
    
    # 1. DB Cache Look-through
    try:
        from sqlmodel import Session, select
        try:
            from src.api.database import get_engine
            from src.api.db_models import TleRecord
        except ImportError:
            from api.database import get_engine  # type: ignore
            from api.db_models import TleRecord  # type: ignore

        engine = get_engine()
        if engine:
            with Session(engine) as session:
                stmt = select(TleRecord).where(TleRecord.norad_id == norad_id).order_by(TleRecord.fetched_at.desc())
                record = session.exec(stmt).first()
                if record:
                    age_hours = (datetime.now(timezone.utc) - record.fetched_at).total_seconds() / 3600.0
                    if age_hours < 12.0:
                        ts = load.timescale()
                        return EarthSatellite(record.tle_line1, record.tle_line2, str(norad_id), ts)
    except Exception as e:
        print(f"Database TLE fetch failed: {e}")

    # 2. Fetch fresh TLE strings from Celestrak if DB missing or stale
    import httpx
    try:
        url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={norad_id}&FORMAT=tle"
        resp = httpx.get(url, timeout=5.0)
        resp.raise_for_status()
        
        lines = [line.strip() for line in resp.text.strip().split("\n") if line.strip()]
        if len(lines) >= 3:
            name = lines[0]
            line1 = lines[1]
            line2 = lines[2]
        elif len(lines) == 2:
            name = str(norad_id)
            line1 = lines[0]
            line2 = lines[1]
        else:
            raise ValueError(f"Invalid TLE format received for {norad_id}")
            
        # 3. Save the fresh TLE to our Database Cache
        try:
            if engine:
                with Session(engine) as session:
                    new_rec = TleRecord(
                        norad_id=norad_id,
                        epoch_timestamp=datetime.now(timezone.utc), # DB index sorting
                        tle_line1=line1,
                        tle_line2=line2,
                        source="celestrak"
                    )
                    session.add(new_rec)
                    session.commit()
        except Exception as e:
            print(f"Failed to save TLE to DB: {e}")
            
        ts = load.timescale()
        return EarthSatellite(line1, line2, name, ts)
        
    except Exception as e:
        print(f"Failed to fetch fresh TLE from Celestrak: {e}")
        
    # 3. Ultimate Fallback: Offline flat file
    fallback_file = PROJECT_ROOT / "data" / "cache" / f"tle_{norad_id}.txt"
    if fallback_file.exists():
        ts = load.timescale()
        lines = fallback_file.read_text().strip().split("\n")
        if len(lines) >= 2:
            return EarthSatellite(lines[-2].strip(), lines[-1].strip(), str(norad_id), ts)
            
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

@lru_cache(maxsize=4)
def _load_decay_model_assets(days: int):
    models_dir = PROJECT_ROOT / "models"
    model_path = models_dir / f"uwe4_production_model_{days}d.pkl"
    feature_path = models_dir / f"uwe4_production_features_{days}d.json"
    if not model_path.exists() or not feature_path.exists():
        raise FileNotFoundError(f"Missing production orbit-decay artifacts for {days}d horizon")

    with open(feature_path, "r") as f:
        feature_cols = json.load(f)
    model = joblib.load(model_path)
    return model, tuple(feature_cols)


@ttl_cache(ttl_seconds=3600)
def _latest_training_row() -> pd.DataFrame:
    dataset_path = PROJECT_ROOT / "data" / "04_daily_orbit_space_weather_uwe4.csv"
    df = pd.read_csv(dataset_path)
    return df.tail(1).copy()


def _apply_live_features(
    latest_row: pd.DataFrame,
    weather: SpaceWeatherObservation,
    alt_km: float,
) -> pd.DataFrame:
    row = latest_row.copy()
    if alt_km > 0 and "altitude_mean_km" in row.columns:
        row.loc[:, "altitude_mean_km"] = alt_km
    if weather.f107_obs != -999.0 and "f107_obs" in row.columns:
        row.loc[:, "f107_obs"] = weather.f107_obs
    if weather.kp_max != -999.0 and "kp_max" in row.columns:
        row.loc[:, "kp_max"] = weather.kp_max
    if weather.ap_avg != -999.0 and "ap_avg" in row.columns:
        row.loc[:, "ap_avg"] = weather.ap_avg
    if "high_solar_flux_flag" in row.columns and weather.f107_obs != -999.0:
        row.loc[:, "high_solar_flux_flag"] = int(weather.f107_obs >= 150.0)
    if "geomagnetic_active_flag" in row.columns and weather.kp_max != -999.0:
        row.loc[:, "geomagnetic_active_flag"] = int(weather.kp_max >= 5.0)
    return row


def PredictOrbitDecay(satellite_id: int, weather: SpaceWeatherObservation, alt_km: float = 500.0) -> List[OrbitDecayForecast]:
    """
    Predict orbit decay using the pre-trained ML models over 7-day and 30-day horizons.
    """
    forecasts = []
    
    # Load dataset for feature extraction
    try:
        latest_row = _apply_live_features(_latest_training_row(), weather, alt_km)
    except Exception as e:
        print(f"Failed to load ML dataset: {e}")
        latest_row = None
    
    for days in [7, 30]:
        predicted_decay_km = -999.0  # Obvious failure value instead of fallback
        
        if latest_row is not None:
            try:
                model, feature_cols = _load_decay_model_assets(days)
                X_latest = latest_row[list(feature_cols)]
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
