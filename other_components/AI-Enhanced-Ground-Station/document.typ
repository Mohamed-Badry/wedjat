// ═══════════════════════════════════════════════════════════════════
//  UWE-4 Orbital Collision Prediction System — Technical Datasheet
//  Typst Document  |  Version 12  |  Graduation Project 2026
// ═══════════════════════════════════════════════════════════════════

// ─── Page & Font Setup ───────────────────────────────────────────
#set page(
  paper: "a4",
  margin: (top: 2.5cm, bottom: 2.5cm, left: 2.5cm, right: 2.5cm),
  header: context {
    if counter(page).get().first() > 1 {
      grid(
        columns: (1fr, 1fr),
        align(left)[
          #text(9pt, fill: rgb("#4f65f1"), weight: "bold")[UWE-4 Orbital Collision Prediction System]
        ],
        align(right)[
          #text(9pt, fill: rgb("#94a3b8"))[Technical Datasheet — v12]
        ]
      )
      line(length: 100%, stroke: 0.4pt + rgb("#4f65f1").transparentize(50%))
    }
  },
  footer: context {
    if counter(page).get().first() > 1 {
      line(length: 100%, stroke: 0.4pt + rgb("#4f65f1").transparentize(50%))
      grid(
        columns: (1fr, 1fr),
        align(left)[
          #text(8pt, fill: rgb("#64748b"))[Beni Suef University — Ground Station]
        ],
        align(right)[
          #text(8pt, fill: rgb("#64748b"))[Page #counter(page).display() of #counter(page).final().first()]
        ]
      )
    }
  }
)

#set text(font: "Linux Libertine", size: 10.5pt, fill: rgb("#1e293b"))
#set par(justify: true, leading: 0.75em, spacing: 1.2em)
#set heading(numbering: "1.1.1")
#show heading.where(level: 1): it => {
  v(1.5em)
  block[
    #line(length: 100%, stroke: 2pt + rgb("#4f65f1"))
    #v(0.3em)
    #text(16pt, weight: "bold", fill: rgb("#0f172a"))[#it.body]
    #v(0.2em)
  ]
}
#show heading.where(level: 2): it => {
  v(0.9em)
  text(12pt, weight: "bold", fill: rgb("#4f65f1"))[#it.body]
  v(0.3em)
}
#show heading.where(level: 3): it => {
  v(0.6em)
  text(10.5pt, weight: "bold", fill: rgb("#334155"))[#it.body]
  v(0.2em)
}

// ─── Color helpers ───────────────────────────────────────────────
#let accent     = rgb("#4f65f1")
#let accent2    = rgb("#00d4ff")
#let success    = rgb("#10b981")
#let warning    = rgb("#f59e0b")
#let danger     = rgb("#ef4444")
#let dimtext    = rgb("#64748b")
#let bglight    = rgb("#f1f5f9")
#let bgdark     = rgb("#0f172a")

// ─── Callout box ─────────────────────────────────────────────────
#let callout(color, label, body) = block(
  width: 100%,
  fill: color.transparentize(88%),
  stroke: (left: 3pt + color),
  radius: 4pt,
  inset: (x: 14pt, y: 10pt)
)[
  #text(weight: "bold", fill: color, size: 9pt)[#label] \
  #v(3pt)
  #text(size: 9.5pt)[#body]
]

// ─── Code block ──────────────────────────────────────────────────
#let code(lang, body) = block(
  width: 100%,
  fill: rgb("#0f172a"),
  radius: 6pt,
  inset: 14pt
)[
  #if lang != "" {
    text(7pt, fill: rgb("#4f65f1"), weight: "bold")[#upper(lang)]
    v(4pt)
  }
  #text(font: "DejaVu Sans Mono", size: 8.5pt, fill: rgb("#e2e8f0"))[#body]
]

// ─── Key-value table row ─────────────────────────────────────────
#let kv(k, v) = (
  table.cell(fill: bglight)[#text(weight: "semibold", size: 9pt)[#k]],
  table.cell[#text(size: 9.5pt)[#v]],
)

// ════════════════════════════════════════════════════════════════
//  COVER PAGE
// ════════════════════════════════════════════════════════════════
#page(
  margin: (top: 0cm, bottom: 0cm, left: 0cm, right: 0cm),
  header: none,
  footer: none,
)[
  #block(
    width: 100%,
    height: 100%,
    fill: rgb("#05091a"),
  )[
    // Top accent bar
    #block(width: 100%, height: 6pt, fill: gradient.linear(rgb("#4f65f1"), rgb("#00d4ff"), angle: 0deg))

    #align(center)[
      #v(5cm)

      // Satellite icon (SVG-like using shapes)
      #block(
        fill: rgb("#0a1222"),
        stroke: 1.5pt + rgb("#4f65f1"),
        radius: 100pt,
        width: 90pt, height: 90pt,
        inset: 20pt
      )[
        #align(center + horizon)[
          #text(30pt, fill: rgb("#00d4ff"))[⊛]
        ]
      ]

      #v(1.2cm)

      #text(
        28pt, weight: "bold", fill: white,
        tracking: -0.5pt
      )[Orbital Collision Prediction System]

      #v(0.4cm)

      #text(15pt, fill: rgb("#7384f8"), tracking: 2pt)[UWE-4 — NORAD 43880]

      #v(0.8cm)

      #block(
        stroke: 0.5pt + rgb("#4f65f1").transparentize(40%),
        radius: 6pt,
        inset: (x: 24pt, y: 14pt),
        fill: rgb("#0a1222").transparentize(20%)
      )[
        #grid(
          columns: (1fr, 1fr, 1fr),
          gutter: 24pt,
          align(center)[
            #text(9pt, fill: rgb("#64748b"), weight: "bold")[VERSION]\
            #v(3pt)
            #text(18pt, weight: "bold", fill: rgb("#4f65f1"))[v12]
          ],
          align(center)[
            #text(9pt, fill: rgb("#64748b"), weight: "bold")[GROUND STATION]\
            #v(3pt)
            #text(11pt, weight: "bold", fill: rgb("#00d4ff"))[Beni Suef Univ.]
          ],
          align(center)[
            #text(9pt, fill: rgb("#64748b"), weight: "bold")[DATE]\
            #v(3pt)
            #text(12pt, weight: "bold", fill: rgb("#10b981"))[June 2026]
          ],
        )
      ]

      #v(1.5cm)

      #text(12pt, fill: rgb("#94a3b8"), style: "italic")[
        Technical Datasheet — Graduation Project Documentation
      ]

      #v(2cm)

      #block(
        stroke: none,
        fill: rgb("#0a1222"),
        radius: 8pt,
        inset: (x: 30pt, y: 18pt),
        width: 340pt
      )[
        #text(9pt, fill: rgb("#64748b"))[
          *Backend:* FastAPI + SGP4 + scikit-learn \
          *Frontend:* HTML5 + Chart.js + D3.js \
          *AI Models:* Orbital Correction + Collision Probability \
          *Data:* CelesTrak TLE | UWE-4 Telemetry CSV
        ]
      ]
    ]

    // Bottom accent bar
    #place(bottom)[
      #block(width: 100%, height: 6pt, fill: gradient.linear(rgb("#4f65f1"), rgb("#00d4ff"), angle: 0deg))
    ]
  ]
]

