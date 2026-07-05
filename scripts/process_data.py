"""
Telemetry Processing Pipeline.

Implements the full data refinement pipeline for Project Wedjat:

    data/raw/{norad_id}/*.jsonl   (SatNOGS API fetches)
      ↓  Stage 1: Decode (Kaitai Structs)
    data/interim/{norad_id}.csv   (All decoded fields, unmodified)
      ↓  Stage 2: Adapt (Unit conversion + field mapping)
    data/processed/{norad_id}.csv (SI-unit Golden Features, ML-ready)

Usage:
    pixi run python scripts/process_data.py --norad 43880
    pixi run python scripts/process_data.py --all
    just process                    # Interactive
    just process --norad 43880      # Specific satellite
"""

import json
import argparse
from collections import Counter
import pandas as pd
from pathlib import Path

from loguru import logger
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

# Import the core — triggers decoder registration via decoders/__init__.py
from gr_sat.core.processing import (
    annotate_pass_and_cadence_metadata,
    deduplicate_processed_frames,
)
from gr_sat.core.satellite_profiles import feature_completeness_mask, get_satellite_profile
from gr_sat.core.telemetry import DecoderRegistry
import gr_sat.core.decoders  # noqa: F401

# --- Paths (matching README data directory structure) ---
RAW_DIR = Path("data/raw")
INTERIM_DIR = Path("data/interim")
PROCESSED_DIR = Path("data/processed")

# Ensure output directories exist
INTERIM_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# --- Logging ---
logger.configure(
    handlers=[
        {"sink": RichHandler(show_time=False, markup=True), "format": "{message}"}
    ]
)


def load_raw_frames(sat_dir: Path) -> list[dict]:
    """Read all JSONL files for a satellite and return a list of raw records."""
    frames = []
    for filepath in sorted(sat_dir.glob("*.jsonl")):
        with open(filepath, "r") as f:
            for line in f:
                try:
                    frames.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return frames


def _log_failure_breakdown(stage_name: str, counts: Counter) -> None:
    if not counts:
        return
    breakdown = ", ".join(f"{code}={count}" for code, count in sorted(counts.items()))
    logger.info(f"{stage_name} failure breakdown: {breakdown}")


