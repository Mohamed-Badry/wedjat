import json
import logging
import faulthandler
faulthandler.enable()
import os
import time
import csv
import queue
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("edge_streamer")

# Import modular demodulator registry
from gr_sat.demodulators.registry import DemodulatorRegistry
# Trigger auto-registration
import gr_sat.demodulators  # noqa: F401

# Environment config
MQTT_HOST = os.getenv("MQTT_BROKER_URL", "broker")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))
MQTT_USER = os.getenv("MQTT_USERNAME", "wedjat")
MQTT_PASS = os.getenv("MQTT_PASSWORD", "secretpassword")
STATION_ID = os.getenv("STATION_ID", "edge_station_sdr")
ZMQ_ENDPOINT = os.getenv("ZMQ_ENDPOINT", "tcp://0.0.0.0:5555")
INITIAL_TARGET_NORAD_ID = int(os.getenv("TARGET_NORAD_ID", 43880))
FALLBACK_PATH = os.getenv("EDGE_LOCAL_BACKUP_PATH", "/app/data/raw/fallback_buffer.csv")

CONTROL_TOPIC = f"edge/control/{STATION_ID}/target"

# Thread-safe queue for target updates from MQTT thread to main thread
target_update_queue = queue.Queue()

def _flush_fallback(client):
    if not os.path.exists(FALLBACK_PATH):
        return

    logger.info("Flushing offline fallback buffer...")
    to_retry = []
    try:
        with open(FALLBACK_PATH, "r") as csvfile:
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
        payload["norad_id"] = int(payload["norad_id"])
        payload["snr"] = float(payload["snr"])
        
        info = client.publish(
            f"telemetry/live/{payload['norad_id']}", json.dumps(payload), qos=1
        )
        if info.rc == mqtt.MQTT_ERR_SUCCESS:
            success_count += 1

    if success_count == len(to_retry):
        logger.info(f"Successfully flushed {success_count} offline frames. Clearing buffer.")
        os.remove(FALLBACK_PATH)
    else:
        logger.warning(f"Only flushed {success_count}/{len(to_retry)} frames. Buffer preserved.")

def _write_fallback(payload):
    os.makedirs(os.path.dirname(FALLBACK_PATH), exist_ok=True)
    file_exists = os.path.isfile(FALLBACK_PATH)
    try:
        with open(FALLBACK_PATH, "a", newline="") as csvfile:
            fieldnames = ["timestamp", "norad_id", "station_id", "snr", "raw_frame"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(payload)
    except Exception as e:
        logger.error(f"Failed to write to fallback buffer: {e}")

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Edge Streamer connected to MQTT broker")
        client.connected_flag = True
        client.subscribe(CONTROL_TOPIC)
        logger.info(f"Subscribed to control topic: {CONTROL_TOPIC}")
        _flush_fallback(client)
    else:
        logger.error(f"Edge Streamer failed to connect: {rc}")
        client.connected_flag = False

def on_disconnect(client, userdata, rc):
    logger.warning("Edge Streamer disconnected from MQTT broker")
    client.connected_flag = False

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        if "target_norad_id" in payload:
            new_target = int(payload["target_norad_id"])
            logger.info(f"Received MQTT command to switch target to NORAD {new_target}")
            target_update_queue.put(new_target)
    except Exception as e:
        logger.error(f"Failed to parse control message: {e}")

def main():
    logger.info("Initializing Edge Live Streamer...")

    # Setup MQTT Connection
    use_tls = os.getenv("MQTT_USE_TLS", "false").lower() == "true"
    use_wss = os.getenv("MQTT_USE_WSS", "false").lower() == "true" or MQTT_PORT == 443

    if use_wss:
        client = mqtt.Client(transport="websockets")
        client.ws_set_options(path="/mqtt")
    else:
        client = mqtt.Client()

    client.connected_flag = False
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    if MQTT_USER and MQTT_PASS:
        client.username_pw_set(MQTT_USER, MQTT_PASS)

    if use_tls or (use_wss and MQTT_PORT == 443):
        client.tls_set()

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

    current_target_id = INITIAL_TARGET_NORAD_ID
    demodulator_cls = DemodulatorRegistry.get(current_target_id)
    if not demodulator_cls:
        logger.error(f"No demodulator registered for initial NORAD ID: {current_target_id}")
        return

    demodulator = demodulator_cls()
    frame_count = 0

    def get_on_frame_decoded_callback(target_id):
        def on_frame_decoded(frame_bytes: bytes):
            nonlocal frame_count
            logger.info(f"Decoded a frame of {len(frame_bytes)} bytes")
            frame_count += 1
            payload = {
                "norad_id": target_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "raw_frame": frame_bytes.hex(),
                "station_id": STATION_ID,
                "snr": 15.0,  # Default SNR
            }
            topic = f"telemetry/live/{target_id}"
            
            if getattr(client, "connected_flag", False):
                info = client.publish(topic, json.dumps(payload), qos=1)
                if info.rc == mqtt.MQTT_ERR_SUCCESS:
                    logger.info(f"Live Stream: Published frame #{frame_count} to topic: {topic}")
                else:
                    logger.error(f"Publish failed (rc={info.rc}), using offline fallback")
                    _write_fallback(payload)
            else:
                logger.warning("MQTT disconnected. Writing to offline fallback buffer.")
                _write_fallback(payload)
        return on_frame_decoded

    logger.info(f"Starting live stream for NORAD {current_target_id} listening on {ZMQ_ENDPOINT}")
    
    try:
        demodulator.start_live_stream(ZMQ_ENDPOINT, get_on_frame_decoded_callback(current_target_id))
        logger.info("Entering main loop...")
        
        while True:
            # Check for target updates
            try:
                new_target = target_update_queue.get(timeout=1.0)
                if new_target != current_target_id:
                    new_demodulator_cls = DemodulatorRegistry.get(new_target)
                    if not new_demodulator_cls:
                        logger.error(f"Cannot switch: No demodulator registered for NORAD {new_target}")
                        continue
                        
                    logger.info(f"Tearing down live stream for NORAD {current_target_id}...")
                    demodulator.stop_live_stream()
                    
                    logger.info(f"Spinning up live stream for NORAD {new_target}...")
                    current_target_id = new_target
                    demodulator = new_demodulator_cls()
                    frame_count = 0 # Reset frame count for new target
                    demodulator.start_live_stream(ZMQ_ENDPOINT, get_on_frame_decoded_callback(current_target_id))
            except queue.Empty:
                pass # No new target, just continue

    except KeyboardInterrupt:
        logger.info("Shutting down streamer...")
        if demodulator:
            demodulator.stop_live_stream()
    except BaseException as e:
        logger.error(f"Streaming failed with BaseException: {repr(e)}", exc_info=True)
        if demodulator:
            demodulator.stop_live_stream()
    except Exception as e:
        logger.error(f"Streaming failed: {e}", exc_info=True)
        if demodulator:
            demodulator.stop_live_stream()
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
