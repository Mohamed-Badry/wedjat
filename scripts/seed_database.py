import sys
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
from loguru import logger
from sqlmodel import Session, select

# Ensure api and gr_sat can be imported
sys.path.append(str(Path(__file__).parent.parent / "src"))

from api.database import get_engine
from api.db_models import RawFrame, TelemetryRow
from api.dashboard_data import DashboardDataRepository

# Feature keys of TelemetryFrame
FEATURE_KEYS = [
    "src_callsign", "dest_callsign",
    "batt_voltage", "batt_current",
    "batt_a_voltage", "batt_b_voltage",
    "batt_a_current", "batt_b_current",
    "power_consumption", "temp_obc",
    "temp_batt_a", "temp_batt_b", "temp_panel_z",
    "uptime"
]

def seed_satellite(norad_id: int):
    logger.info(f"Starting database seeding for NORAD {norad_id}...")
    csv_path = Path("data/processed") / f"{norad_id}.csv"
    if not csv_path.exists():
        logger.error(f"Processed CSV not found at {csv_path}")
        return

    df = pd.read_csv(csv_path)
    logger.info(f"Loaded {len(df)} rows from {csv_path}")

    engine = get_engine()
    if not engine:
        logger.error("Database engine not configured.")
        return

    # Check if a model is ready to compute anomaly scores on the fly
    repo = DashboardDataRepository(processed_dir="data/processed")
    model_status = repo.model_status(norad_id)
    has_model = model_status.status == "ready"
    if has_model:
        logger.info(f"Trained model found for NORAD {norad_id}. Anomaly scores will be computed during seeding.")
        # Compute anomaly scores for the whole dataframe
        score_df = df.copy()
        score_df["timestamp"] = pd.to_datetime(score_df["timestamp"])
        score_df["is_anomaly"] = False
        score_df["anomaly_score"] = float("nan")
        try:
            scored = repo._score_frames(norad_id, score_df, model_status)
            df["anomaly_score"] = scored["anomaly_score"]
            df["is_anomaly"] = scored["is_anomaly"]
            logger.info("Successfully computed anomaly scores.")
        except Exception as e:
            logger.warning(f"Failed to score telemetry on the fly: {e}. Seeding without scores.")
            df["anomaly_score"] = None
            df["is_anomaly"] = False
    else:
        logger.info(f"No trained model found for NORAD {norad_id}. Seeding with null anomaly scores.")
        df["anomaly_score"] = None
        df["is_anomaly"] = False

    # Convert timestamps
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    batch_size = 500
    rows_added = 0

    with Session(engine) as session:
        # Get existing timestamps to prevent duplicates
        existing_ts = set(
            session.exec(
                select(TelemetryRow.timestamp).where(TelemetryRow.norad_id == norad_id)
            ).all()
        )
        logger.info(f"Found {len(existing_ts)} existing rows in database. Skipping duplicates.")

        batch = []

        for idx, row in df.iterrows():
            ts = row["timestamp"]
            # Convert to UTC datetime timezone-aware
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            else:
                ts = ts.astimezone(timezone.utc)

            if ts in existing_ts:
                continue

            raw_frame_hex = str(row["raw_frame"]) if "raw_frame" in row and pd.notna(row["raw_frame"]) else ""
            snr = float(row["snr"]) if "snr" in row and pd.notna(row["snr"]) else None
            
            raw_record = RawFrame(
                timestamp=ts,
                norad_id=norad_id,
                station_id="satnogs_db",
                raw_frame=raw_frame_hex,
                snr=snr
            )
            session.add(raw_record)
            batch.append((raw_record, row))

            if len(batch) >= batch_size:
                session.flush()  # Populate raw frame IDs
                for r_rec, r_row in batch:
                    features = {}
                    for k in FEATURE_KEYS:
                        if k in r_row and pd.notna(r_row[k]):
                            val = r_row[k]
                            if isinstance(val, (int, float)):
                                features[k] = float(val)
                            else:
                                features[k] = str(val)

                    req_keys = ["batt_voltage", "batt_current", "temp_obc", "temp_batt_a", "temp_panel_z"]
                    
                    if "frame_is_complete" in r_row and pd.notna(r_row["frame_is_complete"]):
                        frame_is_complete = bool(r_row["frame_is_complete"])
                    else:
                        frame_is_complete = all(k in features and features[k] is not None for k in req_keys)

                    if "missing_raw_fields" in r_row and pd.notna(r_row["missing_raw_fields"]):
                        missing_raw_fields = str(r_row["missing_raw_fields"])
                        try:
                            import json
                            missing = json.loads(missing_raw_fields) if isinstance(missing_raw_fields, str) else []
                        except Exception:
                            missing = []
                    else:
                        missing = [f"missing_{k}" for k in req_keys if k not in features or features[k] is None]
                        import json
                        missing_raw_fields = json.dumps(missing)

                    anomaly_score = float(r_row["anomaly_score"]) if pd.notna(r_row["anomaly_score"]) else None
                    is_anomaly = bool(r_row["is_anomaly"]) if pd.notna(r_row["is_anomaly"]) else False

                    dropped_packet_suspect = bool(r_row["dropped_packet_suspect"]) if "dropped_packet_suspect" in r_row and pd.notna(r_row["dropped_packet_suspect"]) else False
                    sampling_irregular = bool(r_row["sampling_irregular"]) if "sampling_irregular" in r_row and pd.notna(r_row["sampling_irregular"]) else False
                    pass_id = int(r_row["pass_id"]) if "pass_id" in r_row and pd.notna(r_row["pass_id"]) else None
                    pass_duration_sec = float(r_row["pass_duration_sec"]) if "pass_duration_sec" in r_row and pd.notna(r_row["pass_duration_sec"]) else None
                    pass_frame_count = int(r_row["pass_frame_count"]) if "pass_frame_count" in r_row and pd.notna(r_row["pass_frame_count"]) else None

                    telem_record = TelemetryRow(
                        timestamp=r_rec.timestamp,
                        norad_id=norad_id,
                        raw_frame_id=r_rec.id,
                        features=features,
                        anomaly_score=anomaly_score,
                        is_anomaly=is_anomaly,
                        missing_fields=missing,
                        frame_is_complete=frame_is_complete,
                        missing_raw_fields=missing_raw_fields,
                        dropped_packet_suspect=dropped_packet_suspect,
                        sampling_irregular=sampling_irregular,
                        pass_id=pass_id,
                        pass_duration_sec=pass_duration_sec,
                        pass_frame_count=pass_frame_count
                    )
                    session.add(telem_record)
                session.commit()
                rows_added += len(batch)
                logger.info(f"Committed {rows_added} rows...")
                batch = []

        # Commit remaining
        if batch:
            session.flush()
            for r_rec, r_row in batch:
                features = {}
                for k in FEATURE_KEYS:
                    if k in r_row and pd.notna(r_row[k]):
                        val = r_row[k]
                        if isinstance(val, (int, float)):
                            features[k] = float(val)
                        else:
                            features[k] = str(val)

                req_keys = ["batt_voltage", "batt_current", "temp_obc", "temp_batt_a", "temp_panel_z"]
                
                if "frame_is_complete" in r_row and pd.notna(r_row["frame_is_complete"]):
                    frame_is_complete = bool(r_row["frame_is_complete"])
                else:
                    frame_is_complete = all(k in features and features[k] is not None for k in req_keys)

                if "missing_raw_fields" in r_row and pd.notna(r_row["missing_raw_fields"]):
                    missing_raw_fields = str(r_row["missing_raw_fields"])
                    try:
                        import json
                        missing = json.loads(missing_raw_fields) if isinstance(missing_raw_fields, str) else []
                    except Exception:
                        missing = []
                else:
                    missing = [f"missing_{k}" for k in req_keys if k not in features or features[k] is None]
                    import json
                    missing_raw_fields = json.dumps(missing)

                anomaly_score = float(r_row["anomaly_score"]) if pd.notna(r_row["anomaly_score"]) else None
                is_anomaly = bool(r_row["is_anomaly"]) if pd.notna(r_row["is_anomaly"]) else False

                dropped_packet_suspect = bool(r_row["dropped_packet_suspect"]) if "dropped_packet_suspect" in r_row and pd.notna(r_row["dropped_packet_suspect"]) else False
                sampling_irregular = bool(r_row["sampling_irregular"]) if "sampling_irregular" in r_row and pd.notna(r_row["sampling_irregular"]) else False
                pass_id = int(r_row["pass_id"]) if "pass_id" in r_row and pd.notna(r_row["pass_id"]) else None
                pass_duration_sec = float(r_row["pass_duration_sec"]) if "pass_duration_sec" in r_row and pd.notna(r_row["pass_duration_sec"]) else None
                pass_frame_count = int(r_row["pass_frame_count"]) if "pass_frame_count" in r_row and pd.notna(r_row["pass_frame_count"]) else None

                telem_record = TelemetryRow(
                    timestamp=r_rec.timestamp,
                    norad_id=norad_id,
                    raw_frame_id=r_rec.id,
                    features=features,
                    anomaly_score=anomaly_score,
                    is_anomaly=is_anomaly,
                    missing_fields=missing,
                    frame_is_complete=frame_is_complete,
                    missing_raw_fields=missing_raw_fields,
                    dropped_packet_suspect=dropped_packet_suspect,
                    sampling_irregular=sampling_irregular,
                    pass_id=pass_id,
                    pass_duration_sec=pass_duration_sec,
                    pass_frame_count=pass_frame_count
                )
                session.add(telem_record)
            session.commit()
            rows_added += len(batch)

    logger.info(f"✅ Successfully seeded {rows_added} rows into database for NORAD {norad_id}.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Seed TimescaleDB with processed historical CSVs")
    parser.add_argument("--norad", type=int, help="NORAD ID of the satellite to seed")
    parser.add_argument("--all", action="store_true", help="Seed all discovered processed CSVs")
    args = parser.parse_args()

    if args.all:
        for csv_file in Path("data/processed").glob("*.csv"):
            try:
                norad_id = int(csv_file.stem)
                seed_satellite(norad_id)
            except ValueError:
                continue
    elif args.norad:
        seed_satellite(args.norad)
    else:
        parser.print_help()
