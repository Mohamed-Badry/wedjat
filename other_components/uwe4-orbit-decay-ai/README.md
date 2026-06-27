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
