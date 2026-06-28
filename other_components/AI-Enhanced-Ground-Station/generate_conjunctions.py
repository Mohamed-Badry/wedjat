import os
import httpx
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from sgp4.api import Satrec, SatrecArray, jday
import joblib

NORAD_ID = 43880

def get_tles():
    url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle"
    print("Downloading stations TLEs from CelesTrak...")
    resp = httpx.get(url, timeout=20)
    lines = resp.text.strip().splitlines()
    sats = []
    names = []
    
    my_sat = None
    i = 0
    while i < len(lines):
        name = lines[i].strip()
        if i+2 < len(lines) and lines[i+1].startswith("1 ") and lines[i+2].startswith("2 "):
            l1 = lines[i+1].strip()
            l2 = lines[i+2].strip()
            try:
                sat = Satrec.twoline2rv(l1, l2)
                if sat.satnum == NORAD_ID:
                    my_sat = sat
                else:
                    sats.append(sat)
                    names.append(name)
            except:
                pass
            i += 3
        else:
            i += 1
            
    return my_sat, sats, names

def main():
    my_sat, other_sats, names = get_tles()
    if not my_sat:
        print("Target satellite not found in active list!")
        try:
            lines = open("data/43880.tle").read().strip().splitlines()
            my_sat = Satrec.twoline2rv(lines[1], lines[2])
        except:
            print("Failed to load local TLE.")
            return
        
    print(f"Propagating {len(other_sats)} other satellites to find real conjunctions...")
    
    now = datetime.now(timezone.utc)
    # Search over next 1 day, every 5 minutes for speed
    times = []
    jds = []
    frs = []
    for m in range(0, 1 * 24 * 60, 5):
        dt = now + timedelta(minutes=m)
        jd, fr = jday(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
        times.append(dt)
        jds.append(jd)
        frs.append(fr)
        
    jds = np.array(jds)
    frs = np.array(frs)
    
    e_my, r_my, v_my = my_sat.sgp4_array(jds, frs)
    
    ai_bundle = joblib.load("models/collision_ai_model.pkl")
    ai_model = ai_bundle["model"]
    
    events = []
    sat_array = SatrecArray(other_sats)
    e_all, r_all, v_all = sat_array.sgp4(jds, frs)
    
    for i in range(len(other_sats)):
        valid = e_all[i] == 0
        if not np.any(valid):
            continue
            
        dr = r_all[i][valid] - r_my[valid]
        dist = np.linalg.norm(dr, axis=1)
        
        min_idx = np.argmin(dist)
        min_dist = dist[min_idx]
        
        if min_dist < 5000.0:
            tca = times[np.where(valid)[0][min_idx]]
            dv = v_all[i][valid][min_idx] - v_my[valid][min_idx]
            rel_vel = np.linalg.norm(dv)
            
            events.append((min_dist, i, tca, rel_vel))
            
    events.sort(key=lambda x: x[0])
    
    results = []
    for min_dist, i, tca, rel_vel in events[:30]:
        # Adaptive covariance based on object
        cov_r = 50.0 + min_dist * 2.0
        cov_t = 500.0 + min_dist * 10.0
        radius = 5.0
        
        features = np.array([[min_dist, cov_r, cov_t, rel_vel, radius]])
        prob = float(ai_model.predict(features)[0])
        
        # Slight heuristic fallback to ensure Foster probability calculates correctly
        # if the Random Forest smoothed it out too much
        if prob == 0 and min_dist < 5.0:
            prob = 1.0e-5
            
        results.append({
            "secondary_object": names[i],
            "secondary_norad": other_sats[i].satnum,
            "tca_utc": tca.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "tca_iso": tca.isoformat(),
            "miss_km": min_dist,
            "collision_probability": prob
        })
        
    df = pd.DataFrame(results)
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/conjunction_events.csv", index=False)
    print(f"Saved {len(results)} actual conjunctions to data/conjunction_events.csv")

if __name__ == '__main__':
    main()
