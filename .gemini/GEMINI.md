# Gemini Context: Project Watchdog (gr_sat)

## 1. Project Overview
**Goal:** Real-time anomaly detection for amateur satellite telemetry using an Autoencoder.
**Key Concept:** "The Golden Cohort" (Optimal targets) → "Shared Core" (Normalization) → "The Lab" (Training) / "The Watchdog" (Inference).

## 2. Agent Mandates & Conventions
*   **Package Manager:** STRICTLY use `pixi`. NEVER use `pip install` or `venv` directly.
*   **Task Runner:** Use `just` for all standard workflows defined in `justfile`.
*   **Version Control:** Use `jj` (Jujutsu), not `git`.
*   **Decoders:** Use `satnogs-decoders` (Kaitai Structs) for all telemetry parsing. DO NOT write manual `construct` decoders.
*   **Notebooks:** Use `jupytext` to manage scripts as notebooks. Always prefer editing `.py` files and converting/syncing them.
*   **Slides:** Use `typst` for presentations (`docs/slides.typ`). Keep slides up to date with progress.
*   **Python:** Version 3.11. Use `loguru` for logging (never stdlib `logging`).
*   **Frontend:** Svelte 5 + Tailwind v4 + Bun. Use semantic CSS token classes (`text-ink`, `bg-panel`, etc.) — never hardcode Tailwind color values like `text-slate-700`.
*   **Docker Secrets:** All credentials use `${VAR:-default}` in `docker-compose.yml`, sourced from `.env`. Never hardcode secrets in compose or Dockerfiles.
*   **Documentation:** ALWAYS update relevant documentation (e.g., `DETAILS.md`, `README.md`, `docs/slides.typ`) to ensure it remains consistent with code changes.
*   **Dictionary & Tooltips (NEW):** When adding new telemetry fields, quality metrics, or scientific concepts to the dashboard, ALWAYS update the `frontend/src/lib/data/dictionary.ts` file. It serves as the single source of truth for the entire application. Use the `<Tooltip text={getFeatureDescription(key)} />` component in the Svelte UI to display these definitions to the operator.
*   **Paths:**
    *   `src/gr_sat/`: Library code (Shared Core, Telemetry Models).
    *   `src/gr_sat/decoders/`: Satellite-specific decoders (Kaitai Structs).
    *   `src/api/`: FastAPI backend scaffold and Dockerfile.
    *   `src/simulator/`: Replay simulator scaffold and Dockerfile.
    *   `frontend/`: Bun + SvelteKit + Tailwind v4 web UI.
    *   `db/init/`: SQL schema init scripts (mounted into TimescaleDB).
    *   `scripts/`: Executable pipelines (Data ingestion/processing).
    *   `data/`: Data storage (Gitignored).
    *   `models/`: Trained model artifacts (Gitignored).
    *   `docs/`: User-facing documentation and slides.
*   **Commits:** Follow conventional commits (e.g., `feat: add telemetry parser`, `fix: correct orbit calculation`).

