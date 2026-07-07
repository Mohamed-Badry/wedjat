import sys
import zmq
import time
import argparse
import numpy as np

def main():
    parser = argparse.ArgumentParser(description="Bridge rtl_sdr raw output to the Edge Demodulator ZMQ socket.")
    parser.add_argument("--endpoint", type=str, default="tcp://0.0.0.0:5555", help="ZMQ PUSH Endpoint")
    parser.add_argument("--chunk-size", type=int, default=8192, help="Bytes to read from stdin per chunk")
    args = parser.parse_args()

    print(f"Binding ZMQ PUSH socket to {args.endpoint}...")
    context = zmq.Context()
    socket = context.socket(zmq.PUSH)
    socket.bind(args.endpoint)
    
    print("Waiting 1 second for Edge Demodulator to connect...")
    time.sleep(1)
    
    print("Reading from stdin (pipe from rtl_sdr) and pushing to ZMQ...")
    
    try:
        # Read from raw unbuffered stdin
        stdin_fd = sys.stdin.fileno()
        total_bytes = 0
        
        while True:
            # Read 8-bit unsigned data from rtl_sdr
            data = sys.stdin.buffer.read(args.chunk_size)
            if not data:
                break
                
            # Convert 8-bit unsigned to 16-bit signed
            # rtl_sdr format: 8-bit unsigned, centered at 127.5
            arr_u8 = np.frombuffer(data, dtype=np.uint8)
            arr_i16 = (arr_u8.astype(np.int16) - 127) * 256
            
            # Send to ZMQ
            socket.send(arr_i16.tobytes())
            total_bytes += len(data)
            
            if total_bytes % (args.chunk_size * 100) == 0:
                print(f"Bridged {total_bytes / 1024 / 1024:.2f} MB...", end='\r')
                
    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        socket.setsockopt(zmq.LINGER, 0)
        socket.close()
        context.term()
        print("\nDone.")

if __name__ == "__main__":
    main()
