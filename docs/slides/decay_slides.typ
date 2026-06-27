#import "@preview/touying:0.5.3": *
#import themes.metropolis: *

#let color-primary = rgb("#092e4b") // Dark Navy
#let color-secondary = rgb("#e64848") // Soft Red
#let color-code-bg = rgb("#f4f4f4")

#show: metropolis-theme.with(
  aspect-ratio: "16-9",
  config-info(
    title: [Orbit Decay AI Engine],
    subtitle: [Research & Implementation Methods],
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

= Research Methods

== Aggregation and Physics Modeling

To accurately predict orbital decay, we constructed a robust ML pipeline driven by fundamental astrodynamics:

#v(1em)
#list(
  [*1. Historical Aggregation:* Correlated historical UWE-4 TLE data against CelesTrak `SW-All.csv` solar weather data.],
  [*2. Physics Modeling:* Integrated NRLMSISE-00 to calculate localized exospheric temperature and density.],
  [*3. Feature Engineering:* Computed 7-Day & 30-Day F10.7 Solar Flux rolling averages, Kp Max geomagnetic activity indices, and extracted ballistic coefficients ($B^*$).],
)

== Machine Learning Regressor

We implemented an ensemble model to regress drag parameters directly to altitude drops.

#align(center)[
  #task-card(
    "1",
    "Random Forest Regressor",
    "Predict 7-day and 30-day semi-major axis degradation.",
    "Map environmental parameters (F10.7, Kp, density) to observed historical orbital drops.",
    "A highly accurate prediction of orbital decay with confidence intervals.",
  )
]

= Deployment & Resiliency

== The Production Pipeline

The AI models have been integrated into our production FastAPI stack:

#v(1em)

#list(
  [*1. FastAPI Endpoint:* Provides on-demand 7D and 30D forecast inferences.],
  [*2. Memory Caching:* All CelesTrak outgoing API calls are wrapped in an aggressive 3600s `@ttl_cache` to prevent rate-limiting.],
  [*3. Environment Locking:* Strict adherence to `scikit-learn==1.6.1` across Pixi and Docker to prevent deserialization faults.],
  [*4. Svelte UI:* A seamless, reactive dashboard utilizing WebSockets and interactive charts.],
)

= Results

== Forecast Overview (Light)

#align(center)[
  #image("../../frontend/static/screenshots/orbit-decay-overview-light.png", width: 95%)
]

== Model Diagnostics (Light)

#align(center)[
  #image("../../frontend/static/screenshots/orbit-decay-diagnostics-light.png", width: 95%)
]
