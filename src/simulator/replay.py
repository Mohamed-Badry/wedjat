import os
import json
import time
import logging
import random
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Simulator")

def main():
    broker_url = os.getenv("MQTT_BROKER_URL", "localhost")
    broker_port = int(os.getenv("MQTT_BROKER_PORT", 1883))
    
    client = mqtt.Client()
    try:
        client.connect(broker_url, broker_port, 60)
        logger.info(f"Simulator connected to MQTT broker at {broker_url}:{broker_port}")
    except Exception as e:
        logger.error(f"Simulator failed to connect: {e}")
        return

    # Simulate reading from data/raw/
    raw_dir = "/app/data/raw" if os.path.exists("/app/data/raw") else "../../data/raw"
    if not os.path.exists(raw_dir):
        logger.warning(f"Raw data dir {raw_dir} not found. Mocking random data.")
        mock_mode = True
    else:
        mock_mode = False
        # Read a sample JSONL file
        files = [f for f in os.listdir(raw_dir) if f.endswith('.jsonl')]
        if files:
            with open(os.path.join(raw_dir, files[0])) as f:
                lines = f.readlines()
        else:
            mock_mode = True

    idx = 0
    while True:
        if mock_mode:
            norad_id = 43880
            # A valid UWE-4 raw packet header mock
            raw_frame = "8A8A8A8A8A8A608A8A8A8A8A8A6103F0" + "".join([random.choice("0123456789ABCDEF") for _ in range(64)])
        else:
            try:
                record = json.loads(lines[idx % len(lines)])
                norad_id = record.get("norad_id", 43880)
                raw_frame = record.get("frame", "")
                idx += 1
            except:
                norad_id = 43880
                raw_frame = "8A8A8A8A8A8A"
        
        payload = {
            "norad_id": norad_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "raw_frame": raw_frame,
            "station_id": "sim_station_1",
            "snr": round(random.uniform(5.0, 25.0), 1)
        }
        
        client.publish(f"telemetry/live/{norad_id}", json.dumps(payload))
        logger.info(f"Published to telemetry/live/{norad_id}")
        time.sleep(5)

if __name__ == "__main__":
    time.sleep(10) # Wait for broker to start
    main()
