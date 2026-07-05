#!/usr/bin/env bash
# deploy_vps.sh - Project Wedjat Cloud Deployment
# Target: Ubuntu/Debian VPS

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
        log_info "Created .env from .env.example. Please update database passwords and API keys before running again."
        exit 0
    else
        log_error "No .env.example found to copy. Please create a .env file manually."
    fi
fi

# Validate critical Cloud environment variables
for var in POSTGRES_USER POSTGRES_PASSWORD POSTGRES_DB; do
    if ! grep -q "^${var}=" .env; then
        log_error "Missing ${var} in .env file. Cloud deployment requires explicit database credentials."
    fi
done

# Ensure fallback defaults are not used in production
if grep -q "^POSTGRES_PASSWORD=wedjat_pass$" .env; then
    log_warn "You are using the default development database password. This is highly discouraged for VPS deployment."
    read -p "Do you want to continue anyway? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_error "Deployment aborted by user to fix database password."
    fi
fi

log_info "Initializing Cloud deployment sequence."

log_info "Building and starting cloud services (db, backend, frontend-prod, broker, scheduler)..."
docker compose --profile cloud up -d --build

log_info "Cloud deployment completed successfully."
