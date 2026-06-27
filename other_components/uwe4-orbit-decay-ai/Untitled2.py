# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.1
#   kernelspec:
#     display_name: Python 3
#     name: python3
# ---

# %% colab={"base_uri": "https://localhost:8080/"} id="NN_dXTAFOouy" outputId="115d6a4d-ef79-4ca9-b155-ba4861c74124"
# ============================================================
# Cell 1 — Install Required Libraries
# UWE-4 Orbit Decay AI Prediction Project
# ============================================================

# !pip -q install pandas numpy requests matplotlib scikit-learn joblib sgp4 fastapi uvicorn python-dotenv pydantic

print("✅ Libraries installed successfully.")

# %% colab={"base_uri": "https://localhost:8080/"} id="qCk0U-QOOqve" outputId="b9317bb7-f8f0-473b-f1d3-e6a5ba2771eb"
# ============================================================
# Cell 2 — Imports + Project Settings
# ============================================================

import os
import json
import math
import time
import warnings
from datetime import datetime, timedelta, timezone
from getpass import getpass

import numpy as np
import pandas as pd
import requests
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")

# -----------------------------
# Satellite Settings
# -----------------------------
SATELLITE_NAME = "UWE-4"
NORAD_ID = 43880

# Approximate UWE-4 physical properties
# دي قيم مبدئية لموديل فيزيائي/AI، ونقدر نعدلها لو عندك مصدر أدق
SATELLITE_MASS_KG = 1.1
SATELLITE_AREA_M2 = 0.01      # 1U CubeSat face area تقريبًا
DRAG_COEFFICIENT = 2.2
EARTH_RADIUS_KM = 6378.137
EARTH_MU_KM3_S2 = 398600.4418

BALLISTIC_COEFFICIENT = SATELLITE_MASS_KG / (DRAG_COEFFICIENT * SATELLITE_AREA_M2)

# -----------------------------
# Prediction Settings
# -----------------------------
PREDICTION_HORIZONS_DAYS = [7, 30]

# -----------------------------
# Project Folders
# -----------------------------
PROJECT_ROOT = "."

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports")
API_DIR = os.path.join(PROJECT_ROOT, "api")

for folder in [PROJECT_ROOT, DATA_DIR, RAW_DIR, PROCESSED_DIR, MODELS_DIR, REPORTS_DIR, API_DIR]:
    os.makedirs(folder, exist_ok=True)

config = {
    "satellite_name": SATELLITE_NAME,
    "norad_id": NORAD_ID,
    "mass_kg": SATELLITE_MASS_KG,
    "area_m2": SATELLITE_AREA_M2,
    "drag_coefficient": DRAG_COEFFICIENT,
    "ballistic_coefficient": BALLISTIC_COEFFICIENT,
    "prediction_horizons_days": PREDICTION_HORIZONS_DAYS,
    "earth_radius_km": EARTH_RADIUS_KM,
    "earth_mu_km3_s2": EARTH_MU_KM3_S2,
    "created_at_utc": datetime.now(timezone.utc).isoformat()
}

config_path = os.path.join(PROJECT_ROOT, "project_config.json")

with open(config_path, "w") as f:
    json.dump(config, f, indent=4)

print("✅ Project initialized successfully.")
print(f"📁 Project root: {PROJECT_ROOT}")
print(f"🛰 Satellite: {SATELLITE_NAME}")
print(f"🆔 NORAD ID: {NORAD_ID}")
print(f"⚖️ Mass: {SATELLITE_MASS_KG} kg")
print(f"📐 Area: {SATELLITE_AREA_M2} m²")
print(f"🧲 Cd: {DRAG_COEFFICIENT}")
print(f"🚀 Ballistic coefficient: {BALLISTIC_COEFFICIENT:.3f} kg/m²")
print(f"💾 Config saved to: {config_path}")

# %% colab={"base_uri": "https://localhost:8080/"} id="i7yHiyJpOwGH" outputId="a9680d10-43b2-4d4f-fd1a-a99c56c555b1"
# ============================================================
# Cell 3 — Secure Space-Track Credentials
# Do NOT hard-code username/password in notebook
# ============================================================

SPACE_TRACK_USERNAME = input("Enter Space-Track username/email: ").strip()
SPACE_TRACK_PASSWORD = getpass("Enter Space-Track password: ").strip()

if not SPACE_TRACK_USERNAME or not SPACE_TRACK_PASSWORD:
    raise ValueError("❌ Space-Track username/password cannot be empty.")

print("✅ Space-Track credentials loaded in memory only.")
print("🔐 Credentials were NOT saved to any file.")


# %% colab={"base_uri": "https://localhost:8080/"} id="CHJ4Kuw0PECA" outputId="400705e3-2423-4521-e674-eef1de8fd627"
# ============================================================
# Cell 4 — Quick Environment Test
# ============================================================

def test_url(url, timeout=20):
    try:
        r = requests.get(url, timeout=timeout)
        return r.status_code, r.text[:120]
    except Exception as e:
        return None, str(e)

# Test CelesTrak public access
celestrak_test_url = "https://celestrak.org/SpaceData/SW-All.csv"
status_code, preview = test_url(celestrak_test_url)

print("===== Environment Check =====")
print(f"Python working: ✅")
print(f"Pandas version: {pd.__version__}")
print(f"Project folder exists: {os.path.exists(PROJECT_ROOT)}")
print(f"CelesTrak test status: {status_code}")

if status_code == 200:
    print("✅ Internet + CelesTrak access working.")
else:
    print("⚠️ CelesTrak test did not return 200. ممكن نجرب لينك بديل بعد ما تبعتلي النتيجة.")

print("\nPreview:")
print(preview[:300])

# %% colab={"base_uri": "https://localhost:8080/", "height": 1000} id="UGW4PVMCPZEa" outputId="f1084a7f-7d4d-41fa-e822-55e544951a83"
# ============================================================
# Cell 5 — Login to Space-Track + Test Latest UWE-4 GP Data
# ============================================================

SPACE_TRACK_BASE_URL = "https://www.space-track.org"
LOGIN_URL = f"{SPACE_TRACK_BASE_URL}/ajaxauth/login"

space_track_session = requests.Session()

login_payload = {
    "identity": SPACE_TRACK_USERNAME,
    "password": SPACE_TRACK_PASSWORD
}

login_response = space_track_session.post(
    LOGIN_URL,
    data=login_payload,
    timeout=60
)

print("Login status code:", login_response.status_code)

if login_response.status_code != 200:
    raise RuntimeError("❌ Space-Track login request failed. Check username/password or internet connection.")

# Test query: latest GP data for UWE-4
latest_gp_url = (
    f"{SPACE_TRACK_BASE_URL}/basicspacedata/query/"
    f"class/gp/"
    f"NORAD_CAT_ID/{NORAD_ID}/"
    f"orderby/EPOCH desc/"
    f"limit/1/"
    f"format/json"
)

latest_response = space_track_session.get(latest_gp_url, timeout=60)

print("Latest GP query status code:", latest_response.status_code)

if latest_response.status_code != 200:
    print(latest_response.text[:500])
    raise RuntimeError("❌ Could not fetch latest GP data from Space-Track.")

latest_data = latest_response.json()

if not latest_data:
    raise RuntimeError("❌ Space-Track returned empty latest GP data for UWE-4.")

latest_df = pd.DataFrame(latest_data)

print("✅ Space-Track login and latest GP test successful.")
print("Latest UWE-4 record:")
display(latest_df.T)

# %% colab={"base_uri": "https://localhost:8080/", "height": 1000} id="xYYQy3yLPdzr" outputId="857984db-7ff4-43e9-8eaf-2b4436bf7b6a"
# ============================================================
# Cell 6 — Download Historical GP Data for UWE-4
# ============================================================

START_DATE = "2018-12-27"  # UWE-4 launch date تقريبًا
END_DATE = datetime.now(timezone.utc).strftime("%Y-%m-%d")

historical_gp_url = (
    f"{SPACE_TRACK_BASE_URL}/basicspacedata/query/"
    f"class/gp_history/"
    f"NORAD_CAT_ID/{NORAD_ID}/"
    f"EPOCH/{START_DATE}--{END_DATE}/"
    f"orderby/EPOCH asc/"
    f"format/json"
)

print("Downloading historical GP data...")
print(f"Satellite: {SATELLITE_NAME}")
print(f"NORAD ID: {NORAD_ID}")
print(f"Date range: {START_DATE} → {END_DATE}")

hist_response = space_track_session.get(historical_gp_url, timeout=180)

print("Historical GP query status code:", hist_response.status_code)

if hist_response.status_code != 200:
    print(hist_response.text[:1000])
    raise RuntimeError("❌ Failed to download historical GP data.")

try:
    hist_data = hist_response.json()
except Exception:
    print(hist_response.text[:1000])
    raise RuntimeError("❌ Response is not valid JSON. Space-Track may have returned an error page.")

if not isinstance(hist_data, list) or len(hist_data) == 0:
    print(hist_response.text[:1000])
    raise RuntimeError("❌ No historical GP data returned for UWE-4.")

raw_gp_df = pd.DataFrame(hist_data)

# Save raw file
raw_gp_path = os.path.join(RAW_DIR, "00_raw_gp_history_uwe4.csv")
raw_gp_df.to_csv(raw_gp_path, index=False)

print("✅ Historical GP data downloaded successfully.")
print(f"Rows: {len(raw_gp_df):,}")
print(f"Columns: {len(raw_gp_df.columns)}")
print(f"Saved to: {raw_gp_path}")

print("\nColumns:")
print(list(raw_gp_df.columns))

print("\nFirst rows:")
display(raw_gp_df.head())

print("\nLast rows:")
display(raw_gp_df.tail())

# %% colab={"base_uri": "https://localhost:8080/", "height": 609} id="rR8CkZ3VPu_a" outputId="c0b22c12-155c-49d2-d314-1cdba6d09cc7"
# ============================================================
# Cell 7 — Quick Quality Check for Raw GP Data
# ============================================================

check_df = raw_gp_df.copy()

# Normalize column names to uppercase
check_df.columns = [c.upper() for c in check_df.columns]

if "EPOCH" not in check_df.columns:
    raise ValueError("❌ EPOCH column not found in Space-Track data.")

check_df["EPOCH"] = pd.to_datetime(check_df["EPOCH"], errors="coerce", utc=True)

print("===== Raw GP Data Quality Check =====")
print(f"Total rows: {len(check_df):,}")
print(f"Date min: {check_df['EPOCH'].min()}")
print(f"Date max: {check_df['EPOCH'].max()}")
print(f"Duplicate EPOCH rows: {check_df['EPOCH'].duplicated().sum():,}")
print(f"Missing EPOCH rows: {check_df['EPOCH'].isna().sum():,}")

important_cols = [
    "EPOCH",
    "MEAN_MOTION",
    "ECCENTRICITY",
    "INCLINATION",
    "RA_OF_ASC_NODE",
    "ARG_OF_PERICENTER",
    "MEAN_ANOMALY",
    "BSTAR",
    "MEAN_MOTION_DOT",
    "MEAN_MOTION_DDOT"
]

existing_important_cols = [c for c in important_cols if c in check_df.columns]

print("\nImportant columns found:")
print(existing_important_cols)

print("\nMissing values in important columns:")
display(check_df[existing_important_cols].isna().sum().to_frame("missing_count"))

# Save normalized raw copy
normalized_raw_gp_path = os.path.join(RAW_DIR, "00_raw_gp_history_uwe4_normalized.csv")
check_df.to_csv(normalized_raw_gp_path, index=False)

print(f"\n✅ Normalized raw copy saved to: {normalized_raw_gp_path}")

# %% colab={"base_uri": "https://localhost:8080/", "height": 802} id="EhSQvSCjPxcp" outputId="9afee8c1-580d-453e-d8f7-f60df42a4e71"
# ============================================================
# Cell 8 — Quick Raw Plots
# ============================================================

plot_df = check_df.copy()

numeric_cols = ["MEAN_MOTION", "BSTAR", "ECCENTRICITY", "INCLINATION"]
for col in numeric_cols:
    if col in plot_df.columns:
        plot_df[col] = pd.to_numeric(plot_df[col], errors="coerce")

# Mean Motion plot
if "MEAN_MOTION" in plot_df.columns:
    plt.figure(figsize=(14, 5))
    plt.plot(plot_df["EPOCH"], plot_df["MEAN_MOTION"], linewidth=1)
    plt.title("UWE-4 Historical Mean Motion from Space-Track GP History")
    plt.xlabel("Date")
    plt.ylabel("Mean Motion [rev/day]")
    plt.grid(True)
    plt.show()

# BSTAR plot
if "BSTAR" in plot_df.columns:
    plt.figure(figsize=(14, 5))
    plt.plot(plot_df["EPOCH"], plot_df["BSTAR"], linewidth=1)
    plt.title("UWE-4 Historical BSTAR from Space-Track GP History")
    plt.xlabel("Date")
    plt.ylabel("BSTAR")
    plt.grid(True)
    plt.show()

print("✅ Quick raw plots completed.")

# %% colab={"base_uri": "https://localhost:8080/", "height": 1000} id="dtg2JnGYRrBv" outputId="0c03c877-d926-42ea-d070-7a476e651851"
# ============================================================
# Cell 9 — Clean GP History + Build Epoch-Level Orbit Features
# ============================================================

# لو raw_gp_df مش موجود بسبب عمل restart للـ runtime، نقرأه من الملف
raw_gp_path = os.path.join(RAW_DIR, "00_raw_gp_history_uwe4.csv")

if "raw_gp_df" not in globals():
    if not os.path.exists(raw_gp_path):
        raise FileNotFoundError(f"❌ Raw GP file not found: {raw_gp_path}")
    raw_gp_df = pd.read_csv(raw_gp_path)

df = raw_gp_df.copy()
df.columns = [c.upper().strip() for c in df.columns]

print("===== Starting Cleaning =====")
print(f"Raw rows: {len(df):,}")
print(f"Raw columns: {len(df.columns)}")

# -----------------------------
# Parse dates
# -----------------------------
df["EPOCH"] = pd.to_datetime(df["EPOCH"], errors="coerce", utc=True)

if "CREATION_DATE" in df.columns:
    df["CREATION_DATE"] = pd.to_datetime(df["CREATION_DATE"], errors="coerce", utc=True)
else:
    df["CREATION_DATE"] = pd.NaT

# -----------------------------
# Convert important columns to numeric
# -----------------------------
numeric_columns = [
    "MEAN_MOTION",
    "ECCENTRICITY",
    "INCLINATION",
    "RA_OF_ASC_NODE",
    "ARG_OF_PERICENTER",
    "MEAN_ANOMALY",
    "BSTAR",
    "MEAN_MOTION_DOT",
    "MEAN_MOTION_DDOT",
    "SEMIMAJOR_AXIS",
    "PERIOD",
    "APOAPSIS",
    "PERIAPSIS",
    "REV_AT_EPOCH",
    "GP_ID",
    "FILE",
    "NORAD_CAT_ID"
]

for col in numeric_columns:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# -----------------------------
# Remove rows without epoch or mean motion
# -----------------------------
before = len(df)
df = df.dropna(subset=["EPOCH", "MEAN_MOTION"]).copy()
print(f"Removed rows with missing EPOCH/MEAN_MOTION: {before - len(df):,}")

# -----------------------------
# Remove exact duplicate rows
# -----------------------------
before = len(df)
df = df.drop_duplicates()
print(f"Removed exact duplicate rows: {before - len(df):,}")

# -----------------------------
# Handle duplicate EPOCHs
# Keep the latest created / highest GP_ID record for each EPOCH
# -----------------------------
before = len(df)

sort_cols = ["EPOCH"]
if "CREATION_DATE" in df.columns:
    sort_cols.append("CREATION_DATE")
if "GP_ID" in df.columns:
    sort_cols.append("GP_ID")

df = df.sort_values(sort_cols).copy()
df = df.drop_duplicates(subset=["EPOCH"], keep="last").copy()

