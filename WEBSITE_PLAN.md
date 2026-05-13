# gr_sat Web Interface & Integration Plan

Based on the analysis of the current `gr_sat` repository, this document outlines the state of the project, major architectural flaws related to online operations, and a comprehensive plan for building a modern web-based frontend (SvelteKit) and API backend (FastAPI), orchestrated via **Docker**. The initial Docker and SvelteKit scaffolding now exists in the repository; this document still describes the broader target UX and service behavior that remain to be built.

## 1. Current State Analysis
The `gr_sat` repository has successfully established a robust **offline machine learning pipeline** for satellite telemetry:
- **Data Pipeline:** Fetching (SatNOGS API) -> Decoding (Kaitai Structs) -> Normalization (Golden Features).
- **Modeling:** Per-satellite Autoencoders/VAEs are trained and evaluated using synthetic-fault benchmarking.
- **Core Logic:** The Python codebase (`src/gr_sat`) is well-structured with dedicated modules for decoding, processing, profiles, and models.
- **Minimal Runtime:** A rudimentary, single-threaded online inference loop (`watchdog_runtime.py`) exists but lacks network ingress, persistence, or a UI.

---

## 2. Containerization Strategy & Tech Stack (Docker)
Dockerizing this project provides a clean separation of concerns and makes deploying to edge hardware (like a ground station PC or Raspberry Pi) trivial. We will use **Docker Compose** to orchestrate 5 microservices:

1. **`broker` (Eclipse Mosquitto - MQTT):** 
   - *Tech:* C (Mosquitto).
   - *Role:* The message bus handling live high-frequency telemetry from the antenna. Extremely lightweight.
2. **`db` (PostgreSQL + TimescaleDB):** 
   - *Tech:* PostgreSQL with the TimescaleDB extension.
   - *Role:* Time-series optimized database to persist telemetry history, ML anomalies, and pass metadata.
3. **`backend` (FastAPI):** 
   - *Tech:* Python, FastAPI, Uvicorn, PyTorch, Paho-MQTT, SQLAlchemy/SQLModel.
   - *Role:* Subscribes to the `broker`, runs the Kaitai decoders & VAE ML inference, writes to the `db`, and serves WebSockets/REST APIs to the frontend.
4. **`frontend` (SvelteKit):** 
   - *Tech:* **Bun** (Runtime/Package Manager - *No Node.js*), Svelte 5, TypeScript, TailwindCSS, Shadcn-Svelte/Skeleton.
   - *Role:* Serves the real-time UI dashboard and orbital tracking visualizations.
5. **`simulator` (Python):** 
   - *Tech:* Python.
   - *Role:* A testing container that replays historical offline data from `data/raw/` into the `broker` to simulate a live antenna.

---

## 3. Database Schema Strategy (Raw vs. Processed)

To ensure the web dashboard is extremely fast, **we must store both raw and processed data.** 

If we only stored the `raw_frame`, the backend would be forced to re-run the Kaitai decoder and the PyTorch ML model every single time the user opens the dashboard or changes the timeframe to view historical charts. This is computationally wasteful.

### Proposed Table Schema: `telemetry_frames` (TimescaleDB Hypertable)
We will use a hypertable partitioned by `timestamp`.

- `id` (UUID or BigSerial): Primary Key.
- `timestamp` (Timestamptz): Exact time of reception (Hypertable index).
- `norad_id` (Integer): Satellite identifier (e.g., 43880).
- `station_id` (String): Which antenna received it.
- `raw_frame` (String): The original hex-encoded payload.
- `features` (JSONB): The decoded "Golden Features" (e.g., `{"batt_voltage": 5.1, "temp_batt_a": 12.0}`). Using JSONB means we don't need to migrate the database schema every time a new satellite profile with different features is added.
- `anomaly_score` (Float): The loss value from the VAE model.
- `is_anomaly` (Boolean): Whether the score exceeded the pre-calibrated threshold.
- `missing_fields` (JSONB/Array): List of fields that could not be parsed.

---

## 4. Telemetry Streaming: The MQTT Antenna Contract

