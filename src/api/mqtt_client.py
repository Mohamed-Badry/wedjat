import os
import json
import logging
from datetime import datetime
import paho.mqtt.client as mqtt
from sqlmodel import Session

try:
    from .database import get_engine
    from .models import RawFrame, TelemetryFrame
    from .dashboard_data import DashboardDataRepository
except ImportError:
    from database import get_engine
    from models import RawFrame, TelemetryFrame
    from dashboard_data import DashboardDataRepository

import pandas as pd
from gr_sat.telemetry import process_frame_result

logger = logging.getLogger("mqtt_client")


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Connected to MQTT Broker!")
        client.subscribe("telemetry/live/#")
    else:
        logger.error(f"Failed to connect, return code {rc}")


def on_message(client, userdata, msg):
    logger.info(f"Received message on topic: {msg.topic}")
    try:
        payload = json.loads(msg.payload.decode())
        norad_id = payload.get("norad_id")
        raw_hex = payload.get("raw_frame")
        station_id = payload.get("station_id")
        snr = payload.get("snr")
        timestamp_str = payload.get("timestamp")

        if not all([norad_id, raw_hex, timestamp_str]):
            logger.warning("Missing required fields in MQTT payload")
            return

        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

        engine = get_engine()
        if not engine:
            logger.warning("Database not configured, cannot persist MQTT message.")
            return

        # Process the frame
        raw_bytes = bytes.fromhex(raw_hex)
        res = process_frame_result(
            norad_id=int(norad_id),
            payload=raw_bytes,
            source=station_id or "mqtt",
            timestamp=timestamp,
        )

        features = {}
        missing = []
        if res.frame:
            # Convert TelemetryFrame dataclass to dict
            features = res.frame.to_dict()
        else:
            if res.failure:
                missing = [f"{res.failure.stage}: {res.failure.code}"]

        with Session(engine, expire_on_commit=False) as session:
            try:
                raw_record = RawFrame(
                    timestamp=timestamp,
                    norad_id=norad_id,
                    station_id=station_id,
                    raw_frame=raw_hex,
                    snr=snr,
                )
                session.add(raw_record)

                # Score anomaly if possible
                is_anomaly = False
                anomaly_score = None

                if res.frame:
                    repo = DashboardDataRepository()
                    model_status = repo.model_status(norad_id)
                    if model_status.status == "ready":
                        # Let's mock a single row dataframe to use the repo's internal scoring for now
                        df = pd.DataFrame([features])
                        df["timestamp"] = timestamp
                        df["is_anomaly"] = False
                        df["anomaly_score"] = float("nan")
                        df = repo._score_frames(norad_id, df, model_status)
                        if not df.empty and not pd.isna(df.iloc[0]["anomaly_score"]):
                            anomaly_score = float(df.iloc[0]["anomaly_score"])
                            is_anomaly = bool(df.iloc[0]["is_anomaly"])

                telem_record = TelemetryFrame(
                    timestamp=timestamp,
                    norad_id=norad_id,
                    raw_frame_id=raw_record.id,
                    features=features,
                    anomaly_score=anomaly_score,
                    is_anomaly=is_anomaly,
                    missing_fields=missing,
                )
                session.add(telem_record)
                
                # Single atomic commit
                session.commit()
                logger.info(f"Persisted frame for NORAD {norad_id}")
            except Exception as e:
                session.rollback()
                logger.error(f"Transaction failed, rolled back: {e}", exc_info=True)

    except Exception as e:
        logger.error(f"Error processing MQTT message: {e}", exc_info=True)


def start_mqtt_client():
    broker_url = os.getenv("MQTT_BROKER_URL", "localhost")
    broker_port = int(os.getenv("MQTT_BROKER_PORT", 1883))

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(broker_url, broker_port, 60)
        client.loop_start()
        logger.info(f"Started MQTT loop connecting to {broker_url}:{broker_port}")
        return client
    except Exception as e:
        logger.error(
            f"Could not connect to MQTT broker at {broker_url}:{broker_port}: {e}"
        )
        return None
