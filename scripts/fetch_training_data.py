import os
import json
import time
import argparse
import sys
import httpx
from pathlib import Path
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Modern Tooling
from loguru import logger
from rich.logging import RichHandler
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
)

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
SATNOGS_API_URL = "https://db.satnogs.org/api/telemetry/"
API_TOKEN = os.getenv("SATNOGS_API_TOKEN")
MAX_RETRIES = 5
CHUNK_SIZE_DAYS = 1

# Rate Limiting (SatNOGS: ~1 req/sec is safe, or 240/hr = 1 req/15s conservatively)
# We'll stick to a safe 2s delay between requests to avoid hitting 429s constantly.
REQUEST_DELAY_SECONDS = 5.0

# --- LOAD TARGETS FROM CENTRAL REGISTRY ---
from gr_sat.core.satellite_profiles import _SATELLITE_PROFILES
TARGETS = {str(k): v.name for k, v in _SATELLITE_PROFILES.items()}
logger.info(f"Loaded {len(TARGETS)} targets from core satellite profiles.")

# --- LOGGING SETUP ---
logger.configure(
    handlers=[
        {
            "sink": RichHandler(markup=True, rich_tracebacks=True, show_time=False),
            "format": "{message}",
            "level": "INFO",
        },
        {
            "sink": "logs/downloader_{time}.log",
            "rotation": "10 MB",
            "retention": "1 week",
            "format": "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
            "level": "DEBUG",
        },
    ]
)


class SatNOGSDownloader:
    def __init__(self, output_dir="data/raw"):
        self.token = API_TOKEN
        self.base_url = SATNOGS_API_URL
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if not self.token:
            logger.critical("SATNOGS_API_TOKEN not found in .env file.")
            sys.exit(1)

        self.session = httpx.Client(
            headers={
                "Authorization": f"Token {self.token}",
                "Accept": "application/json",
            }
        )

    def _get_chunk_filename(self, norad_id: str, chunk_start: datetime) -> Path:
        sat_dir = self.output_dir / str(norad_id)
        sat_dir.mkdir(parents=True, exist_ok=True)
        return sat_dir / f"{chunk_start.strftime('%Y-%m-%d')}.jsonl"

    def download_chunk(
        self,
        norad_id: str,
        chunk_start: datetime,
        chunk_end: datetime,
        progress_task_id,
        progress_obj,
    ):
        """
        Downloads frames for a specific time chunk and streams them to disk.
        """
        outfile = self._get_chunk_filename(norad_id, chunk_start)
        sat_name = TARGETS.get(norad_id, "Unknown")
        date_str = chunk_start.strftime("%Y-%m-%d")

        # Display Context (Persist in logs)
        log_prefix = f"[cyan]{sat_name}[/] ([dim]{norad_id}[/]) | [green]{date_str}[/]"

        # Checkpointing
        if outfile.exists() and outfile.stat().st_size > 0:
            logger.info(f"{log_prefix} | Skipped (Exists)")
            return

        params = {
            "satellite": norad_id,
            "format": "json",
            "start": chunk_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end": chunk_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "page": 1,
        }

        # Update Progress Bar (Show what we are working on)
        progress_obj.update(progress_task_id, description=f"Fetching {log_prefix}...")

        frames_downloaded = 0
        chunk_seen_hashes = set()  # Circuit breaker for infinite page loops

        # Cursor Pagination Logic
        # We start with the base URL and params. Subsequent requests use the 'next' URL from the API.
        current_url = self.base_url
        current_params = params

        with open(outfile, "a") as f:
            while True:
                retry_count = 0
                success = False

                # Enforce Rate Limit (Pre-emptive)
                time.sleep(REQUEST_DELAY_SECONDS)

                # Retry Loop
                while retry_count < MAX_RETRIES:
                    try:
                        # Use params only if we are hitting the base URL (first page)
                        # If we are following a 'next' link, params are already in the string.
                        req_params = (
                            current_params if current_url == self.base_url else None
                        )

                        response = self.session.get(
                            current_url, params=req_params, timeout=15
                        )

                        if response.status_code == 429:
                            sleep_time = 60 * (retry_count + 1)
                            logger.warning(
                                f"{log_prefix} | [yellow]Rate Limit (429)[/] Sleeping {sleep_time}s..."
                            )

                            # Visual Countdown
                            for remaining in range(sleep_time, 0, -1):
                                progress_obj.update(
                                    progress_task_id,
                                    description=f"[yellow]Rate Limit: Sleeping {remaining}s...[/] {log_prefix}",
                                )
                                time.sleep(1)

                            # Restore description
                            progress_obj.update(
                                progress_task_id,
                                description=f"Fetching {log_prefix}...",
                            )
                            retry_count += 1
                            continue

                        if response.status_code == 404:
                            logger.warning(f"{log_prefix} | [yellow]No Data (404)[/]")
                            success = False
                            break

                        response.raise_for_status()
                        raw_data = response.json()

                        # Handle Pagination
                        if isinstance(raw_data, dict) and "results" in raw_data:
                            frames_list = raw_data["results"]
                        elif isinstance(raw_data, list):
                            frames_list = raw_data
                        else:
                            frames_list = []

                        success = True
                        break

                    except Exception as e:
                        logger.error(f"{log_prefix} | Network Error: {e}")
                        time.sleep(5 * (retry_count + 1))
                        retry_count += 1

                if not success:
                    break

                if not frames_list:
                    break

                # --- LOOP DETECTION (Circuit Breaker) ---
                if len(frames_list) > 0:
                    first_frame = frames_list[0]
                    page_sig = f"{first_frame.get('timestamp')}_{first_frame.get('observation_id')}_{len(frames_list)}"

                    if page_sig in chunk_seen_hashes:
                        logger.warning(
                            f"{log_prefix} | [red]Loop Detected[/] (API returned duplicate page). Stopping chunk."
                        )
                        break
                    chunk_seen_hashes.add(page_sig)
                # ----------------------------------------

                for frame in frames_list:
                    f.write(json.dumps(frame) + "\n")
                    frames_downloaded += 1

                # PAGINATION UPDATE
                # Check for 'next' link. If present, use it for the next iteration.
                next_link = raw_data.get("next")
                if next_link:
                    current_url = next_link
                    current_params = None  # Clear params since they are in the URL now
                else:
                    break  # End of pages

        # Cleanup
        if frames_downloaded == 0:
            if outfile.exists() and outfile.stat().st_size == 0:
                outfile.unlink()
                if success:
                    logger.info(f"{log_prefix} | [yellow]Empty (0 frames)[/]")
        else:
            logger.success(f"{log_prefix} | Saved {frames_downloaded} frames")


