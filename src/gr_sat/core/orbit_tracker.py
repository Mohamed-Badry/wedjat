"""
Core orbital tracking physics engine.
Ports the valid math from the AI-Enhanced-Ground-Station prototype 
into our core conventions, replacing the monolithic architecture.
"""
import math
import numpy as np
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from skyfield.api import Topos, EarthSatellite, load
from typing import Optional, List, Dict

from gr_sat.core.config import GS_LATITUDE, GS_LONGITUDE, GS_ELEVATION, GS_NAME
from gr_sat.core.orbit_decay import get_satellite, ttl_cache  # Re-use our centralized loader

# --- Pydantic Models ---

class OrbitalElements(BaseModel):
    semi_major_axis_km: float
    eccentricity: float
    inclination_deg: float
    raan_deg: float
    arg_perigee_deg: float
    mean_anomaly_deg: float
    true_anomaly_deg: float
    period_min: float
    mean_motion_rev_day: float
    apogee_km: float
    perigee_km: float
    angular_velocity_deg_min: float
    time_since_perigee_min: float
    time_to_perigee_min: float
    radial_distance_km: float
    bstar: str

class GroundStationView(BaseModel):
    azimuth_deg: float
    elevation_deg: float
    range_km: float
    doppler_khz: float

class SatelliteState(BaseModel):
    timestamp_utc: str
    altitude_km: float
    velocity_km_s: float
    latitude_deg: float
    longitude_deg: float
    pos_eci: dict
    vel_eci: dict
    coe: OrbitalElements
    ground_station: GroundStationView

class TrackPoint(BaseModel):
    lat: float
    lon: float
    alt_km: float
    t_offset_min: int

class ForecastPoint(BaseModel):
    label: str
    minutes: int
    timestamp_utc: str
    altitude_km: float
    velocity_km_s: float
    true_anomaly_deg: float

class TrackerSnapshot(BaseModel):
    state: SatelliteState
    forecast: List[ForecastPoint]
    elevation_profile: List[float]
    azimuth_profile: List[float]
    ground_track: List[TrackPoint]
    ground_station: dict
    tle_source: str
    tle_age_hr: Optional[float]


# --- Physics Math (Ported from Prototype) ---

MU = 398600.4418  # km^3/s^2
R_EARTH = 6371.01 # km

def mag(v):
    return math.sqrt(sum(x*x for x in v))

def cross(a, b):
    return [a[1]*b[2] - a[2]*b[1], a[2]*b[0] - a[0]*b[2], a[0]*b[1] - a[1]*b[0]]

def dot(a, b):
    return sum(x*y for x, y in zip(a, b))

def eccentricity_vec(r, v):
    r_mag = mag(r)
    v_mag = mag(v)
    rv_dot = dot(r, v)
    c1 = (v_mag**2 - MU/r_mag)
    c2 = rv_dot
    return [(c1*rx - c2*vx)/MU for rx, vx in zip(r, v)]

def gmst(jd):
    # GMST approximation
    T = (jd - 2451545.0) / 36525.0
    theta = 280.46061837 + 360.98564736629*(jd - 2451545.0) + 0.000387933*T*T - (T**3)/38710000.0
    return (theta % 360) * math.pi/180.0

def range_rate(r_eci, v_eci, glat, glon, theta):
    glat_rad = math.radians(glat)
    r_gs_eci = [
        R_EARTH * math.cos(glat_rad) * math.cos(theta),
        R_EARTH * math.cos(glat_rad) * math.sin(theta),
        R_EARTH * math.sin(glat_rad)
    ]
    w_earth = 7.2921159e-5
    v_gs_eci = [-w_earth * r_gs_eci[1], w_earth * r_gs_eci[0], 0]
    
    rho = [r - g for r, g in zip(r_eci, r_gs_eci)]
    rho_dot = [vr - vg for vr, vg in zip(v_eci, v_gs_eci)]
    rho_mag = mag(rho)
    if rho_mag == 0: return 0.0
    return dot(rho, rho_dot) / rho_mag

