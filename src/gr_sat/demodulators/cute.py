import logging
from pathlib import Path
from typing import List

try:
    from gnuradio import gr, blocks
    import pmt
    HAS_GNURADIO = True
except ImportError:
    HAS_GNURADIO = False
    # Mock base classes to avoid NameErrors at import-time on non-GNU Radio hosts (like Cloud VPS)
    class gr:
        class basic_block:
            def __init__(self, *args, **kwargs): pass

from gr_sat.demodulators.base import BaseDemodulator
from gr_sat.demodulators.registry import DemodulatorRegistry

logger = logging.getLogger("cute_demodulator")

SAMP_RATE = 57600
BAUD_RATE = 9600


class FrameCollector(gr.basic_block):
    """Collects decoded AX.25 PDU frames from msg port."""

    def __init__(self):
        gr.basic_block.__init__(self, name="Frame Collector", in_sig=[], out_sig=[])
        self.frames = []
        self.message_port_register_in(pmt.intern("in"))
        self.set_msg_handler(pmt.intern("in"), self._handle_msg)

    def _handle_msg(self, msg):
        try:
            # Extract byte data from PMT u8vector inside PDU
            data = bytes(pmt.u8vector_elements(pmt.cdr(msg)))
            self.frames.append(data)
        except Exception as e:
            logger.debug(f"Failed to parse PDU message: {e}")


def is_valid_ax25(frame: bytes) -> bool:
    """Validate AX.25 UI frame structure."""
    if len(frame) < 17:
        return False

    # Check source and destination callsigns
    for b in frame[0:6] + frame[7:13]:
        ch = b >> 1
        if ch < 0x20 or ch > 0x7E:
            return False

    # Control = 0x03 (UI frame), PID = 0xF0 (no layer 3)
    if frame[14] != 0x03 or frame[15] != 0xF0:
        return False

    return True


def deduplicate_frames(frames: List[bytes]) -> List[bytes]:
    """Remove duplicate frames, preserving order."""
    seen = set()
    unique = []
    for f in frames:
        if f not in seen:
            seen.add(f)
            unique.append(f)
    return unique


@DemodulatorRegistry.register(49263)
class CUTEDemodulator(BaseDemodulator):
    """Productionized CUTE (NORAD 49263) GFSK 9600 Demodulator.

    Requires the `gr-satellites` out-of-tree module.
    """

    def demodulate(self, iq_path: Path) -> List[bytes]:
        """Demodulate raw complex float IQ file using gr-satellites components."""
        if not HAS_GNURADIO:
            raise ImportError(
                "GNU Radio is required to run the CUTE demodulator. "
                "Install it on your edge system (e.g., `apt-get install gnuradio`)."
            )

        try:
            import satellites.components.deframers  # noqa: F401
            import satellites.components.demodulators  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "gr-satellites is required to run the CUTE demodulator. "
                "Install it on your edge system (e.g., `apt-get install gr-satellites`)."
            ) from e

        if not iq_path.exists():
            raise FileNotFoundError(f"IQ file not found: {iq_path}")

        tb = gr.top_block("CUTE Demodulator")

        # Source: complex float IQ
        src = blocks.file_source(gr.sizeof_gr_complex, str(iq_path), False)

        # FSK Demodulator
        demod = satellites.components.demodulators.fsk_demodulator(
            baudrate=BAUD_RATE,
            samp_rate=SAMP_RATE,
            iq=True,
            subaudio=False,
            options="",
        )

        # AX.25 Deframer
        deframer = satellites.components.deframers.ax25_deframer(
            g3ruh_scrambler=True, options=""
        )

        # Frame Collector
        collector = FrameCollector()

        # Connect blocks
        tb.connect(src, demod)
        tb.connect(demod, deframer)
        tb.msg_connect(deframer, "out", collector, "in")

        # Run flowgraph
        logger.info(f"Running CUTE GFSK demodulation for: {iq_path.name}")
        tb.run()

        # Filter and deduplicate
        valid = [f for f in collector.frames if is_valid_ax25(f)]
        return deduplicate_frames(valid)
