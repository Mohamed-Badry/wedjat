# syntax=docker/dockerfile:1.7
FROM python:3.11.15-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY src/simulator/requirements.txt /tmp/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    python -m pip install --no-compile -r /tmp/requirements.txt

COPY src/simulator /app/src/simulator

WORKDIR /app/src/simulator

CMD ["python", "replay.py"]
