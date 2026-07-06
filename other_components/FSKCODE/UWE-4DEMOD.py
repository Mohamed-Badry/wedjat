#!/usr/bin/env python3
"""
UWE-4 Satellite IQ Demodulator
================================
Decodes UWE-4 (43880) FSK 9600 AX.25 telemetry from raw IQ recordings.

Signal Processing Chain:
    IQ File → Int16-to-Complex → Bandpass Filter → FM Demodulation →
    Clock Recovery (M&M) → Binary Slicer → NRZI Decode → Descramble →
    HDLC Deframe → AX.25 Frames (hex)

Usage:
    Place your IQ recording (.raw) in the same folder as this script, then run:
        python UWE-4DEMOD.py

Requirements:
    - GNU Radio 3.10+ (install via Radioconda on Windows)
    - NumPy
"""

import os
import sys
import glob
import numpy as np
from gnuradio import gr, blocks, filter, digital, analog
from gnuradio.fft import window
import pmt


# ═══════════════════════════════════════════════════════════════════
#  Configuration
# ═══════════════════════════════════════════════════════════════════
SAMP_RATE       = 57600          # IQ sample rate (Hz)
BAUD_RATE       = 9600           # Symbol rate (baud)
DEVIATION       = 2400           # FSK deviation (Hz)
FILTER_CUTOFF   = 7500           # Low-pass filter cutoff (Hz)
FILTER_TRANS    = 1500           # Filter transition width (Hz)
HDLC_MIN_LEN    = 32             # Minimum HDLC frame length (bits)
HDLC_MAX_LEN    = 500            # Maximum HDLC frame length (bytes)
DESCRAMBLER_POLY = 0x21          # G3RUH descrambler polynomial
DESCRAMBLER_LEN  = 16            # Descrambler register length


# ═══════════════════════════════════════════════════════════════════
#  GNU Radio Custom Blocks
# ═══════════════════════════════════════════════════════════════════
class NRZIDecoder(gr.sync_block):
    """Decodes NRZI encoding: same level = 1, transition = 0."""
    def __init__(self):
        gr.sync_block.__init__(self, name="NRZI Decoder",
            in_sig=[np.uint8], out_sig=[np.uint8])
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
        gr.basic_block.__init__(self, name="Frame Collector",
            in_sig=[], out_sig=[])
        self.frames = []
        self.message_port_register_in(pmt.intern("in"))
        self.set_msg_handler(pmt.intern("in"), self._handle_msg)

    def _handle_msg(self, msg):
        try:
            data = bytes(pmt.u8vector_elements(pmt.cdr(msg)))
            self.frames.append(data)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════
#  Demodulation Engine
# ═══════════════════════════════════════════════════════════════════
def demodulate(iq_path, invert=False, gain_mu=0.175, descramble_first=True):
    """
    Build and run the full demodulation flowgraph.

    Args:
        iq_path:          Path to the raw IQ file (interleaved int16).
        invert:           Invert FM demodulator polarity.
        gain_mu:          M&M clock recovery gain parameter.
        descramble_first: If True, descramble before NRZI decode.

    Returns:
        List of decoded frame byte strings.
    """
    sps = SAMP_RATE / BAUD_RATE
    tb  = gr.top_block("UWE-4 Demodulator")

    # Source: interleaved int16 IQ → complex
    src   = blocks.file_source(gr.sizeof_short, iq_path, False)
    i2c   = blocks.interleaved_short_to_complex(False, False)
    scale = blocks.multiply_const_cc(1.0 / 32768.0)

    # Bandpass filtering
    taps = filter.firdes.low_pass(1.0, SAMP_RATE, FILTER_CUTOFF,
                                   FILTER_TRANS, window.WIN_HAMMING)
    lpf  = filter.fir_filter_ccf(1, taps)

    # FM demodulation
    gain = SAMP_RATE / (2 * 3.14159265 * DEVIATION)
    demod = analog.quadrature_demod_cf(-gain if invert else gain)

    # Clock recovery (Mueller & Müller)
    clk = digital.clock_recovery_mm_ff(
        sps, 0.25 * gain_mu ** 2, 0.5, gain_mu, 0.005)

    # Decision + decoding
    slicer      = digital.binary_slicer_fb()
    descrambler = digital.descrambler_bb(DESCRAMBLER_POLY, 0, DESCRAMBLER_LEN)
    nrzi        = NRZIDecoder()
    hdlc        = digital.hdlc_deframer_bp(HDLC_MIN_LEN, HDLC_MAX_LEN)
    collector   = FrameCollector()

    # Connect signal chain
    tb.connect(src, i2c, scale, lpf, demod, clk, slicer)
    if descramble_first:
        tb.connect(slicer, descrambler, nrzi, hdlc)
    else:
        tb.connect(slicer, nrzi, descrambler, hdlc)
    tb.msg_connect(hdlc, "out", collector, "in")

    tb.run()
    return collector.frames


