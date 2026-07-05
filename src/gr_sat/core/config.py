"""
Shared core configuration constants for Project Wedjat.
"""

import os
from pathlib import Path

# Project layout
# __file__ is src/gr_sat/core/config.py
# .parent is core
# .parent.parent is gr_sat
# .parent.parent.parent is src
# .parent.parent.parent.parent is root (e.g. /app or /home/.../gr_sat)
PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", Path(__file__).resolve().parents[3]))
MODEL_DIR = Path(os.getenv("MODEL_DIR", PROJECT_ROOT / "models"))
DATA_DIR = Path(os.getenv("DATA_DIR", PROJECT_ROOT / "data"))
DOCS_DIR = Path(os.getenv("DOCS_DIR", PROJECT_ROOT / "docs"))

# Ground Station config
GS_LATITUDE = float(os.getenv("GS_LATITUDE", "29.0661"))
GS_LONGITUDE = float(os.getenv("GS_LONGITUDE", "31.0994"))
GS_ELEVATION = float(os.getenv("GS_ELEVATION", "32.0"))
GS_NAME = os.getenv("GS_NAME", "Beni Suef, Egypt")