duplicate_removed = before - len(df)
print(f"Removed duplicate EPOCH rows: {duplicate_removed:,}")

# -----------------------------
# Compute orbital features from mean motion
# -----------------------------
# mean motion [rev/day] -> rad/s
df["mean_motion_rad_s"] = df["MEAN_MOTION"] * 2 * np.pi / 86400.0

# semi-major axis from Kepler's 3rd law
df["semi_major_axis_from_mm_km"] = (EARTH_MU_KM3_S2 / (df["mean_motion_rad_s"] ** 2)) ** (1 / 3)

# Use Space-Track semi-major axis when available, otherwise computed one
if "SEMIMAJOR_AXIS" in df.columns:
    df["semi_major_axis_km"] = df["SEMIMAJOR_AXIS"].fillna(df["semi_major_axis_from_mm_km"])
else:
    df["semi_major_axis_km"] = df["semi_major_axis_from_mm_km"]

# Difference check between Space-Track and computed semi-major axis
if "SEMIMAJOR_AXIS" in df.columns:
    df["semi_major_axis_diff_km"] = df["SEMIMAJOR_AXIS"] - df["semi_major_axis_from_mm_km"]
else:
    df["semi_major_axis_diff_km"] = np.nan

# Eccentricity
df["eccentricity"] = df["ECCENTRICITY"].astype(float)

# Computed perigee/apogee altitude
df["perigee_altitude_computed_km"] = df["semi_major_axis_km"] * (1 - df["eccentricity"]) - EARTH_RADIUS_KM
df["apogee_altitude_computed_km"] = df["semi_major_axis_km"] * (1 + df["eccentricity"]) - EARTH_RADIUS_KM

# Use Space-Track apoapsis/periapsis if available
# ملاحظة: Space-Track APOAPSIS/PERIAPSIS هنا Altitude مش radius
if "PERIAPSIS" in df.columns:
    df["perigee_altitude_km"] = df["PERIAPSIS"].fillna(df["perigee_altitude_computed_km"])
else:
    df["perigee_altitude_km"] = df["perigee_altitude_computed_km"]

if "APOAPSIS" in df.columns:
    df["apogee_altitude_km"] = df["APOAPSIS"].fillna(df["apogee_altitude_computed_km"])
else:
    df["apogee_altitude_km"] = df["apogee_altitude_computed_km"]

# Mean altitude
df["altitude_mean_km"] = (df["perigee_altitude_km"] + df["apogee_altitude_km"]) / 2.0

# Period
if "PERIOD" in df.columns:
    df["orbital_period_min"] = df["PERIOD"]
else:
    df["orbital_period_min"] = 1440.0 / df["MEAN_MOTION"]

# -----------------------------
# Rename / select model-friendly columns
# -----------------------------
features = pd.DataFrame({
    "epoch": df["EPOCH"],
    "date": df["EPOCH"].dt.floor("D"),
    "creation_date": df["CREATION_DATE"],
    "norad_id": df["NORAD_CAT_ID"] if "NORAD_CAT_ID" in df.columns else NORAD_ID,
    "object_name": df["OBJECT_NAME"] if "OBJECT_NAME" in df.columns else SATELLITE_NAME,

    "mean_motion_rev_day": df["MEAN_MOTION"],
    "mean_motion_dot": df["MEAN_MOTION_DOT"] if "MEAN_MOTION_DOT" in df.columns else np.nan,
    "mean_motion_ddot": df["MEAN_MOTION_DDOT"] if "MEAN_MOTION_DDOT" in df.columns else np.nan,

    "eccentricity": df["ECCENTRICITY"],
    "inclination_deg": df["INCLINATION"],
    "raan_deg": df["RA_OF_ASC_NODE"],
    "arg_perigee_deg": df["ARG_OF_PERICENTER"],
    "mean_anomaly_deg": df["MEAN_ANOMALY"],

    "bstar": df["BSTAR"],

    "semi_major_axis_km": df["semi_major_axis_km"],
    "semi_major_axis_from_mm_km": df["semi_major_axis_from_mm_km"],
    "semi_major_axis_diff_km": df["semi_major_axis_diff_km"],

    "perigee_altitude_km": df["perigee_altitude_km"],
    "apogee_altitude_km": df["apogee_altitude_km"],
    "altitude_mean_km": df["altitude_mean_km"],
    "orbital_period_min": df["orbital_period_min"],

    "mass_kg": SATELLITE_MASS_KG,
    "area_m2": SATELLITE_AREA_M2,
    "drag_coefficient": DRAG_COEFFICIENT,
    "ballistic_coefficient": BALLISTIC_COEFFICIENT
})

# -----------------------------
# Basic physical sanity flags
# مش هنحذف BSTAR spikes دلوقتي، بس هنعلمها flag
# -----------------------------
features["bad_orbit_flag"] = (
    (features["semi_major_axis_km"] < EARTH_RADIUS_KM + 250) |
    (features["semi_major_axis_km"] > EARTH_RADIUS_KM + 800) |
    (features["altitude_mean_km"] < 250) |
    (features["altitude_mean_km"] > 800) |
    (features["eccentricity"] < 0) |
    (features["eccentricity"] > 0.05) |
    (features["inclination_deg"] < 80) |
    (features["inclination_deg"] > 110)
).astype(int)

# BSTAR robust outlier flag
bstar_median = features["bstar"].median()
bstar_iqr = features["bstar"].quantile(0.75) - features["bstar"].quantile(0.25)

if bstar_iqr == 0 or pd.isna(bstar_iqr):
    features["bstar_outlier_flag"] = 0
else:
    lower = bstar_median - 8 * bstar_iqr
    upper = bstar_median + 8 * bstar_iqr
    features["bstar_outlier_flag"] = (
        (features["bstar"] < lower) |
        (features["bstar"] > upper)
    ).astype(int)

# Remove only physically bad orbit rows
before = len(features)
features_clean = features[features["bad_orbit_flag"] == 0].copy()
removed_bad_orbit = before - len(features_clean)

features_clean = features_clean.sort_values("epoch").reset_index(drop=True)

epoch_features_path = os.path.join(PROCESSED_DIR, "01_epoch_orbit_features_uwe4.csv")
features_clean.to_csv(epoch_features_path, index=False)

print("\n===== Cleaning Summary =====")
print(f"Raw rows: {len(raw_gp_df):,}")
print(f"After cleaning rows: {len(features_clean):,}")
print(f"Duplicate EPOCH rows removed: {duplicate_removed:,}")
print(f"Physically bad orbit rows removed: {removed_bad_orbit:,}")
print(f"BSTAR outlier flags kept, not removed: {features_clean['bstar_outlier_flag'].sum():,}")

print("\nDate range:")
print("Start:", features_clean["epoch"].min())
print("End:  ", features_clean["epoch"].max())

print("\nLatest cleaned record:")
display(features_clean.tail(1).T)

print(f"\n✅ Epoch-level orbit features saved to:\n{epoch_features_path}")

# %% colab={"base_uri": "https://localhost:8080/", "height": 1000} id="XhM1r1r1R6nb" outputId="deae3d5f-08de-45de-e170-4c491c6e561c"
# ============================================================
# Cell 10 — Build Daily Orbit Decay Dataset + Targets
# ============================================================

epoch_df = features_clean.copy()
epoch_df["date"] = pd.to_datetime(epoch_df["date"], utc=True).dt.floor("D")

# نختار آخر TLE في كل يوم عشان يبقى عندنا record واحد لكل يوم
daily = (
    epoch_df
    .sort_values("epoch")
    .groupby("date", as_index=False)
    .tail(1)
    .sort_values("date")
    .reset_index(drop=True)
)

print("===== Daily Dataset Before Reindex =====")
print(f"Daily rows with actual TLE: {len(daily):,}")
print(f"Date min: {daily['date'].min()}")
print(f"Date max: {daily['date'].max()}")

# Reindex to full daily date range
full_dates = pd.date_range(
    start=daily["date"].min(),
    end=daily["date"].max(),
    freq="D",
    tz="UTC"
)

daily = daily.set_index("date").reindex(full_dates)
daily.index.name = "date"

daily["had_tle_that_day"] = daily["epoch"].notna().astype(int)

# Interpolate only numerical orbit columns for missing days
numeric_interpolate_cols = [
    "mean_motion_rev_day",
    "mean_motion_dot",
    "mean_motion_ddot",
    "eccentricity",
    "inclination_deg",
    "raan_deg",
    "arg_perigee_deg",
    "mean_anomaly_deg",
    "bstar",
    "semi_major_axis_km",
    "semi_major_axis_from_mm_km",
    "semi_major_axis_diff_km",
    "perigee_altitude_km",
    "apogee_altitude_km",
    "altitude_mean_km",
    "orbital_period_min",
    "mass_kg",
    "area_m2",
    "drag_coefficient",
    "ballistic_coefficient",
    "bstar_outlier_flag"
]

existing_numeric_cols = [c for c in numeric_interpolate_cols if c in daily.columns]

for col in existing_numeric_cols:
    daily[col] = pd.to_numeric(daily[col], errors="coerce")

daily[existing_numeric_cols] = daily[existing_numeric_cols].interpolate(
    method="time",
    limit=7,
    limit_direction="both"
)

# Fill constants
daily["norad_id"] = daily["norad_id"].fillna(NORAD_ID)
daily["object_name"] = daily["object_name"].fillna(SATELLITE_NAME)
daily["mass_kg"] = daily["mass_kg"].fillna(SATELLITE_MASS_KG)
daily["area_m2"] = daily["area_m2"].fillna(SATELLITE_AREA_M2)
daily["drag_coefficient"] = daily["drag_coefficient"].fillna(DRAG_COEFFICIENT)
daily["ballistic_coefficient"] = daily["ballistic_coefficient"].fillna(BALLISTIC_COEFFICIENT)

# Flag interpolated days
daily["interpolated_day_flag"] = (daily["had_tle_that_day"] == 0).astype(int)

# Reset index
daily = daily.reset_index()

# Time features
daily["year"] = daily["date"].dt.year
daily["month"] = daily["date"].dt.month
daily["day_of_year"] = daily["date"].dt.dayofyear
daily["days_since_start"] = (daily["date"] - daily["date"].min()).dt.days

# -----------------------------
# Observed decay
# positive value = altitude decreased from previous day
# -----------------------------
daily["observed_decay_km_day"] = daily["altitude_mean_km"].shift(1) - daily["altitude_mean_km"]
daily["observed_sma_decay_km_day"] = daily["semi_major_axis_km"].shift(1) - daily["semi_major_axis_km"]

# Smooth observed decay to reduce TLE noise
for window in [3, 7, 14, 30]:
    daily[f"observed_decay_rolling_{window}d_km_day"] = (
        daily["observed_decay_km_day"]
        .rolling(window=window, min_periods=2)
        .mean()
    )

    daily[f"altitude_rolling_{window}d_km"] = (
        daily["altitude_mean_km"]
        .rolling(window=window, min_periods=2)
        .mean()
    )

    daily[f"bstar_rolling_{window}d"] = (
        daily["bstar"]
        .rolling(window=window, min_periods=2)
        .mean()
    )

# Lag features
for lag in [1, 2, 3, 7, 14, 30]:
    daily[f"altitude_lag_{lag}d_km"] = daily["altitude_mean_km"].shift(lag)
    daily[f"mean_motion_lag_{lag}d"] = daily["mean_motion_rev_day"].shift(lag)
    daily[f"bstar_lag_{lag}d"] = daily["bstar"].shift(lag)
    daily[f"decay_lag_{lag}d_km_day"] = daily["observed_decay_km_day"].shift(lag)

# Future targets for AI prediction
for horizon in PREDICTION_HORIZONS_DAYS:
    daily[f"target_altitude_after_{horizon}d_km"] = daily["altitude_mean_km"].shift(-horizon)
    daily[f"target_decay_next_{horizon}d_km"] = (
        daily["altitude_mean_km"] - daily[f"target_altitude_after_{horizon}d_km"]
    )
    daily[f"target_decay_rate_next_{horizon}d_km_day"] = (
        daily[f"target_decay_next_{horizon}d_km"] / horizon
    )

# Clean impossible rows after interpolation
daily = daily.dropna(subset=["altitude_mean_km", "semi_major_axis_km", "mean_motion_rev_day"]).copy()

daily_path = os.path.join(PROCESSED_DIR, "02_daily_orbit_decay_targets_uwe4.csv")
daily.to_csv(daily_path, index=False)

print("\n===== Daily Orbit Decay Dataset Summary =====")
print(f"Daily rows total: {len(daily):,}")
print(f"Actual TLE days: {daily['had_tle_that_day'].sum():,}")
print(f"Interpolated days: {daily['interpolated_day_flag'].sum():,}")
print(f"Date range: {daily['date'].min()} → {daily['date'].max()}")

latest = daily.tail(1).iloc[0]

print("\n===== Latest Orbit State =====")
print(f"Latest date: {latest['date']}")
print(f"Altitude mean: {latest['altitude_mean_km']:.3f} km")
print(f"Perigee: {latest['perigee_altitude_km']:.3f} km")
print(f"Apogee: {latest['apogee_altitude_km']:.3f} km")
print(f"Mean motion: {latest['mean_motion_rev_day']:.6f} rev/day")
print(f"BSTAR: {latest['bstar']:.8f}")

print("\n===== Recent Observed Decay =====")
for window in [7, 14, 30]:
    col = f"observed_decay_rolling_{window}d_km_day"
    val = latest[col]
    print(f"Last {window}d avg decay: {val:.6f} km/day = {val*1000:.2f} m/day")

print("\n===== Target Availability =====")
for horizon in PREDICTION_HORIZONS_DAYS:
    target_col = f"target_decay_next_{horizon}d_km"
    available = daily[target_col].notna().sum()
    missing = daily[target_col].isna().sum()
    print(f"{horizon}d target available rows: {available:,} | missing rows: {missing:,}")

print(f"\n✅ Daily orbit decay dataset saved to:\n{daily_path}")

display(daily.tail(10))

# %% colab={"base_uri": "https://localhost:8080/", "height": 1000} id="SNGYosRbSQ8N" outputId="7d963ff6-6c5e-4c21-c548-426a211aa603"
# ============================================================
# Cell 11 — Visual Check: Clean Altitude and Decay Trend
# ============================================================

plot_daily = daily.copy()

# 1) Mean altitude
plt.figure(figsize=(14, 5))
plt.plot(plot_daily["date"], plot_daily["altitude_mean_km"], linewidth=1.5)
plt.title("UWE-4 Mean Altitude Over Time — Cleaned Daily Dataset")
plt.xlabel("Date")
plt.ylabel("Mean Altitude [km]")
plt.grid(True)
plt.show()

# 2) Perigee and apogee
plt.figure(figsize=(14, 5))
plt.plot(plot_daily["date"], plot_daily["perigee_altitude_km"], linewidth=1, label="Perigee altitude")
plt.plot(plot_daily["date"], plot_daily["apogee_altitude_km"], linewidth=1, label="Apogee altitude")
plt.title("UWE-4 Perigee and Apogee Altitude Over Time")
plt.xlabel("Date")
plt.ylabel("Altitude [km]")
plt.legend()
plt.grid(True)
plt.show()

# 3) Daily decay raw vs smoothed
plt.figure(figsize=(14, 5))
plt.plot(plot_daily["date"], plot_daily["observed_decay_km_day"], linewidth=0.7, alpha=0.5, label="Daily observed decay")
plt.plot(plot_daily["date"], plot_daily["observed_decay_rolling_7d_km_day"], linewidth=1.5, label="7-day rolling avg")
plt.plot(plot_daily["date"], plot_daily["observed_decay_rolling_30d_km_day"], linewidth=2, label="30-day rolling avg")
plt.title("UWE-4 Observed Orbit Decay Rate")
plt.xlabel("Date")
plt.ylabel("Decay [km/day]")
plt.legend()
plt.grid(True)
plt.show()

