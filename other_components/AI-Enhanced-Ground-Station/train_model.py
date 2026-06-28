import argparse
import math
import os
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor
from sklearn.metrics import mean_squared_error
from sklearn.multioutput import MultiOutputRegressor


FEATURE_COLUMNS = [
    "sgp4_x_km",
    "sgp4_y_km",
    "sgp4_z_km",
    "sgp4_vx_km_s",
    "sgp4_vy_km_s",
    "sgp4_vz_km_s",
    "sgp4_altitude_km",
]

TRUTH_COLUMNS = [
    "true_x_km",
    "true_y_km",
    "true_z_km",
    "true_vx_km_s",
    "true_vy_km_s",
    "true_vz_km_s",
]

TARGET_COLUMNS = [
    "delta_x_km",
    "delta_y_km",
    "delta_z_km",
    "delta_vx_km_s",
    "delta_vy_km_s",
    "delta_vz_km_s",
]


def require_columns(df, columns):
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")


def load_real_training_rows(csv_path):
    df = pd.read_csv(csv_path)
    require_columns(df, FEATURE_COLUMNS + TRUTH_COLUMNS)
    df = df.dropna(subset=FEATURE_COLUMNS + TRUTH_COLUMNS).copy()
    if len(df) < 50:
        raise ValueError("Need at least 50 real truth/reference samples to train a verified model.")

    df["delta_x_km"] = df["true_x_km"] - df["sgp4_x_km"]
    df["delta_y_km"] = df["true_y_km"] - df["sgp4_y_km"]
    df["delta_z_km"] = df["true_z_km"] - df["sgp4_z_km"]
    df["delta_vx_km_s"] = df["true_vx_km_s"] - df["sgp4_vx_km_s"]
    df["delta_vy_km_s"] = df["true_vy_km_s"] - df["sgp4_vy_km_s"]
    df["delta_vz_km_s"] = df["true_vz_km_s"] - df["sgp4_vz_km_s"]
    return df


def temporal_split(df, test_fraction):
    split_index = int(len(df) * (1.0 - test_fraction))
    split_index = min(max(split_index, 1), len(df) - 1)
    train = df.iloc[:split_index]
    test = df.iloc[split_index:]
    return train, test


def train_and_save_model(csv_path, output_path, estimator_name):
    df = load_real_training_rows(csv_path)
    train, test = temporal_split(df, 0.2)

    if estimator_name == "extra_trees":
        base = ExtraTreesRegressor(n_estimators=400, min_samples_leaf=2, n_jobs=-1)
    else:
        base = RandomForestRegressor(n_estimators=300, min_samples_leaf=2, n_jobs=-1)

    model = MultiOutputRegressor(base)
    model.fit(train[FEATURE_COLUMNS], train[TARGET_COLUMNS])

    pred = model.predict(test[FEATURE_COLUMNS])
    truth_delta = test[TARGET_COLUMNS].to_numpy()

    pos_error = pred[:, :3] - truth_delta[:, :3]
    vel_error = pred[:, 3:] - truth_delta[:, 3:]
    position_rmse_km = math.sqrt(mean_squared_error(np.zeros_like(pos_error), pos_error))
    velocity_rmse_km_s = math.sqrt(mean_squared_error(np.zeros_like(vel_error), vel_error))
    position_mean_error_km = float(np.mean(np.sqrt(np.sum(pos_error * pos_error, axis=1))))
    velocity_mean_error_km_s = float(np.mean(np.sqrt(np.sum(vel_error * vel_error, axis=1))))

    bundle = {
        "model": model,
        "feature_columns": FEATURE_COLUMNS,
        "target_columns": TARGET_COLUMNS,
        "metrics": {
            "position_rmse_km": position_rmse_km,
            "velocity_rmse_km_s": velocity_rmse_km_s,
            "position_mean_error_km": position_mean_error_km,
            "velocity_mean_error_km_s": velocity_mean_error_km_s,
            "train_rows": int(len(train)),
            "test_rows": int(len(test)),
        },
        "training_source_csv": os.path.abspath(csv_path),
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "real_data_only": True,
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    joblib.dump(bundle, output_path)
    print(f"Saved verified-model bundle to {output_path}")
    print(f"Position RMSE: {position_rmse_km:.6f} km")
    print(f"Velocity RMSE: {velocity_rmse_km_s:.9f} km/s")


def main():
    parser = argparse.ArgumentParser(
        description="Train the orbital correction model from real reference state vectors only."
    )
    parser.add_argument("--csv", required=True, help="CSV containing SGP4 state and real truth/reference state columns.")
    parser.add_argument("--out", default="models/orbit_ai_model.pkl", help="Output joblib model bundle.")
    parser.add_argument("--estimator", choices=["extra_trees", "random_forest"], default="extra_trees")
    args = parser.parse_args()
    train_and_save_model(args.csv, args.out, args.estimator)


if __name__ == "__main__":
    main()