// ════════════════════════════════════════════════════════════════
//  TABLE OF CONTENTS
// ════════════════════════════════════════════════════════════════
#page(
  header: none,
  footer: none,
)[
  #v(1cm)
  #align(center)[
    #text(22pt, weight: "bold", fill: rgb("#0f172a"))[Table of Contents]
    #v(0.3cm)
    #line(length: 8cm, stroke: 2pt + accent)
  ]
  #v(0.8cm)
  #outline(
    title: none,
    indent: auto,
    fill: repeat[#text(fill: rgb("#cbd5e1"))[. ]]
  )
]

// ════════════════════════════════════════════════════════════════
//  SECTION 1 — PROJECT OVERVIEW
// ════════════════════════════════════════════════════════════════

= Project Overview

== Introduction

The *UWE-4 Orbital Collision Prediction System* (v12) is a full-stack, real-time ground-station dashboard developed as a graduation project at Beni Suef University, Egypt. The system continuously tracks the CubeSat *UWE-4* (NORAD catalog number 43880), propagates its orbit using the SGP4 model, and applies two trained machine-learning models to (1) correct orbital-state-vector errors and (2) estimate the probability of collision with other tracked objects.

The platform is designed to support passive ground-station operations: it receives no uplink commands but monitors every computed pass, telemetry frame, and conjunction event in real time through a premium browser-based dashboard.

== Mission Statement

#callout(accent, "MISSION", [
  Provide a passive ground-station operator with accurate, real-time situational awareness of the UWE-4 CubeSat's orbital state, health telemetry, upcoming passes, and collision-risk events — with no manual data entry and no fabricated values.
])

== Key Design Principles

#table(
  columns: (auto, 1fr),
  fill: (_, row) => if calc.even(row) { bglight } else { white },
  stroke: 0.5pt + rgb("#e2e8f0"),
  inset: 10pt,
  [*Principle*], [*Implementation*],
  [No random / synthetic data], [Every value computed from real TLE or real CSV telemetry],
  [Physics-first AI], [ML models trained on orbital mechanics equations (Foster 1992)],
  [Graceful degradation], [Cached TLE fallback; API returns errors instead of fake data],
  [Real-time updates], [SGP4 propagation every 2 seconds; threat refresh every 60 s],
  [Single-page application], [Tab-based UI with no page reloads; smooth CSS animations],
)

== System Architecture

#callout(success, "ARCHITECTURE", [
  *Three-layer design:* \
  (1) *Data Layer* — CelesTrak TLE feed + UWE-4 CSV telemetry + conjunction CSV \
  (2) *Backend Layer* — FastAPI server executing SGP4 propagation + ML inference \
  (3) *Frontend Layer* — Browser dashboard polling REST API every 2–60 seconds
])

#code("", [
Browser (Edge / Chrome)
  └── dashboard.html  ← single-page app
        ├── Chart.js  ← real-time line/radar/bar charts
        └── D3.js     ← orbital radar SVG

FastAPI Server  (localhost:8000)
  ├── /api/orbit       ← SGP4 + ML correction every call
  ├── /api/telemetry   ← UWE-4 CSV last row
  ├── /api/threats     ← Conjunction events + AI probability
  ├── /api/passes      ← Visible pass schedule
  └── /api/tle         ← Live TLE from CelesTrak

Data Sources
  ├── CelesTrak GP API  ← TLE (refreshed hourly)
  ├── data/43880.csv    ← 14,565 telemetry rows
  └── data/conjunction_events.csv  ← computed threat log
])

// ════════════════════════════════════════════════════════════════
//  SECTION 2 — SATELLITE & GROUND STATION PARAMETERS
// ════════════════════════════════════════════════════════════════

= Satellite & Ground Station Parameters

== Satellite: UWE-4

UWE-4 (*University Würzburg Experimentalsatellit 4*) is a 1U CubeSat developed by the University of Würzburg, Germany. It was launched in 2018 and placed in a near-circular Low Earth Orbit (LEO).

#table(
  columns: (0.9fr, 1.1fr),
  fill: (_, row) => if calc.even(row) { bglight } else { white },
  stroke: 0.5pt + rgb("#e2e8f0"),
  inset: 10pt,
  [*Parameter*], [*Value*],
  ..kv("NORAD Catalog ID", "43880"),
  ..kv("Satellite Name", "UWE-4"),
  ..kv("Form Factor", "1U CubeSat (10×10×10 cm)"),
  ..kv("Orbital Class", "LEO — Low Earth Orbit"),
  ..kv("Typical Altitude", "~510–560 km"),
  ..kv("Inclination", "~97.5° (Sun-synchronous)"),
  ..kv("Orbital Period", "~94–95 minutes"),
  ..kv("UHF Downlink Frequency", "435.6 MHz"),
  ..kv("BSTAR Drag Term", "Provided live from TLE"),
  ..kv("Eccentricity", "Near-circular (< 0.002)"),
)

== Ground Station: Beni Suef University

The system is configured for the ground station located at Beni Suef University, Egypt. All look-angle computations (elevation, azimuth, range) and Doppler shift calculations reference this geographic position.

#table(
  columns: (0.9fr, 1.1fr),
  fill: (_, row) => if calc.even(row) { bglight } else { white },
  stroke: 0.5pt + rgb("#e2e8f0"),
  inset: 10pt,
  [*Parameter*], [*Value*],
  ..kv("Institution", "Beni Suef University"),
  ..kv("Country", "Egypt"),
  ..kv("Geodetic Latitude", "29.0463209° N"),
  ..kv("Geodetic Longitude", "31.0907943° E"),
  ..kv("Altitude Above Sea Level", "~27 m (0.027 km)"),
  ..kv("Earth Radius Model", "Spherical  RE = 6371.0 km"),
  ..kv("Standard Gravitational Parameter", "µ = 398,600.4418 km³/s²"),
)

== Orbital Reference Frame

