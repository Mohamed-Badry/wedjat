import sys
import pandas as pd
from datetime import datetime, timedelta
sys.path.append("src")
from gr_sat.core.orbit_decay import fetch_latest_space_weather, PredictOrbitDecay
weather = fetch_latest_space_weather()
forecasts = PredictOrbitDecay(43880, weather, alt_km=500.0)
for f in forecasts:
    print(f"{f.horizon}: {f.predicted_decay_km}")
