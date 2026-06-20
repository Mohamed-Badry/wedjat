from skyfield.api import load, wgs84
import pandas as pd
from pathlib import Path
import datetime

# --- Configuration ---
LOCATION_NAME = "Beni Suef, Egypt"
LATITUDE = 29.0661
LONGITUDE = 31.0994
ELEVATION_M = 32.0
MIN_ALTITUDE_DEG = 30.0  # Filter for high quality passes
DAYS_TO_PREDICT = 3

DATA_DIR = Path("data")
INPUT_FILE = DATA_DIR / "golden_candidates.csv"
OUTPUT_FILE = DATA_DIR / "visible_passes.csv"

# CelesTrak TLE URL (Active Satellites)
TLE_URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"


def main():
    if not INPUT_FILE.exists():
        print(f"Error: {INPUT_FILE} not found. Run analysis first.")
        return

    print(f"Loading candidates from {INPUT_FILE}...")
    candidates = pd.read_csv(INPUT_FILE)

    # Ensure norad_cat_id is integer for matching
    # Some datasets might have float 12345.0
    candidates["norad_cat_id"] = (
        pd.to_numeric(candidates["norad_cat_id"], errors="coerce").fillna(0).astype(int)
    )
    target_ids = set(candidates["norad_cat_id"].tolist())

    print(f"Targeting {len(target_ids)} satellites from the Golden Cohort.")

    print("Fetching TLE data from CelesTrak (this may take a moment)...")
    from skyfield.api import Loader
    custom_loader = Loader(str(DATA_DIR))
    filename = "celestrak_active.txt"
    file_path = DATA_DIR / filename
    
    reload = True
    if file_path.exists():
        if custom_loader.days_old(filename) < 0.25:
            reload = False
            print("Using recently cached TLEs.")
            
    try:
        satellites = custom_loader.tle_file(TLE_URL, filename=filename, reload=reload)
    except Exception as e:
        print(f"Warning: Failed to fetch new TLEs: {e}")
        print("Attempting to fallback to stale cache...")
        satellites = custom_loader.tle_file(TLE_URL, filename=filename, reload=False)

    # Filter for our targets
    {sat.name: sat for sat in satellites}
    by_id = {sat.model.satnum: sat for sat in satellites}

    my_sats = []
    found_count = 0

    for nid in target_ids:
        if nid in by_id:
            my_sats.append(by_id[nid])
            found_count += 1

    print(f"Found TLEs for {found_count} of {len(target_ids)} candidates.")

    # Setup Location
    ts = load.timescale()
    t0 = ts.now()
    t1 = ts.from_datetime(t0.utc_datetime() + datetime.timedelta(days=DAYS_TO_PREDICT))

    ground_station = wgs84.latlon(LATITUDE, LONGITUDE, elevation_m=ELEVATION_M)

    print(
        f"Calculating passes for {LOCATION_NAME} over the next {DAYS_TO_PREDICT} days..."
    )
    print(f"Filter: Max Elevation > {MIN_ALTITUDE_DEG}°")

    pass_data = []

    for sat in my_sats:
        # find_events returns: times, events (0=rise, 1=culminate, 2=set)
        times, events = sat.find_events(ground_station, t0, t1, altitude_degrees=0.0)

        # We need to group events into passes (Rise -> Set)
        # Simplified: Iterate through events
        current_rise = None

        for ti, event in zip(times, events):
            if event == 0:  # Rise
                current_rise = ti
            elif event == 2:  # Set
                if current_rise is not None:
                    # We have a complete pass, find max elevation
                    # It's usually roughly between rise and set
                    # Ideally we check the culmination event if it exists in between

                    # Let's verify peak altitude
                    # (Simplified: check mid-point or just use culmination if provided by find_events)
                    # Actually find_events gives 0,1,2. 1 is culmination.
                    pass
                current_rise = None

        # Re-run with finding culmination to get exact max alt
        # Or just iterate: find indices where event=1
        for i in range(len(events)):
            if events[i] == 1:  # Culminate (Max Alt)
                # Check if it has a rise before and set after ideally, but mainly check alt
                t_peak = times[i]
                alt, az, distance = (sat - ground_station).at(t_peak).altaz()

                if alt.degrees >= MIN_ALTITUDE_DEG:
                    # Find rise time (searching backwards)
                    t_rise = None
                    for j in range(i, -1, -1):
                        if events[j] == 0:
                            t_rise = times[j]
                            break

                    # Find set time (searching forwards)
                    t_set = None
                    for j in range(i, len(events)):
                        if events[j] == 2:
                            t_set = times[j]
                            break

                    if t_rise is not None and t_set is not None:
                        # Extract Name from candidates
                        cand_row = candidates[
                            candidates["norad_cat_id"] == sat.model.satnum
                        ].iloc[0]

                        pass_data.append(
                            {
                                "norad_id": sat.model.satnum,
                                "name": cand_row["amsat_name"],  # Use our clean name
                                "frequency": cand_row["primary_freq"],
                                "mode": cand_row["mode"],
                                "rise_time": t_rise.utc_iso(),
                                "peak_time": t_peak.utc_iso(),
                                "set_time": t_set.utc_iso(),
                                "max_elev": round(alt.degrees, 1),
                                "duration_min": round((t_set - t_rise) * 24 * 60, 1),
                            }
                        )

    # Output
    df_passes = pd.DataFrame(pass_data)

    if not df_passes.empty:
        # Sort by time
        df_passes = df_passes.sort_values("rise_time")

        print(f"\nFound {len(df_passes)} high-quality passes.")
        print(
            df_passes[["name", "rise_time", "max_elev", "frequency"]]
            .head(10)
            .to_string(index=False)
        )

        df_passes.to_csv(OUTPUT_FILE, index=False)
        print(f"\nDetailed schedule saved to {OUTPUT_FILE}")

        # Summary of best sats
        print("\n--- Best Performing Satellites (Most High Passes) ---")
        print(df_passes["name"].value_counts().head(5))
    else:
        print("No passes found matching criteria.")


if __name__ == "__main__":
    main()