# 4) BSTAR with rolling average
plt.figure(figsize=(14, 5))
plt.plot(plot_daily["date"], plot_daily["bstar"], linewidth=0.7, alpha=0.5, label="BSTAR")
plt.plot(plot_daily["date"], plot_daily["bstar_rolling_14d"], linewidth=2, label="BSTAR 14-day rolling avg")
plt.title("UWE-4 BSTAR Trend")
plt.xlabel("Date")
plt.ylabel("BSTAR")
plt.legend()
plt.grid(True)
plt.show()

print("✅ Visual checks completed.")

# %% colab={"base_uri": "https://localhost:8080/"} id="Bon6s1BBSiey" outputId="8e91880f-cf38-4f2a-c3d5-269fb932eaba"
# ============================================================
# Cell 12 — Sanity Report for Project Submission
# ============================================================

report = {}

first_row = daily.iloc[0]
last_row = daily.iloc[-1]

report["satellite"] = SATELLITE_NAME
report["norad_id"] = NORAD_ID
report["data_start"] = str(first_row["date"])
report["data_end"] = str(last_row["date"])
report["daily_rows"] = int(len(daily))
report["actual_tle_days"] = int(daily["had_tle_that_day"].sum())
report["interpolated_days"] = int(daily["interpolated_day_flag"].sum())

report["initial_altitude_mean_km"] = float(first_row["altitude_mean_km"])
report["latest_altitude_mean_km"] = float(last_row["altitude_mean_km"])
report["total_observed_altitude_loss_km"] = float(first_row["altitude_mean_km"] - last_row["altitude_mean_km"])

total_days = max((last_row["date"] - first_row["date"]).days, 1)
report["average_decay_km_day_whole_period"] = report["total_observed_altitude_loss_km"] / total_days
report["average_decay_m_day_whole_period"] = report["average_decay_km_day_whole_period"] * 1000

for window in [7, 14, 30, 90]:
    if len(daily) >= window:
        recent_decay = daily["observed_decay_km_day"].tail(window).mean()
        report[f"recent_{window}d_avg_decay_km_day"] = float(recent_decay)
        report[f"recent_{window}d_avg_decay_m_day"] = float(recent_decay * 1000)

report_path = os.path.join(REPORTS_DIR, "01_orbit_decay_data_sanity_report.json")

with open(report_path, "w") as f:
    json.dump(report, f, indent=4)

print("===== UWE-4 Orbit Decay Data Sanity Report =====")
for k, v in report.items():
    if isinstance(v, float):
        print(f"{k}: {v:.6f}")
    else:
        print(f"{k}: {v}")

print(f"\n✅ Sanity report saved to:\n{report_path}")

# %% colab={"base_uri": "https://localhost:8080/", "height": 856} id="gXSiaa2lTuwb" outputId="b3588613-76c4-416a-fb85-897c8a2ab08f"
# ============================================================
# Cell 13 — Final Validation Before Space Weather Merge
# ============================================================

validation = {}

validation["total_daily_rows"] = int(len(daily))
validation["date_min"] = str(daily["date"].min())
validation["date_max"] = str(daily["date"].max())

# Check duplicated dates
validation["duplicate_dates"] = int(daily["date"].duplicated().sum())

# Check missing important columns
important_daily_cols = [
    "date",
    "altitude_mean_km",
    "perigee_altitude_km",
    "apogee_altitude_km",
    "semi_major_axis_km",
    "mean_motion_rev_day",
    "eccentricity",
    "inclination_deg",
    "bstar",
    "observed_decay_km_day",
    "observed_decay_rolling_7d_km_day",
    "observed_decay_rolling_30d_km_day",
    "target_decay_next_7d_km",
    "target_decay_next_30d_km"
]

missing_summary = {}
for col in important_daily_cols:
    if col in daily.columns:
        missing_summary[col] = int(daily[col].isna().sum())
    else:
        missing_summary[col] = "COLUMN_NOT_FOUND"

validation["missing_summary"] = missing_summary

# Check target availability
for horizon in PREDICTION_HORIZONS_DAYS:
    target_col = f"target_decay_next_{horizon}d_km"
    rate_col = f"target_decay_rate_next_{horizon}d_km_day"

    validation[f"{horizon}d_target_available_rows"] = int(daily[target_col].notna().sum())
    validation[f"{horizon}d_target_missing_rows"] = int(daily[target_col].isna().sum())

    train_ready = daily.dropna(subset=[target_col, rate_col]).copy()
    validation[f"{horizon}d_train_ready_rows_before_space_weather"] = int(len(train_ready))

# Check suspicious altitude jumps
daily["abs_daily_altitude_change_km"] = daily["altitude_mean_km"].diff().abs()

suspicious_jumps = daily[daily["abs_daily_altitude_change_km"] > 2.0][
    ["date", "altitude_mean_km", "abs_daily_altitude_change_km", "had_tle_that_day", "interpolated_day_flag"]
].copy()

validation["suspicious_altitude_jumps_gt_2km"] = int(len(suspicious_jumps))

# Decay stats
decay_stats = daily["observed_decay_km_day"].describe().to_dict()
validation["observed_decay_stats_km_day"] = {
    k: float(v) for k, v in decay_stats.items()
}

# Save validation report
validation_report_path = os.path.join(REPORTS_DIR, "02_daily_dataset_validation_report.json")

with open(validation_report_path, "w") as f:
    json.dump(validation, f, indent=4)

print("===== Final Daily Dataset Validation =====")
print(f"Rows: {validation['total_daily_rows']}")
print(f"Date range: {validation['date_min']} → {validation['date_max']}")
print(f"Duplicate dates: {validation['duplicate_dates']}")
print(f"Suspicious altitude jumps > 2 km/day: {validation['suspicious_altitude_jumps_gt_2km']}")

print("\n===== Missing Values Summary =====")
for col, miss in missing_summary.items():
    print(f"{col}: {miss}")

print("\n===== Target Training Rows =====")
for horizon in PREDICTION_HORIZONS_DAYS:
    print(
        f"{horizon}d target rows before space weather: "
        f"{validation[f'{horizon}d_train_ready_rows_before_space_weather']}"
    )

print("\n===== Observed Decay Stats [km/day] =====")
display(daily["observed_decay_km_day"].describe().to_frame("observed_decay_km_day"))

if len(suspicious_jumps) > 0:
    print("\n⚠️ Suspicious jumps found. Displaying first rows:")
    display(suspicious_jumps.head(20))
else:
    print("\n✅ No suspicious altitude jumps greater than 2 km/day.")

print(f"\n✅ Validation report saved to:\n{validation_report_path}")

# %% colab={"base_uri": "https://localhost:8080/", "height": 891} id="N4DkEnKmURUF" outputId="7b0a16e4-a3fd-4408-a6aa-dcfce34155d9"
# ============================================================
# Cell 14 — Download CelesTrak Space Weather Data
# ============================================================

space_weather_url = "https://celestrak.org/SpaceData/SW-All.csv"
space_weather_raw_path = os.path.join(RAW_DIR, "01_raw_celestrak_space_weather.csv")

print("Downloading CelesTrak Space Weather data...")
print(space_weather_url)

sw_response = requests.get(space_weather_url, timeout=120)

print("Status code:", sw_response.status_code)

if sw_response.status_code != 200:
    print(sw_response.text[:500])
    raise RuntimeError("❌ Failed to download CelesTrak Space Weather data.")

with open(space_weather_raw_path, "wb") as f:
    f.write(sw_response.content)

sw_raw = pd.read_csv(space_weather_raw_path)

print("✅ Space Weather data downloaded successfully.")
print(f"Rows: {len(sw_raw):,}")
print(f"Columns: {len(sw_raw.columns)}")
print(f"Saved to: {space_weather_raw_path}")

print("\nColumns:")
print(list(sw_raw.columns))

print("\nFirst rows:")
display(sw_raw.head())

print("\nLast rows:")
display(sw_raw.tail())

# %% colab={"base_uri": "https://localhost:8080/", "height": 1000} id="qIbBkKVuUWjV" outputId="19759ddc-e0c2-4cb5-ce5b-2e679d63cb4d"
# ============================================================
# Cell 15 — Clean Space Weather + Build Weather Features
# ============================================================

sw = sw_raw.copy()
sw.columns = [c.upper().strip() for c in sw.columns]

if "DATE" not in sw.columns:
    raise ValueError("❌ DATE column not found in Space Weather data.")

sw["date"] = pd.to_datetime(sw["DATE"], errors="coerce", utc=True).dt.floor("D")

# Convert all non-date columns to numeric where possible
for col in sw.columns:
    if col not in ["DATE", "date"]:
        sw[col] = pd.to_numeric(sw[col], errors="coerce")

# Replace common missing/sentinel values
# بعض ملفات Space Weather بتحط 999 أو -1 كقيم ناقصة
for col in sw.columns:
    if col not in ["DATE", "date"]:
        sw.loc[sw[col].isin([999, 999.0, 9999, 9999.0, -999, -9999]), col] = np.nan

# Helper function to find possible column names
def find_first_existing_column(df, possible_names):
    for name in possible_names:
        if name in df.columns:
            return name
    return None

f107_obs_col = find_first_existing_column(sw, ["F10.7_OBS", "F107_OBS", "F10_7_OBS"])
f107_adj_col = find_first_existing_column(sw, ["F10.7_ADJ", "F107_ADJ", "F10_7_ADJ"])
sunspot_col = find_first_existing_column(sw, ["ISN", "SSN", "SUNSPOT_NUMBER"])
ap_avg_col = find_first_existing_column(sw, ["AP_AVG", "APAVG"])
kp_sum_col = find_first_existing_column(sw, ["KP_SUM", "KPSUM"])

kp_cols = [c for c in [f"KP{i}" for i in range(1, 9)] if c in sw.columns]
ap_cols = [c for c in [f"AP{i}" for i in range(1, 9)] if c in sw.columns]

print("===== Detected Space Weather Columns =====")
print("F10.7 observed:", f107_obs_col)
print("F10.7 adjusted:", f107_adj_col)
print("Sunspot number:", sunspot_col)
print("AP average:", ap_avg_col)
print("KP sum:", kp_sum_col)
print("KP columns:", kp_cols)
print("AP columns:", ap_cols)

weather = pd.DataFrame()
weather["date"] = sw["date"]

# F10.7 solar flux
weather["f107_obs"] = sw[f107_obs_col] if f107_obs_col else np.nan
weather["f107_adj"] = sw[f107_adj_col] if f107_adj_col else np.nan

# Sunspot number
weather["sunspot_number"] = sw[sunspot_col] if sunspot_col else np.nan

# KP handling
# CelesTrak KP values أحيانًا بتكون مضروبة ×10، فهنكشف ده تلقائيًا
if kp_cols:
    kp_values = sw[kp_cols].copy()
    kp_max_raw = kp_values.max().max()

    if pd.notna(kp_max_raw) and kp_max_raw > 9:
        kp_values = kp_values / 10.0
        print("ℹ️ KP values appear to be scaled by 10. Divided KP columns by 10.")
    else:
        print("ℹ️ KP values appear to be normal 0–9 scale.")

    # Remove impossible KP values
    kp_values = kp_values.where((kp_values >= 0) & (kp_values <= 9), np.nan)

    weather["kp_mean"] = kp_values.mean(axis=1)
    weather["kp_max"] = kp_values.max(axis=1)
    weather["kp_sum"] = kp_values.sum(axis=1)
else:
    weather["kp_mean"] = np.nan
    weather["kp_max"] = np.nan
    weather["kp_sum"] = sw[kp_sum_col] if kp_sum_col else np.nan

# AP handling
if ap_cols:
    ap_values = sw[ap_cols].copy()
    ap_values = ap_values.where(ap_values >= 0, np.nan)

    weather["ap_mean"] = ap_values.mean(axis=1)
    weather["ap_max"] = ap_values.max(axis=1)
    weather["ap_sum"] = ap_values.sum(axis=1)
else:
    weather["ap_mean"] = sw[ap_avg_col] if ap_avg_col else np.nan
    weather["ap_max"] = np.nan
    weather["ap_sum"] = np.nan

if ap_avg_col:
    weather["ap_avg"] = sw[ap_avg_col]
else:
    weather["ap_avg"] = weather["ap_mean"]

# Clean impossible solar values
for col in ["f107_obs", "f107_adj"]:
    weather[col] = pd.to_numeric(weather[col], errors="coerce")
    weather.loc[weather[col] <= 0, col] = np.nan

weather["sunspot_number"] = pd.to_numeric(weather["sunspot_number"], errors="coerce")
weather.loc[weather["sunspot_number"] < 0, "sunspot_number"] = np.nan

# Sort and remove duplicate dates
weather = weather.dropna(subset=["date"]).sort_values("date").drop_duplicates("date", keep="last")

# Rolling and lag features
base_weather_cols = [
    "f107_obs",
    "f107_adj",
    "sunspot_number",
    "kp_mean",
    "kp_max",
    "kp_sum",
    "ap_avg",
    "ap_mean",
    "ap_max",
    "ap_sum"
]

for col in base_weather_cols:
    if col in weather.columns:
        weather[col] = pd.to_numeric(weather[col], errors="coerce")

for window in [3, 7, 14, 27, 81]:
    for col in ["f107_obs", "f107_adj", "sunspot_number", "kp_mean", "kp_max", "ap_avg", "ap_max"]:
        if col in weather.columns:
            weather[f"{col}_rolling_{window}d"] = (
                weather[col]
                .rolling(window=window, min_periods=2)
                .mean()
            )

for lag in [1, 2, 3, 7, 14, 27]:
    for col in ["f107_obs", "f107_adj", "sunspot_number", "kp_mean", "kp_max", "ap_avg", "ap_max"]:
        if col in weather.columns:
            weather[f"{col}_lag_{lag}d"] = weather[col].shift(lag)

# Recent storm flags
weather["geomagnetic_active_flag"] = (
    (weather["kp_max"] >= 5) |
    (weather["ap_max"] >= 50)
).astype(int)

weather["high_solar_flux_flag"] = (
    weather["f107_obs"] >= weather["f107_obs"].quantile(0.80)
).astype(int)

space_weather_features_path = os.path.join(PROCESSED_DIR, "03_space_weather_features.csv")
weather.to_csv(space_weather_features_path, index=False)

print("\n===== Space Weather Features Summary =====")
print(f"Rows: {len(weather):,}")
print(f"Date range: {weather['date'].min()} → {weather['date'].max()}")
print(f"Columns: {len(weather.columns)}")
print(f"Saved to: {space_weather_features_path}")

print("\nMissing values in key weather columns:")
display(weather[["date", "f107_obs", "f107_adj", "sunspot_number", "kp_mean", "kp_max", "ap_avg", "ap_max"]].isna().sum().to_frame("missing_count"))

print("\nSample:")
display(weather.tail(10))

# %% colab={"base_uri": "https://localhost:8080/", "height": 1000} id="1R47l0UEUcpa" outputId="ce035a29-5bf5-4bae-d060-47d3a4001fc2"
# ============================================================
# Cell 16 — Merge Daily Orbit Dataset with Space Weather
# ============================================================

daily_path = os.path.join(PROCESSED_DIR, "02_daily_orbit_decay_targets_uwe4.csv")

if "daily" not in globals():
    if not os.path.exists(daily_path):
        raise FileNotFoundError(f"❌ Daily orbit dataset not found: {daily_path}")
    daily = pd.read_csv(daily_path)

orbit_daily = daily.copy()

orbit_daily["date"] = pd.to_datetime(orbit_daily["date"], errors="coerce", utc=True).dt.floor("D")
weather["date"] = pd.to_datetime(weather["date"], errors="coerce", utc=True).dt.floor("D")

dataset = orbit_daily.merge(
    weather,
    on="date",
    how="left",
    suffixes=("", "_weather")
)

print("===== Merge Summary =====")
print(f"Orbit daily rows: {len(orbit_daily):,}")
print(f"Weather rows: {len(weather):,}")
print(f"Merged rows: {len(dataset):,}")