All position and velocity vectors are expressed in the *Earth-Centred Inertial (ECI)* J2000 frame, as returned by the SGP4 propagator. Coordinate transformations to geodetic latitude/longitude use Greenwich Mean Sidereal Time (GMST).

#code("Python — GMST calculation", [
def gmst(jd_full):
    t = (jd_full - 2451545.0) / 36525.0
    theta = (280.46061837
             + 360.98564736629 * (jd_full - 2451545.0)
             + 0.000387933 * t * t
             - t * t * t / 38710000.0)
    return math.radians(theta % 360)
])

// ════════════════════════════════════════════════════════════════
//  SECTION 3 — BACKEND: FASTAPI SERVER (app.py)
// ════════════════════════════════════════════════════════════════

= Backend — FastAPI Server (`app.py`)

== Overview

The backend is a *FastAPI* application (version 12.1) running under *Uvicorn* on port 8000. It exposes a REST API consumed by the dashboard and serves the static HTML file. The server uses a thread-safe in-memory cache (`_cache`) to avoid redundant TLE fetches and CSV re-reads.

#code("Python — App instantiation", [
app = FastAPI(title="UWE-4 Ground Station API", version="12.1")
app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
])

== Thread-Safe Cache

#code("Python — Cache structure", [
_lock = threading.Lock()
_cache = {
    "tle1": None,        # TLE line 1 string
    "tle2": None,        # TLE line 2 string
    "tle_at": 0.0,       # Unix timestamp of last TLE fetch
    "tle_src": "not loaded",
    "df": None,          # pandas DataFrame (telemetry CSV)
    "model_bundle": None, # loaded sklearn model bundle
    "model_status": None, # validation metadata dict
}
])

All reads/writes to `_cache` are protected by `_lock` to allow safe concurrent API requests.

== TLE Management

=== Fetching Logic

The system attempts to fetch fresh TLE data from CelesTrak every *3600 seconds* (1 hour). Two fallback URLs are tried in sequence:

#code("Python — TLE URLs", [
urls = [
    f"https://celestrak.org/NORAD/elements/gp.php?CATNR={NORAD_ID}&FORMAT=TLE",
    f"https://celestrak.org/satcat/tle.php?CATNR={NORAD_ID}",
]
])

If both fail, the system falls back to the locally cached file `data/43880.tle`. If no cache exists, the `/api/orbit` endpoint returns HTTP 503.

=== TLE Validation

Every TLE string is validated before use:

#code("Python — parse_tle_text()", [
def parse_tle_text(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    line1 = next((l for l in lines if l.startswith("1 ")), None)
    line2 = next((l for l in lines if l.startswith("2 ")), None)
    if not line1 or not line2:
        raise ValueError("TLE response did not contain line 1 and line 2")
    if line1[2:7].strip() != str(NORAD_ID):
        raise ValueError("TLE catalog number mismatch")
    Satrec.twoline2rv(line1, line2)   # raises on bad format
    return line1, line2
])

The NORAD catalog number in both lines is verified to equal `43880` before the TLE is accepted.

== SGP4 Orbit Propagation

=== Core Propagation

The system uses the *sgp4* Python library (wrapping the official SGP4 C++ implementation) for all position/velocity computations. The Julian Date is computed with sub-second precision:

#code("Python — state_from_tle()", [
def state_from_tle(sat, when):
    jd, fr = jday(when.year, when.month, when.day,
                  when.hour, when.minute,
                  when.second + when.microsecond / 1e6)
    code, r_raw, v_raw = sat.sgp4(jd, fr)
    if code != 0:
        raise RuntimeError(f"SGP4 error code {code}")
    r, v, ml_status = apply_model_correction(r_raw, v_raw)
    return jd, fr, r_raw, v_raw, r, v, ml_status
])

The return value includes *both* the raw SGP4 vector (`r_raw`, `v_raw`) and the ML-corrected vector (`r`, `v`), enabling comparison.

=== Derived Orbital Parameters (`state_summary`)

From the ECI state vector, the backend computes a full set of *Classical Orbital Elements (COE)* and operational parameters:

#table(
  columns: (auto, 1fr, auto),
  fill: (_, row) => if calc.even(row) { bglight } else { white },
  stroke: 0.5pt + rgb("#e2e8f0"),
  inset: 9pt,
  [*Symbol*], [*Quantity*], [*Unit*],
  [a], [Semi-major axis], [km],
  [e], [Eccentricity], [—],
  [i], [Inclination], [degrees],
  [Ω (RAAN)], [Right Ascension of the Ascending Node], [degrees],
  [ω], [Argument of Perigee], [degrees],
  [M], [Mean Anomaly], [degrees],
  [ν], [True Anomaly], [degrees],
  [T], [Orbital Period], [minutes],
  [n], [Mean Motion], [rev/day],
  [h_apo], [Apogee Altitude], [km],
  [h_peri], [Perigee Altitude], [km],
  [Az], [Azimuth to Ground Station], [degrees],
  [El], [Elevation from Ground Station], [degrees],
  [R], [Slant Range to Ground Station], [km],
  [Δf], [Doppler Shift at 435.6 MHz], [kHz],
)

=== Doppler Shift Calculation

#code("Python — Doppler computation", [
def range_rate(r_eci, v_eci, glat, glon, theta):
    # Ground station ECI position
    la = math.radians(glat)
    lo = math.radians(glon) + theta          # GMST-corrected
    gs = [RE*cos(la)*cos(lo),
          RE*cos(la)*sin(lo),
          RE*sin(la)]
    dr = [r_eci[i] - gs[i] for i in range(3)]
    dm = mag(dr)
    # GS velocity due to Earth's rotation
    we = 7.2921150e-5  # rad/s
    vgs = [-we*gs[1], we*gs[0], 0.0]
    dv  = [v_eci[i] - vgs[i] for i in range(3)]
    return dot(dv, dr) / dm   # km/s

# Doppler frequency shift
doppler_khz = -range_rate * UHF_DOWNLINK_MHZ / 299792.458
])

A negative range rate (satellite approaching) produces a positive Doppler shift.

=== Look-Angle Computation

The azimuth and elevation angles are computed using the *Haversine* formula for the ground-range arc angle, followed by spherical trigonometry:

