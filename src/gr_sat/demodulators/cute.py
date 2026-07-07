import logging
from pathlib import Path
from typing import List

try:
    from gnuradio import gr, blocks, zeromq
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
from gr_sat.demodulators.utils import FrameCollector, is_valid_ax25, deduplicate_frames

logger = logging.getLogger("cute_demodulator")

SAMP_RATE = 57600
BAUD_RATE = 9600


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

        # Source: complex float IQ (Legacy CUTE implementation uses complex)
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

    def start_live_stream(self, source_endpoint: str, callback: callable) -> None:
        """Start a real-time GNU Radio flowgraph listening on a ZMQ socket."""
        if not HAS_GNURADIO:
            raise ImportError("GNU Radio and gr-satellites are required for live streaming.")
            
        try:
            import satellites.components.deframers
            import satellites.components.demodulators
        except ImportError as e:
            raise ImportError("gr-satellites is required to run the CUTE demodulator.") from e

        self.tb = gr.top_block("CUTE Live Stream Demodulator")

        # Source: ZMQ PULL -> interleaved int16 IQ -> complex
        # Note: 2 is sizeof_short
        src = zeromq.pull_source(2, 1, source_endpoint, 100, False, -1)
        i2c = blocks.interleaved_short_to_complex(False, False)
        scale = blocks.multiply_const_cc(1.0 / 32768.0)

        # Demodulator
        demod = satellites.components.demodulators.fsk_demodulator(
            baudrate=BAUD_RATE,
            samp_rate=SAMP_RATE,
            iq=True,
            subaudio=False,
            options=""
        )

        # Deframer
        deframer = satellites.components.deframers.ax25_deframer(
            g3ruh_scrambler=True,
            options=""
        )

        # Collector WITH live callback
        collector = FrameCollector(callback=callback)

        # Connect signal chain
        self.tb.connect(src, i2c, scale, demod)
        self.tb.connect(demod, deframer)
        self.tb.msg_connect(deframer, "out", collector, "in")

        # Keep Python references alive to prevent C++ segfault
        self._live_blocks = [src, i2c, scale, demod, deframer, collector]

        # Start asynchronously
        self.tb.start()

    def stop_live_stream(self) -> None:
        """Stop the currently running live stream flowgraph."""
        if hasattr(self, "tb") and self.tb is not None:
            self.tb.stop()
            self.tb.wait()
            self.tb = None
            self._live_blocks = []
