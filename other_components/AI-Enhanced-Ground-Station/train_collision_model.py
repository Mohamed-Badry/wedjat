import math
import numpy as np
import os
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error

def calc_foster_prob(miss_km, cov_r, cov_t, combined_radius_m=10.0):
    d_m = miss_km * 1000.0
    if d_m > 10 * max(cov_r, cov_t):
        return 0.0
    r_c_sq = combined_radius_m ** 2
    sigma_xy = cov_r * cov_t
    sigma_sq = (cov_r**2 + cov_t**2) / 2.0
    exponent1 = -r_c_sq / (2.0 * sigma_xy)
    exponent2 = -(d_m**2) / (2.0 * sigma_sq)
    prob = (r_c_sq / (2.0 * math.sqrt(sigma_xy))) * math.exp(exponent2)
    return min(1.0, max(0.0, prob))

def generate_data(num_samples=50000):
    np.random.seed(42)
    miss_km = np.random.uniform(0.1, 100.0, num_samples)
    cov_r = np.random.uniform(10.0, 5000.0, num_samples)
    cov_t = np.random.uniform(50.0, 15000.0, num_samples)
    rel_vel = np.random.uniform(1.0, 15.0, num_samples)
    radius = np.random.uniform(1.0, 20.0, num_samples)
    
    y = np.zeros(num_samples)
    for i in range(num_samples):
        y[i] = calc_foster_prob(miss_km[i], cov_r[i], cov_t[i], radius[i])
        
    X = np.column_stack((miss_km, cov_r, cov_t, rel_vel, radius))
    return X, y

def main():
    print("Generating physics-based training data...")
    X, y = generate_data(20000)
    
    print("Training Random Forest Collision Probability Model...")
    model = RandomForestRegressor(n_estimators=50, max_depth=10, n_jobs=-1, random_state=42)
    model.fit(X, y)
    
    preds = model.predict(X)
    rmse = math.sqrt(mean_squared_error(y, preds))
    print(f"Model trained. RMSE: {rmse:.3e}")
    
    bundle = {
        "model": model,
        "features": ["miss_km", "cov_r_m", "cov_t_m", "rel_vel_km_s", "combined_radius_m"],
        "info": "AI model predicting collision probability based on Foster 1992 mechanics."
    }
    
    out_path = "models/collision_ai_model.pkl"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    joblib.dump(bundle, out_path)
    print(f"Saved to {out_path}")

if __name__ == '__main__':
    main()