## 3. Active Context (Memory)
*   **Current Phase:** Dashboard architecture — Phase 1 (Foundation). Restructuring frontend routes and building the dashboard shell.
*   **Recent Accomplishments:**
    *   Completed offline ML pipeline: fetch → decode → normalize → train → benchmark.
    *   UWE-4 (NORAD 43880) trained VAE model with calibrated threshold (0.295 @ 95th percentile).
    *   Scaffolded 5-service Docker Compose stack: broker, db, backend, frontend, simulator.
    *   Implemented Tailwind v4 `@theme` token system with `prefers-color-scheme: dark` overrides.
    *   Created TimescaleDB init schema with two hypertables: `raw_frames` + `telemetry_frames`.
    *   Centralized Docker secrets via `${VAR:-default}` pattern in compose, sourced from `.env`.
    *   **Approved comprehensive dashboard plan** with API contracts for all sub-pages.
    *   Finalized **V3 Hybrid Edge-to-Cloud Architecture** diagram (Typst) with robust fallback mechanisms.
    *   Hardened MQTT transport with TLS encryption, explicit authentication, and seamless Offline CSV Fallback logic in the Edge Simulator.
    *   Formalized transport resilience and telemetry pipelines using **Allium** domain specification language (`docs/spec/`).
    *   Implemented a live ML validation pipeline for the sensitivity sweep (`/api/ml/sensitivity`), executing dynamic VAE reconstruction error calculations, ROC curves, and F1/Precision/Recall crossover metrics on-the-fly.
    *   Hardened UI typography and layout consistency on the Orbit Decay page, improving visibility of Reality Check and Forecast Summary metrics.
    *   Regenerated all static dashboard screenshots (both dark and light modes) across all SvelteKit pages to document the visual changes.
    *   Anchored `.gitignore` directory patterns (e.g., `/data/`, `/models/`) to prevent Git from recursively ignoring crucial nested frontend code folders (like `frontend/src/lib/data/` which contains `transforms.ts` and `dictionary.ts`).
    *   Implemented custom CORS fallback middleware in FastAPI (`src/api/main.py`) to bypass SvelteKit Server-Side Rendering (SSR) fetch validation check failures.
    *   Switched SvelteKit's Docker builder stage to Node.js for Vite production bundling to resolve multi-threading compiler crashes with Bun inside specific Linux VPS Docker hosts.
    *   Locked down SvelteKit and FastAPI port mappings in `docker-compose.yml` to localhost (`127.0.0.1`), routing all traffic securely through Caddy.
    *   Built a custom Mosquitto image (`mosquitto/Dockerfile`) and entrypoint workflow to enforce `allow_anonymous false` and dynamically generate secure MQTT credentials at runtime from `.env` keys.
*   **Current Sprint (Phase 1 — Foundation):**
    *   Restructure frontend routes into `(landing)` and `(dashboard)` route groups.
    *   Build `DashboardLayout` with sidebar + footer (no antenna bg, no Overview/Team tabs).
    *   Create dashboard home with placeholder cards.
    *   Implement `database.py` and `GET /api/status`.
    *   **Current Task:** Revamp the Analytics Page (`/dashboard/analytics`) to follow `DASHBOARD_SVELTEPLOT_PLAN.md` conventions (components, styling).
*   **Dashboard Sub-Pages (Planned):**
    *   `/dashboard` — Home (service status, recent anomalies, throughput sparkline).
    *   `/dashboard/operations` — Pass prediction, skyplots, scheduling (Skyfield).
    *   `/dashboard/live` — Live packet watcher, decode pipeline visualization (WebSocket).
    *   `/dashboard/insights` — EDA charts, telemetry explorer, PCA.
    *   `/dashboard/ml` — VAE vs Z-Score sensitivity, ROC, latent space, threshold tuning.
*   **Upcoming Phases:**
    *   Phase 2: Live Pipeline (MQTT subscriber, WS endpoint, PipelineVisualizer).
    *   Phase 3: Operations (Skyfield pass predictor service).
    *   Phase 4: Insights & ML Lab (aggregation queries, sensitivity sweep service).
    *   Phase 5: Polish (responsive, skeletons, error boundaries).

## 4. Key Workflows
*   **Fetch Data:** `just fetch` (Interactive) or `just fetch --norad 43880` (Specific).
*   **Process Data:** `just process` (Interactive) or `just process --norad 43880` (Specific).
*   **Train Model:** `just train --norad 43880` (Train scaler + VAE + metadata artifact).
*   **Benchmark:** `just benchmark --norad 43880` (Synthetic fault injection).
*   **Docker Stack:** `docker compose up --build` (All 5 services).
*   **Analyze Targets:** `just analyze-targets` (Filters candidates to "The Golden Cohort").
*   **Visualize Passes:** `just viz-passes` (Generates Skyplots/Gantt charts).
*   **Sync Notebooks:** `just sync-notebooks` (Updates all `.ipynb` from `.py` in `notebooks/`).

