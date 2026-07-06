import json
import logging
import os
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
import paho.mqtt.client as mqtt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("edge_watcher")

# Import modular demodulator registry
from gr_sat.demodulators.registry import DemodulatorRegistry
# Trigger auto-registration
import gr_sat.demodulators  # noqa: F401

# Environment config
WATCH_DIR = Path(os.getenv("WATCH_DIR", "/app/data/iq"))
PROCESSED_DIR = WATCH_DIR / "processed"
MQTT_HOST = os.getenv("MQTT_BROKER_URL", "broker")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))
MQTT_USER = os.getenv("MQTT_USERNAME", "wedjat")
MQTT_PASS = os.getenv("MQTT_PASSWORD", "secretpassword")
STATION_ID = os.getenv("STATION_ID", "edge_station_sdr")
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", 2))

# Filename regex: expect something starting with norad_id (e.g. 43880_recording.raw)
FILENAME_RE = re.compile(r"^(\d+)(?:_.*)?\.raw$")


def parse_norad_id(filename: str) -> Optional[int]:
    """Parse NORAD ID from the beginning of the filename."""
    match = FILENAME_RE.match(filename)
    if match:
        return int(match.group(1))
    return None


def process_iq_file(file_path: Path, mqtt_client: mqtt.Client):
    filename = file_path.name
    logger.info(f"New IQ recording detected: {filename}")

    norad_id = parse_norad_id(filename)
    if not norad_id:
        logger.warning(
            f"Could not determine NORAD ID from filename: {filename}. Expected format: {{norad_id}}_*.raw"
        )
        # Move it to a failed directory or processed to avoid inf-loop
        dest = PROCESSED_DIR / filename
        shutil.move(str(file_path), str(dest))
        return

    demodulator_cls = DemodulatorRegistry.get(norad_id)
    if not demodulator_cls:
        logger.warning(f"No demodulator registered for NORAD ID: {norad_id}")
        dest = PROCESSED_DIR / filename
        shutil.move(str(file_path), str(dest))
        return

    logger.info(f"Invoking demodulator for satellite NORAD {norad_id}")
    try:
        demodulator = demodulator_cls()
        frames = demodulator.demodulate(file_path)
        logger.info(f"Demodulation complete. Decoded {len(frames)} valid frame(s).")

        # Publish each frame to the MQTT broker
        for i, frame in enumerate(frames):
            payload = {
                "norad_id": norad_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "raw_frame": frame.hex(),
                "station_id": STATION_ID,
                "snr": 15.0,  # Default SNR
            }
            topic = f"telemetry/live/{norad_id}"
            info = mqtt_client.publish(topic, json.dumps(payload), qos=1)
            info.wait_for_publish()
            logger.info(f"Published frame #{i + 1} to topic: {topic}")

    except Exception as e:
        logger.error(f"Inference/demodulation failed for file {filename}: {e}", exc_info=True)

    # Move processed file out of the watch directory
    try:
        dest = PROCESSED_DIR / filename
        shutil.move(str(file_path), str(dest))
        logger.info(f"Moved processed file to: {dest}")
    except Exception as e:
        logger.error(f"Failed to move processed file: {e}")


def main():
    logger.info("Initializing Edge Ingress Demodulator Watcher...")
    WATCH_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Setup MQTT Connection
    client = mqtt.Client()
    if MQTT_USER and MQTT_PASS:
        client.username_pw_set(MQTT_USER, MQTT_PASS)

    connected = False
    for attempt in range(5):
        try:
            logger.info(f"Connecting to MQTT Broker at {MQTT_HOST}:{MQTT_PORT} (Attempt {attempt+1}/5)...")
            client.connect(MQTT_HOST, MQTT_PORT, 60)
            connected = True
            break
        except Exception as e:
            logger.warning(f"MQTT connection failed: {e}")
            time.sleep(2)

    if not connected:
        logger.error("Failed to connect to MQTT broker after 5 attempts. Exiting.")
        return

    client.loop_start()
    logger.info(f"Watcher active. Polling directory: {WATCH_DIR} every {POLL_INTERVAL_SECONDS}s")

    try:
        while True:
            # Check for any .raw files in watch directory
            for entry in WATCH_DIR.iterdir():
                if entry.is_file() and entry.suffix == ".raw":
                    process_iq_file(entry, client)
            time.sleep(POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        logger.info("Shutting down watcher...")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    from typing import Optional  # Local import just in case
    main()