# Check missing weather after merge
key_weather_cols = ["f107_obs", "f107_adj", "sunspot_number", "kp_mean", "kp_max", "ap_avg", "ap_max"]

print("\nMissing weather values after merge:")
display(dataset[key_weather_cols].isna().sum().to_frame("missing_count"))

missing_weather_rows = dataset[dataset["f107_obs"].isna() | dataset["ap_avg"].isna() | dataset["kp_mean"].isna()]

print(f"\nRows with missing key weather values: {len(missing_weather_rows):,}")

if len(missing_weather_rows) > 0:
    print("First missing weather rows:")
    display(missing_weather_rows[["date", "altitude_mean_km", "f107_obs", "kp_mean", "ap_avg"]].head(20))

# Interpolate small gaps only
weather_feature_cols = [c for c in dataset.columns if any(
    c.startswith(prefix) for prefix in [
        "f107_",
        "sunspot_",
        "kp_",
        "ap_"
    ]
)]

for col in weather_feature_cols:
    dataset[col] = pd.to_numeric(dataset[col], errors="coerce")

dataset[weather_feature_cols] = dataset[weather_feature_cols].interpolate(
    method="linear",
    limit=3,
    limit_direction="both"
)

# Flag whether weather was originally missing
dataset["weather_interpolated_flag"] = (
    dataset[key_weather_cols].isna().any(axis=1)
).astype(int)

# Fill remaining rolling/lags if early rows only
# أول أيام ممكن rolling/lag تبقى NaN طبيعي؛ هنسيبها دلوقتي وهنتعامل معها في training
merged_dataset_path = os.path.join(PROCESSED_DIR, "04_daily_orbit_space_weather_uwe4.csv")
dataset.to_csv(merged_dataset_path, index=False)

print("\n===== Final Merged Dataset Summary =====")
print(f"Rows: {len(dataset):,}")
print(f"Columns: {len(dataset.columns)}")
print(f"Date range: {dataset['date'].min()} → {dataset['date'].max()}")

print("\nKey columns preview:")
preview_cols = [
    "date",
    "altitude_mean_km",
    "observed_decay_km_day",
    "observed_decay_rolling_7d_km_day",
    "f107_obs",
    "f107_obs_rolling_7d",
    "kp_max",
    "kp_max_rolling_7d",
    "ap_avg",
    "ap_avg_rolling_7d",
    "target_decay_next_7d_km",
    "target_decay_next_30d_km"
]

existing_preview_cols = [c for c in preview_cols if c in dataset.columns]
display(dataset[existing_preview_cols].tail(15))

print(f"\n✅ Merged orbit + space weather dataset saved to:\n{merged_dataset_path}")

# %% colab={"base_uri": "https://localhost:8080/", "height": 1000} id="2-9d-YREUhF3" outputId="354cb7a3-9f54-4cd6-b9f2-ff8b17aba6ba"
# ============================================================
# Cell 17 — Visual Check: Orbit Decay vs Space Weather
# ============================================================

plot_ds = dataset.copy()
plot_ds["date"] = pd.to_datetime(plot_ds["date"], utc=True)

# 1) F10.7 over time
plt.figure(figsize=(14, 5))
plt.plot(plot_ds["date"], plot_ds["f107_obs"], linewidth=0.8, alpha=0.5, label="F10.7 observed")
plt.plot(plot_ds["date"], plot_ds["f107_obs_rolling_27d"], linewidth=2, label="F10.7 27-day rolling avg")
plt.title("Solar Activity — F10.7 Solar Flux")
plt.xlabel("Date")
plt.ylabel("F10.7")
plt.legend()
plt.grid(True)
plt.show()

# 2) Ap over time
plt.figure(figsize=(14, 5))
plt.plot(plot_ds["date"], plot_ds["ap_avg"], linewidth=0.8, alpha=0.5, label="Ap avg")
plt.plot(plot_ds["date"], plot_ds["ap_avg_rolling_7d"], linewidth=2, label="Ap 7-day rolling avg")
plt.title("Geomagnetic Activity — Ap Index")
plt.xlabel("Date")
plt.ylabel("Ap")
plt.legend()
plt.grid(True)
plt.show()

# 3) Kp over time
plt.figure(figsize=(14, 5))
plt.plot(plot_ds["date"], plot_ds["kp_max"], linewidth=0.8, alpha=0.5, label="Daily max Kp")
plt.plot(plot_ds["date"], plot_ds["kp_max_rolling_7d"], linewidth=2, label="Kp max 7-day rolling avg")
plt.title("Geomagnetic Activity — Daily Max Kp")
plt.xlabel("Date")
plt.ylabel("Kp")
plt.legend()
plt.grid(True)
plt.show()

# 4) Decay vs solar activity
plt.figure(figsize=(14, 5))
plt.plot(plot_ds["date"], plot_ds["observed_decay_rolling_30d_km_day"], linewidth=2, label="Decay 30-day rolling avg [km/day]")
plt.plot(
    plot_ds["date"],
    plot_ds["f107_obs_rolling_27d"] / 1000.0,
    linewidth=2,
    label="F10.7 27-day rolling avg / 1000"
)
plt.title("Orbit Decay Trend vs Solar Flux Trend")
plt.xlabel("Date")
plt.ylabel("Scaled Values")
plt.legend()
plt.grid(True)
plt.show()

print("✅ Space weather visual checks completed.")

# %% colab={"base_uri": "https://localhost:8080/"} id="1Y8pk-gnUmqd" outputId="29415a7e-24e4-4f00-a0c2-c37b961aa9b9"
# ============================================================
# Cell 18 — Final Dataset Validation After Space Weather Merge
# ============================================================

final_validation = {}

final_validation["rows"] = int(len(dataset))
final_validation["columns"] = int(len(dataset.columns))
final_validation["date_min"] = str(dataset["date"].min())
final_validation["date_max"] = str(dataset["date"].max())
final_validation["duplicate_dates"] = int(dataset["date"].duplicated().sum())

key_cols_after_merge = [
    "altitude_mean_km",
    "mean_motion_rev_day",
    "bstar",
    "observed_decay_rolling_7d_km_day",
    "observed_decay_rolling_30d_km_day",
    "f107_obs",
    "f107_obs_rolling_7d",
    "f107_obs_rolling_27d",
    "kp_mean",
    "kp_max",
    "kp_max_rolling_7d",
    "ap_avg",
    "ap_avg_rolling_7d",
    "target_decay_next_7d_km",
    "target_decay_next_30d_km"
]

final_validation["missing_key_columns"] = {
    col: int(dataset[col].isna().sum()) if col in dataset.columns else "COLUMN_NOT_FOUND"
    for col in key_cols_after_merge
}

for horizon in PREDICTION_HORIZONS_DAYS:
    target_col = f"target_decay_next_{horizon}d_km"
    target_rate_col = f"target_decay_rate_next_{horizon}d_km_day"

    required_cols = [
        "altitude_mean_km",
        "mean_motion_rev_day",
        "bstar",
        "observed_decay_rolling_7d_km_day",
        "f107_obs",
        "f107_obs_rolling_7d",
        "kp_max",
        "ap_avg",
        target_col,
        target_rate_col
    ]

    existing_required_cols = [c for c in required_cols if c in dataset.columns]

    train_ready_rows = dataset.dropna(subset=existing_required_cols).shape[0]
    final_validation[f"{horizon}d_train_ready_rows_after_weather"] = int(train_ready_rows)

# Save report
final_validation_path = os.path.join(REPORTS_DIR, "03_final_dataset_validation_after_weather.json")

with open(final_validation_path, "w") as f:
    json.dump(final_validation, f, indent=4)

print("===== Final Dataset Validation After Weather Merge =====")
print(f"Rows: {final_validation['rows']}")
print(f"Columns: {final_validation['columns']}")
print(f"Date range: {final_validation['date_min']} → {final_validation['date_max']}")
print(f"Duplicate dates: {final_validation['duplicate_dates']}")

print("\nMissing key columns:")
for col, miss in final_validation["missing_key_columns"].items():
    print(f"{col}: {miss}")

print("\nTrain-ready rows:")
for horizon in PREDICTION_HORIZONS_DAYS:
    print(
        f"{horizon}d train-ready rows: "
        f"{final_validation[f'{horizon}d_train_ready_rows_after_weather']}"
    )

print(f"\n✅ Final validation saved to:\n{final_validation_path}")

# %% colab={"base_uri": "https://localhost:8080/"} id="hv-Jqh0yWz4Y" outputId="b4dd21d7-b50d-415f-929f-f5e22a2c9ef1"
# ============================================================
# Cell 19 — Load Final Dataset + Select Safe ML Features
# ============================================================

import joblib
from sklearn.base import clone
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import Ridge, BayesianRidge, HuberRegressor
from sklearn.ensemble import (
    ExtraTreesRegressor,
    RandomForestRegressor,
    GradientBoostingRegressor,
    HistGradientBoostingRegressor,
    VotingRegressor
)

final_dataset_path = os.path.join(PROCESSED_DIR, "04_daily_orbit_space_weather_uwe4.csv")

if "dataset" not in globals():
    if not os.path.exists(final_dataset_path):
        raise FileNotFoundError(f"❌ Final dataset not found: {final_dataset_path}")
    dataset = pd.read_csv(final_dataset_path)

ml_df = dataset.copy()
ml_df["date"] = pd.to_datetime(ml_df["date"], errors="coerce", utc=True)

print("===== Final Dataset Loaded =====")
print(f"Rows: {len(ml_df):,}")
print(f"Columns: {len(ml_df.columns)}")
print(f"Date range: {ml_df['date'].min()} → {ml_df['date'].max()}")

# -----------------------------
# Columns that must NEVER be used as input features
# -----------------------------
def is_forbidden_feature(col):
    col_lower = col.lower()

    forbidden_keywords = [
        "target_",          # future targets
        "after_7d",
        "after_30d",
        "next_7d",
        "next_30d",
        "tle_line",
        "object_name",
        "creation_date",
        "epoch",
        "comment",
        "originator",
        "center_name",
        "ref_frame",
        "time_system",
        "mean_element_theory",
        "classification_type",
        "country_code",
        "launch_date",
        "site",
        "decay_date",
        "file",
        "gp_id",
        "ccsds",
    ]

    if col_lower in ["date"]:
        return True

    return any(k in col_lower for k in forbidden_keywords)

# Keep only numeric safe features
candidate_features = []

for col in ml_df.columns:
    if is_forbidden_feature(col):
        continue

    if pd.api.types.ric_dtype(ml_df[col]):
        non_missing_count = ml_df[col].notna().sum()
        unique_count = ml_df[col].nunique(dropna=True)

        # remove all-missing and constant columns
        if non_missing_count > 0 and unique_count > 1:
            candidate_features.append(col)

print("\n===== Safe Feature Selection =====")
print(f"Candidate safe features: {len(candidate_features)}")
print(candidate_features)

# Save candidate feature list
candidate_features_path = os.path.join(MODELS_DIR, "candidate_feature_columns.json")
with open(candidate_features_path, "w") as f:
    json.dump(candidate_features, f, indent=4)

print(f"\n✅ Candidate feature columns saved to:\n{candidate_features_path}")


# %% colab={"base_uri": "https://localhost:8080/"} id="imTslwebW9U-" outputId="87813d21-4094-4a67-b6d1-f8ae43dc5cdd"
# ============================================================
# Cell 20 — Training Utilities + Baselines
# ============================================================

def calculate_metrics(y_true, y_pred, horizon_days):
    mae_km = mean_absolute_error(y_true, y_pred)
    rmse_km = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)

    return {
        "MAE_total_km": float(mae_km),
        "RMSE_total_km": float(rmse_km),
        "R2": float(r2),
        "MAE_km_day": float(mae_km / horizon_days),
        "RMSE_km_day": float(rmse_km / horizon_days),
        "MAE_m_day": float((mae_km / horizon_days) * 1000),
        "RMSE_m_day": float((rmse_km / horizon_days) * 1000),
    }


def print_metrics(title, metrics):
    print(f"\n===== {title} =====")
    print(f"MAE total: {metrics['MAE_total_km']:.6f} km")
    print(f"RMSE total: {metrics['RMSE_total_km']:.6f} km")
    print(f"MAE/day: {metrics['MAE_km_day']:.6f} km/day = {metrics['MAE_m_day']:.2f} m/day")
    print(f"RMSE/day: {metrics['RMSE_km_day']:.6f} km/day = {metrics['RMSE_m_day']:.2f} m/day")
    print(f"R²: {metrics['R2']:.6f}")


def make_time_split(df, target_col, feature_cols, horizon_days, val_days=365, test_days=365):
    required_cols = ["date", target_col] + feature_cols
    work = df.dropna(subset=required_cols).copy()
    work = work.sort_values("date").reset_index(drop=True)

    max_date = work["date"].max()

    test_start = max_date - pd.Timedelta(days=test_days - 1)
    val_start = test_start - pd.Timedelta(days=val_days)

    train_df = work[work["date"] < val_start].copy()
    val_df = work[(work["date"] >= val_start) & (work["date"] < test_start)].copy()
    test_df = work[work["date"] >= test_start].copy()

    print(f"\n===== Time Split for {horizon_days}d Target =====")
    print(f"Target: {target_col}")
    print(f"Available rows: {len(work):,}")
    print(f"Train: {len(train_df):,} | {train_df['date'].min()} → {train_df['date'].max()}")
    print(f"Val:   {len(val_df):,} | {val_df['date'].min()} → {val_df['date'].max()}")
    print(f"Test:  {len(test_df):,} | {test_df['date'].min()} → {test_df['date'].max()}")

    if len(train_df) < 500 or len(val_df) < 100 or len(test_df) < 100:
        raise ValueError("❌ Split produced too few rows. Adjust val_days/test_days.")

    return train_df, val_df, test_df


def build_candidate_models(random_state=42):
    models = {
        "Ridge": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", Ridge(alpha=1.0))
        ]),

        "BayesianRidge": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", BayesianRidge())
        ]),

        "HuberRegressor": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", HuberRegressor(max_iter=1000, epsilon=1.35))
        ]),

        "ExtraTrees": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", ExtraTreesRegressor(
                n_estimators=500,
                max_depth=None,
                min_samples_leaf=3,
                random_state=random_state,
                n_jobs=-1
            ))
        ]),

        "RandomForest": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", RandomForestRegressor(
                n_estimators=500,
                max_depth=None,
                min_samples_leaf=4,
                random_state=random_state,
                n_jobs=-1
            ))
        ]),

        "GradientBoosting": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", GradientBoostingRegressor(
                n_estimators=400,
                learning_rate=0.03,
                max_depth=3,
                min_samples_leaf=4,
                random_state=random_state
            ))
        ]),

        "HistGradientBoosting": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", HistGradientBoostingRegressor(
                max_iter=500,
                learning_rate=0.03,
                max_leaf_nodes=31,
                l2_regularization=0.05,
                random_state=random_state
            ))
        ])
    }

    return models


def evaluate_baselines(train_df, eval_df, target_col, horizon_days):
    y_true = eval_df[target_col].values

    baselines = {}

    # Baseline 1: last 7-day decay rate continues
    if "observed_decay_rolling_7d_km_day" in eval_df.columns:
        pred = eval_df["observed_decay_rolling_7d_km_day"].values * horizon_days
        baselines["baseline_recent_7d_rate"] = calculate_metrics(y_true, pred, horizon_days)

    # Baseline 2: last 30-day decay rate continues
    if "observed_decay_rolling_30d_km_day" in eval_df.columns:
        pred = eval_df["observed_decay_rolling_30d_km_day"].values * horizon_days
        baselines["baseline_recent_30d_rate"] = calculate_metrics(y_true, pred, horizon_days)

    # Baseline 3: median target from train
    median_target = train_df[target_col].median()
    pred = np.full_like(y_true, fill_value=median_target, dtype=float)
    baselines["baseline_train_median_target"] = calculate_metrics(y_true, pred, horizon_days)

    return baselines


