# Architecture Review Todo

This file captures the outcomes of the April 11, 2026 architecture/code review and turns them into an execution backlog.

## Status Key

- `Completed`: finished and documented
- `Next`: intended immediate work
- `Planned`: accepted, but not started
- `Deferred`: intentionally postponed
- `Ignored for now`: explicitly out of scope unless requirements change

## Agreed Execution Order

1. Update the docs to match the code and current reality.
2. Make implementation plans for the critical bugs.
3. Fix the critical bugs one by one after the plans are written and reviewed.
4. Revisit deferred major items only if edge inference requirements make them necessary.

## 1. Docs Alignment

### 1.1 Bring documentation in line with the current implementation

- Status: `Completed`
- Why: the current docs overstate what is implemented, and some claims directly conflict with the code.
- Files implicated:
  - `DETAILS.md`
  - `README.md`
  - `docs/dataflow.typ`
  - `docs/slides.typ`
  - `docs/eda_slides.typ`
  - `docs/benchmark_43880.md`
- Output:
  - stale live-ready / hybrid-pipeline claims corrected
  - current benchmark limitations documented
  - implemented-vs-planned boundary made explicit

### Doc mismatches to correct

- The docs say the anomaly threshold is learned during training and used at inference.
  - Actual code: the threshold is computed only inside `scripts/generate_faults.py` during offline evaluation and is not persisted with the model.

- The docs describe a real-time watchdog deployed on edge hardware.
  - Actual code: there is no implemented online inference service, receiver loop, alerting path, or runtime state machine.

- The docs say rolling-variance style temporal features were discarded.
  - Actual code: `scripts/process_data.py` still computes `volt_rolling_std` and `temp_rolling_std`, even though the training script does not use them.

- The slides still describe older or conflicting model architectures.
  - Actual code: the only active model path is the VAE training and synthetic-fault benchmark flow.

- The docs imply more realistic aerospace telemetry coverage than the code currently delivers.
  - Actual code: the feature set is narrow and mostly UWE-4 EPS/thermal focused.

### Output expected from this docs pass

- A clear distinction between:
  - implemented now
  - benchmark/evaluation only
  - planned but not built
- An honest description of the current anomaly threshold workflow.
- A note that only a minimal deterministic edge runtime exists today, while richer ingress/alerting remains planned.
- Removal of stale hybrid/rolling-feature claims unless they are still intentionally planned.

## 2. Critical Bugs

These are accepted as real defects and need explicit implementation plans before code changes.

### 2.1 Timestamp-only deduplication destroys valid telemetry

- Status: `Completed`
- Severity: `Critical`
- Code:
  - `scripts/process_data.py`
- Current behavior:
  - `drop_duplicates(subset=["timestamp"], keep="first")` removes same-timestamp rows even when payload contents differ.
- Why this is a systemic risk:
  - valid frames are being discarded
  - same-second collisions and retransmissions are treated as the same event
  - the training set is materially altered before modeling
- Review evidence:
  - interim file: `data/interim/43880.csv`
  - processed file: `data/processed/43880.csv`
  - the review found many duplicate timestamps with differing packet contents
- Planning goal:
  - define a canonical frame identity and deduplication policy
- Design note:
  - `docs/critical_bug_plans.md` section 1
- Implemented scope:
  - `src/gr_sat/processing.py`
  - exact-duplicate removal now keys off timestamp + payload fingerprint rather than timestamp alone
  - same-timestamp distinct payloads are preserved
- Architectural direction:
  - distinguish exact retransmissions from distinct frames using fields such as:
    - timestamp
    - packet/header identifier
    - source/provenance
    - payload hash
    - observation identifier when present
  - preserve distinct same-timestamp frames
  - deduplicate only exact record duplicates
- Planning questions:
  - what should count as the canonical unique frame key for SatNOGS-sourced training data?
  - when `observation_id` is missing, what fallback identity is safe?
  - do we want to keep duplicate receptions from multiple stations as separate samples or collapse only byte-identical repeats?

### 2.2 VAE inference is stochastic in evaluation mode