def compute_orbital_elements(r, v) -> OrbitalElements:
    r_mag = mag(r)
    v_mag = mag(v)
    h = cross(r, v)
    h_mag = mag(h)
    
    n_vec = [-h[1], h[0], 0]
    n_mag = mag(n_vec)
    
    e_vec = eccentricity_vec(r, v)
    e = mag(e_vec)
    
    energy = (v_mag**2)/2.0 - MU/r_mag
    if energy >= 0:
        a = float('inf')
        period = 0.0
        n_rev = 0.0
    else:
        a = -MU / (2.0 * energy)
        period = 2.0 * math.pi * math.sqrt((a**3)/MU) / 60.0
        n_rev = 1440.0 / period if period > 0 else 0
        
    i = math.acos(h[2]/h_mag) if h_mag > 0 else 0
    
    raan = 0.0
    if n_mag > 0:
        raan = math.acos(n_vec[0]/n_mag)
        if n_vec[1] < 0: raan = 2.0*math.pi - raan
        
    omega = 0.0
    if n_mag > 0 and e > 0:
        omega = math.acos(dot(n_vec, e_vec)/(n_mag*e))
        if e_vec[2] < 0: omega = 2.0*math.pi - omega
        
    nu = 0.0
    if e > 0:
        try:
            val = max(-1.0, min(1.0, dot(e_vec, r)/(e*r_mag)))
            nu = math.acos(val)
            if dot(r, v) < 0: nu = 2.0*math.pi - nu
        except ValueError:
            pass
            
    E = 0.0
    M = 0.0
    if e < 1:
        E = 2.0 * math.atan(math.sqrt((1-e)/(1+e)) * math.tan(nu/2.0))
        M = E - e*math.sin(E)
        if M < 0: M += 2.0*math.pi
        
    apogee = a*(1+e) - R_EARTH
    perigee = a*(1-e) - R_EARTH
    
    angular_velocity = (math.sqrt(MU * a * (1-e**2)) / (r_mag**2)) * (180/math.pi) * 60
    
    ts = load.timescale()
    time_since_p = (M / (2*math.pi)) * period if period > 0 else 0
    time_to_p = period - time_since_p if period > 0 else 0

    return OrbitalElements(
        semi_major_axis_km=a,
        eccentricity=e,
        inclination_deg=math.degrees(i),
        raan_deg=math.degrees(raan),
        arg_perigee_deg=math.degrees(omega),
        mean_anomaly_deg=math.degrees(M),
        true_anomaly_deg=math.degrees(nu),
        period_min=period,
        mean_motion_rev_day=n_rev,
        apogee_km=apogee,
        perigee_km=perigee,
        angular_velocity_deg_min=angular_velocity,
        time_since_perigee_min=time_since_p,
        time_to_perigee_min=time_to_p,
        radial_distance_km=r_mag,
        bstar="N/A" # Will fill later
    )

def compute_look_angles(sat, t, gs):
    difference = sat - gs
    topocentric = difference.at(t)
    alt, az, distance = topocentric.altaz()
    return az.degrees, alt.degrees, distance.km


# --- Main Pipeline ---

def build_forecast(sat: EarthSatellite, ts, now, horizons) -> List[ForecastPoint]:
    forecast = []
    for h in horizons:
        t_f = now + timedelta(minutes=h.minutes)
        t_sky = ts.utc(t_f.year, t_f.month, t_f.day, t_f.hour, t_f.minute, t_f.second)
        geocentric = sat.at(t_sky)
        pos = geocentric.position.km
        vel = geocentric.velocity.km_per_s
        subpoint = geocentric.subpoint()
        
        coe = compute_orbital_elements(pos, vel)
        
        forecast.append(ForecastPoint(
            label=h.label,
            minutes=h.minutes,
            timestamp_utc=t_f.isoformat(),
            altitude_km=subpoint.elevation.km,
            velocity_km_s=mag(vel),
            true_anomaly_deg=coe.true_anomaly_deg
        ))
    return forecast

