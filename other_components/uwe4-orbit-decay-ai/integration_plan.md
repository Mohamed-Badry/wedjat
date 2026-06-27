# Integration & Refactoring Plan: UWE-4 Orbit Decay AI

This component aims to predict the altitude decay of UWE-4 over 7-day and 30-day horizons by merging Space-Track General Perturbations (TLEs) with CelesTrak Space Weather data (F10.7 flux, Kp/Ap indices). While the data pipeline is functional, the scientific methodology and the deployment architecture have significant flaws that must be addressed before integration into our core repository.

## 1. Deep Scientific & Methodological Flaws

### A. The Black-Box Time-Series Formulation
- **Flaw:** The model predicts the total altitude drop exactly 7 or 30 days in the future in a single shot using algorithms like Random Forests, Ridge Regression, or ExtraTrees.
- **Why it's bad:** Orbit decay is fundamentally governed by atmospheric drag ($a_{drag}$), which is a physically-integrable process over time. By forcing a black-box regression to skip intermediate days and predict the 30-day delta directly, the model ignores the laws of orbital mechanics (energy conservation) and becomes purely statistical. It cannot respond to sudden mid-month solar storms because the regression maps today's weather to a drop 30 days from now. 

### B. Time-Series Target/Feature Leakage
- **Flaw:** The dataset uses 27-day and 81-day rolling averages of F10.7 and Ap indices, and lag features. 
- **Why it's bad:** When performing standard train/test temporal splits, the rolling windows cause immense temporal correlation between the end of the training set and the start of the test set. Without a deliberate "purge and embargo" gap (e.g., dropping 30 days of data between train and test), the model's test performance metrics will be overly optimistic due to target leakage.

### C. Deployment Architecture Failures
- **Flaw:** The standalone `app.py` FastAPI server implements a `predict_for_horizon` function that calls `pd.read_csv()` on the entire historical dataset file (`04_daily_orbit_space_weather_uwe4.csv`) on *every single incoming API request* just to extract the `tail(1)` latest row.
- **Why it's bad:** This causes catastrophic latency scaling. Loading an entire multi-year Pandas DataFrame from disk per request is completely unacceptable in production.

---

## 2. Integration & Refactoring Steps

### Phase 1: Algorithmic Overhaul (Backend Tasks)

1. **Refactor Training into Modular Scripts**
   - Discard the monolithic Jupyter notebook (`Untitled2.py`).
   - Create a clean `scripts/train_orbit_decay.py` utilizing our standard `gr_sat.ml` training pipelines.
   - We will preserve the historical CSV data they generated (so we do not need Space-Track passwords), but properly manage the temporal splits and rolling window leakages during ML evaluation.

2. **Migrate Inference to Autoregressive Standards**
   - Ideally, orbit predictions should predict the *daily* decay and auto-regress (feed the prediction back in) for 30 steps. While we will keep their single-shot 7d/30d models for now to honor their work, we must document this limitation in our backend.
   - The trained models (`.pkl`) will be moved into our `data/models/` folder and wrapped in our `ModelArtifactMetadata` schema.

### Phase 2: API Integration

1. **Incremental Daily Updates (No Space-Track Required)**
   - Create a daily background task in `src/gr_sat/core/space_weather.py` to fetch today's space weather from CelesTrak.
   - Use our new `skyfield` TLE fetcher (from the Ground Station plan) to get today's UWE-4 TLE.
   - Append exactly one row to the dataset in memory/database.

2. **Consolidate Endpoints**
   - Delete their `app.py`.
   - Add `/api/orbit/decay-prediction` to our main `src/api/operations.py`. This endpoint will load the latest row *from memory* (using our `DashboardDataRepository`) instead of running `pd.read_csv`.

### Phase 3: Dashboard Implementation (Frontend)

We will build a dedicated "Orbit Decay AI" tab inside the new "Live Tracker & Threats" page:
1. **Forecast Chart:** A time-series chart showing historical altitude for the past 90 days, extending 30 days into the future with the AI's predicted trajectory and a shaded confidence interval.
2. **Space Weather Gauges:** Live indicators for current F10.7 Solar Flux and Kp Index to provide context for high-drag days.
3. **Model Diagnostics:** Display the MAE and RMSE metrics for the 7d and 30d models, confirming transparency for the user.
