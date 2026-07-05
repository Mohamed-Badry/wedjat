"""
gr_sat — The Shared Core for Project Wedjat.

Provides the telemetry standardization layer (TelemetryFrame), the decoder
registry, and satellite-specific decoder implementations.

Key components:
  - telemetry.TelemetryFrame: The universal "Golden Features" DTO (SI units).
  - telemetry.DecoderRegistry: Maps NORAD IDs to decoder classes.
  - telemetry.process_frame: Full pipeline from raw bytes to TelemetryFrame.
  - telemetry.process_frame_result: Same pipeline with structured diagnostics.
  - decoders/: Satellite-specific decoder implementations.
"""

from .core.telemetry import (
    TelemetryFrame,
    DecoderRegistry,
    process_frame,
    process_frame_result,
)

__all__ = ["TelemetryFrame", "DecoderRegistry", "process_frame", "process_frame_result"]
