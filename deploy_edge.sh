#!/usr/bin/env bash
# deploy_edge.sh - Project Wedjat Edge Node Deployment
# Target: Raspberry Pi or local antenna PC

set -e

# Logging utilities
log_info() { echo "[INFO] $1"; }
log_warn() { echo "[WARN] $1" >&2; }
log_error() { echo "[ERROR] $1" >&2; exit 1; }

# Dependency Checks
if ! command -v docker >/dev/null 2>&1; then
    log_error "Docker is not installed. Please install Docker and retry."
fi

if ! docker compose version >/dev/null 2>&1; then
    log_error "Docker Compose (V2) is not installed or available."
fi

# Environment Configuration Check
if [ ! -f .env ]; then
    log_warn ".env file not found. Creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        log_info "Created .env from .env.example. Please review the credentials before running again."
        exit 0
    else
        log_error "No .env.example found to copy. Please create a .env file manually."
    fi
fi

# Validate critical Edge environment variables
if ! grep -q "^MQTT_USERNAME=" .env || ! grep -q "^MQTT_PASSWORD=" .env; then
    log_error "Missing MQTT_USERNAME or MQTT_PASSWORD in .env file. Edge deployment requires secure MQTT credentials."
fi

if ! grep -q "^MQTT_USE_WSS=true" .env; then
    log_warn "MQTT_USE_WSS is not set to true in .env. We strongly recommend using secure WebSockets via Caddy (port 443) for Edge deployments."
fi

log_info "Initializing Edge deployment sequence."

# Prepare local storage structures
if [ ! -d "data/raw" ]; then
    log_info "Creating data/raw directory for offline buffering."
    mkdir -p data/raw
fi

if [ ! -d "data/iq" ]; then
    log_info "Creating data/iq directory for SDR IQ recordings."
    mkdir -p data/iq
fi

log_info "Building and starting local edge demodulator..."
COMPOSE_PROFILES=edge docker compose up -d --build demodulator

log_info "Edge deployment completed successfully."
