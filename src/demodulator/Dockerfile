FROM ubuntu:22.04

# Avoid interactive prompts during apt install
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    gnuradio \
    gr-satellites \
    python3-pip \
    python3-numpy \
    python3-paho-mqtt \
    python3-loguru \
    python3-zmq \
    && rm -rf /var/lib/apt/lists/*

# Set up work directory
WORKDIR /app

# Ensure /app/src is in Python path so gr_sat imports work
ENV PYTHONPATH=/app/src

# Copy only the shared core and the streamer code
COPY src/gr_sat /app/src/gr_sat
COPY src/demodulator/streamer.py /app/streamer.py

# Entrypoint runs the python live streamer daemon
CMD ["python3", "/app/streamer.py"]
