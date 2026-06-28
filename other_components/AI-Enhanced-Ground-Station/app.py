# -*- coding: utf-8 -*-
"""
FastAPI backend for the UWE-4 passive ground-station dashboard.

The API only returns values computed from a real TLE, real CSV telemetry, or a
verified ML model trained from real truth/reference state vectors.
"""

import math
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import joblib
import pandas as pd
import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sgp4.api import Satrec, jday
from skyfield.api import load, EarthSatellite, wgs84

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"
MODEL_PATH = BASE_DIR / "models" / "orbit_ai_model.pkl"
TLE_CACHE_PATH = DATA_DIR / "43880.tle"
CONJUNCTION_PATH = DATA_DIR / "conjunction_events.csv"

NORAD_ID = 43880
SAT_NAME = "UWE-4"
TLE_REFRESH_SEC = 3600
GS_LAT = 29.07
GS_LON = 31.09
GS_ALT_KM = 0.027
RE = 6371.0
MU = 398600.4418
UHF_DOWNLINK_MHZ = 435.6

MODEL_POSITION_RMSE_LIMIT_KM = 1.0
MODEL_VELOCITY_RMSE_LIMIT_KM_S = 0.01
MAX_POSITION_CORRECTION_KM = 10.0
MAX_VELOCITY_CORRECTION_KM_S = 0.05