## 5. Data Pipeline Architecture
Three-stage pipeline matching `data/` directory structure:

```
data/raw/{norad_id}/*.jsonl     SatNOGS API fetches (untouched)
        ↓  decoder.decode()     Kaitai Structs binary parsing
data/interim/{norad_id}.csv     All decoded fields (no unit conversion)
        ↓  decoder.adapt()      Unit conversion + field mapping
data/processed/{norad_id}.csv   SI-unit "Golden Features" (ML-ready)
```

## 6. Technical Specifics
*   **The Shared Core (`src/gr_sat/telemetry.py`):**
    *   **`TelemetryFrame`:** The universal DTO. All decoders MUST produce data mapping to this.
        *   **Key Fields:** `batt_voltage`, `batt_current`, `temp_batt_a`, `temp_batt_b`, `temp_panel_z`, `temp_obc`, `uptime`.
        *   **Units:** SI Units ONLY (Volts, Amps, Celsius).
    *   **`BaseDecoder`:** ABC with two methods:
        *   `decode(payload: bytes) → Dict` — Kaitai Struct parsing (→ interim).
        *   `adapt(decoded: Dict) → Dict` — Unit conversion to Golden Features (→ processed).
    *   **`DecoderRegistry`:**
        *   Use `@DecoderRegistry.register(norad_id)` to register new decoders in `src/gr_sat/decoders/`.
        *   `list_supported()` shows all registered decoders.
*   **Currently Supported:**
    *   UWE-4 (NORAD 43880) — `src/gr_sat/decoders/uwe4.py` — Primary target.

## 7. ML Strategy (The Lab)
*   **Architecture:** Variational Autoencoder (VAE, Self-Supervised).
    *   **Input:** Normalized TelemetryFrame (SI Units, 5-dim vector).
    *   **Output:** Reconstructed Telemetry.
    *   **Loss:** MSE + β·KLD (β = 0.05).
*   **Model Management:** "Shared Tools, Unique Models".
    *   **Training Script:** Generic (`train_model.py`).
    *   **Artifacts:** Per NORAD ID (`models/<norad>_vae.pt`, `_scaler.pkl`, `_metadata.json`).
    *   **Threshold:** Calibrated at 95th percentile on chronological validation split, persisted in metadata.
*   **Interpretability:** Feature Contribution Analysis.
    *   **Metric:** Absolute Error per Feature (`|Input - Reconstruction|`).
*   **Validation:** Synthetic Fault Injection (`generate_faults.py`).

## 8. Docker Architecture
Five services orchestrated by `docker-compose.yml`:
1. **broker** — Mosquitto MQTT (:1883)
2. **db** — TimescaleDB (:5432) with init schema at `db/init/001_schema.sql`
3. **backend** — FastAPI + Uvicorn (:8000), subscribes to broker, writes to db
4. **frontend** — Bun + SvelteKit (:5173), consumes backend REST/WS
5. **simulator** — Replays `data/raw/` into broker for testing

## 9. Frontend Design System
*   **Tokens:** Defined via `@theme` in `app.css`, used as Tailwind utilities (`text-ink`, `bg-panel`, `border-border`, etc.).
*   **Dark mode:** `prefers-color-scheme: dark` media query overrides CSS custom properties.
*   **Color palette:** Brand (#B12142), Muted (#6C7A96), Ink (#111827/light, #F8FAFC/dark).

## 10. EDA Insights & ML Plan (UWE-4)
*   **Data Quality (Zero Variance):** `temp_obc` is stuck at 17°C — dropped before training.
*   **Bursty Data:** Median gap ~18s, max ~11h. Stateless feed-forward VAE, not sequence models.
*   **Bimodal Physics:** Battery current is bimodal (charge/discharge) — NOT outliers.
*   **Feature Selection:** 5-dimensional: `[batt_voltage, batt_current, temp_batt_a, temp_batt_b, temp_panel_z]`.
*   **Scaling:** StandardScaler (Z-score normalization).
