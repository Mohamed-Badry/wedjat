import time
import argparse
import zmq
from pathlib import Path
import sys

import os
from dotenv import load_dotenv

def main():
    load_dotenv()
    default_endpoint = os.getenv("ZMQ_ENDPOINT", "tcp://0.0.0.0:5555")
    
    parser = argparse.ArgumentParser(description="Mock SDR Streamer for ZMQ live testing")
    parser.add_argument("file", type=str, help="Path to the raw IQ file")
    parser.add_argument("--endpoint", type=str, default=default_endpoint, help="ZMQ Push Endpoint")
    parser.add_argument("--samp-rate", type=int, default=57600, help="Sample rate in Hz")
    parser.add_argument("--fast", action="store_true", help="Blast data as fast as possible instead of pacing")
    args = parser.parse_args()

    iq_path = Path(args.file)
    if not iq_path.exists():
        print(f"Error: File not found: {iq_path}")
        sys.exit(1)

    print(f"Binding ZMQ PUSH socket to {args.endpoint}...")
    context = zmq.Context()
    socket = context.socket(zmq.PUSH)
    socket.bind(args.endpoint)
    
    print("Waiting 1 second for connections to establish...")
    time.sleep(1)
    
    # 1 sample = 16-bit I + 16-bit Q = 4 bytes
    bytes_per_sample = 4
    bytes_per_second = args.samp_rate * bytes_per_sample
    
    # Send in chunks of 0.1 seconds
    chunk_size = int(bytes_per_second * 0.1)
    
    try:
        total_size_mb = iq_path.stat().st_size / (1024 * 1024)
        expected_minutes = (iq_path.stat().st_size / bytes_per_second) / 60
        
        print(f"Streaming {iq_path.name} at {args.samp_rate} Hz ({bytes_per_second} bytes/sec)...")
        if not args.fast:
            print(f"Total file size: {total_size_mb:.2f} MB. At real-time speed, this will take ~{expected_minutes:.1f} minutes.")
            print("Note: Decoded frames will only appear in the logs once the SDR stream reaches that point in the file.")
            print("To blast the data instantly, use the --fast flag.")
        
        with open(iq_path, "rb") as f:
            total_bytes = 0
            start_time = time.time()
            
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                    
                socket.send(chunk)
                total_bytes += len(chunk)
                
                if not args.fast:
                    # Pace the stream
                    elapsed = time.time() - start_time
                    expected_time = total_bytes / bytes_per_second
                    if expected_time > elapsed:
                        time.sleep(expected_time - elapsed)

                if total_bytes % (bytes_per_second * 5) < chunk_size:
                    print(f"Streamed {total_bytes / 1024 / 1024:.2f} MB...")
                    
    except KeyboardInterrupt:
        print("\nStreaming interrupted.")
    finally:
        print("Closing socket...")
        socket.setsockopt(zmq.LINGER, 0)
        socket.close()
        context.term()
        print("Done.")

if __name__ == "__main__":
    main()
