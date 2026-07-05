# syntax=docker/dockerfile:1.7
# Stage 1: Builder
FROM python:3.11.15-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_SYSTEM_PYTHON=1

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /build

COPY src/simulator/requirements.txt /tmp/requirements.txt
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --prefix /install -r /tmp/requirements.txt

# Stage 2: Runtime
FROM python:3.11.15-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

COPY --from=builder /install /usr/local

RUN useradd -m -s /bin/bash wedjat
WORKDIR /app

COPY src/simulator /app/src/simulator
COPY src/gr_sat /app/src/gr_sat

RUN chown -R wedjat:wedjat /app
USER wedjat

WORKDIR /app/src/simulator

CMD ["python", "replay.py"]
