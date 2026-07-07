"""
Train Model — The Lab

Trains the Unified Anomaly Detection system (Variational Autoencoder) for a single satellite.
Logic is located in src/gr_sat/training.py.

Usage:
  pixi run python scripts/train_model.py --norad 43880
"""

import argparse
from gr_sat.ml.training import train_for_satellite

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--norad", type=str, required=True, help="Specific NORAD ID to process"
    )
    parser.add_argument("--epochs", type=int, default=100, help="Training epochs")
    args = parser.parse_args()
    train_for_satellite(args.norad, epochs=args.epochs)
