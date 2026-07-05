# syntax=docker/dockerfile:1.7
# Stage 1: Builder
FROM python:3.11.15-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_SYSTEM_PYTHON=1

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /build

COPY src/scheduler/requirements.txt /tmp/requirements.txt
# We also need PyTorch to run the training script!
# Actually, the training script uses `gr_sat.ml.training`. So we need the ML dependencies.
# The backend Dockerfile uses uv to install requirements. Let's just use the API requirements.
COPY src/api/requirements.txt /tmp/api_requirements.txt

RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --prefix /install -r /tmp/requirements.txt -r /tmp/api_requirements.txt

# Stage 2: Runtime
FROM python:3.11.15-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PROJECT_ROOT=/app

COPY --from=builder /install /usr/local

RUN useradd -m -s /bin/bash wedjat
WORKDIR /app

# The scheduler needs access to all scripts and gr_sat core/ml
COPY src/ /app/src/
COPY scripts/ /app/scripts/

RUN chown -R wedjat:wedjat /app
USER wedjat

WORKDIR /app/src/scheduler

CMD ["python", "main.py"]
