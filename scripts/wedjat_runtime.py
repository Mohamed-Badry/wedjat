"""
Minimal deterministic online wedjat CLI.

Supports either:
  - one-shot inference via --payload-hex / --timestamp
  - JSONL stdin mode for sequential packet processing
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json

from gr_sat.ml.wedjat import OnlineWedjat


def _parse_timestamp(raw_timestamp: str) -> datetime:
    return datetime.fromisoformat(raw_timestamp.replace("Z", "+00:00"))


def _print_result(result) -> None:
    payload = {
        "status": result.status,
        "state": result.state,
        "score": result.score,
        "threshold": result.threshold,
        "is_anomaly": result.is_anomaly,
        "error": result.error,
        "failure_code": result.failure_code,
    }
    print(json.dumps(payload))


def main() -> None:
    parser = argparse.ArgumentParser(description="Minimal online wedjat runtime")
    parser.add_argument("--norad", required=True, help="Satellite NORAD ID")
    parser.add_argument("--payload-hex", help="Single packet payload as hex")
    parser.add_argument("--timestamp", help="Packet timestamp in ISO-8601 format")
    parser.add_argument("--source", default="live_station", help="Packet source label")
    parser.add_argument(
        "--gap-timeout-seconds",
        type=float,
        default=180.0,
        help="Seconds without packets before the runtime reports a gap",
    )
    args = parser.parse_args()

    wedjat = OnlineWedjat.from_artifacts(
        norad_id=args.norad,
        gap_timeout_seconds=args.gap_timeout_seconds,
    )

    if args.payload_hex:
        if not args.timestamp:
            raise ValueError("--timestamp is required when using --payload-hex")
        result = wedjat.process_packet(
            payload=bytes.fromhex(args.payload_hex),
            timestamp=_parse_timestamp(args.timestamp),
            source=args.source,
        )
        _print_result(result)
        return

    for line in iter(input, ""):
        record = json.loads(line)
        result = wedjat.process_packet(
            payload=bytes.fromhex(record["payload_hex"]),
            timestamp=_parse_timestamp(record["timestamp"]),
            source=record.get("source", args.source),
        )
        _print_result(result)


if __name__ == "__main__":
    main()
