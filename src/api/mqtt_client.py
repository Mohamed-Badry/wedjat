import os
import json
from loguru import logger
from datetime import datetime
import paho.mqtt.client as mqtt
from sqlmodel import Session

try:
    from .database import get_engine
    from .db_models import RawFrame, TelemetryRow
    from .dashboard_data import DashboardDataRepository
except ImportError:
    from database import get_engine
    from db_models import RawFrame, TelemetryRow
    from dashboard_data import DashboardDataRepository

import pandas as pd
from gr_sat.core.telemetry import process_frame_result
import threading
import queue



score_queue = queue.Queue()

def scoring_worker(repository):
    logger.info("Started background scoring worker thread.")
    while True:
        task = score_queue.get()
        if task is None:
            break
            
        telem_id, norad_id, features = task
        try:
            model_status = repository.model_status(norad_id)
            if model_status.status == "ready":
                df = pd.DataFrame([features])
                df["timestamp"] = datetime.now()
                df["is_anomaly"] = False
                df["anomaly_score"] = float("nan")
                
                df = repository._score_frames(norad_id, df, model_status)
                
                if not df.empty and not pd.isna(df.iloc[0]["anomaly_score"]):
                    anomaly_score = float(df.iloc[0]["anomaly_score"])
                    is_anomaly = bool(df.iloc[0]["is_anomaly"])
                    
                    engine = get_engine()
                    if engine:
                        with Session(engine) as session:
                            telem = session.get(TelemetryRow, (telem_id, datetime.now())) # Wait, TelemetryRow has compound primary key? Let me check db_models.py
                            # Wait, the primary key is (id, timestamp)? Let me fix the select query to be safe.
                            from sqlmodel import select
                            stmt = select(TelemetryRow).where(TelemetryRow.id == telem_id)
                            telem = session.exec(stmt).first()
                            if telem:
                                telem.anomaly_score = anomaly_score
                                telem.is_anomaly = is_anomaly
                                session.commit()
                                logger.info(f"Asynchronously scored frame {telem_id} for NORAD {norad_id}: score={anomaly_score:.3f}")
        except Exception as e:
            logger.error(f"Error scoring frame asynchronously: {e}", exc_info=True)
        finally:
            score_queue.task_done()


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
            for k, v in features.items():
                if isinstance(v, datetime):
                    features[k] = v.isoformat()
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

                telem_record = TelemetryRow(
                    timestamp=timestamp,
                    norad_id=norad_id,
                    raw_frame_id=raw_record.id,
                    features=features,
                    anomaly_score=None,
                    is_anomaly=False,
                    missing_fields=missing,
                    frame_is_complete=len(missing) == 0,
                    missing_raw_fields=json.dumps(missing),
                    dropped_packet_suspect=False,
                    sampling_irregular=False,
                    pass_id=None,
                    pass_duration_sec=None,
                    pass_frame_count=None,
                )
                session.add(telem_record)
                
                # Single atomic commit
                session.commit()
                session.refresh(telem_record)
                logger.info(f"Persisted frame for NORAD {norad_id}")
                
                if res.frame and hasattr(client, "_repository"):
                    score_queue.put((telem_record.id, int(norad_id), features))
                    
            except Exception as e:
                session.rollback()
                logger.error("Transaction failed, rolled back.", exc_info=True)

    except Exception as e:
        logger.error("Error processing MQTT message.", exc_info=True)


def start_mqtt_client(repository=None):
    broker_url = os.getenv("MQTT_BROKER_URL", "localhost")
    broker_port = int(os.getenv("MQTT_BROKER_PORT", 1883))
    username = os.getenv("MQTT_USERNAME")
    password = os.getenv("MQTT_PASSWORD")
    use_tls = os.getenv("MQTT_USE_TLS", "false").lower() == "true"

    client = mqtt.Client()
    
    if repository:
        client._repository = repository
        threading.Thread(target=scoring_worker, args=(repository,), daemon=True).start()
    
    if username and password:
        client.username_pw_set(username, password)
    
    if use_tls:
        client.tls_set()
        
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
