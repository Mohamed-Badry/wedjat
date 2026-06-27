"""Satellite pass prediction using Skyfield orbital mechanics.

Standalone module — no dependency on frame_store, scoring, or database.
"""

from __future__ import annotations

from datetime import timedelta, timezone
from typing import Any
from pathlib import Path

try:
    from .serialization import timestamp_iso
except ImportError:
    from serialization import timestamp_iso


def predict_passes(
    satellite_summaries: list[dict[str, Any]],
    lat: float,
    lon: float,
    elevation_m: float = 0.0,
    station_label: str | None = None,
    lookahead_hours: int = 24,
    min_elevation: float = 10.0,
    include_tracks: bool = True,
) -> dict[str, Any]:
    """Predict visible satellite passes for a ground station.

    Parameters
    ----------
    satellite_summaries:
        List of satellite info dicts (must contain ``norad_id`` and ``name``).
    lat, lon:
        Ground station coordinates in degrees.
    elevation_m:
        Ground station elevation in metres.
    station_label:
        Human-readable label for the station.
    lookahead_hours:
        How far ahead to search (hours).
    min_elevation:
        Minimum peak elevation in degrees to include a pass.
    include_tracks:
        Whether to sample sub-satellite ground tracks.

    Returns
    -------
    dict
        Keys: ``ground_station``, ``lookahead_hours``, ``min_elevation``, ``passes``.
    """
    from datetime import datetime

    from skyfield.api import load, wgs84

    now = datetime.now(timezone.utc)

    if not -90.0 <= lat <= 90.0:
        raise ValueError("Latitude must be between -90 and 90 degrees.")
    if not -180.0 <= lon <= 180.0:
        raise ValueError("Longitude must be between -180 and 180 degrees.")
    if not -500.0 <= elevation_m <= 10000.0:
        raise ValueError(
            "Ground station elevation must be between -500 and 10000 meters."
        )

    station_data = {
        "id": "custom",
        "label": station_label or "Custom Ground Station",
        "lat": float(lat),
        "lon": float(lon),
        "elevation_m": float(elevation_m),
    }

    gs = wgs84.latlon(
        station_data["lat"],
        station_data["lon"],
        elevation_m=station_data["elevation_m"],
    )

    from skyfield.api import Loader
    import os
    
    from gr_sat.core.config import DATA_DIR
    
    # Use a dedicated cache directory instead of polluting the current working directory
    cache_dir = DATA_DIR / "tle"
    cache_dir.mkdir(parents=True, exist_ok=True)
    custom_loader = Loader(str(cache_dir))
    
    ts = custom_loader.timescale()
    t0 = ts.from_datetime(now)
    t1 = ts.from_datetime(now + timedelta(hours=lookahead_hours))

    # Load Celestrak TLEs using skyfield
    url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"
    filename = "celestrak_active.tle"
    
    # Check if cache is older than 6 hours (0.25 days)
    reload = True
    file_path = cache_dir / filename
    if file_path.exists():
        if custom_loader.days_old(filename) < 0.25:
            reload = False
            
    try:
        tle_file = custom_loader.tle_file(url, filename=filename, reload=reload)
    except Exception as e:
        import logging
        logging.error(f"Failed to fetch TLEs: {e}")
        tle_file = None
        if file_path.exists():
            logging.info(f"Falling back to stale TLE cache in pass_predictor")
            tle_file = custom_loader.tle_file(url, filename=filename, reload=False)
            
    if tle_file:
        by_id = {sat.model.satnum: sat for sat in tle_file}
    else:
        by_id = {}

    passes: list[dict[str, Any]] = []
    for sat_info in satellite_summaries:
        sat_id = sat_info["norad_id"]
        if sat_id not in by_id:
            continue

        sat = by_id[sat_id]
        t, events = sat.find_events(gs, t0, t1, altitude_degrees=0.0)

        for i in range(len(events)):
            if events[i] != 1:  # only process culmination events
                continue

            t_peak = t[i]
            alt, az, dist = (sat - gs).at(t_peak).altaz()

            if alt.degrees < min_elevation:
                continue

            t_rise = _find_event_before(t, events, i, event_type=0)
            t_set = _find_event_after(t, events, i, event_type=2)

            if t_rise is None or t_set is None:
                continue

            # Determine general direction
            start_az = (sat - gs).at(t_rise).altaz()[1].degrees
            end_az = (sat - gs).at(t_set).altaz()[1].degrees

            direction = "N->S" if end_az > start_az else "S->N"
            if abs(start_az - end_az) > 180:  # cross 360
                direction = "S->N" if end_az < start_az else "N->S"

            pass_record: dict[str, Any] = {
                "satellite": sat_info["name"],
                "norad_id": sat_id,
                "aos": timestamp_iso(t_rise.utc_datetime()),
                "los": timestamp_iso(t_set.utc_datetime()),
                "max_elevation": round(alt.degrees, 1),
                "direction": direction,
            }
            if include_tracks:
                pass_record["track"] = _sample_track(sat, gs, ts, t_rise, t_set)
            passes.append(pass_record)

    passes.sort(key=lambda p: p["aos"])

    return {
        "ground_station": station_data,
        "lookahead_hours": lookahead_hours,
        "min_elevation": min_elevation,
        "passes": passes,
    }


# ── Private helpers ──────────────────────────────────────────────────


def _find_event_before(t, events, index: int, event_type: int):
    """Walk backward from *index* to find the nearest event of *event_type*."""
    for j in range(index, -1, -1):
        if events[j] == event_type:
            return t[j]
    return None


def _find_event_after(t, events, index: int, event_type: int):
    """Walk forward from *index* to find the nearest event of *event_type*."""
    for j in range(index, len(events)):
        if events[j] == event_type:
            return t[j]
    return None


def _sample_track(
    sat, gs, ts, t_rise, t_set, sample_count: int = 32
) -> list[dict[str, Any]]:
    """Sample the ground track of a satellite pass at *sample_count* points."""
    start_dt = t_rise.utc_datetime()
    end_dt = t_set.utc_datetime()
    duration_seconds = (end_dt - start_dt).total_seconds()
    if duration_seconds <= 0:
        return []

    track: list[dict[str, Any]] = []
    for sample_index in range(sample_count):
        offset = duration_seconds * sample_index / max(sample_count - 1, 1)
        sample_dt = start_dt + timedelta(seconds=offset)
        sample_t = ts.from_datetime(sample_dt)
        subpoint = sat.at(sample_t).subpoint()
        alt, az, distance = (sat - gs).at(sample_t).altaz()
        track.append(
            {
                "time": timestamp_iso(sample_dt),
                "lat": round(subpoint.latitude.degrees, 4),
                "lon": round(subpoint.longitude.degrees, 4),
                "elevation": round(alt.degrees, 1),
                "azimuth": round(az.degrees, 1),
                "range_km": round(distance.km, 1),
            }
        )
    return track
