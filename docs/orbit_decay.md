# Orbit Decay AI Engine - Research & Implementation Methods

## Overview
The Orbit Decay AI predictor is a core module of the Watchdog Dashboard that forecasts atmospheric drag and orbital degradation based on real-time solar telemetry. It utilizes an ensemble machine learning approach to predict the orbital drop of amateur satellites over 7-day and 30-day horizons.

## Research Methods
The physics of low earth orbit (LEO) satellites are heavily influenced by the atmospheric density, which expands and contracts dynamically in response to space weather—specifically solar flux (F10.7) and geomagnetic storms (Kp/Ap indices).

To accurately predict orbital decay, we:
1. **Aggregated Historical Data**: Correlated historical Two-Line Element (TLE) semi-major axis data for UWE-4 (NORAD 43880) against historical space weather data from CelesTrak (`SW-All.csv`).
2. **Physics-Based Modeling**: 
   - Utilized the `skyfield` Python library to propagate TLEs and map them precisely to the WGS84 Geodetic ellipsoid, extracting the mathematically exact latitude, longitude, and elevation.
   - Passed these precise coordinates, along with both the daily F10.7 flux and the 81-day centered average (`F107A`), into the `nrlmsise00` model to calculate the exact localized atmospheric density, accounting for the diurnal atmospheric bulge and Earth's oblateness.
3. **Feature Selection**: Computed rolling averages and engineered features:
   - `F10.7_AVG`: 7-day and 30-day rolling averages of Solar Flux.
   - `KP_MAX_7D` / `KP_MAX_30D`: Max Geomagnetic Activity indices.
   - `B_COEFF`: The satellite's ballistic coefficient ($B^*$) extracted from TLEs.
4. **Machine Learning Regressor**: 
   - A Scikit-Learn `RandomForestRegressor` was trained to map these environmental parameters to the observed orbital altitude drop over a set horizon.
   - The models were strictly pinned to `scikit-learn==1.6.1` to ensure perfect deterministic loading and prevent model deserialization errors in the production FastAPI environment.

## Deployment & Productionization
The research notebooks were migrated into a modular, production-ready pipeline:
- **FastAPI Endpoint (`/api/orbit/decay-prediction`)**: Serves live inferences using pre-trained `.pkl` models.
- **Robust Centralized File Caching**: To prevent CelesTrak from IP banning our server, all outgoing requests are cached persistently to disk (e.g. `data/tle/celestrak_active.tle` and `data/cache/SW-All.csv`). We use `skyfield.api.Loader` to unify TLE parsing.
- **Offline Fallbacks**: If CelesTrak goes offline or times out on a cache reload, the system gracefully falls back to the stale cached file without crashing. If no cache exists, it defaults to a local offline dataset (`data/04_daily_orbit_space_weather_uwe4.csv`) to ensure the dashboard remains 100% operational.
- **Frontend Dashboard**: A Svelte 5 frontend component plots the live historical altitude alongside the AI ensemble predictions and 95% Confidence Intervals, featuring dynamic fallback states and automatic hot-reloading.

## Results
The trained models for UWE-4 successfully generalized the drag coefficients:
- **7-Day Horizon**: Predicting minor drops (~0.01 km) correlated directly with average space weather conditions.
- **30-Day Horizon**: Catching the compounded decay accurately (~0.15 km) with robust handling of anomalous spikes in geomagnetic storms.

The system is fully decoupled, containerized in Docker, and ready for deployment on a production VPS.
