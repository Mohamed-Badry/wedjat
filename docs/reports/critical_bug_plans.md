# Critical Bug Plans

This document turns the accepted critical review findings into implementation plans. No code changes are described here; this is the design/planning layer that should guide the fixes.

## Execution Order

1. Fix frame identity and deduplication.
2. Make inference deterministic.
3. Move threshold calibration into the training artifact flow.
4. Build the online watchdog runtime on top of the corrected artifact contract.

## 1. Frame Identity and Deduplication

### Problem

`scripts/process_data.py` currently deduplicates on `timestamp` alone. The historical UWE-4 data contains same-timestamp rows with different packet contents, so valid telemetry is being discarded.

### Goal

Preserve all distinct frames while still removing exact retransmissions / duplicate records.

### Proposed Design

- Define a canonical training-frame identity separate from wall-clock timestamp.
- Use a composite identity built from:
  - `timestamp`
  - packet/header ID when available
  - raw payload or decoded payload hash
  - `observation_id` when present
  - source/provenance if multiple ingest sources are introduced later
- Treat exact byte-identical or field-identical duplicates as retransmissions.
- Keep distinct same-second frames as separate samples.

### Processing Changes

- Add explicit duplicate classification:
  - exact duplicate
  - same timestamp, different payload
  - same observation, different packet
- Persist enough provenance in interim/processed outputs to explain dedup decisions.
- Emit dedup summary metrics rather than only final row counts.

### Acceptance Criteria

- No same-timestamp frames with differing payloads are silently dropped.
- The processed dataset can explain why a record was kept or removed.
- Re-running processing on the same raw input produces stable row counts and stable identities.

## 2. Deterministic Inference

### Problem

`TelemetryVAE.reparameterize()` samples latent noise unconditionally, so the same frame can produce different anomaly scores even in evaluation mode.

### Goal

Make operational scoring reproducible.

### Proposed Design

- Separate training-time stochastic behavior from runtime scoring behavior.
- Use `mu` directly for deterministic inference by default.
- If uncertainty estimation is still useful, expose it as an explicit Monte Carlo mode with:
  - fixed sample count
  - fixed aggregation rule
  - optional variance output

### Processing Changes

- Define an inference mode in the artifact contract:
  - `deterministic`
  - optional `monte_carlo`
- Ensure benchmarking and future live inference use the same deterministic scoring path unless uncertainty is being intentionally tested.

### Acceptance Criteria

- Repeated inference on the same frame and artifact yields identical scores in deterministic mode.
- Benchmark results become reproducible run-to-run.
- Any non-deterministic mode is explicit and reports uncertainty rather than silently varying the score.

## 3. Threshold Calibration and Artifact Contract

### Problem

The anomaly threshold is currently calibrated inside `scripts/generate_faults.py` using the evaluation set. It is not learned during training, not persisted, and cannot be used unchanged in live inference.

### Goal

Create a reproducible train/validation/test artifact flow with a persisted scoring contract.

### Proposed Design

- Split chronologically into:
  - train
  - validation
  - test
- Fit the scaler on train only.
- Train the VAE on train only.
- Calibrate the anomaly threshold on the clean validation slice only.
- Freeze and persist the threshold with the model artifact.
- Reserve test strictly for offline evaluation.

### Artifact Contents

Persist a single model contract containing:

- feature order
- scaler
- model weights
- inference mode
- score definition
- threshold
- training/validation date ranges
- model/schema version

### Acceptance Criteria

- A trained model can be loaded for inference without recomputing any calibration from evaluation data.
- Benchmarking uses the stored threshold unchanged.
- The scoring path is identical across validation, test, and future live inference.

## 4. Online Watchdog Runtime

### Problem

The repository currently has no implemented live watchdog service. There is no packet-ingest runtime, no model-serving loop, no stream-gap handling, and no alerting path.

### Goal

Define the first practical online runtime around the corrected artifact contract.

### Proposed Design

- Start with a simple, deterministic service rather than a complex concurrent system.
- Suggested first-version components:
  - packet ingress adapter
  - decode/normalize stage
  - artifact loader with schema validation
  - single-frame scoring path
  - runtime state machine
  - alert sink
  - metrics/logging

### Runtime States

- `idle`
- `receiving`
- `gap`
- `degraded`
- `alerting`

### Failure Handling Requirements

- Decoder failure must not crash the service.
- Model failure must move the runtime into `degraded` state with logging/metrics.
- Stream timeout must be visible as a first-class state transition.
- Artifact/schema mismatch must fail fast at startup.

### First Release Scope

- Single-threaded or minimally concurrent
- Deterministic scoring only
- Console/log/file alert output first
- No UI dependency in the first operational cut

### Acceptance Criteria

- A valid packet can flow from ingress to decoded frame to anomaly score to alert output.
- Packet gaps and model failures are observable runtime states.
- The service can run without requiring notebook tooling or benchmark-only code paths.
