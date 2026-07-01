
import os
import json
import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODELS_DIR = os.path.join(BASE_DIR, "models")
DATA_DIR = os.path.join(BASE_DIR, "data")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

DATASET_PATH = os.path.join(DATA_DIR, "04_daily_orbit_space_weather_uwe4.csv")
REGISTRY_PATH = os.path.join(MODELS_DIR, "uwe4_production_model_registry.json")
LATEST_PREDICTION_PATH = os.path.join(REPORTS_DIR, "10_latest_production_prediction.json")

app = FastAPI(
    title="UWE-4 Orbit Decay AI API",
    description="AI-based orbit decay prediction API for UWE-4 CubeSat",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_registry():
    if not os.path.exists(REGISTRY_PATH):
        raise FileNotFoundError("Production model registry not found.")

    with open(REGISTRY_PATH, "r") as f:
        return json.load(f)


def load_dataset():
    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError("Final dataset not found.")

    df = pd.read_csv(DATASET_PATH)
    df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
    df = df.sort_values("date").reset_index(drop=True)
    return df


def predict_for_horizon(horizon_days: int):
    registry = load_registry()
    df = load_dataset()

    horizon_key = f"{horizon_days}d"

    if horizon_key not in registry["models"]:
        raise ValueError(f"No production model available for {horizon_days} days.")

    model_info = registry["models"][horizon_key]

    model_path = os.path.join(MODELS_DIR, model_info["production_model_file"])
    feature_path = os.path.join(MODELS_DIR, model_info["production_feature_file"])

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")

    if not os.path.exists(feature_path):
        raise FileNotFoundError(f"Feature file not found: {feature_path}")

    model = joblib.load(model_path)

    with open(feature_path, "r") as f:
        feature_cols = json.load(f)

    latest_row = df.tail(1).copy()

    missing_features = [col for col in feature_cols if col not in latest_row.columns]

    if len(missing_features) > 0:
        raise ValueError(f"Missing features in dataset: {missing_features[:10]}")

    X_latest = latest_row[feature_cols]

    current_altitude_km = float(latest_row["altitude_mean_km"].iloc[0])
    predicted_decay_km = float(model.predict(X_latest)[0])
    predicted_altitude_km = current_altitude_km - predicted_decay_km

    metrics = model_info.get("test_metrics", {})
    baseline = model_info.get("best_baseline_metrics", {})

    return {
        "satellite": registry.get("satellite", "UWE-4"),
        "norad_id": registry.get("norad_id", 43880),
        "latest_data_date": str(latest_row["date"].iloc[0]),
        "horizon_days": horizon_days,
        "selected_model": model_info.get("selected_model_name"),
        "model_version": model_info.get("version"),
        "current_altitude_km": current_altitude_km,
        "current_perigee_km": float(latest_row["perigee_altitude_km"].iloc[0]),
        "current_apogee_km": float(latest_row["apogee_altitude_km"].iloc[0]),
        "predicted_decay_km": predicted_decay_km,
        "predicted_decay_m": predicted_decay_km * 1000,
        "predicted_decay_rate_m_day": (predicted_decay_km / horizon_days) * 1000,
        "predicted_altitude_after_horizon_km": predicted_altitude_km,
        "model_test_mae_m_day": metrics.get("MAE_m_day"),
        "model_test_rmse_m_day": metrics.get("RMSE_m_day"),
        "model_test_r2": metrics.get("R2"),
        "baseline_mae_m_day": baseline.get("MAE_m_day"),
        "improvement_vs_baseline_pct": model_info.get("improvement_vs_best_baseline_pct")
    }


@app.get("/")
def root():
    return {
        "message": "UWE-4 Orbit Decay AI API is running.",
        "available_endpoints": [
            "/health",
            "/model-info",
            "/latest-prediction",
            "/predict/7",
            "/predict/30"
        ]
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "UWE-4 Orbit Decay AI API"
    }


@app.get("/model-info")
def model_info():
    try:
        return load_registry()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/latest-prediction")
def latest_prediction():
    try:
        if not os.path.exists(LATEST_PREDICTION_PATH):
            raise FileNotFoundError("Latest prediction file not found.")

        with open(LATEST_PREDICTION_PATH, "r") as f:
            return json.load(f)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/predict/{horizon_days}")
def predict(horizon_days: int):
    if horizon_days not in [7, 30]:
        raise HTTPException(
            status_code=400,
            detail="Only 7-day and 30-day predictions are supported."
        )

    try:
        return predict_for_horizon(horizon_days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
