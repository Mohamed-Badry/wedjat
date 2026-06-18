# DISCLAIMER: This project is still nowhere near complete and heavily AI-assisted use at your own discretion.

# Project Watchdog (gr_sat)

This repository hosts the **Project Watchdog** codebase, an end-to-end pipeline for satellite telemetry analysis. It features offline telemetry processing, per-satellite anomaly-model training, synthetic-fault benchmarking, a robust FastAPI backend, and a premium SvelteKit + Tailwind dashboard.

## 📚 Key Documentation

*   **[Technical Details & Architecture](DETAILS.md)**: Deep dive into the system's design, ML models, and "Golden Features".
*   **[WEBSITE_PLAN.md](WEBSITE_PLAN.md)**: Web interface, Docker orchestration, and UX integration plan.
*   **[.gemini/GEMINI.md](.gemini/GEMINI.md)**: Active project context and agent instructions.

## Current Repository Status

**Core Pipeline & Backend:**
*   Offline SatNOGS fetch -> decode -> normalize -> train -> benchmark workflow.
*   Shared telemetry/decoder core with UWE-4 decoder support.
*   Minimal deterministic online watchdog runtime for packet-by-packet inference.
*   FastAPI dashboard REST endpoints (status, telemetry, anomalies, throughput).
*   Docker Compose development stack with pinned service versions.
*   **V3 Hybrid Edge-to-Cloud Architecture** with robust Offline CSV Fallback.

**Frontend Dashboard (SvelteKit + TailwindCSS):**
*   Premium, dark-themed responsive UI with dynamic animations.
*   Live Watcher feed with real-time anomaly detection glowing states.
*   Comprehensive ML Report dashboard with Error Contribution and Expected vs. Actual metrics.
*   Interactive EDA charts (Sensitivity Sweeps, Feature Contributions).
*   Mobile-friendly sidebar navigation and responsive plot containers.

---

## 🚀 Quick Start Guide

