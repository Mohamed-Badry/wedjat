"""
Orbit Decay Model Training Script

Usage:
  pixi run python scripts/train_decay_model.py --norad 43880 --horizons 7,30
"""

import argparse
from loguru import logger
from gr_sat.ml.orbit_decay_training import OrbitDecayTrainer

def main():
    parser = argparse.ArgumentParser(description="Train Orbit Decay ML Models")
    parser.add_argument("--norad", type=int, required=True, help="Satellite NORAD ID")
    parser.add_argument("--horizons", type=str, default="7,30", help="Comma-separated prediction horizons in days")
    parser.add_argument("--dataset", type=str, default="other_components/uwe4-orbit-decay-ai/data/04_daily_orbit_space_weather_uwe4.csv", help="Path to pre-processed dataset")
    parser.add_argument("--output-dir", type=str, default="models", help="Directory to save models")
    
    args = parser.parse_args()
    horizons = [int(h) for h in args.horizons.split(",")]
    
    trainer = OrbitDecayTrainer(
        norad_id=args.norad,
        dataset_path=args.dataset,
        output_dir=args.output_dir
    )
    
    logger.info(f"Starting Orbit Decay training pipeline for NORAD {args.norad}")
    trainer.run_pipeline(horizons=horizons)
    logger.info("Pipeline completed successfully.")

if __name__ == "__main__":
    main()
