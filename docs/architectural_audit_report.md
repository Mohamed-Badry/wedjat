# Architectural Audit Report

**Project:** Project Wedjat — Satellite Telemetry Anomaly Detection System
**Date:** 2026-06-20
**Auditor Role:** Principal Systems Architect
**Scope:** Full-stack audit — core library, API layer, frontend, scripts, infrastructure

---

## 1. Executive Summary

Project Wedjat is a satellite telemetry monitoring and anomaly detection system built around a Python core library (`gr_sat`), a FastAPI backend, a SvelteKit frontend, TimescaleDB for time-series storage, and an MQTT broker for real-time data ingestion. The system fetches telemetry from SatNOGS, decodes satellite frames, trains a Variational Autoencoder (VAE) for anomaly detection, and presents results through a web dashboard.

**The core library (`src/gr_sat/`) is architecturally sound.** It has a clean acyclic dependency graph, well-defined module boundaries, and a solid decoder registry pattern. The decoders subsystem is the best-architected component in the entire codebase. However, the system suffers from **catastrophic architectural rot at the integration boundaries** — specifically the API layer and the scripts layer — where separation of concerns has collapsed entirely.

The single most critical structural failure is `src/api/dashboard_data.py`: a **1,200-line God Class** that has absorbed orbital mechanics, ML inference, time-series algorithms, data aggregation, health scoring, and pass prediction into a single monolithic service. This file alone constitutes a maintainability crisis that will block all future feature development. Combined with zero authentication on all endpoints and an open MQTT broker, the system is **architecturally unviable for any deployment beyond a local development machine**. The path forward requires surgical decomposition of the God Class, extraction of a proper data access layer, and introduction of security boundaries at every integration point.

---

## 2. Misplaced Components & Boundary Violations

### 2.1 Orbital Mechanics in the API Layer

* **Component:** Satellite pass prediction (Skyfield TLE loading, azimuth/elevation computation, sun illumination checks)
* **Current Location:** `src/api/dashboard_data.py` (~150 lines of orbital computation)
* **Why it's wrong:** Orbital mechanics is pure domain/science logic with zero HTTP, database, or dashboard concerns. It has no business existing inside an API data service. This logic is also **duplicated** in `scripts/predict_passes.py` with a completely independent implementation, meaning bug fixes in one location won't propagate to the other.
* **Correct Location:** A new `src/gr_sat/orbital.py` domain module, consumed by both the API layer and the CLI scripts through a clean interface.

### 2.2 ML Inference in the MQTT Callback

* **Component:** VAE model loading, forward pass, anomaly scoring, and result persistence
* **Current Location:** `src/api/mqtt_client.py` `on_message()` callback — interleaves message parsing, database writes, model loading from disk, torch inference, and more database writes in a single callback function.
* **Why it's wrong:** The MQTT callback is a transport-layer concern. It should receive a message, validate it minimally, and hand off to a processing pipeline. Instead, it performs blocking ML inference on the MQTT event loop, creates a new `DashboardDataRepository` instance per message (accessing a private `_score_frames()` method), and has no error isolation — a torch failure kills the entire telemetry ingestion path.
* **Correct Location:** The callback should enqueue frames into an async processing pipeline. ML inference should be handled by a dedicated worker/service that consumes from a queue, using a cached `Wedjat` singleton.

### 2.3 ML Inference Duplicated in API Data Service

* **Component:** VAE forward pass, scaler transforms, anomaly score computation
* **Current Location:** `src/api/dashboard_data.py` (lines performing `torch.no_grad()`, `scaler.transform()`, VAE reconstruction) — duplicates inference logic that already exists in `src/gr_sat/wedjat.py`.
* **Why it's wrong:** The API layer re-implements ML inference instead of delegating to the core library's `Wedjat` or `compute_anomaly_scores()`. This creates a second inference path that can drift from the training path.
* **Correct Location:** All inference should flow through `src/gr_sat/wedjat.py` or `src/gr_sat/models.compute_anomaly_scores()`. The API layer should only orchestrate, never compute.

### 2.4 Data Aggregation Algorithms in the API Layer

