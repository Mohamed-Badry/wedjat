# Integration & Refactoring Plan: AI-Enhanced-Ground-Station

This component aims to provide a real-time orbit propagation dashboard, AI-based corrections to SGP4, and collision probability (conjunction) warnings. However, the current implementation contains severe scientific and methodological flaws. This document outlines the step-by-step plan to resolve those flaws and integrate the component into the main architecture.

## 1. Deep Scientific & Methodological Flaws

### A. The Conjunction/Collision Model (`train_collision_model.py`)
- **Flaw:** The script implements the exact Foster 1992 mathematical formula for computing collision probability, generates random data, and then trains a *Random Forest Regressor* to predict the output of that exact math formula.
- **Why it's absurd:** Using ML to approximate a deterministic, fast, 4-line mathematical equation is completely pointless. It adds inference overhead, bloats the system with unnecessary `.pkl` files, and guarantees the predictions will have an error margin (RMSE) compared to simply calling the formula directly.

### B. The Conjunction Generator (`generate_conjunctions.py`)
- **Flaw (Step Size):** The script propagates orbits using a coarse 5-minute interval (`for m in range(0, 1 * 24 * 60, 5)`). A satellite in Low Earth Orbit (LEO) travels over 2,200 km in 5 minutes! Conjunctions happen in a fraction of a second, meaning this interval completely misses the true Time of Closest Approach (TCA).
- **Flaw (Threshold):** Because the step size is huge, it relies on a massive filter of `min_dist < 5000.0 km`. A miss distance of 5,000 km is not a conjunction; it's a completely different orbit.
- **Flaw (Fake Covariance):** It heuristically hallucinates the position uncertainty (`cov_r = 50.0 + min_dist * 2.0`) based on the inaccurate `min_dist`, meaning the collision probabilities are completely fictional.
- **Flaw (Efficiency):** It does a brute-force $O(N \times T)$ comparison of all active satellites at every time step, which scales horribly.

### C. The AI Orbit Correction (`train_model.py`)
- **Flaw:** It trains a model to take absolute Cartesian vectors (`sgp4_x_km`, `y`, `z`) and predict delta error vectors (`delta_x_km`, `y`, `z`) in the Earth-Centered Inertial (ECI) frame.
- **Why it's bad:** ECI coordinates are absolute coordinates in space that change constantly. Learning an orbital correction in absolute Cartesian coordinates using a Random Forest is physically nonsensical because the geometry is entirely dependent on the satellite's current position in its orbit and the rotation of the Earth. The model will overfit to the exact positions of the training data and fail catastrophically elsewhere.

---

## 2. Integration & Refactoring Steps

### Phase 1: Algorithmic Overhaul (Backend Tasks)

1. **Delete the Collision AI Model**
   - Discard `train_collision_model.py` and its `.pkl` bundle.
   - We will implement the Foster 1992 formula directly as a pure Python math function inside our backend.

2. **Rewrite Conjunction Generation (Astrodynamics Fix)**
   - Create a background task (`src/gr_sat/core/conjunctions.py`).
   - Implement a "Smart Sieve" (apogee/perigee altitude filtering) to instantly discard satellites that never cross UWE-4's orbital altitude band.
   - Replace the 5-minute interval brute-force search with an algorithmic root-finder (like `scipy.optimize.minimize_scalar`) to precisely pinpoint the sub-second TCA and the true minimum distance.
   - Save the results into a cached backend dataset instead of a static CSV.

3. **Fix the Orbit Correction Model (RTN Frame Transformation)**
   - Modify the training pipeline to calculate delta errors in the **RTN (Radial, Transverse, Normal)** frame instead of ECI.
   - Atmospheric drag, the primary source of SGP4 error, manifests almost entirely in the Transverse (along-track) direction.
   - The API will transform the ECI vector to RTN, query the AI model for the RTN correction, and rotate it back to ECI.

### Phase 2: API Integration

1. **Unify the TLE Management**
   - The ground station fetches current TLEs using `skyfield` (which pings CelesTrak without needing a password). We will extract this logic into a unified `src/gr_sat/core/orbit.py` module.
   - The TLE will be cached daily and kept in memory.

2. **Consolidate Endpoints**
   - Discard the separate `app.py` FastAPI server.
   - Move the orbit propagation and AI correction logic directly into `src/api/operations.py`.

### Phase 3: Dashboard Implementation (Frontend)

We will build a dedicated "Live Tracker & Threats" page (or tab) on the frontend:
1. **Live Footprint Map:** Re-implement the D3/Observable Plot 2D ground track map to show the satellite's current SGP4 footprint.
2. **Conjunction Warnings:** A data table listing upcoming real conjunctions (e.g., miss distance < 50km, exact TCA, direct Foster collision probability).
3. **AI Correction Diagnostics:** Toggleable charts comparing the uncorrected SGP4 path versus the AI-corrected path (highlighting the along-track correction).
