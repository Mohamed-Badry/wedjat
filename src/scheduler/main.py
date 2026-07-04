import os
import time
import httpx
import schedule
from loguru import logger
import subprocess
from pathlib import Path

# We run from /app/src/scheduler, but we need to call scripts from /app
PROJECT_ROOT = Path("/app")
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

API_URL = os.getenv("API_URL", "http://backend:8000")

def run_fetch_data():
    logger.info("Starting daily fetch_training_data job (non-interactive, 3 days window)...")
    try:
        subprocess.run(
            ["python", str(SCRIPTS_DIR / "fetch_training_data.py"), "--all", "--days", "3"],
            check=True,
            cwd=str(PROJECT_ROOT)
        )
        logger.info("Successfully fetched new data.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Data fetching failed: {e}")

def run_train_models():
    logger.info("Starting daily train_model job for all active satellites...")
    
    # We query the API for active satellites so we can retrain all known ones.
    satellites = None
    for attempt in range(5):
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{API_URL}/api/satellites")
                response.raise_for_status()
                satellites = response.json().get("satellites", [])
            break
        except Exception as e:
            logger.warning(f"Failed to fetch satellite list from API (attempt {attempt+1}/5): {e}")
            if attempt == 4:
                logger.error("Max retries reached. Skipping train_models job.")
                return
            time.sleep(60)

    if satellites is None:
        return

    success_count = 0
    for sat in satellites:
        norad_id = sat["norad_id"]
        logger.info(f"Retraining model for {norad_id}...")
        try:
            subprocess.run(
                ["python", str(SCRIPTS_DIR / "train_model.py"), "--norad", str(norad_id)],
                check=True,
                cwd=str(PROJECT_ROOT)
            )
            success_count += 1
        except subprocess.CalledProcessError as e:
            logger.error(f"Training failed for {norad_id}: {e}")

    logger.info(f"Successfully retrained {success_count}/{len(satellites)} models.")
    
    # Now reload the API cache
    reload_api_models()

def reload_api_models():
    logger.info("Notifying API to reload model cache...")
    for attempt in range(3):
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(f"{API_URL}/api/admin/reload_models")
                response.raise_for_status()
            logger.info("API model cache reloaded successfully.")
            return
        except Exception as e:
            logger.warning(f"Failed to reload API model cache (attempt {attempt+1}/3): {e}")
            time.sleep(10)
    logger.error("Failed to reload API model cache after retries.")

def main():
    logger.info("Starting Scheduler Service...")
    
    # Schedule the jobs
    # 02:00 UTC for fetching, 02:15 UTC for training
    schedule.every().day.at("02:00").do(run_fetch_data)
    schedule.every().day.at("02:15").do(run_train_models)
    
    logger.info("Jobs scheduled. Entering sleep loop.")
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()
