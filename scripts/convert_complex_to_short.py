import sys
import numpy as np

def convert(in_path, out_path):
    print(f"Loading {in_path} as complex float32...")
    data_f32 = np.fromfile(in_path, dtype=np.complex64)
    print(f"Loaded {len(data_f32)} samples.")
    
    # Normalize to -1.0 to 1.0 (though it might already be)
    max_val = np.max(np.abs(data_f32))
    if max_val > 0:
        data_f32 = data_f32 / max_val
        
    print("Converting to interleaved int16...")
    # interleaved = [real1, imag1, real2, imag2, ...]
    interleaved = np.empty(len(data_f32) * 2, dtype=np.int16)
    interleaved[0::2] = np.int16(data_f32.real * 32767)
    interleaved[1::2] = np.int16(data_f32.imag * 32767)
    
    print(f"Writing to {out_path}...")
    interleaved.tofile(out_path)
    print("Done.")

if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2])
