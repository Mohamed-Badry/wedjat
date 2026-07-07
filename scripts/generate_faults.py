"""
Generate Faults — Benchmark The Edge Models

Tests the Unified Anomaly Detection system (PyTorch VAE) on a held-out test set
by injecting physically-motivated synthetic faults.

Usage:
  pixi run python scripts/generate_faults.py --norad 43880
"""

import argparse
from gr_sat.ml.evaluation import evaluate

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--norad", type=str, required=True, help="Specific NORAD ID")
    args = parser.parse_args()
    evaluate(args.norad)