app = FastAPI(title="UWE-4 Ground Station API", version="12.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

_lock = threading.Lock()
_cache = {
    "tle1": None,
    "tle2": None,
    "tle_at": 0.0,
    "tle_src": "not loaded",
    "df": None,
    "model_bundle": None,
    "model_status": None,
}

ts = load.timescale()


def finite_float(value):
    if value is None or pd.isna(value):
        return None
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        return None
    return value


def rounded(value, digits):
    value = finite_float(value)
    return None if value is None else round(value, digits)


def as_sequence(value, length):
    try:
        if len(value) == length:
            return value
    except TypeError:
        pass
    return [value] * length


def utc_now():
    return datetime.now(timezone.utc)


def parse_tle_text(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    line1 = next((line for line in lines if line.startswith("1 ")), None)
    line2 = next((line for line in lines if line.startswith("2 ")), None)
    if not line1 or not line2:
        raise ValueError("TLE response did not contain line 1 and line 2")
    if line1[2:7].strip() != str(NORAD_ID) or line2[2:7].strip() != str(NORAD_ID):
        raise ValueError("TLE catalog number did not match configured satellite")
    Satrec.twoline2rv(line1, line2)
    return line1, line2


def load_cached_tle():
    if not TLE_CACHE_PATH.exists():
        return False
    try:
        line1, line2 = parse_tle_text(TLE_CACHE_PATH.read_text(encoding="utf-8"))
        with _lock:
            _cache["tle1"] = line1
            _cache["tle2"] = line2
            _cache["tle_at"] = TLE_CACHE_PATH.stat().st_mtime
            _cache["tle_src"] = f"local cache ({TLE_CACHE_PATH.name})"
        return True
    except Exception as exc:
        print(f"[TLE] Local cache rejected: {exc}")
        return False


def fetch_tle(force=False):
    with _lock:
        age = time.time() - float(_cache["tle_at"] or 0)
        has_fresh = _cache["tle1"] is not None and age <= TLE_REFRESH_SEC
    if has_fresh and not force:
        return True

    url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={NORAD_ID}&FORMAT=TLE"
    try:
        response = httpx.get(url, timeout=10)
        response.raise_for_status()
        line1, line2 = parse_tle_text(response.text)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        TLE_CACHE_PATH.write_text(f"{SAT_NAME}\n{line1}\n{line2}\n", encoding="utf-8")
        with _lock:
            _cache["tle1"] = line1
            _cache["tle2"] = line2
            _cache["tle_at"] = time.time()
            _cache["tle_src"] = f"CelesTrak live ({url})"
        print("[TLE] Updated via httpx from CelesTrak")
        return True
    except Exception as exc:
        print(f"[TLE] httpx live fetch failed: {exc}")

    try:
        stations = load.tle_file(url, reload=force)
        for sat in stations:
            if str(sat.model.satnum) != str(NORAD_ID):
                continue
            line1, line2 = parse_tle_text(f"{sat.model.line1}\n{sat.model.line2}")
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            TLE_CACHE_PATH.write_text(f"{SAT_NAME}\n{line1}\n{line2}\n", encoding="utf-8")
            with _lock:
                _cache["tle1"] = line1
                _cache["tle2"] = line2
                _cache["tle_at"] = time.time()
                _cache["tle_src"] = f"CelesTrak live ({url})"
            print(f"[TLE] Updated via Skyfield from CelesTrak")
            return True
        print("[TLE] Skyfield live fetch did not return the configured satellite")
    except Exception as exc:
        print(f"[TLE] Skyfield live fetch failed: {exc}")

    load_cached_tle()
    with _lock:
        has_tle = _cache["tle1"] is not None
    if not has_tle:
        print("[TLE] No real TLE available. Orbit endpoint will report unavailable.")
    return has_tle


def get_tle():
    with _lock:
        age = time.time() - float(_cache["tle_at"] or 0)
        has_tle = _cache["tle1"] is not None
    if not has_tle:
        load_cached_tle()
    with _lock:
        age = time.time() - float(_cache["tle_at"] or 0)
        has_tle = _cache["tle1"] is not None
    if not has_tle or age > TLE_REFRESH_SEC:
        fetch_tle()
    with _lock:
        if _cache["tle1"] is None or _cache["tle2"] is None:
            raise RuntimeError("No real TLE is available. Use Update TLE with internet access.")
        return _cache["tle1"], _cache["tle2"]


def load_model():
    status = {
        "model_loaded": False,
        "model_verified": False,
        "used": False,
        "fallback_reason": "model file not found",
        "position_rmse_km": None,
        "velocity_rmse_km_s": None,
        "threshold_position_rmse_km": MODEL_POSITION_RMSE_LIMIT_KM,
        "threshold_velocity_rmse_km_s": MODEL_VELOCITY_RMSE_LIMIT_KM_S,
        "source": str(MODEL_PATH),
    }
    if not MODEL_PATH.exists():
        with _lock:
            _cache["model_bundle"] = None
            _cache["model_status"] = status
        return

    try:
        bundle = joblib.load(MODEL_PATH)
        status["model_loaded"] = True
        if not isinstance(bundle, dict) or "model" not in bundle or "metrics" not in bundle:
            status["fallback_reason"] = "model lacks real validation metadata; raw SGP4 enforced"
            bundle = None
        else:
            metrics = bundle.get("metrics", {})
            pos_rmse = finite_float(metrics.get("position_rmse_km"))
            vel_rmse = finite_float(metrics.get("velocity_rmse_km_s"))
            status["position_rmse_km"] = pos_rmse
            status["velocity_rmse_km_s"] = vel_rmse
            if (
                pos_rmse is not None
                and vel_rmse is not None
                and pos_rmse <= MODEL_POSITION_RMSE_LIMIT_KM
                and vel_rmse <= MODEL_VELOCITY_RMSE_LIMIT_KM_S
            ):
                status["model_verified"] = True
                status["fallback_reason"] = None
            else:
                status["fallback_reason"] = "validation RMSE exceeds accepted threshold"
    except Exception as exc:
        print(f"[ML] Failed to load model: {exc}")
        bundle = None
        status["fallback_reason"] = f"model load error: {exc}"

    with _lock:
        _cache["model_bundle"] = bundle
        _cache["model_status"] = status


load_model()


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def mag(v):
    return math.sqrt(sum(x * x for x in v))


def eccentricity_vec(r, v):
    rm = mag(r)
    vm2 = dot(v, v)
    f = vm2 / MU - 1.0 / rm
    return [f * r[i] - dot(r, v) * v[i] / MU for i in range(3)]


def gmst(jd_full):
    t = (jd_full - 2451545.0) / 36525.0
    theta = 280.46061837 + 360.98564736629 * (jd_full - 2451545.0) + 0.000387933 * t * t - t * t * t / 38710000.0
    return math.radians(theta % 360)


def look_angles(slat, slon, salt, glat, glon, galt):
    la1, lo1, la2, lo2 = map(math.radians, [glat, glon, slat, slon])
    dlo = lo2 - lo1
    dla = la2 - la1
    a = math.sin(dla / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(dlo / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    rg = RE + galt
    rs = RE + salt
    if c < 1e-9:
        return 0.0, 90.0, salt - galt
    rng = math.sqrt(rg * rg + rs * rs - 2 * rg * rs * math.cos(c))
    se = max(-1.0, min(1.0, (rs * rs - rg * rg - rng * rng) / (2 * rg * rng)))
    el = math.degrees(math.asin(se))
    y = math.sin(dlo) * math.cos(la2)
    x = math.cos(la1) * math.sin(la2) - math.sin(la1) * math.cos(la2) * math.cos(dlo)
    az = (math.degrees(math.atan2(y, x)) + 360) % 360
    return az, el, rng


def range_rate(r_eci, v_eci, glat, glon, theta):
    la = math.radians(glat)
    lo = math.radians(glon) + theta
    gs = [RE * math.cos(la) * math.cos(lo), RE * math.cos(la) * math.sin(lo), RE * math.sin(la)]
    dr = [r_eci[i] - gs[i] for i in range(3)]
    dm = mag(dr)
    if dm < 1e-6:
        return 0.0
    we = 7.2921150e-5
    vgs = [-we * gs[1], we * gs[0], 0.0]
    dv = [v_eci[i] - vgs[i] for i in range(3)]
    return dot(dv, dr) / dm


def apply_model_correction(r_raw, v_raw):
    with _lock:
        bundle = _cache["model_bundle"]
        base_status = dict(_cache["model_status"] or {})

    status = {
        **base_status,
        "used": False,
        "position_delta_km": 0.0,
        "velocity_delta_km_s": 0.0,
    }
    
    # Fallback if validation threshold is breached
    if not status.get("model_verified"):
        status["fallback_reason"] = status.get("fallback_reason") or "Model not verified; raw SGP4 enforced"
        return list(r_raw), list(v_raw), status

    # Try PyTorch model hook first if .pt/.pth model exists
    pt_model_path = BASE_DIR / "models" / "orbit_ai_model.pt"
    if not pt_model_path.exists():
        pt_model_path = BASE_DIR / "models" / "satellite_model.pth"
    if not pt_model_path.exists():
        pt_model_path = BASE_DIR / "models" / "orbit_ai_model.pth"

    if pt_model_path.exists():
        try:
            import torch
            model = torch.load(pt_model_path, map_location="cpu")
            model.eval()
            
            rm_orig = mag(r_raw)
            features = [r_raw[0], r_raw[1], r_raw[2], v_raw[0], v_raw[1], v_raw[2], rm_orig - RE]
            
            with torch.no_grad():
                input_tensor = torch.tensor([features], dtype=torch.float32)
                output_tensor = model(input_tensor)
                delta = output_tensor.numpy()[0]
                
            pos_delta = [float(delta[0]), float(delta[1]), float(delta[2])]
            vel_delta = [float(delta[3]), float(delta[4]), float(delta[5])]
            
            pos_norm = mag(pos_delta)
            vel_norm = mag(vel_delta)
            
            if pos_norm > MAX_POSITION_CORRECTION_KM or vel_norm > MAX_VELOCITY_CORRECTION_KM_S:
                status["fallback_reason"] = "prediction correction exceeded physical safety gate"
                return list(r_raw), list(v_raw), status
                
            status["used"] = True
            status["fallback_reason"] = None
            status["position_delta_km"] = round(pos_norm, 6)
            status["velocity_delta_km_s"] = round(vel_norm, 9)
            return [r_raw[i] + pos_delta[i] for i in range(3)], [v_raw[i] + vel_delta[i] for i in range(3)], status
            
        except Exception as exc:
            print(f"[ML] PyTorch model execution failed, trying joblib: {exc}")

    # Fallback to joblib/sklearn .pkl model
    if bundle and "model" in bundle:
        try:
            rm_orig = mag(r_raw)
            features = [[r_raw[0], r_raw[1], r_raw[2], v_raw[0], v_raw[1], v_raw[2], rm_orig - RE]]
            delta = bundle["model"].predict(features)[0]
            pos_delta = [float(delta[0]), float(delta[1]), float(delta[2])]
            vel_delta = [float(delta[3]), float(delta[4]), float(delta[5])]
            pos_norm = mag(pos_delta)
            vel_norm = mag(vel_delta)
            if pos_norm > MAX_POSITION_CORRECTION_KM or vel_norm > MAX_VELOCITY_CORRECTION_KM_S:
                status["fallback_reason"] = "prediction correction exceeded physical safety gate"
                return list(r_raw), list(v_raw), status
            status["used"] = True
            status["fallback_reason"] = None
            status["position_delta_km"] = round(pos_norm, 6)
            status["velocity_delta_km_s"] = round(vel_norm, 9)
            return [r_raw[i] + pos_delta[i] for i in range(3)], [v_raw[i] + vel_delta[i] for i in range(3)], status
        except Exception as exc:
            status["fallback_reason"] = f"model prediction error: {exc}"
            return list(r_raw), list(v_raw), status

    status["fallback_reason"] = "No functional model available"
    return list(r_raw), list(v_raw), status


def state_from_tle(sat, when):
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    t = ts.from_datetime(when)
    geocentric = sat.at(t)
    r_raw = list(geocentric.position.km)
    v_raw = list(geocentric.velocity.km_per_s)
    
    r, v, ml_status = apply_model_correction(r_raw, v_raw)
    
    jd, fr = jday(when.year, when.month, when.day, when.hour, when.minute, when.second + when.microsecond / 1e6)
    return jd, fr, r_raw, v_raw, r, v, ml_status


def state_summary(r, v, when, sat, jd, fr):
    rx, ry, rz = r
    vx, vy, vz = v
    rm = mag(r)
    vm = mag(v)
    alt = rm - RE
    theta = gmst(jd + fr)
    lon = math.degrees(math.atan2(ry, rx) - theta)
    if lon > 180:
        lon -= 360
    if lon < -180:
        lon += 360
    lat = math.degrees(math.asin(max(-1.0, min(1.0, rz / rm))))

    hv = cross(r, v)
    hm = mag(hv)
    nv = cross([0, 0, 1], hv)
    nm = mag(nv)
    ev = eccentricity_vec(r, v)
    ecc = mag(ev)

    inc = math.degrees(math.acos(max(-1.0, min(1.0, hv[2] / hm))))
    raan = math.degrees(math.acos(max(-1.0, min(1.0, nv[0] / nm)))) if nm > 1e-10 else 0.0
    if nv[1] < 0:
        raan = 360 - raan
    aop = math.degrees(math.acos(max(-1.0, min(1.0, dot(nv, ev) / (nm * ecc))))) if (nm > 1e-10 and ecc > 1e-10) else 0.0
    if ev[2] < 0:
        aop = 360 - aop

    semi_major = 1.0 / (2.0 / rm - vm * vm / MU)
    nu_cos = max(-1.0, min(1.0, dot(ev, r) / (ecc * rm))) if ecc > 1e-10 else 1.0
    nu = math.degrees(math.acos(nu_cos))
    if dot(r, v) < 0:
        nu = 360 - nu
    e_rad = 2 * math.atan2(
        math.sqrt(1 - ecc) * math.sin(math.radians(nu) / 2),
        math.sqrt(1 + ecc) * math.cos(math.radians(nu) / 2),
    )
    mean_anomaly = math.degrees(e_rad - ecc * math.sin(e_rad)) % 360
    period_min = 2 * math.pi * math.sqrt(semi_major * semi_major * semi_major / MU) / 60.0
    mean_motion = 86400.0 / (period_min * 60.0)
    peri = semi_major * (1 - ecc) - RE
    apo = semi_major * (1 + ecc) - RE
    angular_velocity = 360.0 / period_min
    time_since_perigee = (nu / 360.0) * period_min
    time_to_perigee = period_min - time_since_perigee

    az, el, rng = look_angles(lat, lon, alt, GS_LAT, GS_LON, GS_ALT_KM)
    rr = range_rate(r, v, GS_LAT, GS_LON, theta)
    doppler = -rr * UHF_DOWNLINK_MHZ / 299792.458

    bstar_val = sat.model.bstar if hasattr(sat, 'model') else getattr(sat, 'bstar', 0.0)

    return {
        "altitude": round(alt, 3),
        "velocity": round(vm, 4),
        "latitude": round(lat, 5),
        "longitude": round(lon, 5),
        "azimuth": round(az, 2),
        "elevation": round(el, 2),
        "range_km": round(rng, 2),
        "doppler_khz": round(doppler, 3),
        "pos_eci": {"x": round(rx, 3), "y": round(ry, 3), "z": round(rz, 3)},
        "vel_eci": {"x": round(vx, 6), "y": round(vy, 6), "z": round(vz, 6)},
        "coe": {
            "a": round(semi_major, 2),
            "e": round(ecc, 6),
            "i": round(inc, 4),
            "raan": round(raan, 4),
            "aop": round(aop, 4),
            "m": round(mean_anomaly, 4),
            "nu": round(nu, 4),
            "T_min": round(period_min, 4),
            "n": round(mean_motion, 6),
            "apo": round(apo, 2),
            "peri": round(peri, 2),
            "bstar": f"{bstar_val:.4e}",
            "ang_vel": round(angular_velocity, 5),
            "time_since_per": round(time_since_perigee, 2),
            "time_to_per": round(time_to_perigee, 2),
            "radial_dist": round(rm, 3),
        },
        "timestamp_utc": when.isoformat(),
    }


def build_forecast(sat, now, horizon_minutes):
    rows = []
    for minutes in horizon_minutes:
        when = now + timedelta(minutes=minutes)
        jd, fr, r_raw, v_raw, r, v, ml_status = state_from_tle(sat, when)
        raw_summary = state_summary(r_raw, v_raw, when, sat, jd, fr)
        out_summary = state_summary(r, v, when, sat, jd, fr)
        rows.append(
            {
                "label": "Now" if minutes == 0 else f"+{minutes:g} min",
                "minutes": minutes,
                "timestamp_utc": when.isoformat(),
                "sgp4_altitude_km": raw_summary["altitude"],
                "sgp4_velocity_km_s": raw_summary["velocity"],
                "output_altitude_km": out_summary["altitude"],
                "output_velocity_km_s": out_summary["velocity"],
                "output_true_anomaly_deg": out_summary["coe"]["nu"],
                "ml_used": ml_status.get("used", False),
            }
        )
    return rows


def compute_orbit():
    line1, line2 = get_tle()
    sat = EarthSatellite(line1, line2, SAT_NAME, ts)
    now = utc_now()
    jd, fr, r_raw, v_raw, r, v, ml_status = state_from_tle(sat, now)
    raw = state_summary(r_raw, v_raw, now, sat, jd, fr)
    output = state_summary(r, v, now, sat, jd, fr)

    with _lock:
        source = _cache["tle_src"]
        tle_at = float(_cache["tle_at"] or 0)

    # ── Vectorized elevation/azimuth profile + ground track ──────────────────
    # Single Skyfield batch call: avoids 80 individual propagations and keeps
    # API latency well under 200 ms.
    # Ground track window: -40 min (past) → +80 min (future) = 120 points.
    from skyfield.api import wgs84
    gs_sf = wgs84.latlon(GS_LAT, GS_LON, elevation_m=GS_ALT_KM * 1000)

    # 80-point window for elevation/azimuth profile (same as before)
    dt_elev = [now + timedelta(minutes=i) for i in range(-40, 40)]
    step_ts_elev = ts.from_datetimes(dt_elev)
    topocentric_batch = (sat - gs_sf).at(step_ts_elev)
    alt_angles, az_angles, _ = topocentric_batch.altaz()
    elevation_profile = [round(float(e), 2) for e in alt_angles.degrees]
    azimuth_profile   = [round(float(a), 2) for a in az_angles.degrees]

    # 120-point ground track: sub-satellite lat/lon for map rendering
    dt_track = [now + timedelta(minutes=i) for i in range(-40, 80)]
    step_ts_track = ts.from_datetimes(dt_track)
    geocentric_track = sat.at(step_ts_track)
    subpoints = wgs84.subpoint_of(geocentric_track)
    track_lats = as_sequence(subpoints.latitude.degrees, 120)
    track_lons = as_sequence(subpoints.longitude.degrees, 120)
    track_alts = as_sequence(subpoints.elevation.km, 120)
    ground_track = [
        {
            "lat": round(float(track_lats[i]), 4),
            "lon": round(float(track_lons[i]), 4),
            "alt": round(float(track_alts[i]), 2),
            "t":   i - 40,          # minutes offset from now (negative = past)
        }
        for i in range(120)
    ]

    horizon_minutes = [0, 10, 30, 60, 120, 360, 1440]
    output.update(
        {
            "raw_sgp4": {
                "altitude": raw["altitude"],
                "velocity": raw["velocity"],
                "pos_eci": raw["pos_eci"],
                "vel_eci": raw["vel_eci"],
            },
            "forecast": build_forecast(sat, now, horizon_minutes),
            "elevation_profile": elevation_profile,
            "azimuth_profile": azimuth_profile,
            "ground_track": ground_track,
            "ground_station": {"lat": GS_LAT, "lon": GS_LON, "alt_km": GS_ALT_KM, "name": "Beni Suef GS"},
            "tle_source": source,
            "tle_age_hr": round((time.time() - tle_at) / 3600, 4) if tle_at else None,
            "ai_active": bool(ml_status.get("used")),
            "ml": ml_status,
        }
    )
    return output


def load_csv():
    with _lock:
        if _cache["df"] is not None:
            return _cache["df"]
    try:
        df = pd.read_csv(DATA_DIR / "43880.csv", parse_dates=["timestamp"])
        df = df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
        with _lock:
            _cache["df"] = df
        print(f"[CSV] Loaded {len(df)} telemetry rows")
        return df
    except Exception as exc:
        print(f"[CSV] Error: {exc}")
        return None


def get_telemetry():
    df = load_csv()
    if df is None or df.empty:
        return {"error": "telemetry CSV unavailable"}
    row = df.iloc[-1]
    last20 = df.tail(20)
    return {
        "timestamp": str(row["timestamp"]),
        "batt_a_voltage": rounded(row.get("batt_a_voltage"), 3),
        "batt_b_voltage": rounded(row.get("batt_b_voltage"), 3),
        "batt_voltage_avg": rounded((row.get("batt_a_voltage") + row.get("batt_b_voltage")) / 2, 3),
        "batt_a_current": rounded(row.get("batt_a_current"), 4),
        "batt_b_current": rounded(row.get("batt_b_current"), 4),
        "power_consumption": rounded(row.get("power_consumption"), 4),
        "temp_obc": rounded(row.get("temp_obc"), 1),
        "temp_batt_a": rounded(row.get("temp_batt_a"), 1),
        "temp_batt_b": rounded(row.get("temp_batt_b"), 1),
        "temp_panel_z": rounded(row.get("temp_panel_z"), 1),
        "uptime_sec": int(row["uptime"]) if finite_float(row.get("uptime")) is not None else None,
        "pass_id": int(row["pass_id"]) if finite_float(row.get("pass_id")) is not None else None,
        "frame_count": int(row["pass_frame_count"]) if finite_float(row.get("pass_frame_count")) is not None else None,
        "volt_trend": rounded(last20["batt_a_voltage"].mean(), 3) if "batt_a_voltage" in last20 else None,
        "temp_trend": rounded(last20["temp_obc"].mean(), 1) if "temp_obc" in last20 else None,
        "total_frames": len(df),
        "total_passes": int(df["pass_id"].dropna().nunique()) if "pass_id" in df else None,
    }


def get_telemetry_history(limit=50):
    df = load_csv()
    if df is None or df.empty:
        return []
    columns = ["timestamp", "batt_a_voltage", "batt_b_voltage", "temp_obc", "power_consumption"]
    sub = df.tail(limit)[columns].copy()
    sub["timestamp"] = sub["timestamp"].astype(str)
    return sub.where(pd.notna(sub), None).to_dict(orient="records")


def get_passes():
    try:
        df = pd.read_csv(DATA_DIR / "visible_passes.csv")
        df = df[df["norad_id"] == NORAD_ID].copy()
        out = []
        for _, row in df.iterrows():
            out.append(
                {
                    "name": row["name"],
                    "rise_time": str(row["rise_time"]),
                    "peak_time": str(row["peak_time"]),
                    "set_time": str(row["set_time"]),
                    "max_elevation": rounded(row["max_elev"], 1),
                    "duration_min": rounded(row["duration_min"], 1),
                    "frequency": rounded(row["frequency"], 3),
                    "mode": row["mode"],
                }
            )
        return out
    except Exception as exc:
        print(f"[PASSES] {exc}")
        return []


def risk_level(probability, miss_km):
    if probability is None or miss_km is None:
        return "UNVERIFIED", "dim"
    if probability >= 1e-4 or miss_km <= 1.0:
        return "CRITICAL", "danger"
    if probability >= 1e-5 or miss_km <= 2.0:
        return "HIGH RISK", "warning"
    if probability >= 1e-6 or miss_km <= 5.0:
        return "WARNING", "warning"
    return "NOMINAL", "success"


def get_threats():
    if not CONJUNCTION_PATH.exists():
        return []
    try:
        df = pd.read_csv(CONJUNCTION_PATH)
        rows = []
        now = utc_now()
        for _, row in df.iterrows():
            tca_value = row.get("tca_utc") or row.get("tca_iso")
            if pd.isna(tca_value):
                continue
            tca = pd.to_datetime(tca_value, utc=True).to_pydatetime()
            tca_offset_min = (tca - now).total_seconds() / 60
            
            if tca_offset_min < 0:
                continue
                
            miss_km = rounded(row.get("miss_km"), 3)
            probability = finite_float(row.get("collision_probability"))
            level, badge = risk_level(probability, miss_km)
            rows.append(
                {
                    "threatId": str(row.get("secondary_object", row.get("threatId", "UNKNOWN"))),
                    "norad": int(row["secondary_norad"]) if finite_float(row.get("secondary_norad")) is not None else None,
                    "tca_utc": tca.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "tca_iso": tca.isoformat(),
                    "tca_offset_min": round(tca_offset_min, 3),
                    "miss_km": miss_km,
                    "prob": f"{probability:.3e}" if probability is not None else None,
                    "collision_probability": probability,
                    "level": level,
                    "badgeClass": badge,
                    "source": CONJUNCTION_PATH.name,
                }
            )
            
        def risk_score(item):
            levels = {"CRITICAL": 0, "HIGH RISK": 1, "WARNING": 2, "NOMINAL": 3, "UNVERIFIED": 4}
            return levels.get(item["level"], 5)
            
        return sorted(rows, key=lambda item: (risk_score(item), item["miss_km"] if item["miss_km"] is not None else float('inf'), item["tca_iso"]))
    except Exception as exc:
        print(f"[THREATS] {exc}")
        return []


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "dashboard.html", media_type="text/html; charset=utf-8")


@app.get("/api/orbit")
def api_orbit():
    try:
        return JSONResponse(compute_orbit())
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=503)


@app.get("/api/telemetry")
def api_telemetry():
    return JSONResponse(get_telemetry())


@app.get("/api/telemetry/history")
def api_telemetry_history():
    return JSONResponse(get_telemetry_history(50))


@app.get("/api/passes")
def api_passes():
    return JSONResponse(get_passes())


@app.get("/api/threats")
def api_threats():
    return JSONResponse(get_threats())


@app.get("/api/tle")
def api_tle():
    try:
        line1, line2 = get_tle()
    except Exception as exc:
        return JSONResponse(
            {
                "line0": SAT_NAME,
                "line1": None,
                "line2": None,
                "source": "unavailable",
                "error": str(exc),
                "age_sec": None,
                "next_refresh_sec": 0,
            },
            status_code=503,
        )
    with _lock:
        source = _cache["tle_src"]
        tle_at = float(_cache["tle_at"] or 0)
    age = time.time() - tle_at
    return JSONResponse(
        {
            "line0": SAT_NAME,
            "line1": line1,
            "line2": line2,
            "source": source,
            "age_sec": round(age, 1),
            "next_refresh_sec": max(0, round(TLE_REFRESH_SEC - age, 1)),
        }
    )


@app.post("/api/tle/update")
def api_update_tle():
    ok = fetch_tle(force=True)
    if not ok:
        raise HTTPException(status_code=503, detail="Could not fetch a real TLE from CelesTrak and no cache is available.")
    return api_tle()


@app.get("/api/ml/status")
def api_ml_status():
    with _lock:
        return JSONResponse(dict(_cache["model_status"] or {}))


@app.get("/api/status")
def api_status():
    with _lock:
        has_tle = _cache["tle1"] is not None
        source = _cache["tle_src"]
        ml_status = dict(_cache["model_status"] or {})
    df = load_csv()
    return JSONResponse(
        {
            "status": "online",
            "tle_loaded": has_tle,
            "tle_source": source,
            "csv_rows": len(df) if df is not None else 0,
            "server_time_utc": utc_now().isoformat(),
            "ground_station": {"lat": GS_LAT, "lon": GS_LON, "alt_km": GS_ALT_KM},
            "satellite": {"name": SAT_NAME, "norad": NORAD_ID},
            "ml": ml_status,
            "conjunction_events_loaded": CONJUNCTION_PATH.exists(),
        }
    )


if __name__ == "__main__":
    print("=" * 60)
    print("  UWE-4 Passive Ground Station Backend - FastAPI v12.1")
    print(f"  Satellite : {SAT_NAME} (NORAD {NORAD_ID})")
    print(f"  Ground Stn: Beni Suef University, Egypt ({GS_LAT}N, {GS_LON}E)")
    print("=" * 60)
    print("[INIT] Loading cached TLE, then refreshing from CelesTrak when available...")
    load_cached_tle()
    fetch_tle()
    print("[INIT] Loading telemetry CSV...")
    load_csv()
    print("[INIT] Starting FastAPI server on http://localhost:8000")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")), log_level="info")