- Status: `Completed`
- Severity: `Critical`
- Code:
  - `src/gr_sat/models.py`
  - `scripts/generate_faults.py`
- Current behavior:
  - `TelemetryVAE.reparameterize()` always samples latent noise, even during evaluation.
- Why this is a systemic risk:
  - identical frames can receive different anomaly scores on different runs
  - thresholds and alerts become non-repeatable
  - operators cannot trust a non-deterministic anomaly pipeline
- Planning goal:
  - define deterministic operational scoring behavior
- Design note:
  - `docs/critical_bug_plans.md` section 2
- Implemented scope:
  - `src/gr_sat/models.py`
  - eval-mode inference now uses deterministic latent means by default
- Architectural direction:
  - use `mu` directly for deterministic inference in operational mode
  - if stochastic inference is still useful, expose it as explicit Monte Carlo scoring with fixed sample counts and uncertainty reporting
  - keep training-time stochastic behavior separate from runtime scoring behavior
- Planning questions:
  - do we want deterministic-only inference, or deterministic default plus optional uncertainty estimation?
  - should benchmark reports include score variance if stochastic scoring is retained anywhere?

### 2.3 Threshold calibration leaks evaluation labels

- Status: `Completed`
- Severity: `Critical`
- Code:
  - `scripts/generate_faults.py`
  - `scripts/train_model.py`
- Current behavior:
  - the anomaly threshold is calibrated from the labeled evaluation set instead of from a held-out clean validation split during training.
- Why this is a systemic risk:
  - benchmark metrics are optimistic
  - the calibration procedure cannot be reproduced in live use
  - the deployed system has no persisted operational threshold artifact
- Planning goal:
  - define a proper train/validation/test artifact flow
- Design note:
  - `docs/critical_bug_plans.md` section 3
- Implemented scope:
  - `src/gr_sat/model_artifacts.py`
  - `scripts/train_model.py`
  - `scripts/generate_faults.py`
  - threshold is now calibrated on chronological validation data and persisted in metadata
- Architectural direction:
  - train on chronological train split
  - calibrate threshold on a clean chronological validation split
  - reserve the final test split for evaluation only
  - persist the threshold alongside the scaler and model
  - keep score normalization and threshold logic identical between validation, test, and live inference
- Planning questions:
  - should thresholding be percentile-based, EVT-based, or stability-based?
  - do we want one threshold per satellite, per subsystem, or per operating regime?

### 2.4 No actual online watchdog runtime exists

- Status: `Completed`
- Severity: `Critical`
- Code impact:
  - repository-wide
- Current behavior:
  - there is no implemented online receiver/inference/alert service, only offline fetch, processing, training, and synthetic benchmarking.
- Why this is a systemic risk:
  - the repo cannot currently operate as the real-time ground-station watchdog described in the docs
  - no timeout handling exists when telemetry stops
  - no fallback state exists if model inference fails
  - no alert transport or runtime observability exists
- Planning goal:
  - define the online architecture before implementation
- Design note:
  - `docs/critical_bug_plans.md` section 4
- Implemented scope:
  - `src/gr_sat/watchdog.py`
  - `scripts/watchdog_runtime.py`
  - deterministic packet-by-packet inference
  - runtime state machine with `idle`, `receiving`, `gap`, `degraded`, `alerting`
  - minimal alert sink callback
- Architectural direction:
  - create a dedicated online inference service with:
    - ingestion adapter
    - bounded queue or single-frame processing path
    - model artifact loading and schema validation
    - runtime states such as `idle`, `receiving`, `gap`, `degraded`, `alerting`
    - explicit error handling for decoder/model failures
    - metrics, logs, and heartbeats
- Planning questions:
  - what is the exact ingress contract for live packets?
  - what alert output is required first: console, log, file, webhook, or UI?
  - should the first online version be single-threaded and deterministic?

## 3. Major Issues

### 3.1 Full in-memory raw-frame loading and DataFrame accumulation

- Status: `Ignored for now`
- Code:
  - `scripts/process_data.py`