* **Component:** LTTB (Largest Triangle Three Buckets) time-series downsampling algorithm, daily aggregation, moving averages, statistical trend analysis
* **Current Location:** `src/api/dashboard_data.py` (~200 lines of algorithmic code)
* **Why it's wrong:** These are reusable, domain-agnostic algorithms. Embedding them in an API data service means they cannot be tested in isolation, reused by notebooks/scripts, or optimized independently.
* **Correct Location:** A `src/gr_sat/analytics.py` or `src/gr_sat/timeseries.py` utilities module.

### 2.5 Health Scoring Logic in the API Layer

* **Component:** Satellite health score computation based on telemetry ranges, battery thresholds, temperature bounds
* **Current Location:** `src/api/dashboard_data.py` (~100 lines)
* **Why it's wrong:** Health scoring is pure business/domain logic. It defines what "healthy" means for a satellite — this is a domain decision, not a presentation concern. It should be testable and auditable independently of the HTTP stack.
* **Correct Location:** `src/gr_sat/health.py` or as methods on `SatelliteProfile`.

### 2.6 Business Logic in Frontend Components

* **Component:** Pearson correlation computation, mean/std calculation, daily time-series aggregation, inter-pass gap detection, anomaly severity classification
* **Current Location:** Inline `<script>` blocks in Svelte components (`CorrelationHeatmap.svelte`, `FeatureDistributionGrid.svelte`, `MacroHealthPlot.svelte`, `InterPassGapHistogram.svelte`, `dashboard/+page.svelte`)
* **Why it's wrong:** Statistical computation is domain logic, not view logic. These implementations are untestable (no unit test framework for inline Svelte script), non-reusable, and some are duplicated from `lib/data/transforms.ts`.
* **Correct Location:** `frontend/src/lib/data/statistics.ts` for client-side computations, or ideally computed server-side and served via API endpoints.

### 2.7 Fake Data Masquerading as a Real Endpoint

* **Component:** Sensitivity sweep returning simulated F1/precision/recall/ROC data generated by mathematical formulas (`1.0 - abs(thresh - 0.5)`, etc.)
* **Current Location:** `src/api/dashboard_data.py` sensitivity sweep method
* **Why it's wrong:** An API endpoint that returns fabricated data is a trust violation. Consumers (the frontend) cannot distinguish this from real evaluation results. The frontend's `SensitivitySweepPlot.svelte`, `ModelComparisonROC.svelte`, and `FeatureContributionPlot.svelte` also embed hardcoded benchmark data directly in components.
* **Correct Location:** If real benchmark data isn't available, the endpoint should return a 404 or a response indicating no data. Hardcoded reference data should live in `frontend/src/lib/data/benchmarks.ts` and be clearly labeled as reference/mock data.

### 2.8 Duplicated Feature Engineering Between Batch and Online Paths

* **Component:** Rolling standard deviation computation for voltage and temperature features
* **Current Location:** `src/gr_sat/processing.py` (batch path, using pandas rolling windows) AND `src/gr_sat/wedjat.py` (online path, using `collections.deque` with independent implementation)
* **Why it's wrong:** Two independent implementations of the same feature engineering will inevitably diverge. If the batch processing module changes window sizes or backing fields, the online wedjat won't follow — causing train/serve skew that silently degrades anomaly detection accuracy.
* **Correct Location:** A shared `FeatureEngineer` abstraction in `src/gr_sat/features.py` with both batch (DataFrame) and online (streaming) implementations that share configuration (window sizes, field names) from a single source of truth.

### 2.9 Satellite Profile Data Duplicated Across Scripts

* **Component:** NORAD ID → satellite name/decoder mappings
* **Current Location:** `src/gr_sat/satellite_profiles.py` (canonical source) AND `scripts/fetch_training_data.py` (hardcoded fallback list with its own NORAD IDs and names)
* **Why it's wrong:** Two sources of truth for satellite identity. Adding a new satellite requires changes in multiple files.
* **Correct Location:** All satellite identity should flow from `src/gr_sat/satellite_profiles.py`. Scripts should import from the core library.

---

## 3. Critical Structural Flaws

### 3.1 The God Class: `DashboardDataRepository`

