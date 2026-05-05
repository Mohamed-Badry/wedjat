# syntax=docker/dockerfile:1.7
FROM python:3.11.15-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=0 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY src/api/requirements.txt /tmp/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    python -m pip install --no-compile -r /tmp/requirements.txt

COPY pyproject.toml README.md /app/
COPY src/gr_sat /app/src/gr_sat
COPY src/api /app/src/api

WORKDIR /app/src/api

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app/src/api", "--reload-dir", "/app/src/gr_sat"]
