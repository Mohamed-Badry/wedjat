#import "@preview/touying:0.5.3": *
#import themes.metropolis: *

#let color-primary = rgb("#092e4b") // Dark Navy
#let color-secondary = rgb("#e64848") // Soft Red
#let color-code-bg = rgb("#f4f4f4")

#show: metropolis-theme.with(
  aspect-ratio: "16-9",
  config-info(
    title: [UWE-4 System Architecture],
    subtitle: [Docker Topologies & Edge Integration],
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

= Architecture & Integration

== The Edge-to-Cloud Topology

#align(center)[
  #image("../architecture_diagrams/architecture_v3_hybrid_cloud.png", height: 80%)
]

== The Dockerized Application Stack

Our Cloud VPS is fully containerized with an automated nightly training job.

#align(center)[
  #image("../architecture_diagrams/docker_components.png", height: 75%)
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
  #image("../figures/telemetry_43880.png", height: 80%)
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