#code("Python — look_angles()", [
def look_angles(slat, slon, salt, glat, glon, galt):
    la1, lo1, la2, lo2 = map(radians, [glat, glon, slat, slon])
    dlo = lo2 - lo1
    a   = sin((la2-la1)/2)**2 + cos(la1)*cos(la2)*sin(dlo/2)**2
    c   = 2 * atan2(sqrt(a), sqrt(1-a))    # ground-range angle
    rg  = RE + galt
    rs  = RE + salt
    rng = sqrt(rg**2 + rs**2 - 2*rg*rs*cos(c))
    se  = (rs**2 - rg**2 - rng**2) / (2*rg*rng)
    el  = degrees(asin(se))
    # Azimuth
    y   = sin(dlo) * cos(la2)
    x   = cos(la1)*sin(la2) - sin(la1)*cos(la2)*cos(dlo)
    az  = (degrees(atan2(y, x)) + 360) % 360
    return az, el, rng
])

== Orbital Forecast

The backend pre-computes future states at fixed time horizons using the same SGP4 propagator:

#code("Python — Forecast horizons", [
horizon_minutes = [0, 10, 30, 60, 120, 360, 1440]
# returns: altitude, velocity, true anomaly, ml_used flag
])

Each forecast row contains both the raw SGP4 result and the ML-corrected output for visual comparison in the dashboard chart.

== REST API Endpoints

#table(
  columns: (auto, auto, 1fr),
  fill: (_, row) => if calc.even(row) { bglight } else { white },
  stroke: 0.5pt + rgb("#e2e8f0"),
  inset: 9pt,
  [*Method*], [*Path*], [*Description*],
  [GET], [`/`], [Serves `dashboard.html` as the root page],
  [GET], [`/api/orbit`], [Full orbital state: COE, look angles, Doppler, forecast, ML status],
  [GET], [`/api/telemetry`], [Latest telemetry row from CSV (voltages, temps, uptime)],
  [GET], [`/api/telemetry/history`], [Last 50 telemetry rows for chart rendering],
  [GET], [`/api/threats`], [Conjunction events sorted by risk level + miss distance],
  [GET], [`/api/passes`], [Upcoming visible passes from the CSV schedule],
  [GET], [`/api/tle`], [Current TLE lines, source, age, time to next refresh],
  [POST], [`/api/tle/update`], [Force-fetch latest TLE from CelesTrak immediately],
  [GET], [`/api/ml/status`], [ML model load status and validation metrics],
  [GET], [`/api/status`], [System health: TLE loaded, CSV rows, ML status, server time],
)

// ════════════════════════════════════════════════════════════════
//  SECTION 4 — MACHINE LEARNING MODELS
// ════════════════════════════════════════════════════════════════

= Machine Learning Models

The project includes *two distinct AI models*, each with a separate training script and saved bundle.

== Model 1 — Orbital Correction Model (`orbit_ai_model.pkl`)

=== Purpose

SGP4 propagation accumulates errors over time due to simplified atmospheric drag, solar radiation pressure, and geomagnetic perturbation modelling. This model learns the *residual error* (delta) between the SGP4-predicted state and the true reference state, then applies a correction at inference time.

=== Training Data

The model requires a CSV with both the SGP4-predicted columns and the true/reference state vectors:

#table(
  columns: (0.5fr, 1fr),
  fill: (_, row) => if calc.even(row) { bglight } else { white },
  stroke: 0.5pt + rgb("#e2e8f0"),
  inset: 9pt,
  [*Feature Columns*], [*Target Columns*],
  [`sgp4_x_km`], [`delta_x_km  = true_x - sgp4_x`],
  [`sgp4_y_km`], [`delta_y_km  = true_y - sgp4_y`],
  [`sgp4_z_km`], [`delta_z_km  = true_z - sgp4_z`],
  [`sgp4_vx_km_s`], [`delta_vx_km_s = true_vx - sgp4_vx`],
  [`sgp4_vy_km_s`], [`delta_vy_km_s = true_vy - sgp4_vy`],
  [`sgp4_vz_km_s`], [`delta_vz_km_s = true_vz - sgp4_vz`],
  [`sgp4_altitude_km`], [—],
)

=== Model Architecture

#code("Python — Estimator pipeline (train_model.py)", [
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.multioutput import MultiOutputRegressor

base  = ExtraTreesRegressor(
    n_estimators=400, min_samples_leaf=2, n_jobs=-1
)
model = MultiOutputRegressor(base)
model.fit(train[FEATURE_COLUMNS], train[TARGET_COLUMNS])
])

- *Algorithm:* Extra Trees Regressor (multi-output)
- *Outputs:* 6-dimensional delta vector [Δx, Δy, Δz, Δvx, Δvy, Δvz]
- *Temporal split:* 80% training / 20% test (time-ordered, no data leakage)
- *Minimum samples:* 50 real truth rows required

=== Validation Gate

The model is *only activated* at runtime if both RMSE thresholds are satisfied:

#code("Python — Model verification logic", [
MODEL_POSITION_RMSE_LIMIT_KM   = 1.0   # km
MODEL_VELOCITY_RMSE_LIMIT_KM_S = 0.01  # km/s

if (pos_rmse <= 1.0 and vel_rmse <= 0.01):
    status["model_verified"] = True
else:
    status["fallback_reason"] = "RMSE exceeds accepted threshold"
    # raw SGP4 used instead
])

=== Safety Gate at Inference

Even if the model passes validation, each individual prediction is subject to a physical plausibility check:

#code("Python — Safety gate in apply_model_correction()", [
MAX_POSITION_CORRECTION_KM   = 10.0   # km
MAX_VELOCITY_CORRECTION_KM_S = 0.05   # km/s

if (pos_norm > MAX_POSITION_CORRECTION_KM or
    vel_norm > MAX_VELOCITY_CORRECTION_KM_S):
    # Discard prediction, use raw SGP4
    return list(r_raw), list(v_raw), status
])

=== Saved Bundle Format

#code("Python — Bundle dictionary (joblib)", [
bundle = {
    "model":           model,          # fitted MultiOutputRegressor
    "feature_columns": FEATURE_COLUMNS,
    "target_columns":  TARGET_COLUMNS,
    "metrics": {
        "position_rmse_km":          float,
        "velocity_rmse_km_s":        float,
        "position_mean_error_km":    float,
        "velocity_mean_error_km_s":  float,
        "train_rows":  int,
        "test_rows":   int,
    },
    "trained_at_utc":   "ISO-8601 string",
    "real_data_only":   True,
}
])

== Model 2 — Collision Probability Model (`collision_ai_model.pkl`)

=== Purpose

Given the closest-approach geometry of a conjunction event, this model estimates the *collision probability* using principles derived from Foster (1992) hard-body probability theory.

=== Physics Background — Foster's Method

The collision probability between two objects is:

#align(center)[
  $ P_c = frac(r_c^2, 2 sqrt(sigma_R sigma_T)) exp(-frac(d^2, 2 sigma^2)) $
]

