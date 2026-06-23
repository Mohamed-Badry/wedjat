#import "@preview/touying:0.5.3": *
#import themes.metropolis: *

#let color-primary = rgb("#092e4b") // Dark Navy
#let color-secondary = rgb("#e64848") // Soft Red
#let color-code-bg = rgb("#f4f4f4")

#show: metropolis-theme.with(
  aspect-ratio: "16-9",
  config-info(
    title: [UWE-4 ML Models],
    subtitle: [Variational Autoencoder & Baseline],
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

== Conclusion: Current State

1. *Implemented now:* Offline ML pipeline, VAE training, Dockerized 5-component microservice stack, FastAPI backend, and SvelteKit real-time dashboard.
2. *Next Step:* Integrate live SDR (Software Defined Radio) ingress, expand decoder coverage, and tune production anomaly thresholds based on live operational feedback.