print("✅ Training utilities ready.")

# %% colab={"base_uri": "https://localhost:8080/", "height": 1000} id="gkaE7EQEXFAJ" outputId="f36a4501-3be0-4859-e590-a8ad4cca308f"
# ============================================================
# Cell 21 — Train AI Models for 7-Day and 30-Day Orbit Decay
# ============================================================

trained_results = {}
all_prediction_frames = []

for horizon in PREDICTION_HORIZONS_DAYS:
    target_col = f"target_decay_next_{horizon}d_km"

    print("\n" + "="*80)
    print(f"🚀 Training models for {horizon}-day orbit decay prediction")
    print("="*80)

    train_df, val_df, test_df = make_time_split(
        df=ml_df,
        target_col=target_col,
        feature_cols=candidate_features,
        horizon_days=horizon,
        val_days=365,
        test_days=365
    )

    X_train = train_df[candidate_features]
    y_train = train_df[target_col].values

    X_val = val_df[candidate_features]
    y_val = val_df[target_col].values

    X_test = test_df[candidate_features]
    y_test = test_df[target_col].values

    # -----------------------------
    # Baselines
    # -----------------------------
    val_baselines = evaluate_baselines(train_df, val_df, target_col, horizon)
    test_baselines = evaluate_baselines(train_df, test_df, target_col, horizon)

    print("\n--- Validation Baselines ---")
    for name, metrics in val_baselines.items():
        print_metrics(name, metrics)

    print("\n--- Test Baselines ---")
    for name, metrics in test_baselines.items():
        print_metrics(name, metrics)

    # -----------------------------
    # Candidate AI models
    # -----------------------------
    candidate_models = build_candidate_models(random_state=42)

    leaderboard_rows = []
    fitted_train_models = {}
    val_predictions = {}

    for model_name, model in candidate_models.items():
        print(f"\nTraining {model_name}...")

        fitted_model = clone(model)
        fitted_model.fit(X_train, y_train)

        pred_val = fitted_model.predict(X_val)
        val_predictions[model_name] = pred_val

        val_metrics = calculate_metrics(y_val, pred_val, horizon)

        leaderboard_rows.append({
            "model_name": model_name,
            **val_metrics
        })

        fitted_train_models[model_name] = fitted_model

        print(f"{model_name} validation MAE/day: {val_metrics['MAE_m_day']:.2f} m/day | R²: {val_metrics['R2']:.4f}")

    leaderboard = pd.DataFrame(leaderboard_rows).sort_values("MAE_total_km").reset_index(drop=True)

    print("\n===== Validation Leaderboard =====")
    display(leaderboard)

    # -----------------------------
    # Weighted top-3 ensemble validation check
    # -----------------------------
    top3_names = leaderboard["model_name"].head(3).tolist()
    top3_mae = leaderboard["MAE_total_km"].head(3).values
    weights = 1.0 / np.maximum(top3_mae, 1e-9)
    weights = weights / weights.sum()

    ensemble_val_pred = np.zeros_like(y_val, dtype=float)
    for name, w in zip(top3_names, weights):
        ensemble_val_pred += w * val_predictions[name]

    ensemble_val_metrics = calculate_metrics(y_val, ensemble_val_pred, horizon)

    print_metrics(f"WeightedTop3Ensemble validation ({top3_names})", ensemble_val_metrics)

    best_individual_name = leaderboard.iloc[0]["model_name"]
    best_individual_val_mae = leaderboard.iloc[0]["MAE_total_km"]

    if ensemble_val_metrics["MAE_total_km"] < best_individual_val_mae:
        selected_model_name = "WeightedTop3Ensemble"
        selected_top3_names = top3_names
        selected_weights = weights.tolist()
        print(f"\n✅ Selected model: WeightedTop3Ensemble")
        print("Top models:", selected_top3_names)
        print("Weights:", selected_weights)
    else:
        selected_model_name = best_individual_name
        selected_top3_names = []
        selected_weights = []
        print(f"\n✅ Selected model: {selected_model_name}")

    # -----------------------------
    # Retrain selected model on train + validation
    # Then evaluate on untouched test
    # -----------------------------
    train_val_df = pd.concat([train_df, val_df], axis=0).sort_values("date").reset_index(drop=True)
    X_train_val = train_val_df[candidate_features]
    y_train_val = train_val_df[target_col].values

    if selected_model_name == "WeightedTop3Ensemble":
        estimators = []
        for name in selected_top3_names:
            estimators.append((name, clone(candidate_models[name])))

        final_model = VotingRegressor(
            estimators=estimators,
            weights=selected_weights,
            n_jobs=-1
        )
    else:
        final_model = clone(candidate_models[selected_model_name])

    final_model.fit(X_train_val, y_train_val)

    pred_test = final_model.predict(X_test)
    test_metrics = calculate_metrics(y_test, pred_test, horizon)

    print_metrics(f"FINAL SELECTED MODEL TEST — {selected_model_name} — {horizon}d", test_metrics)

    # Compare against best baseline on test
    best_baseline_name = min(test_baselines, key=lambda k: test_baselines[k]["MAE_total_km"])
    best_baseline_metrics = test_baselines[best_baseline_name]

    improvement_pct = (
        (best_baseline_metrics["MAE_total_km"] - test_metrics["MAE_total_km"])
        / best_baseline_metrics["MAE_total_km"]
    ) * 100

    print(f"\n===== Improvement vs Best Baseline =====")
    print(f"Best baseline: {best_baseline_name}")
    print(f"Best baseline MAE/day: {best_baseline_metrics['MAE_m_day']:.2f} m/day")
    print(f"AI model MAE/day: {test_metrics['MAE_m_day']:.2f} m/day")
    print(f"Improvement: {improvement_pct:.2f}%")

    # Save prediction frame
    pred_frame = test_df[[
        "date",
        "altitude_mean_km",
        "observed_decay_rolling_7d_km_day",
        "observed_decay_rolling_30d_km_day",
        target_col
    ]].copy()

    pred_frame["horizon_days"] = horizon
    pred_frame["selected_model"] = selected_model_name
    pred_frame["actual_decay_km"] = y_test
    pred_frame["predicted_decay_km"] = pred_test
    pred_frame["actual_decay_rate_km_day"] = pred_frame["actual_decay_km"] / horizon
    pred_frame["predicted_decay_rate_km_day"] = pred_frame["predicted_decay_km"] / horizon
    pred_frame["prediction_error_km"] = pred_frame["predicted_decay_km"] - pred_frame["actual_decay_km"]
    pred_frame["prediction_abs_error_km"] = pred_frame["prediction_error_km"].abs()

    all_prediction_frames.append(pred_frame)

    trained_results[horizon] = {
        "horizon_days": horizon,
        "target_col": target_col,
        "feature_columns": candidate_features,
        "selected_model_name": selected_model_name,
        "selected_top3_names": selected_top3_names,
        "selected_weights": selected_weights,
        "final_model": final_model,
        "validation_leaderboard": leaderboard,
        "validation_ensemble_metrics": ensemble_val_metrics,
        "test_metrics": test_metrics,
        "test_baselines": test_baselines,
        "best_baseline_name": best_baseline_name,
        "best_baseline_metrics": best_baseline_metrics,
        "improvement_vs_best_baseline_pct": float(improvement_pct),
        "train_rows": int(len(train_df)),
        "val_rows": int(len(val_df)),
        "test_rows": int(len(test_df)),
        "train_start": str(train_df["date"].min()),
        "train_end": str(train_df["date"].max()),
        "val_start": str(val_df["date"].min()),
        "val_end": str(val_df["date"].max()),
        "test_start": str(test_df["date"].min()),
        "test_end": str(test_df["date"].max()),
    }

predictions_df = pd.concat(all_prediction_frames, axis=0).reset_index(drop=True)

predictions_path = os.path.join(REPORTS_DIR, "04_test_predictions_7d_30d.csv")
predictions_df.to_csv(predictions_path, index=False)

print("\n✅ Training completed for all horizons.")
print(f"✅ Test predictions saved to:\n{predictions_path}")

# %% colab={"base_uri": "https://localhost:8080/", "height": 1000} id="QOITrxoNXNmF" outputId="93d873a4-56e4-404b-f13f-48fe782e1708"
# ============================================================
# Cell 22 — Actual vs Predicted Plots
# ============================================================

for horizon in PREDICTION_HORIZONS_DAYS:
    p = predictions_df[predictions_df["horizon_days"] == horizon].copy()
    p["date"] = pd.to_datetime(p["date"], utc=True)

    model_name = p["selected_model"].iloc[0]

    # Time-series plot
    plt.figure(figsize=(14, 5))
    plt.plot(p["date"], p["actual_decay_km"], linewidth=2, label="Actual decay")
    plt.plot(p["date"], p["predicted_decay_km"], linewidth=2, label="Predicted decay")
    plt.title(f"UWE-4 {horizon}-Day Orbit Decay Prediction — Test Set — {model_name}")
    plt.xlabel("Date")
    plt.ylabel(f"Decay over next {horizon} days [km]")
    plt.legend()
    plt.grid(True)
    plt.show()

    # Scatter plot
    plt.figure(figsize=(6, 6))
    plt.scatter(p["actual_decay_km"], p["predicted_decay_km"], alpha=0.7)
    min_val = min(p["actual_decay_km"].min(), p["predicted_decay_km"].min())
    max_val = max(p["actual_decay_km"].max(), p["predicted_decay_km"].max())
    plt.plot([min_val, max_val], [min_val, max_val], linewidth=2)
    plt.title(f"Actual vs Predicted — {horizon}d Decay")
    plt.xlabel("Actual decay [km]")
    plt.ylabel("Predicted decay [km]")
    plt.grid(True)
    plt.show()

    # Error over time
    plt.figure(figsize=(14, 5))
    plt.plot(p["date"], p["prediction_error_km"], linewidth=1.5)
    plt.axhline(0, linewidth=1)
    plt.title(f"Prediction Error Over Time — {horizon}d")
    plt.xlabel("Date")
    plt.ylabel("Prediction error [km]")
    plt.grid(True)
    plt.show()

print("✅ Prediction plots completed.")

# %% colab={"base_uri": "https://localhost:8080/"} id="MKDJG15tYexG" outputId="bcc53435-8f9c-422b-b4ac-0b7a905918ea"
# ============================================================
# Cell 23 — Save Final Models and Metadata for FastAPI
# ============================================================

exported_metrics = {}

for horizon, result in trained_results.items():
    model_filename = f"uwe4_orbit_decay_model_{horizon}d.pkl"
    feature_filename = f"uwe4_feature_columns_{horizon}d.json"
    metrics_filename = f"uwe4_model_metrics_{horizon}d.json"

    model_path = os.path.join(MODELS_DIR, model_filename)
    feature_path = os.path.join(MODELS_DIR, feature_filename)
    metrics_path = os.path.join(MODELS_DIR, metrics_filename)

    # Save model
    joblib.dump(result["final_model"], model_path)

    # Save feature columns
    with open(feature_path, "w") as f:
        json.dump(result["feature_columns"], f, indent=4)

    # Save metrics without model object
    metrics_export = {
        "satellite": SATELLITE_NAME,
        "norad_id": NORAD_ID,
        "horizon_days": horizon,
        "target_col": result["target_col"],
        "selected_model_name": result["selected_model_name"],
        "selected_top3_names": result["selected_top3_names"],
        "selected_weights": result["selected_weights"],
        "test_metrics": result["test_metrics"],
        "test_baselines": result["test_baselines"],
        "best_baseline_name": result["best_baseline_name"],
        "best_baseline_metrics": result["best_baseline_metrics"],
        "improvement_vs_best_baseline_pct": result["improvement_vs_best_baseline_pct"],
        "train_rows": result["train_rows"],
        "val_rows": result["val_rows"],
        "test_rows": result["test_rows"],
        "train_start": result["train_start"],
        "train_end": result["train_end"],
        "val_start": result["val_start"],
        "val_end": result["val_end"],
        "test_start": result["test_start"],
        "test_end": result["test_end"],
        "feature_count": len(result["feature_columns"]),
        "created_at_utc": datetime.now(timezone.utc).isoformat()
    }

    with open(metrics_path, "w") as f:
        json.dump(metrics_export, f, indent=4)

    exported_metrics[horizon] = metrics_export

    print(f"\n✅ Saved {horizon}d model:")
    print(f"Model:   {model_path}")
    print(f"Features:{feature_path}")
    print(f"Metrics: {metrics_path}")

summary_metrics_path = os.path.join(REPORTS_DIR, "05_training_summary_metrics.json")

with open(summary_metrics_path, "w") as f:
    json.dump(exported_metrics, f, indent=4)

print(f"\n✅ Summary metrics saved to:\n{summary_metrics_path}")

# %% colab={"base_uri": "https://localhost:8080/", "height": 167} id="JkxTjQRsYinc" outputId="2e97e89b-3ccc-41be-c81c-5abb10d787dd"
# ============================================================
# Cell 24 — Final Training Summary Table
# ============================================================

summary_rows = []

for horizon, result in trained_results.items():
    test_metrics = result["test_metrics"]
    baseline_metrics = result["best_baseline_metrics"]

    summary_rows.append({
        "horizon_days": horizon,
        "selected_model": result["selected_model_name"],
        "AI_MAE_m_day": test_metrics["MAE_m_day"],
        "AI_RMSE_m_day": test_metrics["RMSE_m_day"],
        "AI_R2": test_metrics["R2"],
        "best_baseline": result["best_baseline_name"],
        "baseline_MAE_m_day": baseline_metrics["MAE_m_day"],
        "improvement_%": result["improvement_vs_best_baseline_pct"],
        "train_rows": result["train_rows"],
        "val_rows": result["val_rows"],
        "test_rows": result["test_rows"],
    })

summary_table = pd.DataFrame(summary_rows)
display(summary_table)

summary_table_path = os.path.join(REPORTS_DIR, "06_final_training_summary_table.csv")
summary_table.to_csv(summary_table_path, index=False)

print(f"✅ Final summary table saved to:\n{summary_table_path}")

# %% colab={"base_uri": "https://localhost:8080/"} id="dabmLQvSa04o" outputId="665d7327-19a6-49a0-896c-0abc3c699c0d"
# ============================================================
# Cell 25 — Build Clean Feature Set for V2 Residual Model
# ============================================================

from sklearn.base import clone
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import Ridge, BayesianRidge, HuberRegressor, ElasticNet
from sklearn.ensemble import (
    RandomForestRegressor,
    ExtraTreesRegressor,
    GradientBoostingRegressor,
    HistGradientBoostingRegressor,
    VotingRegressor
)
import joblib

final_dataset_path = os.path.join(PROCESSED_DIR, "04_daily_orbit_space_weather_uwe4.csv")

if "dataset" not in globals():
    dataset = pd.read_csv(final_dataset_path)

v2_df = dataset.copy()
v2_df["date"] = pd.to_datetime(v2_df["date"], errors="coerce", utc=True)

print("===== V2 Dataset Loaded =====")
print(f"Rows: {len(v2_df):,}")
print(f"Columns: {len(v2_df.columns)}")
print(f"Date range: {v2_df['date'].min()} → {v2_df['date'].max()}")

# ------------------------------------------------------------
# Curated physics-informed features
# نختار features واضحة ومفيدة بدل ما نرمي كل الأعمدة
# ------------------------------------------------------------

