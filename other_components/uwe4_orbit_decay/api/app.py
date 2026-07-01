
import json
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
REPORTS_DIR = BASE_DIR / "reports"
DASHBOARD_DIR = REPORTS_DIR / "dashboard"

DATASET_PATH = DATA_DIR / "04_daily_orbit_space_weather_uwe4.csv"
REGISTRY_PATH = MODELS_DIR / "uwe4_production_model_registry.json"
LATEST_PREDICTION_PATH = REPORTS_DIR / "10_latest_production_prediction.json"
DASHBOARD_PATH = DASHBOARD_DIR / "uwe4_orbit_decay_dashboard.html"

app = FastAPI(
    title="UWE-4 Orbit Decay AI API",
    description="FastAPI backend for UWE-4 7-day and 30-day orbit decay predictions.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def load_json(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path.name}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_dataset():
    if not DATASET_PATH.exists():
        raise FileNotFoundError("Production dataset not found.")
    df = pd.read_csv(DATASET_PATH)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
        df = df.sort_values("date").reset_index(drop=True)
    return df

def load_features(path):
    data = load_json(path)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ["features", "selected_features", "feature_cols"]:
            if key in data:
                return data[key]
    raise ValueError("Invalid features file.")

def find_float(row, cols):
    for c in cols:
        if c in row.index and pd.notna(row[c]):
            try:
                return float(row[c])
            except Exception:
                pass
    return None

def predict_horizon(horizon_days):
    registry = load_json(REGISTRY_PATH)
    df = load_dataset()

    key = f"{horizon_days}d"
    if "models" not in registry or key not in registry["models"]:
        raise ValueError(f"No model found for {horizon_days} days.")

    model_info = registry["models"][key]

    model_path = MODELS_DIR / model_info["model_file"]
    features_path = MODELS_DIR / model_info["features_file"]

    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path.name}")

    if not features_path.exists():
        raise FileNotFoundError(f"Features not found: {features_path.name}")

    model = joblib.load(model_path)
    features = load_features(features_path)

    missing = [f for f in features if f not in df.columns]
    if missing:
        raise ValueError(f"Missing features in dataset: {missing[:20]}")

    latest = df.tail(1).copy()

    X = latest[features].copy()
    for col in features:
        X[col] = pd.to_numeric(X[col], errors="coerce")

    pred_decay_km = float(model.predict(X)[0])

    row = latest.iloc[0]

    current_altitude_km = find_float(
        row,
        ["altitude_mean_km", "mean_altitude_km", "current_mean_altitude_km", "altitude_km"]
    )

    current_perigee_km = find_float(
        row,
        ["perigee_altitude_km", "perigee_km", "current_perigee_altitude_km"]
    )

    current_apogee_km = find_float(
        row,
        ["apogee_altitude_km", "apogee_km", "current_apogee_altitude_km"]
    )

    predicted_altitude_after_horizon_km = None
    if current_altitude_km is not None:
        predicted_altitude_after_horizon_km = current_altitude_km - pred_decay_km

    latest_date = None
    if "date" in latest.columns:
        latest_date = str(latest["date"].iloc[0])

    return {
        "satellite": registry.get("satellite", "UWE-4"),
        "norad_id": registry.get("norad_id", 43880),
        "latest_data_date": latest_date,
        "horizon_days": horizon_days,
        "selected_model": model_info.get("model_name"),
        "feature_group": model_info.get("feature_group"),
        "selected_features_count": model_info.get("selected_features_count"),
        "current_altitude_km": current_altitude_km,
        "current_perigee_km": current_perigee_km,
        "current_apogee_km": current_apogee_km,
        "predicted_decay_km": pred_decay_km,
        "predicted_decay_m": pred_decay_km * 1000,
        "predicted_decay_rate_m_day": (pred_decay_km / horizon_days) * 1000,
        "predicted_altitude_after_horizon_km": predicted_altitude_after_horizon_km
    }

@app.get("/")
def root():
    return {
        "message": "UWE-4 Orbit Decay AI API is running.",
        "docs": "/docs",
        "health": "/health",
        "model_info": "/model-info",
        "latest_prediction": "/latest-prediction",
        "predict_7_days": "/predict/7",
        "predict_30_days": "/predict/30",
        "dashboard": "/dashboard"
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/model-info")
def model_info():
    try:
        return load_json(REGISTRY_PATH)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/latest-prediction")
def latest_prediction():
    try:
        return load_json(LATEST_PREDICTION_PATH)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/predict/{horizon_days}")
def predict(horizon_days: int):
    if horizon_days not in [7, 30]:
        raise HTTPException(status_code=400, detail="Only 7 and 30 days are supported.")
    try:
        return predict_horizon(horizon_days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    if DASHBOARD_PATH.exists():
        return FileResponse(DASHBOARD_PATH)
    return HTMLResponse("<h2>Dashboard file not found. API is running.</h2>")