* **Description:** `src/api/dashboard_data.py` is a 1,200+ line monolithic class that has absorbed at least 10 distinct responsibilities: CSV file loading, database querying, DataFrame normalization, ML model loading and inference, VAE reconstruction diagnosis, satellite pass prediction via Skyfield, throughput analytics, time-series downsampling, health metric computation, JSON serialization, satellite identity resolution, and sensitivity sweep (with fake data). It is the architectural equivalent of a gravitational singularity — everything has collapsed into a single point.
* **Impact:** This class is the central dependency of the entire API. Every new feature, every bug fix, every performance optimization must touch this file. It is untestable in isolation (requires a database, ML models on disk, TLE files, and network access to CelesTrak). Merge conflicts are guaranteed on any team larger than one person. It violates SRP so severely that reasoning about any single behavior requires understanding all behaviors.
* **Evidence:**
  - `src/api/dashboard_data.py` — 45,840 bytes, 1,200+ lines, single class
  - Imports from 5 core library modules, stdlib, numpy, pandas, torch, skyfield, sqlalchemy
  - Contains inline `torch.no_grad()` calls (ML inference)
  - Contains inline Skyfield `EarthSatellite` computations (orbital mechanics)
  - Contains LTTB algorithm implementation (data science)
  - Contains health scoring logic (domain rules)
  - Contains fake data generation (testing concern)

### 3.2 Zero Authentication & Authorization

