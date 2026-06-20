# syntax=docker/dockerfile:1.7
# Stage 1: Builder
FROM python:3.11.15-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_SYSTEM_PYTHON=1

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /build

COPY src/api/requirements-core.txt /tmp/requirements-core.txt
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --prefix /install -r /tmp/requirements-core.txt

COPY src/api/requirements.txt /tmp/requirements.txt
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --prefix /install -r /tmp/requirements.txt

# Stage 2: Runtime
FROM python:3.11.15-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

# Install required system packages for psycopg2 (if any are needed dynamically at runtime, normally libpq5)
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 curl && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

RUN useradd -m -s /bin/bash watchdog
WORKDIR /app

COPY pyproject.toml README.md /app/
COPY src/gr_sat /app/src/gr_sat
COPY src/api /app/src/api

RUN chown -R watchdog:watchdog /app
USER watchdog

WORKDIR /app/src/api

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/status || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