def process_satellite(norad_id: str):
    """
    Run the full pipeline for a single satellite:
      1. Load raw JSONL frames from data/raw/{norad_id}/
      2. Decode via Kaitai Structs → data/interim/{norad_id}.csv
      3. Adapt to Golden Features → data/processed/{norad_id}.csv
    """
    norad_int = int(norad_id)
    sat_dir = RAW_DIR / str(norad_id)

    if not sat_dir.exists():
        logger.warning(f"No raw data found for NORAD {norad_id} at {sat_dir}")
        return

    # Get the registered decoder
    decoder = DecoderRegistry.get_decoder(norad_int)
    if not decoder:
        supported = DecoderRegistry.list_supported()
        logger.error(
            f"No decoder registered for NORAD {norad_id}. Supported: {supported}"
        )
        return

    try:
        profile = get_satellite_profile(norad_int)
    except KeyError as exc:
        logger.error(str(exc))
        return

    # Load raw data
    raw_records = load_raw_frames(sat_dir)
    if not raw_records:
        logger.warning(f"No .jsonl records found in {sat_dir}")
        return

    logger.info(
        f"Processing [cyan]NORAD {norad_id}[/] — "
        f"{len(raw_records)} raw frames from {len(list(sat_dir.glob('*.jsonl')))} files"
    )

    # --- Stage 1: Decode (raw bytes → interim) ---
    interim_rows = []
    decode_failures = 0
    decode_failure_counts: Counter[str] = Counter()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
    ) as progress:
        task = progress.add_task(
            f"[green]Stage 1: Decoding {norad_id}...", total=len(raw_records)
        )

        for record in raw_records:
            progress.advance(task)

            hex_payload = record.get("frame")
            timestamp_str = record.get("timestamp")

            if not hex_payload or not timestamp_str:
                continue

            try:
                payload_bytes = bytes.fromhex(hex_payload)
                decoded_outcome = decoder.decode_with_diagnostics(payload_bytes)

                if decoded_outcome.ok:
                    decoded = dict(decoded_outcome.data)
                    decoded["timestamp"] = timestamp_str
                    decoded["observation_id"] = record.get("observation_id")
                    decoded["raw_frame"] = hex_payload
                    interim_rows.append(decoded)
                else:
                    decode_failures += 1
                    decode_failure_counts[decoded_outcome.failure.code] += 1

            except ValueError:
                decode_failures += 1
                decode_failure_counts["invalid_hex_payload"] += 1
                continue

    if not interim_rows:
        logger.warning(f"No valid frames decoded for NORAD {norad_id}")
        _log_failure_breakdown("Decode", decode_failure_counts)
        return

    # Build interim DataFrame
    df_interim = pd.DataFrame(interim_rows)
    df_interim["timestamp"] = pd.to_datetime(df_interim["timestamp"])
    df_interim = df_interim.sort_values("timestamp")

    # Save interim (all Kaitai fields, unmodified)
    interim_file = INTERIM_DIR / f"{norad_id}.csv"
    df_interim.to_csv(interim_file, index=False)

    logger.success(
        f"Stage 1 complete → [bold]{interim_file}[/] "
        f"({len(df_interim)} frames, {decode_failures} failures)"
    )
    _log_failure_breakdown("Decode", decode_failure_counts)

    # --- Stage 2: Adapt (interim → processed Golden Features) ---
    adapted_rows = []
    adapt_failures = 0
    adapt_failure_counts: Counter[str] = Counter()

    for _, row in df_interim.iterrows():
        adapted_outcome = decoder.adapt_with_diagnostics(row.to_dict())
        if adapted_outcome.ok:
            adapted = dict(adapted_outcome.data)
            adapted["timestamp"] = row["timestamp"]
            adapted["observation_id"] = row.get("observation_id")
            if "raw_frame" in row:
                adapted["raw_frame"] = row["raw_frame"]
            adapted_rows.append(adapted)
        else:
            adapt_failures += 1
            adapt_failure_counts[adapted_outcome.failure.code] += 1

    if not adapted_rows:
        logger.warning(f"No frames adapted for NORAD {norad_id}")
        _log_failure_breakdown("Adapt", adapt_failure_counts)
        return

    # Build processed DataFrame
    df_processed = pd.DataFrame(adapted_rows)

    df_processed, dedup_stats = deduplicate_processed_frames(df_processed)
    dupes = dedup_stats["exact_duplicates_removed"]
    df_processed = annotate_pass_and_cadence_metadata(
        df_processed,
        pass_gap_seconds=profile.pass_gap_seconds,
        cadence_tolerance_ratio=profile.cadence_tolerance_ratio,
        cadence_min_tolerance_seconds=profile.cadence_min_tolerance_seconds,
        rolling_window=profile.rolling_window,
    )

    partial_frames = 0
    if "frame_is_complete" in df_processed.columns:
        partial_frames = int((~df_processed["frame_is_complete"].fillna(False)).sum())

    train_ready_rows = int(
        feature_completeness_mask(
            df_processed,
            profile.feature_contract.feature_names,
        ).sum()
    )
    irregular_rows = int(df_processed["sampling_irregular"].sum())
    dropped_packet_rows = int(df_processed["dropped_packet_suspect"].sum())

    # Save processed (Golden Features, ML-ready)
    processed_file = PROCESSED_DIR / f"{norad_id}.csv"
    df_processed.to_csv(processed_file, index=False)

    logger.success(
        f"Stage 2 complete → [bold]{processed_file}[/] "
        f"({len(df_processed)} frames, {dupes} exact dupes removed, {adapt_failures} adapt failures, "
        f"{partial_frames} partial frames)"
    )
    logger.info(
        "  Dedup Stats: "
        f"{dedup_stats['same_timestamp_multi_payload_groups']} same-timestamp multi-payload groups preserved | "
        f"{dedup_stats['same_observation_multi_payload_rows']} rows share an observation_id but differ by payload"
    )
    logger.info(
        "  Cadence Stats: "
        f"{irregular_rows} irregular cadence rows | "
        f"{dropped_packet_rows} dropped-packet suspects | "
        f"{train_ready_rows} rows complete for feature contract v{profile.feature_contract.version}"
    )
    _log_failure_breakdown("Adapt", adapt_failure_counts)

    # Summary
    logger.info(f"[bold]Pipeline complete for NORAD {norad_id}[/]")
    logger.info(f"  Interim:   {len(df_interim):>6} rows → {interim_file}")
    logger.info(f"  Processed: {len(df_processed):>6} rows → {processed_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Telemetry Processing Pipeline — raw → interim → processed"
    )
    parser.add_argument("--norad", type=str, help="Specific NORAD ID to process")
    parser.add_argument(
        "--all", action="store_true", help="Process all satellites with raw data"
    )

    args = parser.parse_args()

    # Show supported decoders
    supported = DecoderRegistry.list_supported()
    logger.info(f"Registered decoders: {supported}")

    if args.norad:
        process_satellite(args.norad)
    elif args.all:
        # Process all satellite directories that have a registered decoder
        for sat_dir in sorted(RAW_DIR.iterdir()):
            if sat_dir.is_dir():
                norad_id = sat_dir.name
                if DecoderRegistry.get_decoder(int(norad_id)):
                    process_satellite(norad_id)
                else:
                    logger.debug(f"Skipping {norad_id} (no registered decoder)")
    else:
        # Interactive: list available satellites
        sat_dirs = sorted(
            d.name
            for d in RAW_DIR.iterdir()
            if d.is_dir() and DecoderRegistry.get_decoder(int(d.name))
        )
        if not sat_dirs:
            logger.error("No raw data found for any supported satellite.")
            return

        print("\n[?] Available satellites with raw data + decoder:")
        for i, nid in enumerate(sat_dirs, 1):
            decoder_name = supported.get(int(nid), "Unknown")
            n_files = len(list((RAW_DIR / nid).glob("*.jsonl")))
            print(f"    {i}. NORAD {nid} ({decoder_name}) — {n_files} files")
        print("    A. All")

        choice = input("\n> Select [A]: ").strip().upper()

        if choice == "A" or choice == "":
            for nid in sat_dirs:
                process_satellite(nid)
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(sat_dirs):
                    process_satellite(sat_dirs[idx])
                else:
                    logger.error("Invalid selection.")
            except ValueError:
                logger.error("Invalid input.")


if __name__ == "__main__":
    main()
