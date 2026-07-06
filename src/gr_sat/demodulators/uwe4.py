import math
from pathlib import Path
from typing import List
import numpy as np

try:
    from gnuradio import gr, blocks, filter as gr_filter, digital, analog
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


class FrameCollector(gr.basic_block):
    """Collects decoded HDLC/AX.25 PDU frames from message port."""

    def __init__(self):
        gr.basic_block.__init__(self, name="Frame Collector", in_sig=[], out_sig=[])
        self.frames = []
        self.message_port_register_in(pmt.intern("in"))
        self.set_msg_handler(pmt.intern("in"), self._handle_msg)

    def _handle_msg(self, msg):
        try:
            data = bytes(pmt.u8vector_elements(pmt.cdr(msg)))
            self.frames.append(data)
        except Exception:
            pass


def is_valid_ax25(frame: bytes) -> bool:
    """Validate that a frame is a proper AX.25 UI frame."""
    if len(frame) < 17:
        return False

    # Validate callsign bytes: each byte >> 1 should be printable ASCII (0x20-0x7E)
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