The antenna/demodulator software (GNU Radio, SatNOGS client, etc.) simply needs to act as an MQTT Publisher. It should publish a JSON payload to the topic `telemetry/live/{norad_id}` (e.g., `telemetry/live/43880`).

**Required Output Shape:**
```json
{
  "norad_id": 43880,
  "timestamp": "2026-05-05T14:30:22Z",
  "raw_frame": "8A8A8A8A8A8A...",
  "station_id": "my_local_antenna_1",
  "snr": 12.5 
}
```

---

## 5. Recommended Repository Layout

```text
gr_sat/
├── data/                   # Existing data
├── docs/                   # Diagrams and documentation
├── scripts/                # Existing offline ML scripts
├── docker-compose.yml      # Orchestrates all 5 containers
├── src/
│   ├── gr_sat/             # Existing Core Library
│   ├── api/                # FastAPI Backend
│   │   ├── Dockerfile
│   │   ├── main.py         # REST/WebSocket endpoints
│   │   ├── mqtt_client.py  # Subscribes to broker, triggers ML inference
│   │   ├── database.py     # SQLAlchemy async connection
│   │   └── routers/        # Modular endpoint groups
│   │       ├── status.py
│   │       ├── operations.py
│   │       ├── insights.py
│   │       ├── ml.py
│   │       └── websocket.py
│   └── simulator/          # Antenna mock
│       ├── Dockerfile
│       └── replay.py       # Reads data/raw/ and publishes to MQTT
├── frontend/               # SvelteKit Project
│   ├── Dockerfile          # Uses oven/bun base image
│   ├── bun.lock
│   ├── src/
│   │   ├── app.html        # Main HTML shell
│   │   ├── routes/
│   │   │   ├── +layout.svelte     # Root: theme toggle, app.css
│   │   │   ├── (landing)/         # Route group: antenna bg, top nav
│   │   │   │   ├── +layout.svelte
│   │   │   │   ├── +page.svelte   # Landing hero
│   │   │   │   └── team/+page.svelte
│   │   │   └── (dashboard)/       # Route group: sidebar, footer
│   │   │       ├── +layout.svelte
│   │   │       └── dashboard/
│   │   │           ├── +page.svelte       # Dashboard home
│   │   │           ├── operations/        # Pass prediction, skyplots
│   │   │           ├── live/              # Live packet watcher
│   │   │           ├── insights/          # EDA & telemetry explorer
│   │   │           └── ml/               # VAE vs Z-Score, model health
│   │   └── lib/
│   │       ├── components/    # Shared + page-specific components
│   │       └── shaders/       # WebGL shader sources
│   └── tailwind.config.js     # Dual-color Theme definitions
└── README.md
```

---

## 6. Theme, Styling & Layout Architecture (SvelteKit)

The UI will be designed around a **Dual-Color Light/Dark Theme** driven by CSS variables to ensure strict modularity and easy white-labeling. 

### A. Navigation Architecture
The site uses **two distinct layout shells**:

1. **Landing Shell** (`(landing)` route group): For `/` and `/team`.
   - Top navbar with Overview / Team tabs.
   - Holographic antenna WebGL background.
   - Striking "Enter Dashboard →" CTA button on the landing hero.

2. **Dashboard Shell** (`(dashboard)` route group): For `/dashboard/**`.
   - **No** Overview/Team tabs in the header.
   - Collapsible sidebar with sub-page links: Operations, Live, Insights, ML Lab.
   - Footer with links back to Overview/Team/GitHub.
   - Logo click returns to landing (`/`).
   - No antenna background (dashboard has its own data-focused aesthetic).

### B. Color Palette
Derived from the academic Typst templates, adapting to web conventions:
- **Primary Accent:** Pinkish Red (`#B12142`) - Used for highlights, active states, and H1 banners.
- **Secondary Accent:** Muted Slate Gray (`#6C7A96`) - Used for secondary text, borders, and sub-headers.
- **Light Mode Base:** Near-white (`#F8FAFC`) with dark text (`#111827`).
- **Dark Mode Base:** AMOLED black (`#000000`) with light text (`#F8FAFC`).

