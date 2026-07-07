import os
import sys
import time
import argparse
import httpx
from pathlib import Path
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Modern Tooling
from loguru import logger
from rich.logging import RichHandler

# Ensure we can import from src directory
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

# Load environment variables
load_dotenv()

# --- LOGGING SETUP ---
logger.configure(
    handlers=[
        {
            "sink": RichHandler(markup=True, rich_tracebacks=True, show_time=False),
            "format": "{message}",
            "level": "INFO",
        },
        {
            "sink": "logs/tle_fetcher_{time}.log",
            "rotation": "10 MB",
            "retention": "1 week",
            "format": "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
            "level": "DEBUG",
        },
    ]
)

SPACETRACK_LOGIN_URL = "https://www.space-track.org/ajaxauth/login"
SPACETRACK_BASE_QUERY_URL = "https://www.space-track.org/basicspacedata/query"


def parse_epoch(epoch_str: str) -> datetime:
    """Robustly parse epoch string from Space-Track into UTC datetime."""
    # Space-Track epoch: "2026-07-05 18:30:15" or "2026-07-05 18:30:15.123456"
    normalized = epoch_str.replace(" ", "T")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def fetch_tle_spacetrack(
    email: str, password: str, norad_id: int, start_date: datetime, end_date: datetime
) -> list:
    """Authenticate with Space-Track and fetch historical TLEs in JSON format."""
    logger.info(f"Authenticating with Space-Track using email: {email}")

    # Establish session with redirect handling
    client = httpx.Client(follow_redirects=True)

    login_data = {"identity": email, "password": password}

    try:
        login_resp = client.post(SPACETRACK_LOGIN_URL, data=login_data, timeout=15.0)
        login_resp.raise_for_status()

        # Check if login was actually successful
        if (
            login_resp.status_code != 200
            or "error" in login_resp.text.lower()
            or "fail" in login_resp.text.lower()
        ):
            logger.error(
                f"Authentication failed. Status: {login_resp.status_code}, Response: {login_resp.text}"
            )
            return []

        logger.success("Authenticated successfully with Space-Track.")
    except Exception as e:
        logger.critical(f"Failed to connect or log in to Space-Track: {e}")
        return []

    # Format dates as YYYY-MM-DD for Space-Track query syntax
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    # Construct the query URL
    # class: gp_history
    # filter: NORAD_CAT_ID/<norad_id>
    # filter: EPOCH/<start>--<end>
    # orderby: EPOCH asc
    # format: json
    query_url = (
        f"{SPACETRACK_BASE_QUERY_URL}/class/gp_history/NORAD_CAT_ID/{norad_id}"
        f"/EPOCH/{start_str}--{end_str}/orderby/EPOCH%20asc/format/json"
    )

    logger.info(f"Querying historical elements: {start_str} to {end_str}...")
    try:
        # Enforce conservative request rate limiting
        time.sleep(1.0)
        response = client.get(query_url, timeout=30.0)
        response.raise_for_status()

        data = response.json()
        if not isinstance(data, list):
            logger.warning(f"Unexpected response format from Space-Track: {data}")
            return []

        logger.success(f"Successfully retrieved {len(data)} TLEs from Space-Track.")
        return data
    except Exception as e:
        logger.error(f"Failed to query elements from Space-Track: {e}")
        return []
    finally:
        client.close()


def save_to_database(tle_records: list, norad_id: int) -> int:
    """Inserts fetched TLEs into the database, ignoring duplicates."""
    engine = None
    try:
        from api.database import get_engine
        from api.db_models import TleRecord
        from sqlmodel import Session, select

        engine = get_engine()
    except ImportError as e:
        logger.warning(
            f"Could not import database dependencies: {e}. Skipping DB insert."
        )
        return 0

    if not engine:
        logger.warning("Database engine not configured/available. Skipping DB insert.")
        return 0

    inserted_count = 0
    try:
        with Session(engine) as session:
            # Load existing epochs for this satellite to avoid duplicate insertions
            stmt = select(TleRecord.epoch_timestamp).where(
                TleRecord.norad_id == norad_id
            )
            existing_epochs = set(session.exec(stmt).all())
            logger.debug(
                f"Found {len(existing_epochs)} existing TLE epochs in DB for NORAD {norad_id}."
            )

            for item in tle_records:
                epoch_str = item.get("EPOCH")
                line1 = item.get("TLE_LINE1")
                line2 = item.get("TLE_LINE2")

                if not epoch_str or not line1 or not line2:
                    continue

                epoch_dt = parse_epoch(epoch_str)

                # Deduplicate based on exact epoch timestamp
                if epoch_dt in existing_epochs:
                    continue

                tle_rec = TleRecord(
                    norad_id=norad_id,
                    epoch_timestamp=epoch_dt,
                    tle_line1=line1.strip(),
                    tle_line2=line2.strip(),
                    source="spacetrack",
                )
                session.add(tle_rec)
                existing_epochs.add(epoch_dt)
                inserted_count += 1

            session.commit()

        logger.success(f"Saved {inserted_count} new TLE records to database.")
    except Exception as e:
        logger.error(f"Database insertion failed: {e}")

    return inserted_count


def write_fallback_cache(tle_records: list, norad_id: int):
    """Writes the latest TLE lines to the fallback cache file."""
    if not tle_records:
        return

    latest_item = tle_records[-1]
    line1 = latest_item.get("TLE_LINE1")
    line2 = latest_item.get("TLE_LINE2")

    if not line1 or not line2:
        return

    cache_dir = Path("data/cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"tle_{norad_id}.txt"

    try:
        cache_content = f"{line1.strip()}\n{line2.strip()}\n"
        cache_file.write_text(cache_content)
        logger.info(f"Updated local offline cache file: {cache_file}")
    except Exception as e:
        logger.error(f"Failed to update cache file: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Space-Track Historical TLE Downloader"
    )
    parser.add_argument(
        "--norad", type=int, required=True, help="NORAD ID of the target satellite"
    )
    parser.add_argument("--days", type=int, default=30, help="Days of history to fetch")
    parser.add_argument(
        "--start", type=str, help="Start date (YYYY-MM-DD), overrides --days"
    )
    parser.add_argument(
        "--end", type=str, help="End date (YYYY-MM-DD), default is today"
    )

    args = parser.parse_args()

    email = os.getenv("SPACETRACK_EMAIL")
    password = os.getenv("SPACETRACK_PASSWORD")

    if not email or not password:
        logger.critical(
            "SPACETRACK_EMAIL or SPACETRACK_PASSWORD not set in environment or .env file."
        )
        sys.exit(1)

    # Time Window Calculation
    if args.end:
        end_dt = datetime.strptime(args.end, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        end_dt = datetime.now(timezone.utc)

    if args.start:
        start_dt = datetime.strptime(args.start, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
    else:
        start_dt = end_dt - timedelta(days=args.days)

    logger.info(
        f"Fetching elements for NORAD {args.norad} from {start_dt.date()} to {end_dt.date()}"
    )

    raw_records = fetch_tle_spacetrack(email, password, args.norad, start_dt, end_dt)

    if raw_records:
        # Save to database (ignores duplicate epochs)
        save_to_database(raw_records, args.norad)

        # Write the absolute latest record to the offline fallback file
        write_fallback_cache(raw_records, args.norad)
    else:
        logger.warning("No TLE elements were retrieved.")


if __name__ == "__main__":
    main()
