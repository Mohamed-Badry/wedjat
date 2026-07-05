"""
Shared model/training constants for Project Wedjat.
"""

import os
from pathlib import Path

from gr_sat.core.config import (
    PROJECT_ROOT,
    MODEL_DIR,
    DATA_DIR,
    DOCS_DIR,
    GS_LATITUDE,
    GS_LONGITUDE,
    GS_ELEVATION,
    GS_NAME,
)


HIDDEN_DIM = 24
LATENT_DIM = 6
DEFAULT_KLD_WEIGHT = 0.05

TRAIN_SPLIT = 0.8
VALIDATION_SPLIT = 0.1
THRESHOLD_PERCENTILE = 99.9
DEFAULT_INFERENCE_MODE = "deterministic"
