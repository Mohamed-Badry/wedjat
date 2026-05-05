# Project Architecture: AI-Powered Amateur Satellite Ground Station

## 1. Core Objective
**Real-Time Anomaly Detection at the Edge (Target State).**
Project Watchdog is intended to become a "First Responder" for amateur satellite telemetry, flagging anomalies such as power, thermal, and attitude-related faults during a pass.

**Current repository status:** the offline data pipeline, decoder normalization, model training, synthetic-fault benchmarking, and a minimal deterministic packet-by-packet watchdog runtime are implemented. A richer production runtime with broader ingress adapters and operator UX is still planned.

---

## 2. Target Selection Strategy (The Funnel)
To ensure operational viability, we filtered the entire amateur fleet (338+ satellites) using a rigorous funnel:

1.  **Status Check:** Must be confirmed 'Alive' in SatNOGS DB.
2.  **Band Compatibility:** 433-438 MHz (70cm Amateur Band).
3.  **Modulation:** High-rate 9600 bps GMSK/FSK (Modern Standard).
4.  **Decoder Support:** Must be explicitly supported by `satnogs-decoders` (Kaitai Structs).
5.  **Operational Viability:** Ranked by "Total Observable Time" (Sum of pass durations > 30° elevation over 48h).

### The Golden Cohort (Top Candidates)
Based on our Beni Suef ground station and the `satnogs-decoders` library:

1.  **UWE-4 (NORAD 43880)** - The "Golden Path". Solid coverage (~7.5 mins / 48h), 9600 FSK, perfect parser compatibility yielding rich thermal/power telemetry.
2.  **INSPIRESat-1** - 9600 GFSK.
3.  **LEDSAT** - 9600 GMSK.
4.  **BDSat** - 9600 GFSK.

*Note on Data Engineering Challenges:* Initial analysis ranked BugSat-1 (NORAD 40014) highly. However, its real-world telemetry uses an undocumented/custom variation (`US37` payload header) that fails strict Kaitai validation in standard decoders. For ML engineering, we prioritize robust, clean data sources over hacking broken protocols. Thus, UWE-4 is our primary focus.

---

## 3. High-Level Architecture (The V-Model)
The intended system is split into two distinct environments that share a common logic core to ensure consistency.

**Implementation note:** the offline "Lab" path is implemented, and the repository now also contains a minimal deterministic "Watchdog" runtime. The fuller service architecture below remains the target state.

### A. "The Lab" (Offline Training Pipeline)
* **Goal:** Learn "Normal" behavior from historical data.
* **Source:** SatNOGS Database (JSON Archives).

#### 1. Data Ingestion (The Siphon)
*   **Tool:** `scripts/fetch_training_data.py` (Interactive CLI).
*   **Strategy:** "The Lake". We download raw JSON batches (1-day chunks) to `data/raw/`.
*   **Features:**
    *   **Fault Tolerant:** Exponential backoff and coarse resume-by-day behavior.
    *   **Rate Limit Aware:** Token bucket delays to respect SatNOGS API limits.
    *   **Storage Strategy:** Appends to `.jsonl` files to avoid large in-memory raw dumps during fetch.
    *   **Current Limitation:** Partial daily chunks are not yet verified for completeness once a non-empty file exists.

#### 2. Preprocessing & Training
* **Strategy: "Shared Tools, Unique Models"**
    *   **The Problem:** Satellites are physically distinct (different bus voltages, thermal masses). A single "Universal Model" would fail.
    *   **The Solution:** We use the *Shared Core* to normalize data engineering (SI Units), but we train a **separate Unified System per NORAD ID**.
        *   `models/<norad>_scaler.pkl`, `models/<norad>_vae.pt`
* **Algorithm: Unified PyTorch Variational Autoencoder (VAE)**
    *   **Historical Note:** We initially attempted a "Hybrid Pipeline" using `sklearn.covariance.EllipticEnvelope` as a Stage 1 screener. We deprecated it because LEO telemetry physics strictly dictate *Bimodal* operating states (Day/Night). A linear boundary drawing Gaussians was unable to wrap both states without dropping ~50% of the anomaly recalls.
    *   **The VAE Approach:** A PyTorch VAE mathematically handles non-linear bounds efficiently.
    *   **Stage 1 (Detection):** Calculate the overall frame reconstruction error (MSE) + Kullback-Leibler Divergence (KLD). The current repository now calibrates the operating threshold on a chronological validation split during training and persists it alongside the model metadata.
    *   **Stage 2 (Diagnosis):** For flagged frames, inspect the per-node Mean Squared Error. The node with the largest error isolates the Root Cause.