Where:
- $r_c$ = combined hard-body radius (m)
- $d$ = miss distance (m)
- $sigma_R, sigma_T$ = radial and transverse covariance components (m)

=== Training Data Generation

Since historical CDM (Conjunction Data Message) records with full covariance matrices are proprietary, the training dataset is generated synthetically from the Foster physics model across a wide parameter space:

#code("Python — Physics-based data generation (train_collision_model.py)", [
def calc_foster_prob(miss_km, cov_r, cov_t, combined_radius_m=10.0):
    d_m = miss_km * 1000.0
    if d_m > 10 * max(cov_r, cov_t):
        return 0.0
    r_c_sq   = combined_radius_m ** 2
    sigma_sq = (cov_r**2 + cov_t**2) / 2.0
    exponent = -(d_m**2) / (2.0 * sigma_sq)
    prob = (r_c_sq / (2.0 * math.sqrt(cov_r * cov_t))) * math.exp(exponent)
    return min(1.0, max(0.0, prob))

# Parameter ranges for 20,000 training samples
miss_km   = Uniform(0.1, 100.0)     # km
cov_r     = Uniform(10.0, 5000.0)   # m   radial covariance
cov_t     = Uniform(50.0, 15000.0)  # m   transverse covariance
rel_vel   = Uniform(1.0, 15.0)      # km/s
radius    = Uniform(1.0, 20.0)      # m   hard-body
])

=== Model Architecture

#code("Python — Random Forest regressor", [
from sklearn.ensemble import RandomForestRegressor

model = RandomForestRegressor(
    n_estimators=50,
    max_depth=10,
    n_jobs=-1,
    random_state=42
)

# Input features: [miss_km, cov_r_m, cov_t_m, rel_vel_km_s, radius_m]
# Output: scalar collision probability in [0, 1]
])

Training RMSE achieved: ~1.19 × 10⁻³

=== Conjunction Search Algorithm (`generate_conjunctions.py`)

The conjunction search pipeline:

#code("Python — Conjunction search pipeline", [
# 1. Download active satellite TLEs from CelesTrak
url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=TLE"

# 2. Propagate all satellites over 24-hour window (5-min steps)
for m in range(0, 24*60, 5):
    ...  # compute positions via sgp4_array()

# 3. For each satellite: find minimum miss distance
dist = norm(r_all[i] - r_my, axis=1)
min_dist = dist.min()

# 4. If min_dist < 5000 km: compute AI probability
if min_dist < 5000.0:
    features = [[min_dist, cov_r, cov_t, rel_vel, radius]]
    prob = ai_model.predict(features)[0]
    results.append({...})

# 5. Save to data/conjunction_events.csv
])

=== Risk Classification

Conjunction events are classified into four risk tiers:

#table(
  columns: (auto, auto, auto, auto),
  fill: (_, row) => if calc.even(row) { bglight } else { white },
  stroke: 0.5pt + rgb("#e2e8f0"),
  inset: 10pt,
  [*Level*], [*Probability Threshold*], [*Miss Distance*], [*Badge*],
  text(fill: danger, weight: "bold")[CRITICAL],    [P ≥ 1×10⁻⁴], [d ≤ 1.0 km], [Red],
  text(fill: warning, weight: "bold")[HIGH RISK],  [P ≥ 1×10⁻⁵], [d ≤ 2.0 km], [Orange],
  text(fill: warning, weight: "bold")[WARNING],    [P ≥ 1×10⁻⁶], [d ≤ 5.0 km], [Orange],
  text(fill: success, weight: "bold")[NOMINAL],    [P < 1×10⁻⁶],  [d > 5.0 km],  [Green],
)

Threats are sorted *first by risk level, then by miss distance*, ensuring the most dangerous event is always shown first in the alert banner.

// ════════════════════════════════════════════════════════════════
//  SECTION 5 — TELEMETRY & DATA FILES
// ════════════════════════════════════════════════════════════════

= Telemetry & Data Files

== UWE-4 Telemetry CSV (`data/43880.csv`)

The telemetry database contains *14,565 rows* of on-board measurements downlinked from UWE-4. Each row represents one telemetry frame received during a visible pass.

#table(
  columns: (auto, auto, 1fr),
  fill: (_, row) => if calc.even(row) { bglight } else { white },
  stroke: 0.5pt + rgb("#e2e8f0"),
  inset: 9pt,
  [*Column*], [*Unit*], [*Description*],
  [`timestamp`],         [UTC],     [Frame acquisition time],
  [`batt_a_voltage`],    [V],       [Battery A terminal voltage],
  [`batt_b_voltage`],    [V],       [Battery B terminal voltage],
  [`batt_a_current`],    [A],       [Battery A discharge/charge current],
  [`batt_b_current`],    [A],       [Battery B discharge/charge current],
  [`power_consumption`], [W],       [Total system power draw],
  [`temp_obc`],          [°C],      [On-Board Computer temperature],
  [`temp_batt_a`],       [°C],      [Battery A temperature],
  [`temp_batt_b`],       [°C],      [Battery B temperature],
  [`temp_panel_z`],      [°C],      [Solar panel Z-face temperature],
  [`uptime`],            [s],       [Cumulative system uptime],
  [`pass_id`],           [—],       [Unique pass identifier],
  [`pass_frame_count`],  [—],       [Frame sequence number within pass],
)

=== Telemetry API Response

#code("JSON — /api/telemetry sample", [
{
  "timestamp":       "2024-01-15 14:32:01",
  "batt_a_voltage":  3.874,
  "batt_b_voltage":  3.871,
  "batt_voltage_avg": 3.873,
  "power_consumption": 0.412,
  "temp_obc":        18.3,
  "temp_batt_a":     12.1,
  "temp_panel_z":    -23.4,
  "uptime_sec":      7284612,
  "total_frames":    14565,
  "total_passes":    342,
  "volt_trend":      3.869,   // mean of last 20 readings
  "temp_trend":      17.8
}
])

== TLE File (`data/43880.tle`)

The Two-Line Element file is maintained as a local cache. Format:

#code("TLE — UWE-4 example format", [
UWE-4
1 43880U 18111D   26174.60000000  .00001234  00000-0  12345-4 0  9999
2 43880  97.4857 123.4567 0001234 234.5678 125.4321 15.23456789123456
])

- *Line 1:* Epoch, drag term (BSTAR), element set number
- *Line 2:* Inclination, RAAN, eccentricity, AoP, mean anomaly, mean motion, revolution count

== Conjunction Events CSV (`data/conjunction_events.csv`)

Generated by `generate_conjunctions.py` and consumed by `/api/threats`:

