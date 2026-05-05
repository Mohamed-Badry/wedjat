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
├── docker-compose.yml      # NEW: Orchestrates all 5 containers
├── src/
│   ├── gr_sat/             # Existing Core Library
│   ├── api/                # NEW: FastAPI Backend
│   │   ├── Dockerfile
│   │   ├── main.py         # REST/WebSocket endpoints
│   │   ├── mqtt_client.py  # Subscribes to broker, triggers ML inference
│   │   └── database.py     # SQLModel/SQLAlchemy connection
│   └── simulator/          # NEW: Antenna mock
│       ├── Dockerfile
│       └── replay.py       # Reads data/raw/ and publishes to MQTT
├── frontend/               # NEW: SvelteKit Project
│   ├── Dockerfile          # Uses oven/bun base image
│   ├── bun.lockb           # Replaces package-lock.json
│   ├── src/
│   │   ├── app.html        # Main HTML shell
│   │   ├── routes/         # Page components (+page.svelte)
│   │   │   ├── +layout.svelte # Global shell & WebGL Background
│   │   │   ├── +page.svelte   # Landing Page
│   │   │   ├── dashboard/     # Dashboard & sub-services
│   │   │   └── team/          # Team Introduction Page
│   │   └── lib/            # Shared components & styles
│   │       ├── components/ # Shadcn UI blocks
│   │       └── theme/      # CSS Variables and theme logic
│   └── tailwind.config.js  # Dual-color Theme definitions
└── README.md
```

---

## 6. Theme, Styling & Layout Architecture (SvelteKit)

The UI will be designed around a **Dual-Color Light/Dark Theme** driven by CSS variables to ensure strict modularity and easy white-labeling. 

### A. Modularity Strategy
- **`+layout.svelte`:** This root layout file will wrap every page. It will inject the global navbar, manage the Light/Dark mode state, inject the WebGL background, and provide CSS variables to all child pages.
- **CSS Variables:** Colors, logos, and team names will be defined in a centralized `src/lib/theme/config.ts` and injected as CSS variables (e.g., `--color-primary`, `--team-name`). This ensures that swapping the team identity or color scheme reflects instantly across the entire app without hunting down hardcoded values.

### B. Color Palette
Derived from the academic Typst templates, adapting to web conventions:
- **Primary Accent:** Pinkish Red (`#B12142`) - Used for highlights, active states, and H1 banners.
- **Secondary Accent:** Muted Slate Gray (`#6C7A96`) - Used for secondary text, borders, and sub-headers.
- **Light Mode Base:** Near-white (`#F8FAFC`) with dark text (`#111827`).
- **Dark Mode Base:** Deep Slate (`#0F172A`) with light text (`#F8FAFC`).

### C. Visual Components & Typography
We will build Svelte components (`.svelte`) that mimic the Typst academic styling but feel native to the web:
- **H1 Banners:** "Pill-shaped" sticky headers with the Primary color background and white bold text, using rounded corners (e.g., `rounded-r-2xl rounded-l-none`).
- **H2 Sections:** Bold Primary colored text with an underline stretching across the container (`border-b border-slate`).
- **H3 Subsections:** Subtle left-bordered containers with a light background.
- **Callout Blocks (Cards):**
  - **Definitions/Theorems:** Cards with colored backgrounds (lightened versions of Primary/Secondary colors in light mode) and thick left-borders.
  - **Q&A Blocks:** Alternating slate background cards to distinguish between questions and answers clearly.

### D. WebGL Background Integration
The `+layout.svelte` will mount a `<canvas>` element fixed to the background (`z-index: -1`). 
- **Effect:** A grid of antennas that orient themselves to point towards the user's mouse cursor.
- **Animation:** They will shoot a small oscillating signal (using the Primary/Secondary CSS variables for colorization).
- **Performance:** Rendered via WebGL (e.g., Three.js or native WebGL) ensuring it does not block the Svelte UI thread.

### E. Page Structure
1. **`/` (Landing Page):** 
   - Focused on marketing the graduation project.
   - Highlighting the WebGL background.
   - Clear Call-to-Action to enter the Dashboard.
2. **`/dashboard` (Live Monitoring):**
   - The core telemetry grid.
   - Sub-pages (e.g., `/dashboard/ml-metrics`, `/dashboard/other-services`) for teammates to plug in their respective work.
   - Real-time WebSockets feed, Orbit Tracking, and PyTorch inference charts.
3. **`/team` (About Us):**
   - Academic-style introductions, team pictures, roles, and faculty acknowledgment (matching the BSU/NSST logo styles from the Typst cover page).

---

## 7. Execution Steps (How to Proceed)

1. **Scaffold Docker:** Create the `docker-compose.yml` defining the network, TimescaleDB, and Mosquitto Broker.
2. **Build the Simulator:** Create the Python script that reads `data/raw/` and publishes JSON to Mosquitto.
3. **Build Backend (FastAPI):** Write the async Python API that subscribes to the broker, runs inference, writes to TimescaleDB, and broadcasts via WebSockets.
4. **Build Frontend (SvelteKit + Bun):** Initialize Svelte 5 with Bun + Tailwind, configure the Dual-Color theme CSS variables, set up `+layout.svelte` with the WebGL canvas, and build the route skeletons.