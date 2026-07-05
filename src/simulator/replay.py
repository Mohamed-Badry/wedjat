import os
import json
import time
from loguru import logger
from datetime import datetime, timezone
import paho.mqtt.client as mqtt
from gr_sat.core.satellite_profiles import DEFAULT_PROFILE


import csv
from gr_sat.core.config import DATA_DIR


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Simulator connected to MQTT broker")
        client.connected_flag = True
        _flush_fallback(client)
    else:
        logger.error(f"Simulator failed to connect: {rc}")
        client.connected_flag = False


def _flush_fallback(client):
    fallback_path = DATA_DIR / "raw" / "fallback_buffer.csv"
    if not os.path.exists(fallback_path):
        return

    logger.info("Flushing offline fallback buffer...")
    to_retry = []
    try:
        with open(fallback_path, "r") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                to_retry.append(row)
    except Exception as e:
        logger.error(f"Failed to read fallback buffer: {e}")
        return

    if not to_retry:
        return

    success_count = 0
    for payload in to_retry:
        # Convert numeric types back if necessary (since csv reads as strings)
        payload["norad_id"] = int(payload["norad_id"])
        payload["snr"] = float(payload["snr"])

        info = client.publish(
            f"telemetry/live/{payload['norad_id']}", json.dumps(payload), qos=1
        )
        if info.rc == mqtt.MQTT_ERR_SUCCESS:
            success_count += 1

    if success_count == len(to_retry):
        logger.info(
            f"Successfully flushed {success_count} offline frames. Clearing buffer."
        )
        os.remove(fallback_path)
    else:
        logger.warning(
            f"Only flushed {success_count}/{len(to_retry)} frames. Buffer preserved."
        )


def on_disconnect(client, userdata, rc):
    logger.warning("Simulator disconnected from MQTT broker")
    client.connected_flag = False


def main():
    broker_url = os.getenv("MQTT_BROKER_URL", "localhost")
    broker_port = int(os.getenv("MQTT_BROKER_PORT", 1883))
    username = os.getenv("MQTT_USERNAME")
    password = os.getenv("MQTT_PASSWORD")
    use_tls = os.getenv("MQTT_USE_TLS", "false").lower() == "true"
    use_wss = os.getenv("MQTT_USE_WSS", "false").lower() == "true" or broker_port == 443

    if use_wss:
        client = mqtt.Client(transport="websockets")
        client.ws_set_options(path="/mqtt")
    else:
        client = mqtt.Client()

    client.connected_flag = False
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    if username and password:
        client.username_pw_set(username, password)

    if use_tls or use_wss:
        client.tls_set()

    try:
        client.connect(broker_url, broker_port, 60)
        client.loop_start()
    except Exception as e:
        logger.error(f"Simulator initial connection failed: {e}")
        # We don't return, we let the loop try to publish and use the fallback buffer

    # Simulate reading from data/raw/
    import glob

    raw_dir = DATA_DIR / "raw"
    if not os.path.exists(raw_dir):
        logger.warning(f"Raw data dir {raw_dir} not found. Mocking random data.")
        mock_mode = True
    else:
        mock_mode = False
        # Read all sample JSONL files from all subdirectories
        pattern = str(raw_dir / "**" / "*.jsonl")
        files = glob.glob(pattern, recursive=True)
        if files:
            lines = []
            for fpath in files:
                with open(fpath) as f:
                    lines.extend(f.readlines())
            import random

            random.shuffle(lines)
        else:
            mock_mode = True

    idx = 0
    while True:
        if mock_mode:
            norad_id = DEFAULT_PROFILE.norad_id
            # A valid UWE-4 raw packet header mock
            raw_frame = "8A8A8A8A8A8A608A8A8A8A8A8A6103F0" + "".join(
                [random.choice("0123456789ABCDEF") for _ in range(64)]
            )
            original_timestamp = datetime.now(timezone.utc).isoformat()
        else:
            try:
                record = json.loads(lines[idx % len(lines)])
                norad_id = record.get(
                    "norad_cat_id", record.get("norad_id", DEFAULT_PROFILE.norad_id)
                )
                raw_frame = record.get("frame", "")
                original_timestamp = datetime.now(timezone.utc).isoformat()
                idx += 1
            except:
                norad_id = DEFAULT_PROFILE.norad_id
                raw_frame = "8A8A8A8A8A8A"
                original_timestamp = datetime.now(timezone.utc).isoformat()

        payload = {
            "norad_id": norad_id,
            "timestamp": original_timestamp,
            "raw_frame": raw_frame,
            "station_id": "sim_station_1",
            "snr": round(random.uniform(5.0, 25.0), 1),
        }

        payload_str = json.dumps(payload)

        if getattr(client, "connected_flag", False):
            info = client.publish(f"telemetry/live/{norad_id}", payload_str, qos=1)
            if info.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Published to telemetry/live/{norad_id}")
            else:
                logger.error(f"Publish failed (rc={info.rc}), using offline fallback")
                _write_fallback(payload)
        else:
            logger.warning("MQTT disconnected. Writing to offline fallback buffer.")
            _write_fallback(payload)

        time.sleep(5)


def _write_fallback(payload):
    import csv

    fallback_path = DATA_DIR / "raw" / "fallback_buffer.csv"
    os.makedirs(os.path.dirname(fallback_path), exist_ok=True)

    file_exists = os.path.isfile(fallback_path)
    try:
        with open(fallback_path, "a", newline="") as csvfile:
            fieldnames = ["timestamp", "norad_id", "station_id", "snr", "raw_frame"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(payload)
    except Exception as e:
        logger.error(f"Failed to write to fallback buffer: {e}")


if __name__ == "__main__":
    time.sleep(10)  # Wait for broker to start
    main()
