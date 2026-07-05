"""
Orbit Decay Model Training Pipeline
"""

import os
import json
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from loguru import logger
from typing import List, Dict, Any, Tuple

from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor, VotingRegressor
from sklearn.linear_model import BayesianRidge
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


class OrbitDecayTrainer:
    def __init__(self, norad_id: int, dataset_path: str, output_dir: str):
        self.norad_id = norad_id
        self.dataset_path = Path(dataset_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def run_pipeline(self, horizons: List[int]):
        """Executes the full training pipeline for given horizons."""
        logger.info(f"Loading dataset from {self.dataset_path}")
        df = pd.read_csv(self.dataset_path)
        df["date"] = pd.to_datetime(df["date"], utc=True)
        df = df.sort_values("date").reset_index(drop=True)
        
        for horizon in horizons:
            logger.info(f"--- Training models for {horizon}-day horizon ---")
            self._train_for_horizon(df, horizon)
            
    def _train_for_horizon(self, df: pd.DataFrame, horizon: int):
        target_col = f"target_decay_next_{horizon}d_km"
        if target_col not in df.columns:
            logger.error(f"Target column {target_col} not found in dataset. Skipping.")
            return
            
        # 1. Prepare Data
        valid_df = df.dropna(subset=[target_col]).copy()
        
        # 2. Select Features
        features = self._select_features(valid_df, target_col)
        logger.info(f"Selected {len(features)} features for {horizon}d model.")
        
        # 3. Train-Test Split (Temporal)
        train_df, test_df = self._temporal_split(valid_df)
        X_train, y_train = train_df[features], train_df[target_col]
        X_test, y_test = test_df[features], test_df[target_col]
        
        # 4. Build and Train Model Pipeline
        logger.info("Training ensemble model pipeline...")
        model = self._build_ensemble_model()
        model.fit(X_train, y_train)
        
        # 5. Evaluate
        preds = model.predict(X_test)
        mae = mean_absolute_error(y_test, preds)
        rmse = np.sqrt(mean_squared_error(y_test, preds))
        r2 = r2_score(y_test, preds)
        
        logger.info(f"Test MAE: {(mae / horizon) * 1000:.2f} m/day | RMSE: {(rmse / horizon) * 1000:.2f} m/day | R2: {r2:.3f}")
        
        # 6. Save Artifacts
        self._save_artifacts(model, features, horizon, mae, rmse, r2)
        
    def _temporal_split(self, df: pd.DataFrame, test_size: float = 0.2) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Splits the dataframe chronologically."""
        split_idx = int(len(df) * (1 - test_size))
        return df.iloc[:split_idx], df.iloc[split_idx:]
        
    def _select_features(self, df: pd.DataFrame, target_col: str) -> List[str]:
        """
        Productionized feature selection:
        Uses a proven, leak-free feature subset (PHYSICS_DECAY_BSTAR_WEATHER) if available.
        Otherwise programmatically filters out future target leakage columns.
        """
        whitelist = [
            "observed_decay_rolling_30d_km_day",
            "observed_decay_rolling_7d_km_day",
            "mean_motion_dot",
            "altitude_mean_km",
            "decay_lag_1d_km_day",
            "observed_decay_km_day",
            "bstar",
            "decay_lag_7d_km_day",
            "bstar_lag_7d",
            "bstar_lag_14d",
            "bstar_lag_30d",
            "f107_obs_rolling_27d_known_lag1d",
            "f107_obs_known_lag1d",
            "f107_adj_known_lag1d",
            "sunspot_number_known_lag1d",
            "high_solar_flux_flag_known_lag1d"
        ]
        
        # Check if we can use the whitelist
        available_whitelist = [f for f in whitelist if f in df.columns]
        if len(available_whitelist) >= 10:
            return available_whitelist
            
        forbidden = ["date", "norad_id", "satellite_name", "epoch", "creation_date", target_col]
        potential = [c for c in df.columns if c not in forbidden and pd.api.types.is_numeric_dtype(df[c])]
        
        # Drop columns containing "target" or "next" (future leakage)
        potential = [c for c in potential if "target" not in c and "next" not in c]
        
        # Drop columns containing the word 'decay' unless it's a lag or rolling average of past values
        potential = [c for c in potential if not ("decay" in c and not ("lag" in c or "rolling" in c))]
        
        # Drop high nulls
        null_ratios = df[potential].isnull().mean()
        potential = [c for c in potential if null_ratios[c] < 0.3]
        
        return potential

    def _build_ensemble_model(self):
        """Constructs a robust regression pipeline using an ensemble of models."""
        estimators = [
            ('hgb', HistGradientBoostingRegressor(max_iter=200, random_state=42)),
            ('rf', RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)),
            ('bridge', BayesianRidge())
        ]
        
        ensemble = VotingRegressor(estimators=estimators, weights=[0.5, 0.3, 0.2])
        
        pipeline = Pipeline([
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler()),
            ('ensemble', ensemble)
        ])
        
        return pipeline
        
    def _save_artifacts(self, model: Pipeline, features: List[str], horizon: int, mae: float, rmse: float, r2: float):
        model_path = self.output_dir / f"uwe4_production_model_{horizon}d.pkl"
        feature_path = self.output_dir / f"uwe4_production_features_{horizon}d.json"
        metrics_path = self.output_dir / f"uwe4_production_metrics_{horizon}d.json"
        registry_path = self.output_dir / "uwe4_production_model_registry.json"
        
        joblib.dump(model, model_path)
        with open(feature_path, "w") as f:
            json.dump(features, f, indent=4)
        
        # Write metrics JSON
        from datetime import datetime, timezone
        metrics = {
            "satellite": "UWE-4",
            "norad_id": self.norad_id,
            "horizon_days": horizon,
            "target_col": f"target_decay_next_{horizon}d_km",
            "model_type": "VotingRegressor(HGB+RF+BayesianRidge)",
            "test_metrics": {
                "MAE_total_km": mae,
                "RMSE_total_km": rmse,
                "R2": r2,
                "MAE_m_day": (mae / horizon) * 1000,
                "RMSE_m_day": (rmse / horizon) * 1000,
            },
            "feature_count": len(features),
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        with open(metrics_path, "w") as f:
            json.dump(metrics, f, indent=4)
        
        # Update or create model registry
        if registry_path.exists():
            with open(registry_path, "r") as f:
                registry = json.load(f)
        else:
            registry = {
                "satellite": "UWE-4",
                "norad_id": self.norad_id,
                "models": {}
            }
        
        key = f"{horizon}d"
        registry["models"][key] = {
            "horizon_days": horizon,
            "model_name": "VotingRegressor(HGB+RF+BayesianRidge)",
            "model_file": f"uwe4_production_model_{horizon}d.pkl",
            "features_file": f"uwe4_production_features_{horizon}d.json",
            "metrics_file": f"uwe4_production_metrics_{horizon}d.json",
            "target_column": f"target_decay_next_{horizon}d_km",
            "feature_group": "PHYSICS_DECAY_BSTAR_WEATHER",
            "selected_features_count": len(features),
        }
        registry["created_at_utc"] = datetime.now(timezone.utc).isoformat()
        registry["production_model"] = "VotingRegressor(HGB+RF+BayesianRidge)"
        
        with open(registry_path, "w") as f:
            json.dump(registry, f, indent=4)
            
        logger.success(f"Saved {horizon}d model to {model_path}")