curated_features = [
    # Current orbital state
    "altitude_mean_km",
    "perigee_altitude_km",
    "apogee_altitude_km",
    "semi_major_axis_km",
    "mean_motion_rev_day",
    "mean_motion_dot",
    "eccentricity",
    "inclination_deg",
    "bstar",

    # Recent orbit decay behavior
    "observed_decay_km_day",
    "observed_decay_rolling_3d_km_day",
    "observed_decay_rolling_7d_km_day",
    "observed_decay_rolling_14d_km_day",
    "observed_decay_rolling_30d_km_day",

    # Altitude rolling behavior
    "altitude_rolling_3d_km",
    "altitude_rolling_7d_km",
    "altitude_rolling_14d_km",
    "altitude_rolling_30d_km",

    # BSTAR behavior
    "bstar_rolling_3d",
    "bstar_rolling_7d",
    "bstar_rolling_14d",
    "bstar_rolling_30d",
    "bstar_lag_1d",
    "bstar_lag_3d",
    "bstar_lag_7d",
    "bstar_lag_14d",
    "bstar_lag_30d",

    # Orbit lags
    "altitude_lag_1d_km",
    "altitude_lag_3d_km",
    "altitude_lag_7d_km",
    "altitude_lag_14d_km",
    "altitude_lag_30d_km",
    "mean_motion_lag_1d",
    "mean_motion_lag_3d",
    "mean_motion_lag_7d",
    "mean_motion_lag_14d",
    "mean_motion_lag_30d",
    "decay_lag_1d_km_day",
    "decay_lag_3d_km_day",
    "decay_lag_7d_km_day",
    "decay_lag_14d_km_day",
    "decay_lag_30d_km_day",

    # Space weather current
    "f107_obs",
    "f107_adj",
    "sunspot_number",
    "kp_mean",
    "kp_max",
    "ap_avg",
    "ap_max",

    # Solar rolling
    "f107_obs_rolling_3d",
    "f107_obs_rolling_7d",
    "f107_obs_rolling_14d",
    "f107_obs_rolling_27d",
    "f107_obs_rolling_81d",
    "f107_adj_rolling_7d",
    "f107_adj_rolling_27d",
    "f107_adj_rolling_81d",
    "sunspot_number_rolling_7d",
    "sunspot_number_rolling_27d",
    "sunspot_number_rolling_81d",

    # Geomagnetic rolling
    "kp_mean_rolling_3d",
    "kp_mean_rolling_7d",
    "kp_mean_rolling_14d",
    "kp_max_rolling_3d",
    "kp_max_rolling_7d",
    "kp_max_rolling_14d",
    "ap_avg_rolling_3d",
    "ap_avg_rolling_7d",
    "ap_avg_rolling_14d",
    "ap_max_rolling_3d",
    "ap_max_rolling_7d",
    "ap_max_rolling_14d",

    # Weather lags
    "f107_obs_lag_1d",
    "f107_obs_lag_3d",
    "f107_obs_lag_7d",
    "f107_obs_lag_14d",
    "f107_obs_lag_27d",
    "kp_max_lag_1d",
    "kp_max_lag_3d",
    "kp_max_lag_7d",
    "kp_max_lag_14d",
    "ap_avg_lag_1d",
    "ap_avg_lag_3d",
    "ap_avg_lag_7d",
    "ap_avg_lag_14d",

    # Flags and constants
    "had_tle_that_day",
    "interpolated_day_flag",
    "bstar_outlier_flag",
    "geomagnetic_active_flag",
    "high_solar_flux_flag",
    "weather_interpolated_flag",
    "mass_kg",
    "area_m2",
    "drag_coefficient",
    "ballistic_coefficient",

    # Time features
    "month",
    "day_of_year",
    "days_since_start"
]

# Keep only existing numeric columns
v2_feature_cols = []
missing_curated = []

for col in curated_features:
    if col in v2_df.columns and pd.api.types.is_numeric_dtype(v2_df[col]):
        if v2_df[col].nunique(dropna=True) > 1:
            v2_feature_cols.append(col)
    else:
        missing_curated.append(col)

print("\n===== V2 Curated Feature Selection =====")
print(f"Selected V2 features: {len(v2_feature_cols)}")
print(f"Missing/skipped curated features: {len(missing_curated)}")

print("\nSelected features:")
print(v2_feature_cols)

v2_features_path = os.path.join(MODELS_DIR, "uwe4_v2_curated_feature_columns_base.json")
with open(v2_features_path, "w") as f:
    json.dump(v2_feature_cols, f, indent=4)

print(f"\n✅ V2 base feature list saved to:\n{v2_features_path}")


# %% colab={"base_uri": "https://localhost:8080/"} id="NXPOKeYJa3m0" outputId="a5ca3a06-af20-42e4-8177-08b8d07e983c"
# ============================================================
# Cell 26 — Residual Training Utilities
# ============================================================

def calculate_metrics_v2(y_true, y_pred, horizon_days):
    mae_km = mean_absolute_error(y_true, y_pred)
    rmse_km = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)

    return {
        "MAE_total_km": float(mae_km),
        "RMSE_total_km": float(rmse_km),
        "R2": float(r2),
        "MAE_km_day": float(mae_km / horizon_days),
        "RMSE_km_day": float(rmse_km / horizon_days),
        "MAE_m_day": float((mae_km / horizon_days) * 1000),
        "RMSE_m_day": float((rmse_km / horizon_days) * 1000),
    }


def print_metrics_v2(title, metrics):
    print(f"\n===== {title} =====")
    print(f"MAE total: {metrics['MAE_total_km']:.6f} km")
    print(f"RMSE total: {metrics['RMSE_total_km']:.6f} km")
    print(f"MAE/day: {metrics['MAE_km_day']:.6f} km/day = {metrics['MAE_m_day']:.2f} m/day")
    print(f"RMSE/day: {metrics['RMSE_km_day']:.6f} km/day = {metrics['RMSE_m_day']:.2f} m/day")
    print(f"R²: {metrics['R2']:.6f}")


def make_v2_time_split(df, target_col, feature_cols, horizon_days, val_days=365, test_days=365):
    required_cols = ["date", target_col, "observed_decay_rolling_30d_km_day"] + feature_cols
    work = df.dropna(subset=required_cols).copy()
    work = work.sort_values("date").reset_index(drop=True)

    # Baseline prediction: recent 30-day decay rate persists
    work[f"baseline_30d_prediction_{horizon_days}d_km"] = (
        work["observed_decay_rolling_30d_km_day"] * horizon_days
    )

    # Residual target
    work[f"residual_target_{horizon_days}d_km"] = (
        work[target_col] - work[f"baseline_30d_prediction_{horizon_days}d_km"]
    )

    # Add baseline prediction as a model feature
    final_feature_cols = feature_cols + [f"baseline_30d_prediction_{horizon_days}d_km"]

    max_date = work["date"].max()
    test_start = max_date - pd.Timedelta(days=test_days - 1)
    val_start = test_start - pd.Timedelta(days=val_days)

    train_df = work[work["date"] < val_start].copy()
    val_df = work[(work["date"] >= val_start) & (work["date"] < test_start)].copy()
    test_df = work[work["date"] >= test_start].copy()

    print(f"\n===== V2 Time Split for {horizon_days}d Residual Target =====")
    print(f"Target: {target_col}")
    print(f"Residual target: residual_target_{horizon_days}d_km")
    print(f"Available rows: {len(work):,}")
    print(f"Train: {len(train_df):,} | {train_df['date'].min()} → {train_df['date'].max()}")
    print(f"Val:   {len(val_df):,} | {val_df['date'].min()} → {val_df['date'].max()}")
    print(f"Test:  {len(test_df):,} | {test_df['date'].min()} → {test_df['date'].max()}")

    return train_df, val_df, test_df, final_feature_cols


def build_v2_residual_models(random_state=42):
    models = {
        "Ridge_residual": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", Ridge(alpha=0.5))
        ]),

        "BayesianRidge_residual": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", BayesianRidge())
        ]),

        "Huber_residual": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", HuberRegressor(max_iter=2000, epsilon=1.25))
        ]),

        "ElasticNet_residual": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", ElasticNet(alpha=0.0005, l1_ratio=0.15, max_iter=5000, random_state=random_state))
        ]),

        "GradientBoosting_residual": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", GradientBoostingRegressor(
                n_estimators=300,
                learning_rate=0.025,
                max_depth=2,
                min_samples_leaf=8,
                subsample=0.85,
                random_state=random_state
            ))
        ]),

        "HistGradientBoosting_residual": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", HistGradientBoostingRegressor(
                max_iter=350,
                learning_rate=0.025,
                max_leaf_nodes=15,
                min_samples_leaf=12,
                l2_regularization=0.2,
                random_state=random_state
            ))
        ]),

        "ExtraTrees_residual": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", ExtraTreesRegressor(
                n_estimators=400,
                max_depth=10,
                min_samples_leaf=8,
                random_state=random_state,
                n_jobs=-1
            ))
        ])
    }

    return models


print("✅ V2 residual utilities ready.")

# %% colab={"base_uri": "https://localhost:8080/", "height": 1000} id="WOJl9CEVa52x" outputId="eff4ff73-2dd6-49b9-af64-1d31e6be3748"
# ============================================================
# Cell 27 — Train V2 Residual Models
# ============================================================

v2_results = {}
v2_prediction_frames = []

for horizon in PREDICTION_HORIZONS_DAYS:
    target_col = f"target_decay_next_{horizon}d_km"
    baseline_col = f"baseline_30d_prediction_{horizon}d_km"
    residual_col = f"residual_target_{horizon}d_km"

    print("\n" + "="*90)
    print(f"🚀 V2 Residual Training for {horizon}-day Orbit Decay Prediction")
    print("="*90)

    train_df, val_df, test_df, final_v2_features = make_v2_time_split(
        df=v2_df,
        target_col=target_col,
        feature_cols=v2_feature_cols,
        horizon_days=horizon,
        val_days=365,
        test_days=365
    )

    X_train = train_df[final_v2_features]
    y_train_residual = train_df[residual_col].values

    X_val = val_df[final_v2_features]
    y_val_actual = val_df[target_col].values
    y_val_baseline = val_df[baseline_col].values
    y_val_residual = val_df[residual_col].values

    X_test = test_df[final_v2_features]
    y_test_actual = test_df[target_col].values
    y_test_baseline = test_df[baseline_col].values
    y_test_residual = test_df[residual_col].values

    # Baseline metrics
    val_baseline_metrics = calculate_metrics_v2(y_val_actual, y_val_baseline, horizon)
    test_baseline_metrics = calculate_metrics_v2(y_test_actual, y_test_baseline, horizon)

    print_metrics_v2(f"V2 Baseline only validation — {horizon}d", val_baseline_metrics)
    print_metrics_v2(f"V2 Baseline only test — {horizon}d", test_baseline_metrics)

    residual_models = build_v2_residual_models(random_state=42)

    leaderboard_rows = []
    fitted_models = {}
    val_final_predictions = {}

    for model_name, model in residual_models.items():
        print(f"\nTraining {model_name}...")

        fitted_model = clone(model)
        fitted_model.fit(X_train, y_train_residual)

        pred_val_residual = fitted_model.predict(X_val)

        # Optional safety clipping:
        # نخلي تصحيح الموديل داخل حدود منطقية من residuals التدريب
        residual_low = np.quantile(y_train_residual, 0.01)
        residual_high = np.quantile(y_train_residual, 0.99)
        pred_val_residual_clipped = np.clip(pred_val_residual, residual_low, residual_high)

        pred_val_final = y_val_baseline + pred_val_residual_clipped
        val_final_predictions[model_name] = pred_val_final

        val_metrics = calculate_metrics_v2(y_val_actual, pred_val_final, horizon)

        leaderboard_rows.append({
            "model_name": model_name,
            **val_metrics
        })

        fitted_models[model_name] = fitted_model

        print(
            f"{model_name} validation MAE/day: "
            f"{val_metrics['MAE_m_day']:.2f} m/day | R²: {val_metrics['R2']:.4f}"
        )

    v2_leaderboard = pd.DataFrame(leaderboard_rows).sort_values("MAE_total_km").reset_index(drop=True)

    print("\n===== V2 Validation Leaderboard =====")
    display(v2_leaderboard)

    # Weighted top-3 ensemble for residual correction
    top3_names = v2_leaderboard["model_name"].head(3).tolist()
    top3_mae = v2_leaderboard["MAE_total_km"].head(3).values

    weights = 1.0 / np.maximum(top3_mae, 1e-9)
    weights = weights / weights.sum()

    ensemble_val_pred = np.zeros_like(y_val_actual, dtype=float)
    for name, w in zip(top3_names, weights):
        ensemble_val_pred += w * val_final_predictions[name]

    ensemble_val_metrics = calculate_metrics_v2(y_val_actual, ensemble_val_pred, horizon)
    print_metrics_v2(f"V2 WeightedTop3 validation {top3_names}", ensemble_val_metrics)

    best_name = v2_leaderboard.iloc[0]["model_name"]
    best_mae = v2_leaderboard.iloc[0]["MAE_total_km"]

    if ensemble_val_metrics["MAE_total_km"] < best_mae:
        selected_v2_name = "V2_WeightedTop3Residual"
        selected_top3_names = top3_names
        selected_weights = weights.tolist()
    else:
        selected_v2_name = best_name
        selected_top3_names = []
        selected_weights = []

    print(f"\n✅ V2 selected model for {horizon}d: {selected_v2_name}")
    if selected_top3_names:
        print("Top3:", selected_top3_names)
        print("Weights:", selected_weights)

    # Retrain selected model on train + validation residuals
    train_val_df = pd.concat([train_df, val_df], axis=0).sort_values("date").reset_index(drop=True)

    X_train_val = train_val_df[final_v2_features]
    y_train_val_residual = train_val_df[residual_col].values

    # clipping limits from train+val residuals
    residual_clip_low = float(np.quantile(y_train_val_residual, 0.01))
    residual_clip_high = float(np.quantile(y_train_val_residual, 0.99))

    if selected_v2_name == "V2_WeightedTop3Residual":
        estimators = []
        for name in selected_top3_names:
            estimators.append((name, clone(residual_models[name])))

        final_v2_model = VotingRegressor(
            estimators=estimators,
            weights=selected_weights,
            n_jobs=-1
        )
    else:
        final_v2_model = clone(residual_models[selected_v2_name])

    final_v2_model.fit(X_train_val, y_train_val_residual)

    pred_test_residual = final_v2_model.predict(X_test)
    pred_test_residual_clipped = np.clip(pred_test_residual, residual_clip_low, residual_clip_high)

    pred_test_final = y_test_baseline + pred_test_residual_clipped

    v2_test_metrics = calculate_metrics_v2(y_test_actual, pred_test_final, horizon)

    print_metrics_v2(f"FINAL V2 TEST — {selected_v2_name} — {horizon}d", v2_test_metrics)

    improvement_vs_baseline = (
        (test_baseline_metrics["MAE_total_km"] - v2_test_metrics["MAE_total_km"])
        / test_baseline_metrics["MAE_total_km"]
    ) * 100

    print("\n===== V2 Improvement vs Baseline =====")
    print(f"Baseline MAE/day: {test_baseline_metrics['MAE_m_day']:.2f} m/day")
    print(f"V2 MAE/day: {v2_test_metrics['MAE_m_day']:.2f} m/day")
    print(f"Improvement: {improvement_vs_baseline:.2f}%")

    # Compare with old V1 if available
    v1_metrics = None
    if "trained_results" in globals() and horizon in trained_results:
        v1_metrics = trained_results[horizon]["test_metrics"]
        improvement_vs_v1 = (
            (v1_metrics["MAE_total_km"] - v2_test_metrics["MAE_total_km"])
            / v1_metrics["MAE_total_km"]
        ) * 100

        print("\n===== V2 Improvement vs V1 Direct Model =====")
        print(f"V1 MAE/day: {v1_metrics['MAE_m_day']:.2f} m/day")
        print(f"V2 MAE/day: {v2_test_metrics['MAE_m_day']:.2f} m/day")
        print(f"Improvement vs V1: {improvement_vs_v1:.2f}%")
    else:
        improvement_vs_v1 = None

    # Save predictions
    v2_pred_frame = test_df[[
        "date",
        "altitude_mean_km",
        "observed_decay_rolling_7d_km_day",
        "observed_decay_rolling_30d_km_day",
        target_col,
        baseline_col,
        residual_col
    ]].copy()

    v2_pred_frame["horizon_days"] = horizon
    v2_pred_frame["selected_v2_model"] = selected_v2_name
    v2_pred_frame["actual_decay_km"] = y_test_actual
    v2_pred_frame["baseline_prediction_km"] = y_test_baseline
    v2_pred_frame["predicted_residual_km"] = pred_test_residual_clipped
    v2_pred_frame["v2_predicted_decay_km"] = pred_test_final
    v2_pred_frame["v2_prediction_error_km"] = pred_test_final - y_test_actual
    v2_pred_frame["v2_abs_error_km"] = np.abs(v2_pred_frame["v2_prediction_error_km"])

    v2_prediction_frames.append(v2_pred_frame)

    v2_results[horizon] = {
        "horizon_days": horizon,
        "target_col": target_col,
        "baseline_col": baseline_col,
        "residual_col": residual_col,
        "feature_columns": final_v2_features,
        "selected_model_name": selected_v2_name,
        "selected_top3_names": selected_top3_names,
        "selected_weights": selected_weights,
        "final_model": final_v2_model,
        "residual_clip_low": residual_clip_low,
        "residual_clip_high": residual_clip_high,
        "validation_leaderboard": v2_leaderboard,
        "test_metrics": v2_test_metrics,
        "baseline_test_metrics": test_baseline_metrics,
        "improvement_vs_baseline_pct": float(improvement_vs_baseline),
        "v1_test_metrics": v1_metrics,
        "improvement_vs_v1_pct": None if improvement_vs_v1 is None else float(improvement_vs_v1),
        "train_rows": int(len(train_df)),
        "val_rows": int(len(val_df)),
        "test_rows": int(len(test_df)),
        "train_start": str(train_df["date"].min()),
        "train_end": str(train_df["date"].max()),
        "val_start": str(val_df["date"].min()),
        "val_end": str(val_df["date"].max()),
        "test_start": str(test_df["date"].min()),
        "test_end": str(test_df["date"].max()),
    }

