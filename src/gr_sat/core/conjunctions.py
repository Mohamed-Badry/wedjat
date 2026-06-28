import math
import numpy as np
import urllib.request
from datetime import datetime, timedelta, timezone
from sgp4.api import Satrec, SatrecArray, jday
from pydantic import BaseModel
from typing import List, Optional
import scipy.optimize

# Hardcoded NORAD ID for the primary satellite
PRIMARY_NORAD = 43880

class ConjunctionEvent(BaseModel):
    primary_norad: int
    secondary_norad: int
    secondary_name: str
    tca: datetime
    miss_distance_km: float
    relative_velocity_km_s: float
    probability: float
    risk_level: str

def get_risk_level(prob: float, dist: float) -> str:
    if prob > 1e-4 and dist < 1.0:
        return "CRITICAL"
    elif prob > 1e-5 and dist < 5.0:
        return "HIGH"
    elif prob > 1e-6 and dist < 20.0:
        return "WARNING"
    return "NOMINAL"

def calc_foster_prob(miss_km: float, sigma_r_km: float, sigma_t_km: float, combined_radius_km: float = 0.015) -> float:
    """
    Foster 1992 collision probability formula.
    All inputs in km for consistency with the rest of the pipeline.
    
    combined_radius_km: sum of hard-body radii of both objects (default 15m = cubesat + debris).
    sigma_r_km: radial position uncertainty (cross-track, ~0.1-1 km for SGP4).
    sigma_t_km: along-track position uncertainty (~1-10 km for SGP4).
    """
    d = miss_km
    # Early-out: if miss distance is far beyond the covariance envelope, probability is negligible
    if d > 8 * max(sigma_r_km, sigma_t_km):
        return 0.0
    
    r_c_sq = combined_radius_km ** 2
    sigma_prod = sigma_r_km * sigma_t_km
    sigma_sq = (sigma_r_km**2 + sigma_t_km**2) / 2.0
    
    if sigma_prod == 0 or sigma_sq == 0:
        return 0.0
        
    exponent = -(d**2) / (2.0 * sigma_sq)
    try:
        prob = (r_c_sq / (2.0 * math.sqrt(sigma_prod))) * math.exp(exponent)
    except OverflowError:
        prob = 0.0
    return min(1.0, max(0.0, prob))

import urllib.request
import time
from functools import wraps

def ttl_cache(ttl_seconds: int):
    """Simple in-memory TTL cache decorator to prevent API rate limiting."""
    def decorator(func):
        cache = {}
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            now = time.time()
            if key in cache:
                val, timestamp = cache[key]
                if now - timestamp < ttl_seconds:
                    return val
            val = func(*args, **kwargs)
            cache[key] = (val, now)
            return val
        return wrapper
    return decorator

@ttl_cache(ttl_seconds=3600)  # 1 hour cache
def get_active_satellites() -> tuple[Optional[Satrec], List[Satrec], List[str]]:
    from skyfield.api import Loader
    from gr_sat.core.config import PROJECT_ROOT
    
    cache_dir = PROJECT_ROOT / "data" / "tle"
    cache_dir.mkdir(parents=True, exist_ok=True)
    custom_loader = Loader(str(cache_dir))
    
    url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"
    sats_skyfield = custom_loader.tle_file(url, filename="celestrak_active.tle")
    
    sats = []
    names = []
    my_sat = None
    
    for sat in sats_skyfield:
        if not hasattr(sat, 'model'): continue
        if sat.model.satnum == PRIMARY_NORAD:
            my_sat = sat.model
        else:
            sats.append(sat.model)
            names.append(sat.name)
            
    return my_sat, sats, names

def compute_orbital_elements(sat: Satrec):
    """Approximate perigee and apogee from mean motion and eccentricity."""
    # Mean motion is in radians/minute in SGP4
    # Actually, we can get semi-major axis from mean motion
    # But for a quick sieve, it's easier to just use standard sgp4 parameters
    n = sat.no_kozai  # rad/min
    e = sat.ecco
    if n == 0:
        return 0, 0
    # a = (GM / n^2)^(1/3)
    # Earth GM ~ 398600.4418 km^3/s^2, n needs to be rad/s
    n_rad_s = n / 60.0
    a = (398600.4418 / (n_rad_s**2))**(1/3)
    perigee = a * (1 - e) - 6371.0
    apogee = a * (1 + e) - 6371.0
    return perigee, apogee