def is_valid_ax25(frame):
    """
    Validate that a frame is a proper AX.25 UI frame.

    Checks:
      - Minimum length (17 bytes: 14 header + control + PID + payload)
      - Destination and source callsigns contain valid ASCII characters
      - Control byte is 0x03 (UI frame)
      - PID byte is 0xF0 (no layer 3 protocol)
    """
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


def deduplicate_frames(frames):
    """Remove duplicate frames, preserving order."""
    seen = set()
    unique = []
    for f in frames:
        key = f.hex()
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique


def find_iq_file():
    """Auto-detect a .raw IQ file in the same directory as this script."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    raw_files  = glob.glob(os.path.join(script_dir, "*.raw"))
    if len(raw_files) == 1:
        return raw_files[0]
    elif len(raw_files) > 1:
        print(f"Found {len(raw_files)} .raw files — using the first one:")
        for f in raw_files:
            print(f"  - {os.path.basename(f)}")
        return raw_files[0]
    return None


# ═══════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  UWE-4 Satellite IQ Demodulator")
    print("  FSK 9600 | AX.25 | HDLC | G3RUH Descrambling")
    print("=" * 60)

    # ── Locate IQ file ────────────────────────────────────────
    iq_path = find_iq_file()
    if not iq_path:
        print("\n  ERROR: No .raw IQ file found.")
        print("  Place your IQ recording (.raw) next to this script.")
        sys.exit(1)
    print(f"\n  IQ file : {os.path.basename(iq_path)}")
    print(f"  Size    : {os.path.getsize(iq_path) / 1e6:.1f} MB")

    # ── Try all parameter permutations ────────────────────────
    print("\n  Searching best parameters...\n")
    best_frames = []
    best_config = ""

    for inv in [False, True]:
        for gmu in [0.175, 0.3]:
            for d_first in [True, False]:
                tag = f"  inv={str(inv):5s}  gain_mu={gmu}  descramble_first={d_first}"
                raw_frames = demodulate(iq_path, inv, gmu, d_first)
                # Filter: keep only valid AX.25 frames, remove duplicates
                valid = [f for f in raw_frames if is_valid_ax25(f)]
                valid = deduplicate_frames(valid)
                count = len(valid)
                status = f"  {count} valid frame(s)"
                print(f"{tag}  ->  {status}")
                if count > len(best_frames):
                    best_frames = valid
                    best_config = tag

    # ── Display decoded frames ────────────────────────────────
    print(f"\n{'=' * 60}")
    print(f"  RESULTS: {len(best_frames)} frame(s) decoded")
    if best_config:
        print(f"  Best config:{best_config}")
    print(f"{'=' * 60}")

    for i, frame in enumerate(best_frames):
        hex_str = " ".join(f"{b:02X}" for b in frame)
        print(f"\n  Frame #{i + 1}  [{len(frame)} bytes]")
        print(f"  {hex_str}")

    print(f"\n{'=' * 60}")
    print("  Done")
    print(f"{'=' * 60}\n")
