#import "@preview/touying:0.5.3": *
#import themes.metropolis: *

#let color-primary = rgb("#092e4b") // Dark Navy
#let color-secondary = rgb("#e64848") // Soft Red
#let color-code-bg = rgb("#f4f4f4")

#show: metropolis-theme.with(
  aspect-ratio: "16-9",
  config-info(
    title: [Project Watchdog],
    subtitle: [AI-Powered Amateur Satellite Ground Station],
    author: [],
  ),
  config-colors(
    primary: color-primary,
    secondary: color-secondary,
  ),
)

#set text(font: "New Computer Modern", size: 20pt)

// --- Custom Components ---

#let code-block(content) = {
  block(
    fill: color-code-bg,
    inset: 1em,
    radius: 4pt,
    width: 100%,
    stroke: none,
    text(size: 0.8em, font: "FiraCode Nerd Font Mono", content),
  )
}

#let task-card(id, title, context_str, instructions, deliverable) = {
  block(
    width: 100%,
    stroke: (left: 4pt + color-secondary),
    fill: rgb("#ffffff"), // Clean white bg
    outset: 0pt,
    inset: (left: 1em, top: 0.5em, bottom: 0.5em),
    radius: 0pt,
    spacing: 1em,
    breakable: false,
  )[
    #text(weight: "bold", fill: color-secondary, size: 1.1em)[#title]
    #v(0.5em)
    #grid(
      columns: (auto, 1fr),
      gutter: 0.8em,
      strong("Goal:"), text(fill: luma(40%))[#context_str],
      strong("Logic:"), text(fill: luma(40%))[#instructions],
    )
    #v(0.6em)
    #block(
      fill: color-primary.lighten(90%),
      inset: 0.8em,
      radius: 4pt,
      width: 100%,
    )[
      #text(fill: color-primary, weight: "bold", size: 0.9em)[Result:] #text(size: 0.9em)[#deliverable]
    ]
  ]
}

// --- Slides ---

#title-slide()

== Mission Objective

*Real-Time Anomaly Detection*

Instead of just logging data, this system provides early warnings for satellite failures.

#v(1em)
*Key Capabilities:*
- *Universal Decoding:* Uses `satnogs-decoders` (Kaitai Structs).
- *Standardization:* Converts raw telemetry to standard units (V, A, °C).
- *Validation:* Tests detection with simulated physical failures.

== The Problem vs. The Solution

#text(size: 16pt)[
  #grid(
    columns: (1fr, 1fr),
    gutter: 1.5em,
    block(
      fill: color-secondary.lighten(90%),
      height: 19em,
      inset: 1em,
      radius: 4pt,
      width: 100%,
      stroke: (left: 4pt + color-secondary),
      [
        *The Problem: "Post-Mortem Analysis"*
        #v(0.5em)
        Current amateur ground stations are passive data loggers.
        #v(0.5em)
        - *Latency Gap:* Anomalies are detected weeks later by humans manually reviewing logs.
        #v(0.1em)
        - *Static Thresholds:* Simple limits fail to catch complex, multivariate failures (e.g., thermal runaway during eclipse).
        #v(0.1em)
        - *Scale:* No operator can monitor 300+ live downlinks 24/7.
      ],
    ),
    block(
      fill: color-primary.lighten(90%),
      height: 19em,
      inset: 1em,
      radius: 4pt,
      width: 100%,
      stroke: (left: 4pt + color-primary),
      [
        *Our Solution: The Watchdog*
        #v(0.5em)
        Running an *Unsupervised ML Model* on the ground station.
        #v(0.5em)
        - *Real-Time:* Analyzes data as it is received.
        #v(0.1em)
        - *Context Aware:* Learns correlations (e.g., high current is only normal when charging).
        #v(0.1em)
        - *Data Efficient:* Trains on normal data, no "failure" labels needed.
      ],
    ),
  )
]


= Phase 1: The Selection Funnel

== Selection Criteria

To build a reliable detector, we need reliable data. We filter the entire amateur fleet through five critical layers to identify our "Golden Targets."

#v(1em)
#list(
  [*Status:* Must be confirmed 'Alive' in SatNOGS DB.],
  [*Band:* 433-438 MHz (70cm Amateur Band) for antenna compatibility.],
  [*Modulation:* High-rate 9600 bps FSK/GFSK for high-fidelity signal profiles.],
  [*Support:* Explicitly supported by `satnogs-decoders` (Kaitai) for automated parsing.],
  [*Visibility:* High-elevation passes (>30°) for clean, noise-free reception.],
)

== Stage 1: The Fleet Landscape

We analyzed 149 active satellites in the target band to identify dominant communication standards.