v2_predictions_df = pd.concat(v2_prediction_frames, axis=0).reset_index(drop=True)

v2_predictions_path = os.path.join(REPORTS_DIR, "07_v2_residual_test_predictions.csv")
v2_predictions_df.to_csv(v2_predictions_path, index=False)

print("\n✅ V2 residual training completed.")
print(f"✅ V2 predictions saved to:\n{v2_predictions_path}")

# %% colab={"base_uri": "https://localhost:8080/", "height": 1000} id="1dRkoBf-a8i-" outputId="92b0b491-0a44-4595-8d3f-d88dd08d7e67"
# ============================================================
# Cell 28 — V2 Plots: Baseline vs AI Residual Model
# ============================================================

for horizon in PREDICTION_HORIZONS_DAYS:
    p = v2_predictions_df[v2_predictions_df["horizon_days"] == horizon].copy()
    p["date"] = pd.to_datetime(p["date"], utc=True)

    model_name = p["selected_v2_model"].iloc[0]

    # 1) Actual vs baseline vs V2 prediction
    plt.figure(figsize=(14, 5))
    plt.plot(p["date"], p["actual_decay_km"], linewidth=2, label="Actual decay")
    plt.plot(p["date"], p["baseline_prediction_km"], linewidth=1.5, label="Baseline prediction")
    plt.plot(p["date"], p["v2_predicted_decay_km"], linewidth=2, label="V2 residual AI prediction")
    plt.title(f"UWE-4 {horizon}-Day Orbit Decay — Baseline vs V2 AI — {model_name}")
    plt.xlabel("Date")
    plt.ylabel(f"Decay over next {horizon} days [km]")
    plt.legend()
    plt.grid(True)
    plt.show()

    # 2) Actual vs predicted scatter
    plt.figure(figsize=(6, 6))
    plt.scatter(p["actual_decay_km"], p["v2_predicted_decay_km"], alpha=0.7)
    min_val = min(p["actual_decay_km"].min(), p["v2_predicted_decay_km"].min())
    max_val = max(p["actual_decay_km"].max(), p["v2_predicted_decay_km"].max())
    plt.plot([min_val, max_val], [min_val, max_val], linewidth=2)
    plt.title(f"V2 Actual vs Predicted — {horizon}d Decay")
    plt.xlabel("Actual decay [km]")
    plt.ylabel("V2 predicted decay [km]")
    plt.grid(True)
    plt.show()

    # 3) Error over time
    plt.figure(figsize=(14, 5))
    plt.plot(p["date"], p["v2_prediction_error_km"], linewidth=1.5)
    plt.axhline(0, linewidth=1)
    plt.title(f"V2 Prediction Error Over Time — {horizon}d")
    plt.xlabel("Date")
    plt.ylabel("Prediction error [km]")
    plt.grid(True)
    plt.show()

print("✅ V2 plots completed.")

# %% colab={"base_uri": "https://localhost:8080/"} id="dGpRr0kea_JN" outputId="9b93d2b3-d5e2-407c-f959-cc9d84417f7c"
# ============================================================
# Cell 29 — Save V2 Models and Metadata for FastAPI
# ============================================================

v2_exported_metrics = {}

for horizon, result in v2_results.items():
    model_filename = f"uwe4_v2_residual_model_{horizon}d.pkl"
    feature_filename = f"uwe4_v2_feature_columns_{horizon}d.json"
    metrics_filename = f"uwe4_v2_model_metrics_{horizon}d.json"

    model_path = os.path.join(MODELS_DIR, model_filename)
    feature_path = os.path.join(MODELS_DIR, feature_filename)
    metrics_path = os.path.join(MODELS_DIR, metrics_filename)

    # Save model
    joblib.dump(result["final_model"], model_path)

    # Save features
    with open(feature_path, "w") as f:
        json.dump(result["feature_columns"], f, indent=4)

    # Save metrics and residual metadata
    metrics_export = {
        "satellite": SATELLITE_NAME,
        "norad_id": NORAD_ID,
        "model_version": "V2_residual_baseline_correction",
        "horizon_days": horizon,
        "target_col": result["target_col"],
        "baseline_col": result["baseline_col"],
        "residual_col": result["residual_col"],
        "selected_model_name": result["selected_model_name"],
        "selected_top3_names": result["selected_top3_names"],
        "selected_weights": result["selected_weights"],
        "residual_clip_low": result["residual_clip_low"],
        "residual_clip_high": result["residual_clip_high"],
        "test_metrics": result["test_metrics"],
        "baseline_test_metrics": result["baseline_test_metrics"],
        "improvement_vs_baseline_pct": result["improvement_vs_baseline_pct"],
        "v1_test_metrics": result["v1_test_metrics"],
        "improvement_vs_v1_pct": result["improvement_vs_v1_pct"],
        "train_rows": result["train_rows"],
        "val_rows": result["val_rows"],
        "test_rows": result["test_rows"],
        "train_start": result["train_start"],
        "train_end": result["train_end"],
        "val_start": result["val_start"],
        "val_end": result["val_end"],
        "test_start": result["test_start"],
        "test_end": result["test_end"],
        "feature_count": len(result["feature_columns"]),
        "created_at_utc": datetime.now(timezone.utc).isoformat()
    }

    with open(metrics_path, "w") as f:
        json.dump(metrics_export, f, indent=4)

    v2_exported_metrics[horizon] = metrics_export

    print(f"\n✅ Saved V2 {horizon}d model:")
    print(f"Model:    {model_path}")
    print(f"Features: {feature_path}")
    print(f"Metrics:  {metrics_path}")

v2_summary_metrics_path = os.path.join(REPORTS_DIR, "08_v2_training_summary_metrics.json")

with open(v2_summary_metrics_path, "w") as f:
    json.dump(v2_exported_metrics, f, indent=4)

print(f"\n✅ V2 summary metrics saved to:\n{v2_summary_metrics_path}")

# %% colab={"base_uri": "https://localhost:8080/", "height": 167} id="mMY8bqAJbCOf" outputId="e65bc91f-a3b0-47c4-937a-54cc51921f29"
# ============================================================
# Cell 30 — V1 vs V2 Final Comparison Table
# ============================================================

comparison_rows = []

for horizon, result in v2_results.items():
    v2_metrics = result["test_metrics"]
    baseline_metrics = result["baseline_test_metrics"]

    row = {
        "horizon_days": horizon,
        "v2_selected_model": result["selected_model_name"],
        "baseline_MAE_m_day": baseline_metrics["MAE_m_day"],
        "v2_MAE_m_day": v2_metrics["MAE_m_day"],
        "v2_RMSE_m_day": v2_metrics["RMSE_m_day"],
        "v2_R2": v2_metrics["R2"],
        "v2_improvement_vs_baseline_%": result["improvement_vs_baseline_pct"],
        "train_rows": result["train_rows"],
        "val_rows": result["val_rows"],
        "test_rows": result["test_rows"]
    }

    if result["v1_test_metrics"] is not None:
        row["v1_MAE_m_day"] = result["v1_test_metrics"]["MAE_m_day"]
        row["v2_improvement_vs_v1_%"] = result["improvement_vs_v1_pct"]
    else:
        row["v1_MAE_m_day"] = np.nan
        row["v2_improvement_vs_v1_%"] = np.nan

    comparison_rows.append(row)

v2_comparison_table = pd.DataFrame(comparison_rows)

display(v2_comparison_table)

v2_comparison_path = os.path.join(REPORTS_DIR, "09_v1_vs_v2_comparison_table.csv")
v2_comparison_table.to_csv(v2_comparison_path, index=False)

print(f"✅ V1 vs V2 comparison table saved to:\n{v2_comparison_path}")

# %% colab={"base_uri": "https://localhost:8080/"} id="1YE-j26bcNNj" outputId="436f42bd-29c4-402f-ac1a-e284fa74a0c5"
# ============================================================
# Cell 31 — Select Official Production Models for FastAPI
# ============================================================

import os
import json
import shutil
from datetime import datetime, timezone

# ------------------------------------------------------------
# Official decision based on final test results:
# V1 beats V2 for both 7d and 30d
# ------------------------------------------------------------

official_selection = {
    7: {
        "version": "V1_direct_model",
        "selected_model_name": "Ridge",
        "source_model_file": "uwe4_orbit_decay_model_7d.pkl",
        "source_feature_file": "uwe4_feature_columns_7d.json",
        "source_metrics_file": "uwe4_model_metrics_7d.json",
        "reason": "V1 Ridge achieved lower test MAE than V2 residual model for 7-day prediction."
    },
    30: {
        "version": "V1_direct_model",
        "selected_model_name": "BayesianRidge",
        "source_model_file": "uwe4_orbit_decay_model_30d.pkl",
        "source_feature_file": "uwe4_feature_columns_30d.json",
        "source_metrics_file": "uwe4_model_metrics_30d.json",
        "reason": "V1 BayesianRidge achieved lower test MAE than V2 residual model and baseline for 30-day prediction."
    }
}

production_registry = {
    "satellite": SATELLITE_NAME,
    "norad_id": NORAD_ID,
    "project": "UWE-4 AI Orbit Decay Prediction",
    "production_model_policy": "Use the best model on the untouched time-based test set.",
    "created_at_utc": datetime.now(timezone.utc).isoformat(),
    "models": {}
}

for horizon, info in official_selection.items():
    src_model_path = os.path.join(MODELS_DIR, info["source_model_file"])
    src_feature_path = os.path.join(MODELS_DIR, info["source_feature_file"])
    src_metrics_path = os.path.join(MODELS_DIR, info["source_metrics_file"])

    if not os.path.exists(src_model_path):
        raise FileNotFoundError(f"❌ Missing source model: {src_model_path}")

    if not os.path.exists(src_feature_path):
        raise FileNotFoundError(f"❌ Missing feature file: {src_feature_path}")

    if not os.path.exists(src_metrics_path):
        raise FileNotFoundError(f"❌ Missing metrics file: {src_metrics_path}")

    prod_model_filename = f"uwe4_production_model_{horizon}d.pkl"
    prod_feature_filename = f"uwe4_production_features_{horizon}d.json"
    prod_metrics_filename = f"uwe4_production_metrics_{horizon}d.json"

    prod_model_path = os.path.join(MODELS_DIR, prod_model_filename)
    prod_feature_path = os.path.join(MODELS_DIR, prod_feature_filename)
    prod_metrics_path = os.path.join(MODELS_DIR, prod_metrics_filename)

    shutil.copy2(src_model_path, prod_model_path)
    shutil.copy2(src_feature_path, prod_feature_path)
    shutil.copy2(src_metrics_path, prod_metrics_path)

    with open(src_metrics_path, "r") as f:
        metrics_data = json.load(f)

    production_registry["models"][f"{horizon}d"] = {
        "horizon_days": horizon,
        "version": info["version"],
        "selected_model_name": info["selected_model_name"],
        "production_model_file": prod_model_filename,
        "production_feature_file": prod_feature_filename,
        "production_metrics_file": prod_metrics_filename,
        "reason": info["reason"],
        "test_metrics": metrics_data.get("test_metrics", {}),
        "best_baseline_name": metrics_data.get("best_baseline_name", None),
        "best_baseline_metrics": metrics_data.get("best_baseline_metrics", {}),
        "improvement_vs_best_baseline_pct": metrics_data.get("improvement_vs_best_baseline_pct", None),
        "feature_count": metrics_data.get("feature_count", None)
    }

    print(f"\n✅ Production files created for {horizon}d:")
    print(f"Model:    {prod_model_path}")
    print(f"Features: {prod_feature_path}")
    print(f"Metrics:  {prod_metrics_path}")

registry_path = os.path.join(MODELS_DIR, "uwe4_production_model_registry.json")

with open(registry_path, "w") as f:
    json.dump(production_registry, f, indent=4)

print("\n" + "="*70)
print("✅ Official production model registry saved.")
print("="*70)
print(registry_path)

print("\n===== Production Model Summary =====")
for horizon_key, model_info in production_registry["models"].items():
    metrics = model_info["test_metrics"]
    baseline = model_info["best_baseline_metrics"]

    print(f"\nHorizon: {horizon_key}")
    print(f"Selected model: {model_info['selected_model_name']}")
    print(f"Version: {model_info['version']}")
    print(f"AI MAE/day: {metrics.get('MAE_m_day', None):.2f} m/day")
    print(f"Baseline MAE/day: {baseline.get('MAE_m_day', None):.2f} m/day")
    print(f"Improvement: {model_info['improvement_vs_best_baseline_pct']:.2f}%")

# %% colab={"base_uri": "https://localhost:8080/"} id="nbBuGQYydeDl" outputId="80393974-15e1-499c-e07b-79427c10fc7f"
# ============================================================
# Cell 32 — Latest Production Prediction from Saved Models
# ============================================================

import os
import json
import joblib
import pandas as pd
import numpy as np
from datetime import datetime, timezone

final_dataset_path = os.path.join(PROCESSED_DIR, "04_daily_orbit_space_weather_uwe4.csv")
registry_path = os.path.join(MODELS_DIR, "uwe4_production_model_registry.json")

if not os.path.exists(final_dataset_path):
    raise FileNotFoundError(f"❌ Final dataset not found: {final_dataset_path}")

if not os.path.exists(registry_path):
    raise FileNotFoundError("❌ Production registry not found. Run Cell 31 first.")

dataset_latest = pd.read_csv(final_dataset_path)
dataset_latest["date"] = pd.to_datetime(dataset_latest["date"], errors="coerce", utc=True)

with open(registry_path, "r") as f:
    production_registry = json.load(f)

latest_row = dataset_latest.sort_values("date").tail(1).copy()
latest_date = latest_row["date"].iloc[0]