### C. WebGL Background Integration
The `(landing)/+layout.svelte` will mount a `<canvas>` element fixed to the background (`z-index: -1`). 
- **Effect:** A grid of antennas that orient themselves to point towards the user's mouse cursor.
- **Animation:** They will shoot a small oscillating signal (using the Primary/Secondary CSS variables for colorization).
- **Performance:** Rendered via WebGL ensuring it does not block the Svelte UI thread.
- **Scope:** Only active on landing/team pages — disabled inside dashboard.

---

## 7. Dashboard Architecture

> **Full specification with API contracts, data shapes, and component hierarchy:**
> See `dashboard_plan.md` (artifact) for the complete dashboard blueprint.

> **Visualization layer migration plan (LayerChart → SveltePlot):**
> See [`frontend/DASHBOARD_SVELTEPLOT_PLAN.md`](frontend/DASHBOARD_SVELTEPLOT_PLAN.md) for the granular, 5-phase refactoring execution plan covering every chart component, data transforms, theming, and interactivity.

### Summary of Dashboard Sub-Pages:

1. **Dashboard Home** (`/dashboard`) — Service status grid, active satellites, recent anomalies, throughput sparkline.
2. **Operations** (`/dashboard/operations`) — Pass prediction, skyplots, timeline Gantt, satellite rankings. Powered by Skyfield.
3. **Live Watcher** (`/dashboard/live`) — Real-time packet decode visualization, feature gauges, anomaly score timeline. Powered by WebSocket.
4. **EDA & Insights** (`/dashboard/insights`) — Historical telemetry explorer, distributions, eclipse scatter, correlation heatmap, PCA projection.
5. **ML Lab** (`/dashboard/ml`) — VAE vs Z-Score sensitivity curves, ROC comparisons, score distributions, latent space visualization, threshold tuning.

---

## 8. Execution Phases

### Phase 1 — Foundation (Current)
- Restructure frontend routes into `(landing)` and `(dashboard)` groups
- Build DashboardLayout with sidebar + footer
- Create dashboard home with placeholder cards
- Implement `database.py` and `GET /api/status`

Implemented backend API contracts:
- `GET /api/status` returns API/database/artifact component health, dashboard endpoint links, and supported satellite identity metadata.
- `GET /api/dashboard/summary` returns the dashboard-home payload: service status, total frame/anomaly/pass counts, active satellites, recent anomalies, and throughput buckets.
- `GET /api/satellites` and `GET /api/satellites/{norad_id}` expose dataset coverage, feature-contract details, decoder identity, and model artifact health.
- `GET /api/telemetry/recent` returns recent frames in a stable `{timestamp, norad_id, source, features, quality, model}` structure.
- `GET /api/anomalies/recent` returns recent anomaly records sorted newest-first.
- `GET /api/telemetry/throughput` returns hour/day buckets with frame and anomaly counts for sparkline rendering.

Current data source: local `data/processed/{norad_id}.csv` plus `models/{norad_id}_metadata.json`, scaler, and VAE artifacts. The same response shapes are intended to be backed by TimescaleDB once live persistence is implemented.

### Phase 2 — Live Pipeline
- Implement MQTT subscriber → decode → score → persist
- Implement `WS /api/ws/telemetry`
- Build PipelineVisualizer (animated decode flow)
- Wire simulator → broker → backend → frontend end-to-end

### Phase 3 — Operations
- Port pass prediction logic into backend service
- Build skyplot, schedule table, timeline Gantt

### Phase 4 — Insights & ML Lab
- Implement aggregation queries for EDA
- Port sensitivity sweep into backend
- Build all insight + ML frontend components

### Phase 5 — Polish
- Responsive sidebar, loading skeletons, error boundaries
- Theme verification, performance audit

---

## 9. UI/UX Polish & Modernization Plan

This section outlines the detailed strategy to elevate the visual fidelity of the application, ensuring a modern, "alive," and polished feel through typography, spacing, subtle interactions, and consistent design language.

### A. UI & Asset Polish