#grid(
  columns: (1fr, 1.2fr),
  gutter: 1em,
  [
    *Observations:*
    - Huge variety in modulation types.
    - Many legacy satellites use low-rate AFSK or CW.
    - No single "universal" standard exists across the entire fleet.
  ],
  align(center + horizon)[
    #image("../figures/modulation_distribution.png", width: 100%)
  ],
)

== Stage 2: Technical Filtering

We narrow the funnel by applying technical constraints required for edge anomaly detection.

#v(0.5em)
#table(
  columns: (auto, 1fr, auto),
  inset: 10pt,
  align: horizon,
  table.header([*Funnel Step*], [*Constraint*], [*Remaining*]),
  "1. Bandwidth", "70cm Amateur (433-438 MHz)", "149",
  "2. Decodeable", "Explicitly supported by `satnogs-decoders`", "7",
  "3. High Rate", "9600 bps GMSK/GFSK/FSK", "2",
)

#v(0.5em)
*Result:* We converged on a "Golden Cohort" of 2 targets that provide high-fidelity telemetry for ML training.


= Phase 2: Operational Planning

== Heuristic: "Total Observable Time"

Pass count isn't enough. We rank satellites by the *total duration* they spend above 30° elevation over 48 hours.

#task-card(
  "1",
  "Satellite Scoring",
  "Maximize data collection opportunity",
  [Sum(Duration of all passes > 30°)],
  "Top Operational Targets",
)

== Stage 3: Operational Convergence

Ranked by "Total Observable Time" over Beni Suef (>30° Elevation).

#table(
  columns: (1fr, auto, auto, auto),
  inset: 8pt,
  align: horizon,
  table.header([*Satellite*], [*Passes (48h)*], [*Total Mins*], [*Max El*]),
  "INSPIRESat-1", "4", "7.8 m", "85.8°",
  "UWE-4", "2", "5.8 m", "87.4°",
)

#v(0.5em)
*Why UWE-4?*
Despite having fewer passes than INSPIRESat-1, UWE-4 is our primary "Golden Path" due to its rich, multi-sensor telemetry (Panel temps, Battery currents, OBC health) which is essential for complex anomaly detection.

#v(1em)
*\*Data Engineering Reality Check:* BugSat-1 was dropped despite high visibility due to undocumented protocol variations (`US37` payload header) causing Kaitai parser failures. ML requires clean data; UWE-4 provides perfect compatibility and rich thermal/power telemetry.

== Operational Reality: Skyplot

Where to point the antenna for the Top targets.

#align(center)[
  #image("../figures/skyplot_top_candidates.png", height: 85%)
]

== Operational Reality: Schedule

When to operate the ground station (Next 48 Hours).

#align(center)[
  #image("../figures/timeline_schedule.png", height: 82%)
]


== The V-Model Strategy

Two distinct environments sharing a single *Shared Core*.

#grid(
  columns: (1fr, 1fr),
  gutter: 1em,
  [
    *A. The Lab (Offline)*
    - Establish Baseline from history
    - Source: SatNOGS DB
    - *Action:* Train Autoencoder
  ],
  [
    *B. The Watchdog (Edge Deployment)*
    - Live anomaly detection (5 Docker Microservices)
    - Source: Live Antenna -> SDR -> MQTT
    - *Action:* FastAPI backend inference & SvelteKit dashboard
  ],
)

== Standardization: The Golden Features

#text(style: "italic", fill: luma(50%))[A universal interface for heterogeneous satellite hardware.]

#table(
  columns: (auto, auto, 1fr),
  inset: 10pt,
  align: horizon,
  table.header([*Feature*], [*Unit*], [*Description*]),
  `batt_voltage`, "Volts", "Standardized from mV/ADC",
  `batt_current`, "Amps", "Charge/Discharge rate",
  `power_consumption`, "Watts", "Spacecraft power draw",
  `temp_obc`, "Celsius", "Main computer temp",
  `temp_batt_a/b`, "Celsius", "Battery thermal health",
  `temp_panel_z`, "Celsius", "Orbit-phase context",
  `uptime`, "Seconds", "Time since reset",
)


= Architecture & Integration

== Architecture

#align(center)[
  #image("../architecture_diagrams/architecture_v3.png", width: 100%)
]

== ML Pipeline

#align(center)[
  #image("../architecture_diagrams/ml_pipeline_architecture.png", width: 100%)
]

== Docker Setup

#align(center)[
  #image("../architecture_diagrams/docker_components.png", width: 100%)
]


= Implementation Logic

== The Shared Core Pipeline

We use the "Shared Core" (`src/gr_sat/telemetry.py`) which acts as the universal adapter between raw bits and our AI model.

