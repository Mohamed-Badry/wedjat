# ⚠️ LEGACY ARCHIVE: UWE-4 Orbit Decay AI Prototype

> [!WARNING]
> **This directory contains legacy prototype code and is NOT production-ready.**
> The code and notebooks here represent early experimental scripts developed separately to sweep models. They contain suboptimal engineering practices and hardcoded paths. 

## Status & Migration
* **Do Not Deploy:** This directory is preserved strictly for historical reference.
* **Production Core:** The robust orbit decay pipeline (incorporating NRLMSISE-00 atmospheric density and Skyfield propagation) has been cleanly integrated into the primary project space:
  - Core Module: [src/gr_sat/core/orbit_decay.py](file:///home/crim/Projects/gr_sat/src/gr_sat/core/orbit_decay.py)
  - Backend API: [src/api/dashboard_data.py](file:///home/crim/Projects/gr_sat/src/api/dashboard_data.py)
  - Frontend Panel: [frontend/src/routes/(dashboard)/dashboard/orbit-decay/](file:///home/crim/Projects/gr_sat/frontend/src/routes/(dashboard)/dashboard/orbit-decay/)

---

# Original Prototype README Below

# UWE-4 AI Orbit Decay Prediction

This project predicts the orbit decay of the UWE-4 CubeSat using historical TLE/GP data, space weather data, and machine learning.

## Project Objective

The system predicts future orbital decay for UWE-4 after:

- 7 days
- 30 days

It uses real orbital parameters and space weather indicators instead of assuming a fixed decay rate.

## Data Sources

- Space-Track GP/TLE history for UWE-4
- CelesTrak Space Weather data

## Main Features

The model uses features such as:

- Mean altitude
- Perigee altitude
- Apogee altitude
- Semi-major axis
- Mean motion
- Eccentricity
- BSTAR
- Recent decay rates
- F10.7 solar flux
- Kp index
- Ap index
- Sunspot number

## Final Production Models

### 7-Day Prediction

- Model: Ridge Regression
- MAE: approximately 23.90 m/day
- Improvement over baseline: approximately 18.83%

### 30-Day Prediction

- Model: Bayesian Ridge Regression
- MAE: approximately 20.09 m/day
- Improvement over baseline: approximately 9.79%

## API Usage

Install dependencies:

pip install -r requirements.txt

Run the API:

uvicorn api.app:app --reload

Open API documentation:

http://127.0.0.1:8000/docs

## API Endpoints

- GET /
- GET /health
- GET /model-info
- GET /latest-prediction
- GET /predict/7
- GET /predict/30

## Dashboard

Open the dashboard file:

reports/dashboard/uwe4_orbit_decay_dashboard.html

## Important Security Note

Do not upload Space-Track username or password to GitHub. Use environment variables or a local .env file for credentials.