- Reason for deferral:
  - current use is laptop-based offline training
  - edge inference would be a different path and can process frame-by-frame
- Revisit if:
  - training data scale grows enough to become a practical bottleneck
  - we unify offline and online ingestion around one streaming architecture

### 3.2 Non-empty daily fetch files are treated as complete

- Status: `Ignored for now`
- Code:
  - `scripts/fetch_training_data.py`
- Reason for deferral:
  - missing a small amount of daily data is currently acceptable
  - the training corpus is already large enough that partial daily loss is not considered high impact right now
- Revisit if:
  - dataset completeness starts affecting experiments
  - we need reproducible dataset manifests

### 3.3 Missing numeric fields are silently converted to physical zeroes

- Status: `Completed`
- Code:
  - `src/gr_sat/decoders/uwe4.py`
- Why it still matters:
  - zero is a real physical value, not a safe placeholder for missing telemetry
  - this can contaminate model training and future live inference
- Architectural direction:
  - track missingness explicitly rather than coercing to zero
- Implemented scope:
  - optional numeric telemetry now remains `None` instead of defaulting to zero
  - derived combined fields stay `None` unless both source measurements are present
  - processed rows now carry `missing_raw_fields`, `missing_raw_field_count`, and `frame_is_complete`

### 3.4 Exception handling loses failure cause detail

- Status: `Completed`
- Code:
  - `src/gr_sat/telemetry.py`
  - `src/gr_sat/decoders/uwe4.py`
  - `scripts/process_data.py`
- Why it still matters:
  - decoder health, bad packets, schema issues, and runtime faults are not separable
- Architectural direction:
  - use structured failure categories and counters
- Implemented scope:
  - `process_frame_result()` now returns structured stage/code/message failures
  - `UWE4Decoder` classifies decode and adapt failures explicitly
  - offline processing logs per-code failure breakdowns
  - watchdog results now expose `failure_code`

### 3.5 Pass segmentation and cadence handling are simplistic

- Status: `Completed`
- Code:
  - `scripts/process_data.py`
- Why it still matters:
  - dropped packets, irregular cadence, and time alignment are only minimally modeled
- Architectural direction:
  - represent pass/session metadata explicitly instead of using only a fixed `>120s` rule
- Implemented scope:
  - pass/cadence annotation moved into shared processing helpers
  - processed data now retains `pass_id`, per-pass counts, duration, cadence reference, and gap flags
  - dropped-packet suspects and irregular cadence are computed explicitly
  - online inference now keeps short rolling history for feature compatibility

### 3.6 Feature contract is too narrow for the system claims

- Status: `Completed`
- Code:
  - `scripts/train_model.py`
  - `src/gr_sat/satellite_profiles.py`
- Why it still matters:
  - current features cover only a limited subset of spacecraft behavior
- Architectural direction:
  - introduce per-satellite manifests and versioned feature contracts
- Implemented scope:
  - added `src/gr_sat/satellite_profiles.py` with a versioned UWE-4 feature contract
  - training and evaluation now load feature sets from the satellite profile instead of hardcoded lists
  - baseline cleaning rules moved into the profile manifest
  - artifact metadata now persists `feature_contract_version` and diagnosis features

### 3.7 Model artifacts do not persist threshold/scoring metadata

- Status: `Completed`
- Code:
  - `scripts/train_model.py`
  - `scripts/generate_faults.py`
- Why it still matters:
  - there is no single persisted artifact contract for reproducible inference
- Architectural direction:
  - store model weights, scaler, threshold, feature order, inference mode, and training metadata together

## 4. Suggested Next Working Session

### Immediate next task

- Update the docs listed in section 1 so they describe the repository as it actually exists today.

### After docs

- Write a design note for the four critical items before touching implementation.
- Start with deduplication and deterministic inference, since they are the most fundamental to data and scoring correctness.

### Progress Update

- Docs pass completed.
- Critical bug planning note written in `docs/critical_bug_plans.md`.
- Critical bug fixes implemented in code.
- Regression coverage added under `tests/`.
- Remaining major items 3.3 through 3.6 implemented and covered by regression tests.