@logger.catch
def main():
    parser = argparse.ArgumentParser(description="SatNOGS Downloader")
    parser.add_argument("--days", type=int, default=30, help="Days to look back")
    parser.add_argument("--norad", type=str, help="Single NORAD ID to fetch.")
    parser.add_argument(
        "--all", action="store_true", help="Fetch ALL configured satellites."
    )
    parser.add_argument("--start", type=str, help="Start YYYY-MM-DD")
    parser.add_argument("--end", type=str, help="End YYYY-MM-DD")

    args = parser.parse_args()

    # Target Selection Logic
    if args.norad:
        targets = {args.norad: TARGETS.get(args.norad, "Manual Target")}
    elif args.all:
        targets = TARGETS
    else:
        # Interactive Mode
        logger.info("[bold]Interactive Mode[/]")
        print("\n[?] Select Target:")
        opts = list(TARGETS.items())
        for i, (nid, name) in enumerate(opts):
            print(f"    {i + 1}. {name} ({nid})")
        print("    A. All Satellites (Default)")

        choice = input("\n> Select [A]: ").strip().upper()

        if choice == "A" or choice == "":
            targets = TARGETS
            logger.info("Selected: [bold]All Satellites[/]")
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(opts):
                    sel_nid, sel_name = opts[idx]
                    targets = {sel_nid: sel_name}
                    logger.info(f"Selected: [bold]{sel_name}[/]")
                else:
                    logger.error("Invalid selection number.")
                    sys.exit(1)
            except ValueError:
                logger.error("Invalid input.")
                sys.exit(1)

        # Interactive Time Window (Only if not set via flags)
        if not args.start and not args.end:
            d_input = input(f"\n> Days to look back [{args.days}]: ").strip()
            if d_input:
                try:
                    args.days = int(d_input)
                except ValueError:
                    logger.error("Invalid number for days.")
                    sys.exit(1)

    # Time Window
    if args.start and args.end:
        start_dt = datetime.strptime(args.start, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
        end_dt = datetime.strptime(args.end, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        end_dt = datetime.now(timezone.utc)
        start_dt = end_dt - timedelta(days=args.days)

    # Calculate Steps
    total_days = (end_dt - start_dt).days
    total_steps = total_days * len(targets)

    downloader = SatNOGSDownloader()

    logger.info(
        f"Targeting [bold]{len(targets)}[/] Satellites | Window: {start_dt.date()} -> {end_dt.date()}"
    )

    # RICH PROGRESS BAR
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
    ) as progress:
        main_task = progress.add_task("[green]Total Progress", total=total_steps)

        current_dt = start_dt
        while current_dt < end_dt:
            chunk_end = current_dt + timedelta(days=CHUNK_SIZE_DAYS)
            if chunk_end > end_dt:
                chunk_end = end_dt

            for norad_id, name in targets.items():
                downloader.download_chunk(
                    norad_id, current_dt, chunk_end, main_task, progress
                )
                progress.advance(main_task)

            current_dt = chunk_end

    logger.success("Download Complete.")


if __name__ == "__main__":
    main()
