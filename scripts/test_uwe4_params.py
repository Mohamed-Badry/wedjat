from pathlib import Path
from gr_sat.demodulators.uwe4 import UWE4Demodulator, is_valid_ax25, deduplicate_frames
import sys

iq_path = Path("data/iq/processed/43880_test.raw")
d = UWE4Demodulator()

for inv in [False, True]:
    for gmu in [0.175, 0.3]:
        for d_first in [True, False]:
            frames = d._run_flowgraph(iq_path, inv, gmu, d_first)
            valid = [f for f in frames if is_valid_ax25(f)]
            valid = deduplicate_frames(valid)
            print(f"inv={inv}, gmu={gmu}, d_first={d_first} -> {len(valid)} frames")