#### 3. Interpretability & Benchmarking (The Edge)
An opaque "Anomaly Score" (e.g., 0.95) is useless to an operator. We provide actionable insights by analyzing the **reconstruction error per feature** in Stage 2.

*   **Logic:** $\text{Contribution} = | \text{Input} - \text{Reconstruction} |$
*   **Example (Heater Stuck ON):**
    *   **Input:** `[Temp: 50°C, Current: 0.1A]` (Hot but low power draw).
    *   **Model Expectation:** `[Temp: 10°C, Current: 0.1A]` (Model knows low power usually means low temp).
    *   **Result:** `Temp Error`: **40.0** (Critical Contributor -> Flag "Temperature Anomaly").

**Validation Strategy: "Synthetic Fault Injection"**
Since real anomaly labels are rare in amateur telemetry, we validate the model using a custom script (`generate_faults.py`). We programmatically inject physical failures into a clean test set to measure the model's **Recall** and **False Positive Rate**:
1.  **Solar Panel Failure:** Temp indicates sunlight (>15°C), but we artificially force current to remain negative (discharging).
2.  **Thermal Runaway:** We inject a large positive step into the battery temperatures.

*Historical note:* earlier notebook experimentation also included a `Sensor Stuck` scenario, but the current shipped benchmark script does not.

**Edge Performance Metrics:**
These are target metrics for the planned online runtime, not a statement of current deployment status:
1.  **Latency:** Target < 10ms inference per frame.
2.  **Footprint:** Target < 5MB model file size.

### B. "The Watchdog" (Current Minimal Runtime + Target Online Pipeline)
* **Goal:** Detect anomalies during a 10-minute satellite pass.
* **Source:** Local Antenna -> SDR -> `satnogs-decoders`.
* **Current Implemented Runtime:**
    1. Load a persisted scaler/model/threshold artifact.
    2. Decode one packet at a time through the shared telemetry core.
    3. Run deterministic inference on the packet's normalized feature vector.
    4. Track runtime states: `idle`, `receiving`, `gap`, `degraded`, `alerting`.

* **Target Expanded Process:**
    1. Demodulate packets.
    2. Decode & Normalize using `satnogs-decoders` (Kaitai Structs).
    3. Run Inference using the pre-trained model.
    4. Alert on high reconstruction error.

**Current limitation:** the implemented runtime is intentionally minimal. It does not yet include richer network ingress adapters, advanced alert transport, or a full operator UI.

---

## 4. Standardization Strategy
To handle multiple disparate satellites without chaos, the system enforces strict standardization layers.

### Transport Layer: SatNOGS Compatible
* **Protocol:** We leverage the **`satnogs-decoders`** ecosystem.
* **Benefit:** Battle-tested Kaitai Structs that already handle a wide variety of amateur satellite formats.

### Semantic Layer: The Current UWE-4 Feature Contract
The repository currently trains on a UWE-4-centric subset of normalized SI-unit features:

| Feature | Unit | Description |
| :--- | :--- | :--- |
| `batt_voltage` | Volts (V) | Standardized from mV or ADC counts. |
| `batt_current` | Amps (A) | Charge/Discharge rate. |
| `power_consumption` | Watts (W) | Spacecraft power draw estimate. |
| `temp_obc` | Celsius (°C) | Main computer temperature. |
| `temp_batt_a` / `temp_batt_b` | Celsius (°C) | Battery pack temperatures. |
| `temp_panel_z` | Celsius (°C) | External panel temperature used as orbit-phase context. |
| `uptime` | Seconds | Time since last reset. |

*Planned expansion:* fields such as `signal_rssi` and other subsystem-specific channels are still architectural targets, not implemented training inputs in the current repo.

---

## 5. The Shared Python Core (Implementation Details)
This module is imported by the training scripts and notebooks today. A future live receiver/runtime can also reuse it.

### The "Adapter" Pattern
We use a **Registry** to map Callsigns to specific Decoders and Adapters.