#table(
  columns: (auto, 1fr),
  fill: (_, row) => if calc.even(row) { bglight } else { white },
  stroke: 0.5pt + rgb("#e2e8f0"),
  inset: 9pt,
  [*Column*], [*Description*],
  [`secondary_object`],      [Name of the threatening object],
  [`secondary_norad`],       [NORAD ID of the secondary object],
  [`tca_utc`],               [Time of Closest Approach (human-readable)],
  [`tca_iso`],               [TCA in ISO-8601 format (for sorting)],
  [`miss_km`],               [Minimum miss distance in kilometres],
  [`collision_probability`], [AI-computed probability (0–1)],
)

== Visible Pass Schedule (`data/visible_passes.csv`)

Pre-computed pass predictions for the Beni Suef ground station. Each row contains rise time, peak time, set time, maximum elevation angle, duration, and frequency.

// ════════════════════════════════════════════════════════════════
//  SECTION 6 — FRONTEND DASHBOARD
// ════════════════════════════════════════════════════════════════

= Frontend Dashboard (`static/dashboard.html`)

== Technology Stack

The dashboard is a *single HTML file* with no build step or external framework dependency (beyond CDN fonts):

#table(
  columns: (auto, 1fr),
  fill: (_, row) => if calc.even(row) { bglight } else { white },
  stroke: 0.5pt + rgb("#e2e8f0"),
  inset: 9pt,
  [*Library*], [*Usage*],
  [Chart.js (local)],      [Real-time line charts: elevation, Doppler, altitude, convergence, battery, forecast],
  [D3.js (local)],         [Interactive orbital radar SVG animation],
  [Google Fonts],          [Inter (UI), JetBrains Mono (values)],
  [Vanilla JavaScript],    [API polling, DOM updates, countdown logic],
  [CSS Custom Properties], [Full dark-mode design system with glassmorphism],
)

== Design System (CSS Variables)

#code("CSS — Root design tokens", [
:root {
  --bg:          #050a14;   /* deep navy background */
  --bg2:         #0a1222;   /* panel dark */
  --primary:     #4f65f1;   /* indigo accent */
  --accent:      #00d4ff;   /* cyan highlight */
  --success:     #10b981;   /* emerald */
  --danger:      #ef4444;   /* red */
  --warning:     #f59e0b;   /* amber */
  --text:        #f8fafc;   /* near-white */
  --text-muted:  #94a3b8;   /* slate */
  --mono: 'JetBrains Mono', monospace;
  --glass: blur(12px);      /* glassmorphism filter */
}
])

== Dashboard Tabs (6 Views)

=== Tab 1 — Live Telemetry Dashboard

The default view. Contains:
- *Alert Banner:* pulsing collision-risk indicator with countdown timer
- *Metric Cards (×4):* Target name, altitude, velocity, collision probability
- *Trajectory Convergence Chart:* real-time range-to-GS over last 40 samples
- *Telemetry Matrix (×9 boxes):* Altitude, velocity, lat/lon, elevation, azimuth, Doppler, range, true anomaly
- *CSV Telemetry Panel:* live battery voltages, power, temperatures, uptime
- *D3 Orbital Radar:* animated SVG showing satellite position on concentric-ring orbit diagram

=== Tab 2 — Orbital Parameters (COE)

- Full 7-element COE table (a, e, i, Ω, ω, M, ν)
- Derived parameters: period, mean motion, apogee/perigee altitudes
- ECI state vectors (position & velocity)
- True Anomaly SVG diagram with live angular marker

=== Tab 3 — Mission Dynamics Analysis

- *Elevation Profile chart:* Y-axis −5° to 90° with red horizon line at 0°
- *Doppler Shift chart:* −15 to +15 kHz range at 435.6 MHz
- *Sky Plot:* azimuth (0°–360°) vs elevation scatter chart
- *Altitude History:* continuous altitude time series

=== Tab 4 — Deep Learning Diagnostics

- ML model architecture and validation RMSE display
- API inference latency
- Error mitigation bar chart (position RMSE vs velocity RMSE)
- Covariance distribution radar chart (dX, dY, dZ, dVx, dVy, dVz)
- Battery voltage history from last 50 telemetry rows

=== Tab 5 — Conjunction Event Catalog

- Full conjunction events table sorted by risk level then miss distance
- Visible pass schedule from `visible_passes.csv`

=== Tab 6 — AI Orbit Prediction & TLE

- Live TLE display with source and age
- AI Model Verification Gate: accuracy percentage, progress bar, error bounds
- Future position and velocity at +1/+2/+4/+8 orbits and +24 hours
- Altitude forecast chart: SGP4 baseline vs AI-corrected trajectory

== Real-Time Update Loop

#code("JavaScript — Polling intervals", [
setInterval(fetchOrbit,     2000);   // every 2 seconds
setInterval(fetchTelemetry, 30000);  // every 30 seconds
setInterval(fetchTLE,       60000);  // every 60 seconds
setInterval(fetchThreats,   60000);  // every 60 seconds
])

== Collision Alert System & Countdown

=== Alert Banner

The alert banner displays the highest-priority threat from the conjunction events list. It changes colour and animation based on risk level:

#code("CSS — Animated alert modes", [
.alert-banner {
    animation: glow-red 2s infinite;   /* CRITICAL */
}
.alert-banner.warn-mode {
    animation: glow-orange 2s infinite; /* WARNING / HIGH RISK */
}
@keyframes glow-red {
    50% { box-shadow: 0 0 22px rgba(239,68,68,0.6); }
}
])

=== Automatic Threat Cycling

When the countdown for the current threat reaches zero, the system waits 3 seconds then automatically advances to the next threat in the list:

#code("JavaScript — Auto-advance countdown", [
} else if (topTCA === 0) {
    topTCA = -1;
    e.textContent = 'TCA REACHED';
    // After 3-second pause, load next threat
    setTimeout(() => {
        if (threats && threats.length > 1) {
            loadThreatAtIndex(currentThreatIndex + 1);
        }
    }, 3000);
}
])

Events wrap around: after the last threat, the system returns to index 0.

// ════════════════════════════════════════════════════════════════
//  SECTION 7 — MATHEMATICAL FOUNDATIONS
// ════════════════════════════════════════════════════════════════

= Mathematical Foundations

== Classical Orbital Element Derivation

All COEs are derived analytically from the SGP4-output ECI state vector $(bold(r), bold(v))$:

=== Angular Momentum Vector

$ bold(h) = bold(r) times bold(v) $

=== Eccentricity Vector

$ bold(e) = frac(v^2 - mu/r, mu) bold(r) - frac(bold(r) dot bold(v), mu) bold(v) $