#### 1. Shadows & Depth
Currently, the UI might rely on heavy box-shadows. The goal is to transition to a cleaner, more subtle aesthetic.
- [ ] **Audit Existing Shadows:** Identify all components using heavy or default Tailwind `box-shadow` values.
- [ ] **Define Shadow Strategy:** Plan a shift to lighter, more modern utility classes (e.g., `shadow-sm`, border-driven elevation using `border-slate-200/50`, or customized low-opacity drop shadows `shadow-[0_1px_2px_rgba(0,0,0,0.05)]`).
- [ ] **Apply Subtle Depth:** Replace all hard, dark shadows with the new subtle, layered shadow strategy.
- [ ] **Incorporate Borders:** Use subtle 1px borders combined with light shadows to create depth without visual noise.

#### 2. Iconography Standardization
Emojis used as UI elements (especially in sidebars and navigation) can look unprofessional and inconsistent across platforms.
- [ ] **Audit Emoji Usage:** Identify all instances where emojis are used as icons (e.g., in the sidebar, buttons, status indicators).
- [ ] **Integrate Icon Library:** Integrate `lucide-svelte` (or `phosphor-svelte`).
- [ ] **Map Replacements:** Replace emojis with strictly typed icons, leveraging Tailwind utility classes (e.g., `size-5`, `text-slate-500`, `hover:text-primary`) for styling and hover states.

### B. Landing Page Overhaul

The landing page needs to move away from placeholder "status" metrics and instead showcase the actual value and workflows of the application.

- [ ] **Deprecate Status Metrics:** Remove placeholder metrics and "dummy" status indicators from the hero section.
- [ ] **Redesign Hero Section:** Focus on a strong value proposition. Use a clean, bold typography and a clear CTA ("Enter Dashboard →").
- [ ] **Feature Highlights:** Surface actual capabilities drawn directly from the dashboard workflows. Create sections/cards for:
  - **Live Telemetry:** Real-time decoding and monitoring.
  - **Machine Learning Insights:** VAE anomaly detection and feature correlation.
  - **Pass Operations:** Predictive tracking and skyplot visualizations.
- [ ] **Layout Modernization:** Ensure generous whitespace to allow content to breathe. Use a standard zig-zag (text left/image right, then image left/text right) layout for feature highlights.

### C. Animation Strategy & Technical Best Practices

We will adopt a clear division of labor between native Svelte capabilities and GSAP to maximize performance and maintainability.

#### 1. Native Svelte Transitions
- [ ] **Standard Interactions:** Use `svelte/transition` (`fly`, `fade`, `slide`) for standard component mounting/unmounting (e.g., sidebar toggles, dropdowns, modal visibility states).
- [ ] **Bundle Efficiency:** Prefer native Svelte transitions for simple UI micro-interactions to avoid unnecessary bundle overhead.

#### 2. GSAP Integration via Svelte Actions
- [ ] **Complex Animations:** Plan complex landing page sequences and scroll-triggered animations (e.g., ScrollTrigger) using GSAP.
- [ ] **Declarative Approach:** Mandate the use of **Svelte Actions** (e.g., `use:gsapAction`) to attach timelines directly to DOM nodes, keeping component markup clean and declarative.
- [ ] **Lifecycle & Cleanup:** Ensure strict adherence to using `gsap.context()` within the action's lifecycle (destroy/update) to ensure proper garbage collection, prevent memory leaks, and handle ScrollTrigger duplication during Hot Module Replacement (HMR).

#### 3. Entry Staggers
- [ ] **List & Grid Staggers:** When a list of items (e.g., recent anomalies, satellite passes, or feature cards) mounts, use GSAP `stagger` to animate their entry (e.g., slight delay between items) sliding up and fading in.
- [ ] **Dashboard Load:** Animate the initial dashboard load by staggering the entry of individual data cards for a polished feel.

#### 4. Micro-interactions
- [ ] **Hover States:** Add subtle scale-ups (e.g., `scale: 1.02`) and shadow transitions to interactive cards and buttons using GSAP.
- [ ] **Active States:** Add "click" feedback (e.g., slight scale-down) to buttons and actionable elements.
- [ ] **Data Updates:** Briefly flash, pulse, or use GSAP number-tick animations in the dashboard when new live telemetry data arrives to draw attention without being distracting.
