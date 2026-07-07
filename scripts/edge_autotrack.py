#!/usr/bin/env python3
"""
Edge Autotrack Daemon

Runs on the local edge node, predicting passes for all supported satellites and
publishing MQTT commands to swap the active demodulator target automatically.
"""

import os
import time
import json
import logging
from datetime import datetime, timezone
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

# Ensure we can import src.api.pass_predictor
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from api.pass_predictor import predict_passes
from gr_sat.demodulators.registry import DemodulatorRegistry
import gr_sat.demodulators  # Trigger registrations

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] autotrack: %(message)s")

load_dotenv()

MQTT_HOST = os.getenv("MQTT_BROKER_URL", "localhost")

MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))
MQTT_USER = os.getenv("MQTT_USERNAME", "wedjat")
MQTT_PASS = os.getenv("MQTT_PASSWORD", "secretpassword")
STATION_ID = os.getenv("STATION_ID", "edge_station_sdr")

# Default coordinates if not provided in .env
GS_LAT = float(os.getenv("GS_LAT", 34.0522))
GS_LON = float(os.getenv("GS_LON", -118.2437))
GS_ELEV = float(os.getenv("GS_ELEV", 0.0))

CONTROL_TOPIC = f"edge/control/{STATION_ID}/target"

def get_supported_satellites():
    sats = []
    for norad_id in DemodulatorRegistry._registry.keys():
        sats.append({
            "norad_id": norad_id,
            "name": f"SAT-{norad_id}"
        })
    return sats

def publish_target_switch(client, norad_id):
    payload = {"target_norad_id": norad_id}
    client.publish(CONTROL_TOPIC, json.dumps(payload), qos=1)
    logging.info(f"Published target switch to NORAD {norad_id}")

def main():
    logging.info(f"Starting Edge Autotrack for Station: {STATION_ID}")
    logging.info(f"Ground Station Coordinates: {GS_LAT}, {GS_LON}")
    
    # Setup MQTT
    client = mqtt.Client(transport="websockets" if MQTT_PORT in [9001, 443] else "tcp")
    if MQTT_PORT in [9001, 443]:
        client.ws_set_options(path="/mqtt")
        
    if MQTT_USER and MQTT_PASS:
        client.username_pw_set(MQTT_USER, MQTT_PASS)
        
    try:
        client.connect(MQTT_HOST, MQTT_PORT, 60)
        client.loop_start()
    except Exception as e:
        logging.error(f"Failed to connect to MQTT broker: {e}")
        return

    sats = get_supported_satellites()
    logging.info(f"Loaded {len(sats)} supported satellites from DemodulatorRegistry: {[s['norad_id'] for s in sats]}")

    current_target = None

    while True:
        try:
            # Predict passes for the next 6 hours
            prediction = predict_passes(
                satellite_summaries=sats,
                lat=GS_LAT,
                lon=GS_LON,
                elevation_m=GS_ELEV,
                lookahead_hours=6,
                min_elevation=10.0,
                include_tracks=False
            )
            
            passes = prediction.get("passes", [])
            if not passes:
                logging.info("No passes found in the next 6 hours. Sleeping for 15 minutes...")
                time.sleep(900)
                continue

            # Find the next pass that hasn't ended yet
            now = datetime.now(timezone.utc)
            next_pass = None
            for p in passes:
                los = datetime.fromisoformat(p["los"].replace("Z", "+00:00"))
                if los > now:
                    next_pass = p
                    break

            if not next_pass:
                logging.info("All predicted passes have already finished. Re-predicting...")
                time.sleep(60)
                continue

            aos = datetime.fromisoformat(next_pass["aos"].replace("Z", "+00:00"))
            los = datetime.fromisoformat(next_pass["los"].replace("Z", "+00:00"))
            target_id = next_pass["norad_id"]
            
            # If we are currently IN the pass
            if aos <= now <= los:
                if current_target != target_id:
                    logging.info(f"Currently in pass for NORAD {target_id}! Switching immediately.")
                    publish_target_switch(client, target_id)
                    current_target = target_id
                
                sleep_seconds = (los - now).total_seconds() + 5
                logging.info(f"Tracking {target_id}. Sleeping until LOS (+5s): {sleep_seconds:.1f}s")
                time.sleep(sleep_seconds)
                continue

            # If the pass is in the future
            if aos > now:
                time_until_aos = (aos - now).total_seconds()
                # Switch target 1 minute before AOS to give GNU Radio time to spin up
                switch_lead_time = 60
                
                if time_until_aos <= switch_lead_time:
                    if current_target != target_id:
                        logging.info(f"Upcoming pass for NORAD {target_id} in {time_until_aos:.1f}s. Switching now.")
                        publish_target_switch(client, target_id)
                        current_target = target_id
                    
                    # Sleep until LOS
                    sleep_seconds = (los - now).total_seconds() + 5
                    logging.info(f"Tracking {target_id}. Sleeping until LOS (+5s): {sleep_seconds:.1f}s")
                    time.sleep(sleep_seconds)
                else:
                    sleep_seconds = time_until_aos - switch_lead_time
                    logging.info(f"Next pass is NORAD {target_id} at {aos}. Sleeping for {sleep_seconds:.1f}s...")
                    time.sleep(sleep_seconds)

        except KeyboardInterrupt:
            logging.info("Shutting down autotrack daemon...")
            break
        except Exception as e:
            logging.error(f"Error in prediction loop: {e}", exc_info=True)
            time.sleep(60)

    client.loop_stop()
    client.disconnect()

if __name__ == "__main__":
    main()