* **Description:** The entire system has no authentication or authorization layer. All API endpoints are publicly accessible. The MQTT broker has `allow_anonymous true` with port 1883 exposed to the host. CORS is configured with permissive origins. There are no user/session/auth tables in the database schema.
* **Impact:** Any client on the network can: read all telemetry data, trigger ML predictions, inject telemetry via MQTT, and access operational dashboards. This makes the system unsuitable for any deployment beyond localhost. Adding auth retroactively will require changes to every API endpoint, the MQTT client, and the frontend's data fetching layer.
* **Evidence:**
  - `src/api/main.py` — no auth middleware, no token validation on any route
  - `mosquitto/config/mosquitto.conf` — `allow_anonymous true`
  - `docker-compose.yml` — port 1883 exposed to host
  - `.env.example` — contains `MQTT_USERNAME`/`MQTT_PASSWORD` that are **never consumed** by the actual mosquitto.conf (static file that doesn't read env vars)
  - `db/init/001_schema.sql` — no users/roles/sessions tables

### 3.3 Model Loading on Every Request/Message

* **Description:** Both the `/api/predict` endpoint and the MQTT `on_message` callback instantiate new model objects and load PyTorch weights from disk on every invocation. The core library's `ModelArtifactStore` has a caching mechanism (`load_model_artifacts()` with lazy loading), but the API layer creates new instances each time instead of using it as a singleton.
* **Impact:** Model loading involves disk I/O (`torch.load()`, `joblib.load()`), memory allocation, and model construction — operations that take hundreds of milliseconds. Under any non-trivial telemetry throughput, this becomes a catastrophic bottleneck. The documented `MAJOR_BUGS.md` already identifies this as a known issue. Memory pressure from repeated allocations without proper cleanup will lead to OOM in long-running containers.
* **Evidence:**
  - `src/api/mqtt_client.py` — creates `DashboardDataRepository()` per MQTT message
  - `src/api/dashboard_data.py` — `load_model_artifacts()` called in scoring methods
  - `src/MAJOR_BUGS.md` — documents "Repeated model loading from disk" as a known bug
  - `src/gr_sat/model_artifacts.py` — has lazy caching that is never utilized at the API level

### 3.4 Dual Source of Truth for Database Schema

* **Description:** The database schema is defined in two places that contradict each other: `db/init/001_schema.sql` (the actual TimescaleDB init script) and `src/api/models.py` (SQLModel ORM definitions). The SQL script defines `raw_frames` with `id BIGSERIAL` and compound PK `(id, timestamp)`, while the SQLModel classes may define different column sets or constraints. There is no migration framework to keep them synchronized.
* **Impact:** Schema changes require manual coordination between two files with no enforcement mechanism. The SQLModel `create_db_tables()` function in `database.py` could silently create tables with different schemas than the SQL init script. Developers will be confused about which is canonical. This will cause production incidents when columns exist in one definition but not the other.
* **Evidence:**
  - `db/init/001_schema.sql` — raw SQL schema with TimescaleDB hypertables
  - `src/api/models.py` — SQLModel/SQLAlchemy ORM definitions
  - `src/api/database.py` — `create_db_tables()` that calls `SQLModel.metadata.create_all(engine)`
  - No Alembic, no migration scripts, no schema versioning

### 3.5 Synchronous Blocking in Async Context

* **Description:** FastAPI is an async framework, but the API layer performs blocking I/O operations synchronously: database queries via SQLAlchemy (synchronous engine), file reads for model loading, and HTTP requests to CelesTrak for TLE data — all within async route handlers. The MQTT callback also blocks the event loop with ML inference.
* **Impact:** Under concurrent load, a single slow database query or model load blocks the entire event loop, starving all other requests. The documented `RUNTIME_ERRORS.md` identifies "Blocking sync in async routes" as a known issue. This makes the system fundamentally unable to handle concurrent users.
* **Evidence:**
  - `src/api/database.py` — `create_engine()` (sync, not `create_async_engine()`)
  - `src/api/dashboard_data.py` — synchronous Skyfield TLE downloads within request handlers
  - `src/RUNTIME_ERRORS.md` — documents "Blocking I/O in async loop"
  - `src/MAJOR_BUGS.md` — documents "Blocking I/O in async loop — skyfield TLE download"

### 3.6 Dockerfile Production Readiness Failures

* **Description:** Both the API and frontend Dockerfiles ship with development-mode configurations. The API Dockerfile runs `uvicorn --reload` (file watching in production). The frontend Dockerfile runs `bun run dev` (Vite dev server with HMR, source maps, no tree-shaking). Neither has multi-stage builds, health checks, or non-root users.
* **Impact:** Development servers in production expose source maps, enable hot-reload file watching (performance overhead), skip minification/tree-shaking (larger bundles, slower loads), and may expose debug endpoints. The frontend's `adapter-node` build output is never used despite being configured. The API container pulls full CUDA-enabled PyTorch (~2.5GB) because `torch` is specified without the CPU-only index URL.
* **Evidence:**
  - `src/api/Dockerfile` — `CMD ["uvicorn", ... "--reload"]`
  - `frontend/Dockerfile` — `CMD ["bun", "run", "dev"]`
  - `src/api/requirements.txt` — `torch` without version pin or CPU index
  - `frontend/svelte.config.js` — `adapter-node` configured but never used in Docker

### 3.7 No Data Access Layer / Repository Pattern Abandoned

* **Description:** Database access is scattered across multiple locations with no consistent pattern. `dashboard_data.py` queries via SQLModel/SQLAlchemy. `mqtt_client.py` writes via SQLModel `Session`. Some documented versions show raw SQL strings in route handlers. There is no repository abstraction, no unit of work pattern, and no separation between query logic and business logic.
* **Impact:** Database queries cannot be tested without a live database. Query optimization requires hunting across multiple files. Adding database-level caching, read replicas, or switching to async queries requires touching every file that accesses the database.
* **Evidence:**
  - `src/api/dashboard_data.py` — `select()` queries with `.join()` and pandas DataFrame conversion
  - `src/api/mqtt_client.py` — `Session.add()` for writes
  - `src/api/database.py` — raw `text("SELECT 1")` for health checks
  - No `repository.py`, no DAO pattern, no query builder abstraction

### 3.8 Eager Imports Trigger Full Torch Initialization

* **Description:** `src/gr_sat/__init__.py` eagerly imports all modules including `models.py` (which imports `torch`). This means any `import gr_sat` — even if the consumer only needs `satellite_profiles` or `processing` — triggers a full PyTorch initialization (~2-3 seconds of startup time, ~500MB of memory).
* **Impact:** The simulator container copies and installs `gr_sat` (including torch as a transitive dependency) but may only need `satellite_profiles`. CLI scripts that only need to read profiles pay the full torch startup cost. This also bloats Docker images for services that don't need ML capabilities.
* **Evidence:**
  - `src/gr_sat/__init__.py` — `from .models import TelemetryVAE` (triggers `import torch`)
  - `src/simulator/Dockerfile` — `COPY src/gr_sat /app/src/gr_sat` + `pip install -e .`
  - `pixi.toml` — `torch = { version = "*" }` in dependencies

### 3.9 Inconsistent Configuration Management

* **Description:** The project has a `ml_config.py` that centralizes ML hyperparameters and paths, but it is systematically underutilized. Multiple modules hardcode their own paths (`Path("models")`, `Path("data/processed")`) instead of importing from `ml_config`. Hardcoded relative paths assume the working directory is the project root — breaking when scripts or containers run from different directories. Ground station coordinates are hardcoded in `scripts/predict_passes.py` despite being defined in `.env.example`.
* **Impact:** Configuration drift is inevitable. Changing a path requires grepping the entire codebase. Running from a different working directory silently reads/writes to wrong locations. Adding environment variable overrides requires modifying every hardcoded constant individually.
* **Evidence:**
  - `src/gr_sat/ml_config.py` — defines `MODEL_DIR`, `PROCESSED_DIR` etc.
  - `src/gr_sat/training.py` — hardcodes `Path("data/processed")` despite importing `ml_config`
  - `src/gr_sat/evaluation.py` — hardcodes `models_dir="models"`, `processed_dir="data/processed"`
  - `src/gr_sat/wedjat.py` — hardcodes `models_dir=Path("models")`
  - `src/api/dashboard_data.py` — hardcodes `Path("models")` separately
  - `scripts/predict_passes.py` — hardcodes latitude/longitude

### 3.10 Name Collisions Across Package Boundaries

* **Description:** Two critical naming collisions exist: (1) `src/api/models.py` (SQLModel ORM tables) vs `src/gr_sat/models.py` (PyTorch VAE neural network) — both named `models.py` but serving completely different purposes. (2) `TelemetryFrame` exists as a dataclass in `src/gr_sat/telemetry.py` AND as a SQLModel class in `src/api/models.py` — same name, different types, different fields.
* **Impact:** Developers will inevitably write `from models import ...` and get the wrong module depending on `sys.path` order. IDE autocompletion will suggest wrong symbols. Refactoring tools will confuse the two. The `TelemetryFrame` collision is especially dangerous — passing the wrong type across an API boundary will produce subtle runtime errors, not import errors.
* **Evidence:**
  - `src/api/models.py` — defines `RawFrame`, `TelemetryFrame` (ORM)
  - `src/gr_sat/models.py` — defines `TelemetryVAE`, `compute_anomaly_scores` (ML)
  - `src/gr_sat/telemetry.py` — defines `TelemetryFrame` (dataclass)
  - `src/api/dashboard_data.py` — imports from both `gr_sat.models` and `.models` in the same file

### 3.11 2.5MB Stale Data Files Committed to Source Control

* **Description:** Two copies of CelesTrak orbital element data files exist with a misleading `.php` extension: `gp.php` at the project root (2.4MB) and `src/api/gp.php` (2.5MB). These are plain-text TLE data, not PHP code. The `.gitignore` only covers the root copy (`gp.php`), meaning the `src/api/` copy is likely committed to Git. The `.dockerignore` similarly only matches the root copy, so the API Docker image is bloated by 2.5MB of stale orbital data.
* **Evidence:**
  - `/home/crim/Projects/gr_sat/gp.php` — 2,443,728 bytes
  - `/home/crim/Projects/gr_sat/src/api/gp.php` — 2,583,672 bytes (different size = different epoch)
  - `.gitignore` — contains `gp.php` (root only, not `**/gp.php`)
  - `src/api/dashboard_data.py` — references gp.php for TLE loading

---

## 4. Refactoring Directives

### Directive 1: Decompose the God Class (Priority: CRITICAL)

**Target:** `src/api/dashboard_data.py` → 5-6 focused modules

**Steps:**
1. **Extract `src/gr_sat/orbital.py`** — Move all Skyfield pass prediction logic (TLE loading, azimuth/elevation computation, visibility checks) into a new core library module. Define a clean `predict_passes(norad_id, ground_station, time_window) -> list[Pass]` interface. Delete the duplicate in `scripts/predict_passes.py` and replace it with a thin CLI wrapper.
2. **Extract `src/gr_sat/health.py`** — Move health scoring logic (battery thresholds, temperature bounds, health grade computation) into a new core module. Health rules should be defined on or alongside `SatelliteProfile`.
3. **Extract `src/gr_sat/analytics.py`** — Move LTTB downsampling, moving averages, trend analysis, and statistical computations into a reusable analytics module.
4. **Create `src/api/repositories/telemetry_repo.py`** — Extract all database query logic into a proper repository class with methods like `get_frames(norad_id, since, limit)`, `get_anomaly_scores(norad_id, since)`, `insert_frame(frame)`, etc. This becomes the single point of database access.
5. **Reduce `dashboard_data.py` to orchestration only** — It should do nothing more than call repository methods, pass results to domain services, and format responses. Target: <200 lines.
6. **Remove fake sensitivity sweep data** — Either implement real evaluation data storage or return 404 with an appropriate message.

### Directive 2: Implement Application-Level Security (Priority: CRITICAL)

**Steps:**
1. **Add API authentication** — Implement API key or JWT-based authentication middleware in FastAPI. At minimum, add an `X-API-Key` header check for all `/api/*` routes.
2. **Secure the MQTT broker** — Replace the static `mosquitto.conf` with a template that enforces `allow_anonymous false`, configures username/password authentication, and optionally enables TLS. Generate the config from environment variables at container startup using an entrypoint script.
3. **Restrict CORS** — Replace wildcard/permissive CORS with an explicit allowlist sourced from environment variables.
4. **Add rate limiting** — Use `slowapi` or similar to rate-limit prediction and data-heavy endpoints.
5. **Create auth tables** — Add `api_keys` or `users` table to the database schema.

### Directive 3: Introduce Model Caching and Async Processing (Priority: HIGH)

**Steps:**
1. **Create a model cache singleton** — Implement a `ModelCache` class (or use `ModelArtifactStore`'s existing lazy loading) as a FastAPI dependency that loads models once at startup and caches them in memory. Inject via FastAPI's dependency injection.
2. **Decouple MQTT ingestion from ML inference** — The MQTT callback should only validate and persist the raw frame. Anomaly scoring should happen asynchronously via a background task, a separate worker process, or at minimum a FastAPI `BackgroundTasks` queue.
3. **Add error isolation** — Wrap ML inference in a separate try/except from database persistence. A torch failure should never prevent telemetry from being stored.

### Directive 4: Fix Dockerfiles for Production (Priority: HIGH)

**Steps:**
1. **API Dockerfile:** Remove `--reload` from CMD. Add multi-stage build (builder stage for pip install, runtime stage for slim image). Pin `torch` to CPU-only index URL. Add `HEALTHCHECK`. Run as non-root user.
2. **Frontend Dockerfile:** Change `CMD` from `bun run dev` to `bun run build && node build`. Use multi-stage build (build stage with bun, runtime stage with node). Add `HEALTHCHECK`.
3. **Simulator Dockerfile:** Remove the unused `COPY src/gr_sat` if the simulator truly doesn't import it. If it does need profiles, consider extracting `satellite_profiles` into a lightweight package without torch dependency.

### Directive 5: Unify Configuration Management (Priority: HIGH)

**Steps:**
1. **Make `ml_config.py` the single source of truth** — All path constants, hyperparameters, and thresholds must be imported from here. Grep for all hardcoded `Path("models")`, `Path("data/...")` patterns and replace with `ml_config` imports.
2. **Add environment variable overrides** — Modify `ml_config.py` to read from env vars with fallbacks: `MODEL_DIR = Path(os.getenv("MODEL_DIR", "models"))`.
3. **Use absolute paths derived from a project root** — Compute `PROJECT_ROOT = Path(__file__).resolve().parents[2]` once and derive all paths from it.
4. **Move ground station config to `.env`** — The `.env.example` already has `GS_LATITUDE`/`GS_LONGITUDE`. Scripts and API should read from these.

### Directive 6: Resolve Name Collisions (Priority: MEDIUM)

**Steps:**
1. **Rename `src/api/models.py`** → `src/api/db_models.py` or `src/api/schema.py`. Update all imports.
2. **Rename `src/gr_sat/models.py`** → `src/gr_sat/vae.py` or `src/gr_sat/neural.py`. This is the ML model definition — the name should reflect that.
3. **Differentiate `TelemetryFrame` types** — Rename the ORM version to `TelemetryRecord` or `TelemetryRow`. Keep the domain dataclass as `TelemetryFrame`.

### Directive 7: Introduce Database Migration Framework (Priority: MEDIUM)

**Steps:**
1. **Add Alembic** to the project dependencies.
2. **Generate initial migration** from the current `db/init/001_schema.sql` schema.
3. **Make SQLModel definitions canonical** — Remove `db/init/001_schema.sql` after verifying Alembic migrations produce the same schema.
4. **Add migration step** to the Docker Compose startup flow (run Alembic `upgrade head` before the API starts).

### Directive 8: Fix Lazy Import Chain for Core Library (Priority: MEDIUM)

**Steps:**
1. **Make `__init__.py` imports lazy** — Use `__getattr__` pattern or conditional imports so that `import gr_sat` doesn't trigger torch loading.
2. **Split the package** — Consider splitting `gr_sat` into `gr_sat.core` (profiles, processing, telemetry — no torch) and `gr_sat.ml` (models, training, wedjat — requires torch). This allows lightweight consumers (simulator, scripts that only fetch data) to avoid the torch dependency entirely.

### Directive 9: Establish Frontend Data Layer (Priority: MEDIUM)

**Steps:**
1. **Create `frontend/src/lib/stores/`** — Implement Svelte 5 `$state`-based stores for shared data (satellite list, active satellite, connection status). This eliminates redundant fetching across pages.
2. **Move all statistical computation** from Svelte components into `frontend/src/lib/data/statistics.ts`.
3. **Fix the code duplication** — `eda/+page.svelte` re-implements `lib/data/transforms.ts` functions. Delete the duplicates and import from the shared module.
4. **Fix the analytics loader** — `analytics/+page.ts` bypasses the centralized `apiFetch()` client. Migrate it to use the shared API client.
5. **Move hardcoded benchmark data** from chart components into `frontend/src/lib/data/benchmarks.ts` and clearly label it as reference/static data.

### Directive 10: Clean Up Repository Hygiene (Priority: LOW)

**Steps:**
1. **Delete both `gp.php` files** — Add `**/gp.php` to `.gitignore`. Fetch TLE data at runtime or cache it in `data/` (which is already gitignored).
2. **Remove dead dependencies** — `date-fns` (frontend, unused), `loguru` (API requirements.txt, unused per one subagent's analysis).
3. **Standardize script patterns** — Refactor `fetch_training_data.py`, `predict_passes.py`, and `viz_telemetry.py` to follow the thin-wrapper pattern established by `train_model.py` and `generate_faults.py`. Move their business logic into core library modules.
4. **Fix `.env` handling** — Verify `.env` is properly gitignored (it appears to be per `.gitignore`). Remove default credentials from `docker-compose.yml` fallbacks or document them clearly as development-only.

---

## Appendix A: Dependency Graph

```
                     ┌─────────────────────────────────────────────────┐
                     │                   FRONTEND                      │
                     │            SvelteKit + Chart.js                  │
                     │    (fetch → /api/* endpoints, WebSocket)        │
                     └─────────────────────┬───────────────────────────┘
                                           │ HTTP / WS
                     ┌─────────────────────▼───────────────────────────┐
                     │                  API LAYER                       │
                     │     main.py ─► dashboard_data.py (GOD CLASS)    │
                     │     mqtt_client.py ─► dashboard_data.py         │
                     │     database.py    models.py (ORM)              │
                     └──────┬──────────────┬───────────────────────────┘
                            │              │
              ┌─────────────▼──┐    ┌──────▼──────────┐
              │   TimescaleDB  │    │   MQTT Broker    │
              │  (schema in    │    │  (anonymous,     │
              │   SQL + ORM)   │    │   no auth)       │
              └────────────────┘    └──────▲──────────┘
                                          │ MQTT publish
                     ┌────────────────────┴────────────────────────────┐
                     │                 SIMULATOR                        │
                     │    replay.py (standalone, no core imports)       │
                     └─────────────────────────────────────────────────┘

                     ┌─────────────────────────────────────────────────┐
                     │              CORE LIBRARY (gr_sat)               │
                     │                                                  │
                     │  telemetry.py ◄── decoders/uwe4.py              │
                     │  satellite_profiles.py (leaf)                    │
                     │  processing.py (leaf)                            │
                     │  ml_config.py ──► satellite_profiles             │
                     │  models.py ──► ml_config                        │
                     │  model_artifacts.py ──► models, ml_config       │
                     │  training.py ──► model_artifacts, models, ...   │
                     │  evaluation.py ──► model_artifacts, models, ... │
                     │  wedjat.py ──► model_artifacts, models, ...   │
                     │                                                  │
                     │  ✅ Clean DAG — no circular dependencies         │
                     └─────────────────────────────────────────────────┘
```

## Appendix B: File Size Heat Map (Complexity Indicators)

| File | Lines | Bytes | Risk Level |
|------|-------|-------|------------|
| `src/api/dashboard_data.py` | ~1,200 | 45,840 | 🔴 **CRITICAL** |
| `src/gr_sat/telemetry.py` | 294 | 9,566 | 🟢 Clean |
| `src/gr_sat/wedjat.py` | 254 | 8,916 | 🟡 Moderate |
| `src/gr_sat/evaluation.py` | 251 | 9,735 | 🟡 Moderate |
| `src/gr_sat/model_artifacts.py` | 250 | 8,330 | 🟡 Moderate |
| `src/gr_sat/decoders/uwe4.py` | 222 | — | 🟢 Clean |
| `src/gr_sat/processing.py` | 218 | 7,114 | 🟢 Clean |
| `src/gr_sat/training.py` | 198 | 6,115 | 🟡 Moderate |
| `src/api/main.py` | 186 | 6,339 | 🟢 Clean |
| `src/api/mqtt_client.py` | 149 | 5,112 | 🟡 Moderate |
| `src/gr_sat/satellite_profiles.py` | 125 | 3,478 | 🟢 Clean |
| `src/gr_sat/models.py` | 87 | 2,676 | 🟢 Clean |
| `src/api/database.py` | 82 | 2,239 | 🟢 Clean |
| `src/api/models.py` | 32 | 1,103 | 🟢 Clean |
| `src/gr_sat/ml_config.py` | 19 | 510 | 🟢 Clean |
| `scripts/fetch_training_data.py` | 360 | 12,533 | 🟡 Moderate |
| `scripts/process_data.py` | 317 | 11,207 | 🟢 Clean (good delegation) |
| `scripts/predict_passes.py` | 164 | 5,991 | 🟡 Isolated island |
| `frontend operations/+page.svelte` | 448 | — | 🟡 Moderate |
| `frontend eda/+page.svelte` | 382 | — | 🟡 Code duplication |
| `frontend ml/+page.svelte` | 299 | — | 🟡 Moderate |
| `frontend dashboard/+page.svelte` | 273 | — | 🟡 Moderate |

## Appendix C: What's Actually Good

In the interest of objectivity, these components are well-architected and should be preserved as-is:

1. **Decoder registry pattern** (`src/gr_sat/decoders/`) — Clean base class, decorator-based registration, proper separation. Best-in-class component.
2. **Core library dependency graph** — Acyclic DAG with clear leaf nodes. No circular dependencies. Clean layering.
3. **`train_model.py` and `generate_faults.py`** — Exemplary thin CLI wrappers. All other scripts should follow this pattern.
4. **Frontend type contracts** (`lib/types/api.ts`) — 129 lines of well-defined TypeScript interfaces for API responses.
5. **Frontend API client** (`lib/api.ts`) — Centralized, SSR-aware, typed generic fetch wrapper.
6. **Frontend chart component library** — 19 focused chart components in `lib/components/charts/`, most under 100 lines.
7. **Frontend design system** — Tailwind v4 `@theme` tokens with consistent usage across components.
8. **Docker Compose orchestration** — Proper health checks, dependency ordering, volume strategy, and `develop.watch` configuration.
9. **Credential masking** in `database.py` — `safe_url` property strips passwords from logged URLs.
10. **JSONB features column** in database schema — Avoids schema migrations when adding satellites. Pragmatic trade-off.