#v(0.5em)
#grid(
  columns: (1fr, 1fr),
  gutter: 1em,
  [
    *Pipeline Steps:*
    1. *Ingest:* Read raw hex frames (SatNOGS/SDR).
    2. *Parse:* Kaitai Structs via `satnogs-decoders`.
    3. *Normalize:* Convert binary fields to SI Units (V, A, °C).
    4. *Validate:* Check against physical limits.
  ],
  [
    *Current Status:*
    - Core Logic: *Operational (Shared Core)*
    - Decoder Ecosystem: *satnogs-decoders*
    - Coverage: *1 production decoder in-repo (UWE-4)*
    - Online Runtime: *Implemented (FastAPI + TimescaleDB + SvelteKit UI)*
  ],
)

== Validation & Edge Benchmarking

Because real anomaly data is rare, we validate the model using *Synthetic Fault Injection* on clean data.

#grid(
  columns: (1fr, 1fr),
  gutter: 1em,
  [
    *Accuracy (Recall / FPR)*
    1. *Panel Failure:* High temp, but negative current.
    2. *Thermal Runaway:* Inject large positive battery-temp steps.
    3. *Sensor Stuck:* Historical notebook experiment, not in current shipped benchmark.
  ],
  [
    *Edge Targets (Online Runtime)*
    Integrated with Dockerized Backend / MQTT Broker.
    - *Latency:* target $< 10$ ms per frame.
    - *Memory:* target $< 5$ MB model footprint.
  ],
)

== Data Verification (UWE-4)

Telemetry extraction from UWE-4 (NORAD 43880).
Perfect mapping from `satnogs-decoders` to our Golden Features (Volts, Amps, °C).

#align(center)[
  #image("../figures/telemetry_43880.png", height: 82%)
]

== The Inspector Tool

We built an interactive debugger (`telemetry_inspector`) to verify decoders against real historical data.

#align(center)[
  #image("../figures/dashboard_telemetry_inspector.png", height: 75%)
]

== Summary of Phase 3

1. *Targeting:* Locked onto *UWE-4* (43880) as our primary target.
2. *Pipeline:* Processing is operational, successfully generating structurally clean ML inputs.
3. *Data Strategy:* Fetching 180+ days of data to capture seasonal variations.


= Phase 4: Exploratory Data Analysis & Physics

== The Refinery Output

We successfully consolidated 7 months of UWE-4 raw telemetry.

#grid(
  columns: (1fr, 1fr),
  gutter: 2em,
  [
    *Volume Statistics:*
    - *Date Range:* Aug 2025 – Apr 2026
    - *Loss:* Filtered out 24% of frames representing communication artifacts (e.g. 5V+ spikes).
    - *Clean Dataset:* 10,941 ML-Ready Frames
  ],
  [
    *Transformations:*
    - Native `satnogs-decoders` Kaitai Struct parsing.
    - Exact SI-Unit Normalization.
    - Derived physical relationships (`batt_voltage = mean(batt_a, batt_b)`).
  ],
)

== Long-Term Macro Trends

#text(
  size: 16pt,
)[Visualizing 7 months of continuous telemetry reveals massive seasonal variations in solar charging efficiencies rather than short-term noise.]

#align(center)[
  #image("../figures/timeseries_macro_7month.png", width: 75%)
]

== The Day/Night Orbit Cycle

The most prominent feature of LEO telemetry is the orbital Day vs. Night cycle.

#text(
  size: 16pt,
)[The solar panel temperature (`temp_panel_z`) exposes the satellite's state. We observe two distinct thermal clusters:]
#list(
  [*Eclipse (Night):* Approx. $-15^o C$ to $5^o C$],
  [*Sunlight (Day):* Approx. $15^o C$ to $35^o C$],
)

An unsupervised model must learn both "normal" states to avoid false alarms during orbital transitions.

== The Bimodality in Data

#align(center)[
  #image("../figures/feature_distributions.png", width: 85%)
]

== Multivariate Physics & Correlations

When entering eclipse, solar arrays physically cannot generate power.

#grid(
  columns: (1fr, 1.2fr),
  gutter: 1.5em,
  align(center)[
    #image("../figures/eclipse_scatter.png", width: 100%)
  ],
  [
    #v(1em)
    *The Modeling Goal:*

    The AI is tasked with learning these dense non-linear correlations.

    A "positive current" during "low panel temp" instantly signals a physical anomaly (e.g. misattribution, sensor failure, or charging malfunction), even if both numbers are individually "within limits".
  ],
)

== Reception Gaps & Real-Time Constraints

Anomaly detection is limited by Line-Of-Sight (LOS) availability.

#grid(
  columns: (1fr, 1fr),
  gutter: 1.5em,
  [
    #v(1em)
    *Time Gap Distribution:*
    - Median gap *within* a pass: ~10-15s
    - Median gap *between* passes: ~10 hours!

    *Constraints:*
    Traditional time-series models (LSTMs) fail because state memory expires between passes. We use stateless models that evaluate frames independently.
  ],
  align(center)[
    #image("../figures/time_gap_distribution.png", width: 100%)
  ],
)