=== Inclination

$ i = arccos(h_z / |bold(h)|) $

=== RAAN

$ Omega = arccos(hat(N)_x), quad "quadrant check:" quad Omega -> 360 - Omega "if" hat(N)_y < 0 $

Where $bold(N) = hat(z) times bold(h)$ is the node vector.

=== Argument of Perigee

$ omega = arccos(frac(bold(N) dot bold(e)}{|bold(N)| |bold(e)|}), quad "quadrant check:" quad omega -> 360 - omega "if" e_z < 0 $

=== True Anomaly

$ nu = arccos(frac(bold(e) dot bold(r)}{|bold(e)| r}), quad "quadrant check:" quad nu -> 360 - nu "if" bold(r) dot bold(v) < 0 $

=== Semi-Major Axis (Vis-Viva)

$ a = frac(1}{2/r - v^2/mu} $

=== Orbital Period

$ T = 2 pi sqrt(a^3 / mu) $

== Probability of Collision (Foster 1992)

For a conjunction with miss vector $bold(d)$ in the encounter plane, and combined position covariance $bold(C)$:

$ P_c = frac(r_c^2}{2 pi sqrt(det(bold(C)_"2D")}}) integral.double_(|bold(rho)|<=r_c) exp(-frac{1}{2} bold(rho)^T bold(C)_"2D"^(-1) bold(rho)) d bold(rho) $

In the simplified scalar approximation used for training:

$ P_c approx frac(r_c^2}{2 sqrt(sigma_R sigma_T)}) exp(-frac(d^2}{2 sigma^2}) $

// ════════════════════════════════════════════════════════════════
//  SECTION 8 — FILE & FOLDER STRUCTURE
// ════════════════════════════════════════════════════════════════

= File & Folder Structure

#code("", [
v12/
├── app.py                       ← FastAPI backend (708 lines)
├── train_model.py               ← Orbital correction model trainer
├── train_collision_model.py     ← Collision probability model trainer
├── generate_conjunctions.py     ← Conjunction search + CSV generator
├── requirements.txt             ← Python dependencies
├── steps.md                     ← Quick-start run guide
│
├── data/
│   ├── 43880.tle                ← Cached TLE (UWE-4)
│   ├── 43880.csv                ← 14,565 telemetry frames
│   ├── conjunction_events.csv   ← computed conjunction log
│   └── visible_passes.csv       ← Pass schedule for Beni Suef GS
│
├── models/
│   ├── orbit_ai_model.pkl       ← ExtraTrees orbital correction bundle
│   └── collision_ai_model.pkl   ← RandomForest collision prob bundle
│
└── static/
    ├── dashboard.html           ← Full SPA dashboard (1,043 lines)
    ├── chart.umd.js             ← Chart.js library (local, offline)
    └── d3.min.js                ← D3.js library (local, offline)
])

// ════════════════════════════════════════════════════════════════
//  SECTION 9 — INSTALLATION & OPERATION
// ════════════════════════════════════════════════════════════════

= Installation & Operation

== Python Dependencies

#code("requirements.txt", [
fastapi
uvicorn
sgp4
pandas
scikit-learn
joblib
httpx
numpy
])

Install with:

#code("bash", [
pip install fastapi uvicorn sgp4 pandas scikit-learn joblib httpx numpy
])

== Startup Procedure

#code("bash — Step-by-step", [
# Step 1: Navigate to project directory
cd "e:\My-Study\Semester-10\Graduation Project\final_project\v12"

# Step 2: Start the server
python app.py

# Step 3: Open dashboard in browser
# Navigate to: http://localhost:8000

# Step 4 (optional): Refresh conjunction data (needs internet)
python generate_conjunctions.py
])

== Server Startup Output

On successful startup the terminal shows:

#code("", [
============================================================
  UWE-4 Passive Ground Station Backend - FastAPI v12.1
  Satellite : UWE-4 (NORAD 43880)
  Ground Stn: Beni Suef University, Egypt (29.0463209N, 31.0907943E)
============================================================
[INIT] Loading cached TLE, then refreshing from CelesTrak...
[INIT] Loading telemetry CSV...
[CSV] Loaded 14565 telemetry rows
[INIT] Starting FastAPI server on http://localhost:8000
============================================================
INFO:     Application startup complete.
])

== TLE Refresh Behaviour

#table(
  columns: (auto, 1fr),
  fill: (_, row) => if calc.even(row) { bglight } else { white },
  stroke: 0.5pt + rgb("#e2e8f0"),
  inset: 9pt,
  [*Condition*], [*Action*],
  [Cache < 1 hour old],     [Use in-memory cache, skip network request],
  [Cache ≥ 1 hour old],     [Fetch from CelesTrak URL 1, then URL 2 on failure],
  [Both URLs fail],         [Fall back to `data/43880.tle` local file],
  [No local file],          [Return HTTP 503 from `/api/orbit`],
  [Manual Update TLE click],[Force-fetch regardless of cache age],
)

== Common Troubleshooting

#callout(danger, "PORT CONFLICT", [
  If you see `[Errno 10048] address already in use`:
  the server is already running. Simply open `http://localhost:8000`
  in the browser.
])

#callout(warning, "NO TLE", [
  If the dashboard shows "Backend offline": check your internet connection,
  then click *Update TLE* in the AI Orbit Prediction tab.
])

#callout(success, "NO THREATS DISPLAYED", [
  Run `python generate_conjunctions.py` with an active internet connection
  to re-compute and save fresh conjunction events.
])

// ════════════════════════════════════════════════════════════════
//  SECTION 10 — SYSTEM PERFORMANCE & CONSTRAINTS
// ════════════════════════════════════════════════════════════════

= System Performance & Constraints

== Performance Characteristics

#table(
  columns: (1fr, auto),
  fill: (_, row) => if calc.even(row) { bglight } else { white },
  stroke: 0.5pt + rgb("#e2e8f0"),
  inset: 9pt,
  [*Metric*], [*Typical Value*],
  [SGP4 propagation latency (per call)], [< 5 ms],
  [Full `/api/orbit` response time],     [5–30 ms],
  [Telemetry CSV load time (14,565 rows)], [~1.5 s (one-time at startup)],
  [Conjunction search (24 h, 5-min steps)], [~15–30 s (offline)],
  [Browser orbit update interval],        [2 s],
  [ML model inference latency],           [< 1 ms],
  [TLE refresh interval],                 [3600 s],
)

== Known Constraints

#callout(warning, "PASSIVE SYSTEM", [
  This is a *receive-only* ground station system. It cannot command the
  satellite or uplink data. All information is derived from pre-existing
  TLE propagation and stored telemetry.
])