```python
# Conceptual Architecture

# 1. The Registry (Maps Callsign -> Logic)
REGISTRY = {
    "NJ7P": {
        "decoder": Fox1_Construct_Struct, 
        "adapter": adapt_fox1_to_si
    },
    "UPSAT": {
        "decoder": UPSat_Construct_Struct, 
        "adapter": adapt_upsat_to_si
    }
}

# 2. The Universal Loop (Used in Live & Training)
def process_packet(raw_bytes):
    # Step A: Identify (AX.25 Header)
    callsign = parse_ax25_header(raw_bytes).src_callsign
    
    if callsign in REGISTRY:
        # Step B: Decode (Binary -> Raw Dict)
        raw_data = REGISTRY[callsign]["decoder"].parse(raw_bytes)
        
        # Step C: Normalize (Raw Dict -> Golden Features)
        # This is the crucial step for ML consistency
        ml_vector = REGISTRY[callsign]["adapter"](raw_data)
        
        return ml_vector
```

## 6. Development Progress (Updated Apr 2026)

### Implemented Components

#### 1. The Shared Core (`src/gr_sat/telemetry.py`)
*   **`TelemetryFrame`:** The concrete implementation of "Golden Features" as a Python dataclass. Enforces type safety and SI unit standardization.
*   **`DecoderRegistry`:** A singleton registry that automatically registers decoders via decorators (`@DecoderRegistry.register`).
*   **`process_frame`:** The universal entry point function.

#### 2. Data Refinery (`scripts/process_data.py`)
*   **Pipeline:** `Raw JSONL` -> `Decode` -> `Normalize` -> `CSV`.
*   **Status:** Successfully processed UWE-4 (43880) data into a historical processed dataset used for model training and review.

#### 3. Model Training + Offline Benchmarking (`scripts/train_model.py`, `scripts/generate_faults.py`)
*   **Training:** Per-satellite `StandardScaler` + PyTorch `TelemetryVAE`.
*   **Benchmarking:** Synthetic-fault evaluation for comparative offline model analysis.
*   **Current Limitation:** The anomaly threshold is still derived inside the benchmark path and is not yet stored as part of a deployable model artifact.

#### 4. Telemetry Inspector (`notebooks/telemetry_inspector.py`)
*   **Tool:** An interactive Jupyter-based visual debugger.
*   **Goal:** "Ground Truth" verification. Allows humans to visually correlate raw hex bytes with parsed values to ensure the decoder is not hallucinating.
*   **Features:**
    *   **Hex View:** Raw payload inspection.
    *   **Struct View:** Visualization of the intermediate binary parsing steps (ADC counts).
    *   **Telemetry View:** Verification of the final physical values (Volts, Amps).
    *   **Navigation:** Slider-based frame traversal.

### Not Yet Implemented

*   Richer ingress adapters and network-facing live packet receivers
*   Advanced alert transport beyond the minimal callback/CLI runtime
*   Feature-complete operator-facing dashboard / UI integration (the repo now contains a Bun + SvelteKit shell only)

---

## 7. Technology Stack

### Hardware & RF
* **Antenna:** Omnidirectional or Yagi.
*   **SDR:** RTL-SDR.
*   **Demodulator:** `gr_satellites` or raw baseband processors.
*   **Decoder:** `satnogs-decoders` (Kaitai Structs).
*   **Interface:** UDP Stream or SatNOGS DB frames.

### Software

*   **Language:** Python 3.11.

*   **Data Engineering:** `requests`, `loguru`, `rich` (Robust CLI pipelines).

*   **ML Core:** `scikit-learn`, `pytorch`, `pandas`.

*   **Physics Engine:** `skyfield` (Orbit prediction & geometry).

*   **Parsing:** `satnogs-decoders` (Kaitai Struct compiler output).

*   **Visualization:** `matplotlib`, `seaborn` (for operational dashboards).


---

## 8. Reviewer Defense Strategy
* **"How do you know it's not hallucinating?"**
    * We use AX.25 Checksums (CRC-16). We only process mathematically valid packets.
    * We use the embedded Callsign for ID, not orbital predictions.
* **"How do you know the model works without real failure data?"**
    * We use **Synthetic Fault Injection**. We prove the model *would* have caught a failure by mathematically superimposing faults onto historical data and measuring recall.
