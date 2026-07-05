#import "@preview/touying:0.5.3": *
#import themes.metropolis: *

#let color-primary = rgb("#092e4b") // Dark Navy
#let color-secondary = rgb("#e64848") // Soft Red
#let color-code-bg = rgb("#f4f4f4")

#show: metropolis-theme.with(
  aspect-ratio: "16-9",
  config-info(
    title: [UWE-4 Operational Strategy],
    subtitle: [Target Selection & Passes],
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
  #image("../figures/timeline_schedule.png", height: 80%)
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
    *B. The Wedjat (Edge Deployment)*
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