class HorizonPoint:
    def __init__(self, label, minutes):
        self.label = label
        self.minutes = minutes

@ttl_cache(ttl_seconds=5)
def compute_tracker_snapshot(norad_id: int) -> TrackerSnapshot:
    sat = get_satellite(norad_id)
    if not sat:
        raise ValueError(f"Could not load TLE for NORAD {norad_id}")
        
    ts = load.timescale()
    now = datetime.now(timezone.utc)
    t = ts.utc(now.year, now.month, now.day, now.hour, now.minute, now.second)
    
    # 1. Current State
    geocentric = sat.at(t)
    subpoint = geocentric.subpoint()
    pos_eci = geocentric.position.km
    vel_eci = geocentric.velocity.km_per_s
    
    gs = Topos(latitude_degrees=GS_LATITUDE, longitude_degrees=GS_LONGITUDE, elevation_m=GS_ELEVATION)
    
    az, el, rng = compute_look_angles(sat, t, gs)
    theta = gmst(t.tt + 2400000.5)
    rr = range_rate(pos_eci, vel_eci, GS_LATITUDE, GS_LONGITUDE, theta)
    doppler_khz = (-rr / 299792.458) * 435.6e3
    
    coe = compute_orbital_elements(pos_eci, vel_eci)
    coe.bstar = f"{sat.model.bstar:.4e}" if hasattr(sat.model, 'bstar') else "0.0"
    
    state = SatelliteState(
        timestamp_utc=now.isoformat(),
        altitude_km=subpoint.elevation.km,
        velocity_km_s=mag(vel_eci),
        latitude_deg=subpoint.latitude.degrees,
        longitude_deg=subpoint.longitude.degrees,
        pos_eci={"x": pos_eci[0], "y": pos_eci[1], "z": pos_eci[2]},
        vel_eci={"x": vel_eci[0], "y": vel_eci[1], "z": vel_eci[2]},
        coe=coe,
        ground_station=GroundStationView(
            azimuth_deg=az,
            elevation_deg=el,
            range_km=rng,
            doppler_khz=doppler_khz
        )
    )
    
    # 2. Forecast
    horizons = [
        HorizonPoint("Now", 0),
        HorizonPoint("+10m", 10),
        HorizonPoint("+30m", 30),
        HorizonPoint("+1h", 60),
        HorizonPoint("+2h", 120),
        HorizonPoint("+6h", 360),
        HorizonPoint("+24h", 1440)
    ]
    forecast = build_forecast(sat, ts, now, horizons)
    
    # 3. Profiles & Ground Track
    el_prof = []
    az_prof = []
    track = []
    
    for m in range(-40, 81):
        dt = now + timedelta(minutes=m)
        t_i = ts.utc(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
        pos = sat.at(t_i)
        
        difference = sat - gs
        topocentric = difference.at(t_i)
        alt, az_, distance = topocentric.altaz()
        el_prof.append(alt.degrees)
        az_prof.append(az_.degrees)
        
        sub = pos.subpoint()
        track.append(TrackPoint(
            lat=sub.latitude.degrees,
            lon=sub.longitude.degrees,
            alt_km=sub.elevation.km,
            t_offset_min=m
        ))
        
    age_hr = None
    if hasattr(sat, 'epoch'):
        age_hr = (now - sat.epoch.utc_datetime()).total_seconds() / 3600.0
        
    return TrackerSnapshot(
        state=state,
        forecast=forecast,
        elevation_profile=el_prof,
        azimuth_profile=az_prof,
        ground_track=track,
        ground_station={
            "lat": GS_LATITUDE,
            "lon": GS_LONGITUDE,
            "alt_km": GS_ELEVATION / 1000.0,
            "name": GS_NAME
        },
        tle_source="CelesTrak / Cache",
        tle_age_hr=age_hr
    )