#table(
  columns: (1fr, 1fr),
  fill: (_, row) => if calc.even(row) { bglight } else { white },
  stroke: 0.5pt + rgb("#e2e8f0"),
  inset: 9pt,
  [*Constraint*], [*Implication*],
  [SGP4 model accuracy degrades with TLE age], [Errors ~1 km/day for typical LEO],
  [Collision AI trained on simplified Foster model], [Not a replacement for official CDM/CSM data],
  [Spherical Earth model for look angles], [Errors < 0.1° at moderate elevations],
  [14,565 telemetry rows are historical], [CSV data does not update in real time],
  [CelesTrak rate-limits GP requests (2 h)], [Manual TLE updates may return cached server data],
)

== Data Integrity Guarantees

The system enforces the following invariants:

+ *No synthetic orbital data* — SGP4 propagation is the sole source of position/velocity
+ *No synthetic telemetry* — Only CSV rows with valid timestamps are displayed
+ *No unchecked ML output* — Both RMSE gate and physical safety gate must pass
+ *No past threats displayed* — Conjunction events with `tca_offset_min < 0` are filtered out
+ *No catalogue mismatch* — TLE NORAD IDs are verified before acceptance

// ════════════════════════════════════════════════════════════════
//  SECTION 11 — GLOSSARY
// ════════════════════════════════════════════════════════════════

= Glossary

#table(
  columns: (auto, 1fr),
  fill: (_, row) => if calc.even(row) { bglight } else { white },
  stroke: 0.5pt + rgb("#e2e8f0"),
  inset: 9pt,
  [*Term*], [*Definition*],
  [*AoP*],       [Argument of Perigee — angle from ascending node to perigee],
  [*BSTAR*],     [SGP4 drag term (ballistic coefficient × atmospheric density)],
  [*CDM*],       [Conjunction Data Message — standardised NASA/ESA format for close-approach notifications],
  [*COE*],       [Classical Orbital Elements: {a, e, i, Ω, ω, ν}],
  [*CubeSat*],   [Standardised small satellite form factor (1U = 10×10×10 cm)],
  [*ECI*],       [Earth-Centred Inertial reference frame (J2000 epoch)],
  [*GMST*],      [Greenwich Mean Sidereal Time — Earth rotation angle],
  [*GS*],        [Ground Station],
  [*LEO*],       [Low Earth Orbit — altitude 200–2000 km],
  [*ML*],        [Machine Learning],
  [*NORAD*],     [North American Aerospace Defense Command — satellite catalogue authority],
  [*RAAN*],      [Right Ascension of the Ascending Node (Ω)],
  [*REST API*],  [Representational State Transfer Application Programming Interface],
  [*SGP4*],      [Simplified General Perturbations model 4 — standard LEO propagator],
  [*SPA*],       [Single-Page Application],
  [*TCA*],       [Time of Closest Approach — moment of minimum miss distance],
  [*TLE*],       [Two-Line Element set — compact orbital parameter encoding],
  [*UHF*],       [Ultra High Frequency — 300 MHz to 3 GHz radio band],
)

// ════════════════════════════════════════════════════════════════
//  SECTION 12 — REFERENCES
// ════════════════════════════════════════════════════════════════

= References

#set par(hanging-indent: 2em)

[1] Vallado, D.A., Crawford, P., Hujsak, R., & Kelso, T.S. (2006). _Revisiting Spacetrack Report #3: Rev 1_. AIAA 2006-6753.

[2] Hoots, F.R. & Roehrich, R.L. (1980). _Spacetrack Report No. 3: Models for Propagation of NORAD Element Sets_. Aerospace Defense Command.

[3] Foster, J.L. (1992). _A parametric analysis of orbital debris collision probability and maneuver rate for space vehicles_. NASA/JSC Technical Report.

[4] CelesTrak. (2026). _General Perturbations Data_. https://celestrak.org/NORAD/elements/

[5] Rhodes, B. (2024). _sgp4 Python library_. https://pypi.org/project/sgp4/

[6] FastAPI. (2024). _FastAPI — Modern, fast web framework for Python_. https://fastapi.tiangolo.com/

[7] Pedregosa, F., et al. (2011). _Scikit-learn: Machine Learning in Python_. JMLR 12, pp. 2825–2830.

[8] Bostock, M. (2023). _D3.js — Data-Driven Documents_. https://d3js.org/

[9] Chart.js Contributors. (2024). _Chart.js — Simple yet flexible JavaScript charting_. https://www.chartjs.org/

[10] University of Würzburg. (2018). _UWE-4 CubeSat Mission_. https://www.informatik.uni-wuerzburg.de/

// ════════════════════════════════════════════════════════════════
//  BACK COVER
// ════════════════════════════════════════════════════════════════
#page(
  margin: (top: 0cm, bottom: 0cm, left: 0cm, right: 0cm),
  header: none,
  footer: none,
)[
  #block(
    width: 100%,
    height: 100%,
    fill: rgb("#05091a"),
  )[
    #block(width: 100%, height: 6pt, fill: gradient.linear(rgb("#4f65f1"), rgb("#00d4ff"), angle: 0deg))

    #v(4cm)
    #align(center)[
      #text(14pt, fill: rgb("#4f65f1"), weight: "bold", tracking: 3pt)[ORBITAL COLLISION PREDICTION SYSTEM]
      #v(0.3cm)
      #text(10pt, fill: rgb("#64748b"))[UWE-4 — NORAD 43880 — Beni Suef University, Egypt]
      #v(1.5cm)
      #line(length: 6cm, stroke: 0.5pt + rgb("#4f65f1").transparentize(60%))
      #v(1cm)
      #text(10pt, fill: rgb("#94a3b8"))[
        Ground Station Coordinates \
        #text(fill: rgb("#00d4ff"))[29.0463209° N  |  31.0907943° E  |  Alt. 27 m]
      ]
      #v(0.8cm)
      #text(10pt, fill: rgb("#94a3b8"))[
        Uplink Frequency \ #text(fill: rgb("#00d4ff"))[UHF 435.6 MHz]
      ]
      #v(0.8cm)
      #text(10pt, fill: rgb("#94a3b8"))[
        Graduation Project 2026 \
        #text(fill: rgb("#64748b"), size: 9pt)[Faculty of Engineering — Beni Suef University]
      ]
    ]

    #place(bottom)[
      #block(width: 100%, height: 6pt, fill: gradient.linear(rgb("#4f65f1"), rgb("#00d4ff"), angle: 0deg))
    ]
  ]
]