def find_conjunctions(lookahead_hours: int = 24, min_dist_threshold_km: float = 50.0) -> List[ConjunctionEvent]:
    my_sat, other_sats, names = get_active_satellites()
    if not my_sat:
        return []

    # 1. Smart Sieve
    my_peri, my_apo = compute_orbital_elements(my_sat)
    buffer = 50.0 # km
    
    filtered_sats = []
    filtered_names = []
    for sat, name in zip(other_sats, names):
        p, a = compute_orbital_elements(sat)
        # Check if altitude bands overlap
        if (p < my_apo + buffer) and (a > my_peri - buffer):
            filtered_sats.append(sat)
            filtered_names.append(name)
            
    if not filtered_sats:
        return []
        
    now = datetime.now(timezone.utc)
    
    # 2. Coarse grid search (1 minute step instead of 5 minutes for better minimum bracketing)
    # 1 minute is fine because LEO orbits are ~90 minutes, conjunctions are quick.
    step_min = 1
    total_mins = lookahead_hours * 60
    
    times = []
    jds = []
    frs = []
    for m in range(0, total_mins, step_min):
        dt = now + timedelta(minutes=m)
        jd, fr = jday(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
        times.append(dt)
        jds.append(jd)
        frs.append(fr)
        
    jds = np.array(jds)
    frs = np.array(frs)
    
    e_my, r_my, v_my = my_sat.sgp4_array(jds, frs)
    sat_array = SatrecArray(filtered_sats)
    e_all, r_all, v_all = sat_array.sgp4(jds, frs)
    
    events = []
    for i in range(len(filtered_sats)):
        valid = e_all[i] == 0
        if not np.any(valid):
            continue
            
        dr = r_all[i][valid] - r_my[valid]
        dist = np.linalg.norm(dr, axis=1)
        
        # Find all local minima in distance that are below a generous threshold (e.g., 200 km)
        # We can just look at the global minimum for a day to keep it simple, or find all minima
        min_idx = np.argmin(dist)
        coarse_min_dist = dist[min_idx]
        
        if coarse_min_dist < 200.0:
            # 3. Root finding / Optimization to find sub-second TCA
            tca_coarse_dt = times[np.where(valid)[0][min_idx]]
            
            def distance_at_offset(offset_seconds):
                dt = tca_coarse_dt + timedelta(seconds=offset_seconds)
                jd, fr = jday(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
                e1, r1, v1 = my_sat.sgp4(jd, fr)
                e2, r2, v2 = filtered_sats[i].sgp4(jd, fr)
                if e1 != 0 or e2 != 0:
                    return 999999.0
                return np.linalg.norm(np.array(r1) - np.array(r2))
                
            # Search within +/- 1 minute of the coarse minimum
            res = scipy.optimize.minimize_scalar(distance_at_offset, bounds=(-60, 60), method='bounded')
            
            if res.success:
                fine_min_dist = res.fun
                if fine_min_dist < min_dist_threshold_km:
                    exact_tca = tca_coarse_dt + timedelta(seconds=res.x)
                    jd, fr = jday(exact_tca.year, exact_tca.month, exact_tca.day, exact_tca.hour, exact_tca.minute, exact_tca.second)
                    _, r1, v1 = my_sat.sgp4(jd, fr)
                    _, r2, v2 = filtered_sats[i].sgp4(jd, fr)
                    rel_vel = np.linalg.norm(np.array(v1) - np.array(v2))
                    
                    # Compute realistic collision probability
                    # SGP4-propagated TLE covariance estimates (km)
                    # Radial ~0.5 km, Along-track ~5 km (grows with propagation time)
                    cov_r = 0.5   # km radial
                    cov_t = 5.0   # km along-track
                    prob = calc_foster_prob(fine_min_dist, cov_r, cov_t)
                    
                    events.append(ConjunctionEvent(
                        primary_norad=PRIMARY_NORAD,
                        secondary_norad=filtered_sats[i].satnum,
                        secondary_name=filtered_names[i],
                        tca=exact_tca,
                        miss_distance_km=fine_min_dist,
                        relative_velocity_km_s=rel_vel,
                        probability=prob,
                        risk_level=get_risk_level(prob, fine_min_dist)
                    ))
                    
    # Sort by TCA
    events.sort(key=lambda x: x.tca)
    return events