### 1. Install Prerequisites
We use **[Pixi](https://pixi.sh/)** for the core Python environment, and **[Bun](https://bun.sh/)** for the frontend.

**Linux / macOS:**
```bash
curl -fsSL https://pixi.sh/install.sh | bash
curl -fsSL https://bun.sh/install | bash
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy Bypass -c "irm -useb https://pixi.sh/install.ps1 | iex"
powershell -c "irm bun.sh/install.ps1 | iex"
```

### 2. Setup the Project
Clone the repo and install dependencies:
```bash
git clone https://github.com/Mohamed-Badry/watchdog.git
cd watchdog
pixi install
cd frontend && bun install && cd ..
```

### 3. Configure API Keys
To download telemetry, you need a **SatNOGS API Token**.
1.  Log in to [SatNOGS Network](https://network.satnogs.org/login/).
2.  Go to **[Your Profile / Edit](https://db.satnogs.org/user/edit)** and copy your **API Token**.
3.  Create your config and paste your token:
    ```bash
    cp .env.example .env
    ```

### 4. Optional Docker Dev Stack
For the MQTT broker, TimescaleDB, FastAPI backend, and simulator:
```bash
docker compose up --build
```

---

## 🛠 Usage & Task Lifecycle

We use `just` (installed automatically by Pixi) to run all common tasks across the stack.

**Recommended:** Enter the Pixi environment first:
```bash
pixi shell
```

### Phase 1: Data Pipeline (The Lab)
Fetch, decode, and normalize telemetry into ML-ready "Golden Features".
```bash
just fetch                  # Download telemetry (interactive)
just fetch --norad 43880    # Download specific satellite
just process                # Run decode + normalize pipeline (interactive)
just process --norad 43880  # Process specific satellite
```

### Phase 2: Machine Learning Pipeline
Train Autoencoder (VAE) models on the processed data and benchmark them.
```bash
just train --norad 43880            # Train VAE model for a specific satellite
just benchmark --norad 43880        # Run synthetic-fault benchmark
just train-benchmark 43880 100      # Train for 100 epochs, then benchmark immediately
```

### Phase 3: Operations & Frontend
Run the minimal backend watchdog runtime and the beautiful SvelteKit dashboard.
```bash
just watchdog --norad 43880 --help  # Run backend anomaly watchdog
just frontend-dev                   # Start frontend SvelteKit development server (localhost:5173)
just frontend-build                 # Build the frontend production bundle
just frontend-preview               # Preview the production build
```

*To see all available commands, run `just` or `just --list`.*

---

## 📂 Complete Data & Directory Structure

Project Watchdog is strictly organized to separate raw data pipelines, machine learning models, core logic, simulated environments, and user interfaces.

```text
.
├── data/                       # Local data storage (ignored by git, populated by scripts)
│   ├── raw/                    # Stage 0: Raw JSONL files fetched directly from SatNOGS DB API
│   │   ├── 43880/              # e.g., UWE-4 raw telemetry records
│   │   └── ...                 # Other satellite NORAD ID directories
│   ├── interim/                # Stage 1: Kaitai-decoded telemetry CSVs (unaltered fields)
│   └── processed/              # Stage 2: SI-unit "Golden Features" CSVs mapped for Machine Learning
├── frontend/                   # Bun + SvelteKit Web Dashboard
│   ├── src/                
│   │   ├── lib/                # Shared internal components
│   │   │   ├── api.ts          # Strongly-typed fetch wrappers for the FastAPI backend
│   │   │   ├── components/     # UI elements (charts, tables, layout components)
│   │   │   └── chart-theme.ts  # Unified design tokens mapping CSS variables to SveltePlot
│   │   └── routes/             # File-system based router pages
│   │       ├── (dashboard)/    # Authenticated/Main App layout group
│   │       │   └── dashboard/  # Dashboard views:
│   │       │       ├── live/   # Real-time packet watcher feed
│   │       │       ├── ml/     # Model telemetry root cause analysis & reports
│   │       │       ├── eda/    # Exploratory Data Analysis (sensitivity, stats)
│   │       │       ├── operations/# Satellite/model status summaries
│   │       │       └── inspector/ # Ground-truth telemetry variable explorer
│   │       └── (landing)/      # Public facing landing pages
│   ├── tailwind.config.ts      # Tailwind design configuration (Amethyst themes, plugins)
│   └── package.json            # Bun dependencies (SvelteKit, Tailwind, Lucide, Observable Plot)
├── src/                        # Python Backend & Shared Library Code
│   ├── api/                    # FastAPI Dashboard Endpoints
│   │   ├── main.py             # Entrypoint: handles REST routes, artifacts, and summary stats
│   │   └── Dockerfile          # FastAPI service container definition
│   ├── gr_sat/                 # Core domain logic ("The Shared Core")
│   │   ├── decoders/           # Kaitai Struct adapters (e.g. uwe4.py, registry pattern)
│   │   ├── telemetry.py        # Central abstractions for telemetry frames
│   │   ├── models/             # Shared PyTorch/Scikit models (VAE, Autoencoders, Scalers)
│   │   └── utils/              # Data parsing and time manipulation helpers
│   └── simulator/              # Edge Simulator Environment
│       ├── edge_node.py        # Hardened Edge Simulator (TLS MQTT + Offline CSV Buffering)
│       └── Dockerfile          # Simulator service container definition
├── scripts/                    # Executable Pipeline & ML Scripts
│   ├── fetch_training_data.py  # Pipeline Stage 0: Fetches SatNOGS historical API data
│   ├── process_data.py         # Pipeline Stage 1+2: Decodes & normalizes telemetry to Golden Features
│   ├── train_model.py          # Pipeline Stage 3: Trains VAE models on processed satellite data
│   ├── generate_faults.py      # Pipeline Stage 4: Injects synthetic faults and benchmarks models
│   └── watchdog_runtime.py     # Minimal deterministic online runtime for stream processing
├── notebooks/                  # Interactive Jupytext Notebooks for Prototyping
│   ├── uwe4_pipeline_eda.py    # Multi-scale EDA, hyperparameter sweeps, statistical profiling
│   └── telemetry_inspector.py  # Visual ground-truth debugger
├── docs/                       # Formal Documentation & Architecture
│   ├── spec/                   # Allium formally verified domain system contracts
│   ├── architecture_diagrams/  # Architecture assets & Typst layouts
│   └── slides.typ              # Typst presentation slides
├── models/                     # Persisted local ML artifacts (Scalers, PyTorch Models, Metadata)
├── mosquitto/                  # MQTT Broker configuration and TLS certificates
├── tests/                      # Python `unittest` regression coverage
├── .gemini/                    # Agentic context mandates & conversation brain (`GEMINI.md`)
├── .agents/                    # Custom Allium and domain skills for Antigravity
├── docker-compose.yml          # Docker development stack (MQTT, DB, API, Frontend, Simulator)
├── justfile                    # Centralized task runner (Makefile alternative)
├── pixi.toml                   # Conda-compatible environment & dependency manager
├── pyproject.toml              # Ruff linting & Python metadata
└── README.md                   # You are here
```

---

## 🔧 Adding a New Satellite Decoder

The decoder system uses `satnogs-decoders` (Kaitai Structs) for binary parsing and a registry pattern for satellite-specific logic. To add support for a new satellite:

1. Create `src/gr_sat/decoders/<satellite>.py`
2. Subclass `BaseDecoder` and implement `decode()` + `adapt()`
3. Register with `@DecoderRegistry.register(NORAD_ID)`
4. Import in `src/gr_sat/decoders/__init__.py`

### Currently Supported Satellites

| Satellite | NORAD ID | Decoder | Status |
| :--- | :--- | :--- | :--- |
| **UWE-4** | 43880 | `decoders/uwe4.py` | ✅ Primary target, ~7 months of data |
