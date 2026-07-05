#set page(
  paper: "a4",
  margin: (x: 2cm, y: 2.5cm),
)
#set text(
  size: 11pt,
)

#align(center)[
  #text(size: 22pt, weight: "bold")[UWE-4 Anomaly Detection Dataflow] \
  #v(1em)
  #text(size: 12pt, fill: luma(100))[Project Wedjat Core Architecture]
]

= Pipeline Architecture

#v(1em)

#let node(title, body) = align(center)[
  #block(
    fill: rgb("#fafafa"),
    stroke: 1pt + rgb("#e0e0e0"),
    radius: 4pt,
    width: 80%,
    inset: 10pt,
    align(center)[
      #text(weight: "bold", size: 11pt)[#title] \
      #v(1pt)
      #text(size: 10pt, fill: luma(80))[#body]
    ],
  )
]

#let arrow = align(center)[#v(2pt) #text(size: 12pt, fill: luma(150))[↓] #v(2pt)]

#node([Raw Telemetry], [`data/raw/43880/*.jsonl`])
#arrow
#node([Binary Decoder], [Parses raw HEX strings into Kaitai Struct definitions])
#arrow
#node([Unit Conversion], [Maps internal ADC integers to standardized SI units])
#arrow
#node([Processed Features], [`data/processed/43880.csv`])
#arrow
#node([Standard Scaler], [Normalizes feature distributions to $mu=0, sigma=1$])
#arrow
#node([TelemetryVAE Inference], [Pytorch Variational Autoencoder maps correlation losses])
#arrow
#node([Anomaly Detector], [Evaluates latent state against the persisted metadata threshold for deterministic scoring])

#v(2em)

= Core Features

To maintain compatibility across differing satellite hardware platforms, all proprietary telemetry is adapted into a "Golden Feature" target. The models train strictly on these standard physical properties:

- `batt_voltage` [V]: Total electrical potential of the power bus.
- `batt_current` [A]: Electrical current. Positive values indicate active solar charging; negative values indicate battery discharging during eclipse phases.
- `temp_batt_a` / `temp_batt_b` [°C]: Temperatures of the physical battery packs. Used primarily to monitor for thermal runaways.
- `temp_panel_z` [°C]: External solar panel temperature. This establishes orbit phase context (daylight heating vs. eclipse cooling) linking current draw expectations to thermal states.

= Limitations of Temporal Features

Initial architecture iterations attempted to detect "stuck" or frozen sensors by calculating rolling variance windows across consecutive frames. That logic was removed from the model input path, but the preprocessing script still emits rolling-variance columns for inspection / legacy analysis.

Low Earth Orbit CubeSats frequently utilize basic Analog-to-Digital Converters (ADCs) with coarse resolution steps (e.g., rigid 1°C gradients). During normal thermal plateau operations, these sensors legitimately report identical sequential integer values over several minutes. This results in a mathematical variance of exactly 0.0.

Because normal ADC step quantization is mathematically indistinguishable from a stuck sensor fault, applying variance-based anomaly rules generated a massive influx of false positives, crippling the pipeline's overall AUROC from 0.78 down to 0.40.

The current benchmark pipeline relies on the Variational Autoencoder (VAE). It focuses on multivariate correlation anomalies rather than univariate variance, detecting breaking relationships instead of rigid outliers.

#v(1em)
To evaluate true model capability, the benchmark sweeps fault magnitudes from subtle to extreme:

- *Panel Failure:* Override `batt_current` to a subtle negative draw (e.g., -0.2A) while `temp_panel_z` is in full sunlight.
- *Thermal Runaway:* Artificially surge `temp_batt_a` and `temp_batt_b` by minor deviations (e.g., +7°C).

*The "Honest" Verdict:* A basic limit threshold catches large +45°C spikes easily. The true value of the VAE emerges in the "subtle fault zone" where it consistently detects cross-subsystem correlation breaks (like low current during high heat) that completely bypass univariate Z-Score limits.