latest_prediction_results = {
    "satellite": SATELLITE_NAME,
    "norad_id": NORAD_ID,
    "prediction_generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "latest_data_date": str(latest_date),
    "current_orbit_state": {
        "altitude_mean_km": float(latest_row["altitude_mean_km"].iloc[0]),
        "perigee_altitude_km": float(latest_row["perigee_altitude_km"].iloc[0]),
        "apogee_altitude_km": float(latest_row["apogee_altitude_km"].iloc[0]),
        "mean_motion_rev_day": float(latest_row["mean_motion_rev_day"].iloc[0]),
        "bstar": float(latest_row["bstar"].iloc[0]),
        "f107_obs": float(latest_row["f107_obs"].iloc[0]),
        "kp_max": float(latest_row["kp_max"].iloc[0]),
        "ap_avg": float(latest_row["ap_avg"].iloc[0]),
        "recent_7d_decay_m_day": float(latest_row["observed_decay_rolling_7d_km_day"].iloc[0] * 1000),
        "recent_30d_decay_m_day": float(latest_row["observed_decay_rolling_30d_km_day"].iloc[0] * 1000),
    },
    "predictions": {}
}

current_altitude = float(latest_row["altitude_mean_km"].iloc[0])

for horizon_key, model_info in production_registry["models"].items():
    horizon = int(model_info["horizon_days"])

    model_path = os.path.join(MODELS_DIR, model_info["production_model_file"])
    feature_path = os.path.join(MODELS_DIR, model_info["production_feature_file"])

    model = joblib.load(model_path)

    with open(feature_path, "r") as f:
        feature_cols = json.load(f)

    missing_features = [c for c in feature_cols if c not in latest_row.columns]
    if missing_features:
        raise ValueError(f"❌ Missing features for {horizon}d model: {missing_features[:20]}")

    X_latest = latest_row[feature_cols].copy()
    predicted_decay_km = float(model.predict(X_latest)[0])
    predicted_decay_rate_km_day = predicted_decay_km / horizon
    predicted_altitude_after_horizon_km = current_altitude - predicted_decay_km

    metrics = model_info["test_metrics"]
    baseline_metrics = model_info["best_baseline_metrics"]

    latest_prediction_results["predictions"][f"{horizon}d"] = {
        "horizon_days": horizon,
        "model_version": model_info["version"],
        "selected_model_name": model_info["selected_model_name"],
        "predicted_decay_km": predicted_decay_km,
        "predicted_decay_m": predicted_decay_km * 1000,
        "predicted_decay_rate_km_day": predicted_decay_rate_km_day,
        "predicted_decay_rate_m_day": predicted_decay_rate_km_day * 1000,
        "predicted_altitude_after_horizon_km": predicted_altitude_after_horizon_km,
        "test_MAE_m_day": metrics.get("MAE_m_day"),
        "test_RMSE_m_day": metrics.get("RMSE_m_day"),
        "test_R2": metrics.get("R2"),
        "baseline_MAE_m_day": baseline_metrics.get("MAE_m_day"),
        "improvement_vs_baseline_pct": model_info.get("improvement_vs_best_baseline_pct")
    }

latest_prediction_path = os.path.join(REPORTS_DIR, "10_latest_production_prediction.json")

with open(latest_prediction_path, "w") as f:
    json.dump(latest_prediction_results, f, indent=4)

print("===== Latest UWE-4 Production Prediction =====")
print(f"Latest data date: {latest_date}")
print(f"Current mean altitude: {current_altitude:.3f} km")
print(f"Current perigee: {latest_prediction_results['current_orbit_state']['perigee_altitude_km']:.3f} km")
print(f"Current apogee: {latest_prediction_results['current_orbit_state']['apogee_altitude_km']:.3f} km")

for horizon_key, pred in latest_prediction_results["predictions"].items():
    print("\n" + "-"*60)
    print(f"Horizon: {horizon_key}")
    print(f"Model: {pred['selected_model_name']} ({pred['model_version']})")
    print(f"Predicted decay: {pred['predicted_decay_km']:.3f} km")
    print(f"Predicted decay rate: {pred['predicted_decay_rate_m_day']:.2f} m/day")
    print(f"Predicted altitude after {pred['horizon_days']} days: {pred['predicted_altitude_after_horizon_km']:.3f} km")
    print(f"Test MAE: {pred['test_MAE_m_day']:.2f} m/day")
    print(f"Improvement vs baseline: {pred['improvement_vs_baseline_pct']:.2f}%")

print(f"\n✅ Latest production prediction saved to:\n{latest_prediction_path}")

# %% colab={"base_uri": "https://localhost:8080/", "height": 1000} id="62ddyM64etNZ" outputId="b21a4a33-b236-4566-d0da-5cfd22830ceb"
# ============================================================
# Cell 33 Fixed — Generate Self-Contained HTML Dashboard
# Images embedded as Base64 so they work in Colab and browser
# ============================================================

import os
import json
import base64
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import HTML, display

dashboard_dir = os.path.join(REPORTS_DIR, "dashboard")
assets_dir = os.path.join(dashboard_dir, "assets")

os.makedirs(dashboard_dir, exist_ok=True)
os.makedirs(assets_dir, exist_ok=True)

final_dataset_path = os.path.join(PROCESSED_DIR, "04_daily_orbit_space_weather_uwe4.csv")
summary_table_path = os.path.join(REPORTS_DIR, "06_final_training_summary_table.csv")
latest_prediction_path = os.path.join(REPORTS_DIR, "10_latest_production_prediction.json")
predictions_path = os.path.join(REPORTS_DIR, "04_test_predictions_7d_30d.csv")

if not os.path.exists(final_dataset_path):
    raise FileNotFoundError(f"❌ Final dataset not found: {final_dataset_path}")

if not os.path.exists(summary_table_path):
    raise FileNotFoundError(f"❌ Summary table not found: {summary_table_path}")

if not os.path.exists(latest_prediction_path):
    raise FileNotFoundError(f"❌ Latest prediction not found: {latest_prediction_path}")

dash_df = pd.read_csv(final_dataset_path)
dash_df["date"] = pd.to_datetime(dash_df["date"], errors="coerce", utc=True)

summary_table = pd.read_csv(summary_table_path)

with open(latest_prediction_path, "r") as f:
    latest_pred = json.load(f)


def save_current_plot_as_base64(filename):
    """
    Save current matplotlib figure, then return base64 string for embedding in HTML.
    """
    path = os.path.join(assets_dir, filename)
    plt.tight_layout()
    plt.savefig(path, dpi=160, bbox_inches="tight")
    plt.show()

    with open(path, "rb") as img_file:
        encoded = base64.b64encode(img_file.read()).decode("utf-8")

    return f"data:image/png;base64,{encoded}"


# ============================================================
# Create plots and embed them
# ============================================================

# 1) Altitude history
plt.figure(figsize=(14, 5))
plt.plot(dash_df["date"], dash_df["altitude_mean_km"], linewidth=2)
plt.title("UWE-4 Mean Altitude Over Time")
plt.xlabel("Date")
plt.ylabel("Mean altitude [km]")
plt.grid(True)
altitude_plot_b64 = save_current_plot_as_base64("altitude_history.png")

# 2) Recent orbit state
recent_df = dash_df.tail(365).copy()

plt.figure(figsize=(14, 5))
plt.plot(recent_df["date"], recent_df["perigee_altitude_km"], label="Perigee", linewidth=1.5)
plt.plot(recent_df["date"], recent_df["altitude_mean_km"], label="Mean altitude", linewidth=2)
plt.plot(recent_df["date"], recent_df["apogee_altitude_km"], label="Apogee", linewidth=1.5)
plt.title("UWE-4 Recent Orbit Altitude — Last 365 Days")
plt.xlabel("Date")
plt.ylabel("Altitude [km]")
plt.legend()
plt.grid(True)
recent_altitude_plot_b64 = save_current_plot_as_base64("recent_altitude_365d.png")

# 3) Decay trend
plt.figure(figsize=(14, 5))
plt.plot(
    dash_df["date"],
    dash_df["observed_decay_rolling_7d_km_day"] * 1000,
    label="7-day avg decay",
    linewidth=1.5
)
plt.plot(
    dash_df["date"],
    dash_df["observed_decay_rolling_30d_km_day"] * 1000,
    label="30-day avg decay",
    linewidth=2
)
plt.title("UWE-4 Observed Orbit Decay Rate")
plt.xlabel("Date")
plt.ylabel("Decay rate [m/day]")
plt.legend()
plt.grid(True)
decay_plot_b64 = save_current_plot_as_base64("decay_rate.png")

# 4) Space weather vs decay
plt.figure(figsize=(14, 5))
plt.plot(
    dash_df["date"],
    dash_df["observed_decay_rolling_30d_km_day"] * 1000,
    label="30-day decay [m/day]",
    linewidth=2
)
plt.plot(
    dash_df["date"],
    dash_df["f107_obs_rolling_27d"],
    label="F10.7 27-day rolling avg",
    linewidth=2
)
plt.title("Orbit Decay vs Solar Activity")
plt.xlabel("Date")
plt.ylabel("Scaled comparison")
plt.legend()
plt.grid(True)
weather_decay_plot_b64 = save_current_plot_as_base64("decay_vs_f107.png")

# 5) Test prediction plots
prediction_plots_html = ""

if os.path.exists(predictions_path):
    pred_df = pd.read_csv(predictions_path)
    pred_df["date"] = pd.to_datetime(pred_df["date"], errors="coerce", utc=True)

    for horizon in [7, 30]:
        p = pred_df[pred_df["horizon_days"] == horizon].copy()

        if len(p) > 0:
            plt.figure(figsize=(14, 5))
            plt.plot(p["date"], p["actual_decay_km"], label="Actual decay", linewidth=2)
            plt.plot(p["date"], p["predicted_decay_km"], label="Predicted decay", linewidth=2)
            plt.title(f"UWE-4 {horizon}-Day Test Prediction")
            plt.xlabel("Date")
            plt.ylabel(f"Decay next {horizon} days [km]")
            plt.legend()
            plt.grid(True)

            pred_plot_b64 = save_current_plot_as_base64(f"test_prediction_{horizon}d.png")

            prediction_plots_html += f"""
            <div class="plot-card">
                <h3>{horizon}-Day Test Prediction</h3>
                <img src="{pred_plot_b64}" />
            </div>
            """

# ============================================================
# Dashboard values
# ============================================================

latest_state = latest_pred["current_orbit_state"]
pred_7 = latest_pred["predictions"]["7d"]
pred_30 = latest_pred["predictions"]["30d"]

initial_altitude = float(dash_df["altitude_mean_km"].iloc[0])
latest_altitude = float(dash_df["altitude_mean_km"].iloc[-1])
total_loss = initial_altitude - latest_altitude

summary_rows_html = ""

for _, row in summary_table.iterrows():
    summary_rows_html += f"""
    <tr>
        <td>{int(row['horizon_days'])} days</td>
        <td>{row['selected_model']}</td>
        <td>{row['AI_MAE_m_day']:.2f}</td>
        <td>{row['baseline_MAE_m_day']:.2f}</td>
        <td>{row['improvement_%']:.2f}%</td>
        <td>{row['AI_R2']:.3f}</td>
    </tr>
    """

# ============================================================
# Build HTML
# ============================================================

html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>UWE-4 Orbit Decay AI Dashboard</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            background: #f5f7fb;
            margin: 0;
            padding: 0;
            color: #111827;
        }}

        .container {{
            width: 94%;
            margin: auto;
            padding: 24px;
        }}

        .header {{
            background: #111827;
            color: white;
            padding: 28px;
            border-radius: 16px;
            margin-bottom: 24px;
        }}

        .header h1 {{
            margin: 0;
            font-size: 32px;
            color: white;
        }}

        .header p {{
            margin-top: 8px;
            color: #d1d5db;
        }}

        .grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }}

        .card {{
            background: white;
            padding: 20px;
            border-radius: 14px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}

        .card h3 {{
            margin: 0;
            color: #374151;
            font-size: 14px;
        }}

        .card .value {{
            font-size: 28px;
            font-weight: bold;
            margin-top: 8px;
            color: #000000;
        }}

        .section {{
            background: white;
            padding: 22px;
            border-radius: 14px;
            margin-bottom: 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}

        .section h2 {{
            color: #111827;
            margin-top: 0;
        }}

        .plot-card h3 {{
            color: #374151;
        }}

        img {{
            max-width: 100%;
            border-radius: 10px;
            border: 1px solid #e5e7eb;
            background: white;
        }}

        .plot-card {{
            margin-bottom: 28px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 12px;
            color: #111827;
        }}

        th, td {{
            padding: 12px;
            border-bottom: 1px solid #e5e7eb;
            text-align: left;
        }}

        th {{
            background: #f3f4f6;
        }}

        .note {{
            background: #eff6ff;
            border-left: 4px solid #2563eb;
            padding: 14px;
            border-radius: 8px;
            margin-top: 12px;
            color: #111827;
        }}

        @media (max-width: 1000px) {{
            .grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
        }}

        @media (max-width: 600px) {{
            .grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>

<body>
<div class="container">

    <div class="header">
        <h1>UWE-4 AI Orbit Decay Prediction Dashboard</h1>
        <p>NORAD ID: {NORAD_ID} | Latest data date: {latest_pred["latest_data_date"]}</p>
    </div>

    <div class="grid">
        <div class="card">
            <h3>Current Mean Altitude</h3>
            <div class="value">{latest_state["altitude_mean_km"]:.2f} km</div>
        </div>
        <div class="card">
            <h3>Total Altitude Loss</h3>
            <div class="value">{total_loss:.2f} km</div>
        </div>
        <div class="card">
            <h3>Recent 7d Decay</h3>
            <div class="value">{latest_state["recent_7d_decay_m_day"]:.1f} m/day</div>
        </div>
        <div class="card">
            <h3>Recent 30d Decay</h3>
            <div class="value">{latest_state["recent_30d_decay_m_day"]:.1f} m/day</div>
        </div>
    </div>

    <div class="grid">
        <div class="card">
            <h3>7-Day Predicted Decay</h3>
            <div class="value">{pred_7["predicted_decay_km"]:.3f} km</div>
        </div>
        <div class="card">
            <h3>Altitude After 7 Days</h3>
            <div class="value">{pred_7["predicted_altitude_after_horizon_km"]:.2f} km</div>
        </div>
        <div class="card">
            <h3>30-Day Predicted Decay</h3>
            <div class="value">{pred_30["predicted_decay_km"]:.3f} km</div>
        </div>
        <div class="card">
            <h3>Altitude After 30 Days</h3>
            <div class="value">{pred_30["predicted_altitude_after_horizon_km"]:.2f} km</div>
        </div>
    </div>

    <div class="section">
        <h2>Model Performance Summary</h2>
        <table>
            <tr>
                <th>Horizon</th>
                <th>Selected Model</th>
                <th>AI MAE [m/day]</th>
                <th>Baseline MAE [m/day]</th>
                <th>Improvement</th>
                <th>R²</th>
            </tr>
            {summary_rows_html}
        </table>

        <div class="note">
            The baseline assumes that the recent 30-day decay rate continues into the future.
            The AI model outperformed this baseline for both 7-day and 30-day prediction horizons.
        </div>
    </div>

    <div class="section">
        <h2>Orbit History</h2>

        <div class="plot-card">
            <h3>Mean Altitude Over Time</h3>
            <img src="{altitude_plot_b64}" />
        </div>

        <div class="plot-card">
            <h3>Recent Orbit State</h3>
            <img src="{recent_altitude_plot_b64}" />
        </div>

        <div class="plot-card">
            <h3>Observed Decay Rate</h3>
            <img src="{decay_plot_b64}" />
        </div>
    </div>

    <div class="section">
        <h2>Space Weather Relationship</h2>

        <div class="plot-card">
            <h3>Decay vs F10.7 Solar Flux</h3>
            <img src="{weather_decay_plot_b64}" />
        </div>
    </div>

    <div class="section">
        <h2>Test Set Prediction Plots</h2>
        {prediction_plots_html}
    </div>

</div>
</body>
</html>
"""

dashboard_html_path = os.path.join(dashboard_dir, "uwe4_orbit_decay_dashboard.html")

with open(dashboard_html_path, "w", encoding="utf-8") as f:
    f.write(html_content)

print("✅ Fixed self-contained dashboard generated successfully.")
print(f"Dashboard path:\n{dashboard_html_path}")

display(HTML(html_content))
