import math
from pathlib import Path
from typing import List
import numpy as np

try:
    from gnuradio import gr, blocks, filter as gr_filter, digital, analog, zeromq
    from gnuradio.fft import window
    import pmt
    HAS_GNURADIO = True
except ImportError:
    HAS_GNURADIO = False
    # Mock base classes to avoid NameErrors at import-time on non-GNU Radio hosts (like Cloud VPS)
    class gr:
        class sync_block:
            def __init__(self, *args, **kwargs): pass
        class basic_block:
            def __init__(self, *args, **kwargs): pass

from gr_sat.demodulators.base import BaseDemodulator
from gr_sat.demodulators.registry import DemodulatorRegistry

# Signal Parameters
SAMP_RATE = 57600
BAUD_RATE = 9600
DEVIATION = 2400
FILTER_CUTOFF = 7500
FILTER_TRANS = 1500
HDLC_MIN_LEN = 32
HDLC_MAX_LEN = 500
DESCRAMBLER_POLY = 0x21
DESCRAMBLER_LEN = 16


class NRZIDecoder(gr.sync_block):
    """Decodes NRZI encoding: same level = 1, transition = 0."""

    def __init__(self):
        gr.sync_block.__init__(
            self, name="NRZI Decoder", in_sig=[np.uint8], out_sig=[np.uint8]
        )
        self.last = 0

    def work(self, input_items, output_items):
        inp = input_items[0]
        out = output_items[0]
        for i in range(len(inp)):
            current = inp[i] & 1
            out[i] = 1 if current == self.last else 0
            self.last = current
        return len(out)


from gr_sat.demodulators.utils import FrameCollector, is_valid_ax25, deduplicate_frames


@DemodulatorRegistry.register(43880)
class UWE4Demodulator(BaseDemodulator):
    """Productionized UWE-4 AX.25 FSK 9600 Demodulator."""

    def _run_flowgraph(
        self,
        iq_path: Path,
        invert: bool = False,
        gain_mu: float = 0.175,
        descramble_first: bool = True,
    ) -> List[bytes]:
        """Build and run a single GNU Radio demodulation flowgraph iteration."""
        sps = SAMP_RATE / BAUD_RATE
        tb = gr.top_block("UWE-4 Demodulator")

        # Source: interleaved int16 IQ -> complex
        src = blocks.file_source(gr.sizeof_short, str(iq_path), False)
        i2c = blocks.interleaved_short_to_complex(False, False)
        scale = blocks.multiply_const_cc(1.0 / 32768.0)

        # LPF Bandpass filtering
        taps = gr_filter.firdes.low_pass(
            1.0, SAMP_RATE, FILTER_CUTOFF, FILTER_TRANS, window.WIN_HAMMING
        )
        lpf = gr_filter.fir_filter_ccf(1, taps)

        # FM demodulation
        gain = SAMP_RATE / (2 * math.pi * DEVIATION)
        demod = analog.quadrature_demod_cf(-gain if invert else gain)

        # Clock recovery (Mueller & Müller)
        clk = digital.clock_recovery_mm_ff(
            sps, 0.25 * gain_mu**2, 0.5, gain_mu, 0.005
        )

        # Decision + decoding
        slicer = digital.binary_slicer_fb()
        descrambler = digital.descrambler_bb(
            DESCRAMBLER_POLY, 0, DESCRAMBLER_LEN
        )
        nrzi = NRZIDecoder()
        hdlc = digital.hdlc_deframer_bp(HDLC_MIN_LEN, HDLC_MAX_LEN)
        collector = FrameCollector()

        # Connect signal chain
        tb.connect(src, i2c, scale, lpf, demod, clk, slicer)
        if descramble_first:
            tb.connect(slicer, descrambler, nrzi, hdlc)
        else:
            tb.connect(slicer, nrzi, descrambler, hdlc)
        tb.msg_connect(hdlc, "out", collector, "in")

        tb.run()
        return collector.frames

    def demodulate(self, iq_path: Path) -> List[bytes]:
        """Demodulate raw IQ file by trying permutations to find the best decoded set."""
        if not HAS_GNURADIO:
            raise ImportError(
                "GNU Radio is required to run the UWE-4 demodulator. "
                "Install it on your edge system (e.g., `apt-get install gnuradio`)."
            )

        if not iq_path.exists():
            raise FileNotFoundError(f"IQ file not found: {iq_path}")

        best_frames = []

        # Parameter permutations sweep to maximize demodulation yield
        for inv in [False, True]:
            for gmu in [0.175, 0.3]:
                for d_first in [True, False]:
                    raw_frames = self._run_flowgraph(
                        iq_path, inv, gmu, d_first
                    )
                    valid = [f for f in raw_frames if is_valid_ax25(f)]
                    valid = deduplicate_frames(valid)

                    if len(valid) > len(best_frames):
                        best_frames = valid

        return best_frames

    def start_live_stream(self, source_endpoint: str, callback: callable) -> None:
        """Start a real-time GNU Radio flowgraph listening on a ZMQ socket."""
        if not HAS_GNURADIO:
            raise ImportError("GNU Radio is required for live streaming.")
            
        sps = SAMP_RATE / BAUD_RATE
        self.tb = gr.top_block("UWE-4 Live Stream Demodulator")

        # Source: ZMQ PULL -> interleaved int16 IQ -> complex
        # Note: 2 is sizeof_short
        src = zeromq.pull_source(2, 1, source_endpoint, 100, False, -1)
        i2c = blocks.interleaved_short_to_complex(False, False)
        scale = blocks.multiply_const_cc(1.0 / 32768.0)

        # LPF Bandpass filtering
        taps = gr_filter.firdes.low_pass(
            1.0, SAMP_RATE, FILTER_CUTOFF, FILTER_TRANS, window.WIN_HAMMING
        )
        lpf = gr_filter.fir_filter_ccf(1, taps)

        # FM demodulation (default params for live stream: invert=False)
        gain = SAMP_RATE / (2 * math.pi * DEVIATION)
        demod = analog.quadrature_demod_cf(gain)

        # Clock recovery (Mueller & Müller)
        gain_mu = 0.175
        clk = digital.clock_recovery_mm_ff(
            sps, 0.25 * gain_mu**2, 0.5, gain_mu, 0.005
        )

        # Decision + decoding
        slicer = digital.binary_slicer_fb()
        descrambler = digital.descrambler_bb(
            DESCRAMBLER_POLY, 0, DESCRAMBLER_LEN
        )
        nrzi = NRZIDecoder()
        hdlc = digital.hdlc_deframer_bp(HDLC_MIN_LEN, HDLC_MAX_LEN)
        
        # Collector WITH live callback
        collector = FrameCollector(callback=callback)

        # Connect signal chain (descramble_first=True by default)
        self.tb.connect(src, i2c, scale, lpf, demod, clk, slicer)
        self.tb.connect(slicer, descrambler, nrzi, hdlc)
        self.tb.msg_connect(hdlc, "out", collector, "in")

        # Keep Python references alive to prevent C++ segfault
        self._live_blocks = [src, i2c, scale, lpf, demod, clk, slicer, descrambler, nrzi, hdlc, collector]

        # Start asynchronously
        self.tb.start()


    def stop_live_stream(self) -> None:
        """Stop the currently running live stream flowgraph."""
        if hasattr(self, "tb") and self.tb is not None:
            self.tb.stop()
            self.tb.wait()
            self.tb = None
            self._live_blocks = []