= Phase 5: Model Selection History & Current Baseline

== Benchmarking Without Failures

Because *real* spacecraft anomalies are undocumented in our clean set, we benchmark offline models using synthetic fault injection on a held-out test set ($20\%$).

#v(1em)
#list(
  [*1. Panel Failure:* Force `batt_current` to discharge while `temp_panel_z` shows sunlight. (Severed array)],
  [*2. Thermal Runaway:* Inject a large positive step into battery temperatures. (Internal short)],
  [*3. Sensor Stuck:* Historical notebook-only experiment, not part of the current shipped benchmark script.],
)

== Competitive AI Models

We tested 4 unsupervised mathematical models against the synthetic faults.

#align(center)[
  #image("../figures/model_comparison_roc.png", width: 60%)
]

// #v(0.5em)
*Historical outcome:*
- *Elliptic Envelope:* useful exploratory baseline, but not retained in the current repository path.
- *PyTorch VAE:* current repository baseline for training and offline synthetic-fault benchmarking.

== The "Honest" Benchmark: Sensitivity Sweep

A 100% detection rate on extreme faults proves nothing; basic thresholds can catch +45°C thermal spikes. We swept the fault magnitudes from subtle to extreme to find the operational crossover where the VAE's multivariate awareness actually outperforms a simple Z-Score limit.

#align(center)[
  #image("../figures/sensitivity_sweep.png", height: 60%)
]

*The Verdict:* The VAE massively outperforms dumb thresholding (Z-Score) during subtle anomalies (like a 0.1A current drop during sunlight), while performing equally well on obvious, extreme faults.

== The Current Repository Baseline

#task-card(
  "2",
  "Stage 1: Overall Score",
  "The current codebase uses a VAE-only pipeline.",
  "Run the VAE and compute MSE + KLD per frame. The operating threshold is calibrated during training and persisted in the model metadata artifact.",
  "Provides a deployment-ready anomaly threshold for real-time inference.",
)

#v(1em)

#task-card(
  "3",
  "Stage 2: Feature Diagnosis",
  "We need per-feature attribution after a frame is flagged.",
  "Inspect the reconstruction error feature-by-feature and identify the dominant contributor.",
  "Provides real-time subsystem attribution for both dashboards and offline benchmarking.",
)

== Architecture: The Watchdog Stack

We have deployed the real-time watchdog as a 5-container microservice stack:

#grid(
  columns: (1fr, 1fr),
  gutter: 1.5em,
  [
    - *MQTT Broker (Mosquitto):* Live telemetry ingestion.
    - *Database (TimescaleDB):* Time-series telemetry storage.
    - *Backend API (FastAPI):* Inference and WebSocket streaming.
    - *Frontend (SvelteKit):* Real-time dashboard and ML insights.
    - *Simulator:* Replays data to test the pipeline.
  ],
  align(center)[
    #image("../architecture_diagrams/architecture_v2_edge_deployment.png", width: 100%)
  ]
)
== Real-Time Mission Tracker

#grid(
  columns: (1.1fr, 1.3fr),
  gutter: 1em,
  [
    *Universal Tracking View:*
    - *Mission Control:* Live ground station status, active orbital coordinates, and battery charge trends.
    - *Orbital COE:* Classical Orbital Elements ($a$, $e$, $i$, $Omega$, $omega$, $nu$) calculated using `skyfield` and `SGP4` propagation.
    - *State Vectors:* Live Cartesian positions and velocities (ECI coordinates).
  ],
  align(center + horizon)[
    #image("../../frontend/static/screenshots/tracker-mission-dark.png", width: 100%)
    #v(-0.3em)
    #text(size: 11pt, fill: luma(120))[Mission Control Panel (Dark Mode)]
  ]
)

== Orbit Forecast & Conjunction Risk

#grid(
  columns: (1.1fr, 1.3fr),
  gutter: 1em,
  [
    *Safety & Conjunction Analysis:*
    - *Orbit Forecast:* Displays the VAE-predicted altitude drop over a 7-day future window.
    - *Conjunction Detection:* Runs real-time spatial proximity queries.
    - *Collision Probability:* Computes the mathematically exact collision risk utilizing the *Foster (1992)* probability formula on covariance matrices.
  ],
  align(center + horizon)[
    #image("../../frontend/static/screenshots/tracker-conjunctions-dark.png", width: 100%)
    #v(-0.3em)
    #text(size: 11pt, fill: luma(120))[Conjunction Threat Assessment (Dark Mode)]
  ]
)

== Conclusion: Current State

1. *Implemented now:* Offline ML pipeline, VAE training, Dockerized 5-component microservice stack, FastAPI backend, and SvelteKit real-time dashboard.
2. *Next Step:* Integrate live SDR (Software Defined Radio) ingress, expand decoder coverage, and tune production anomaly thresholds based on live operational feedback.


