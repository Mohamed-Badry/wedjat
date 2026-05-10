from __future__ import annotations

import os
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager

try:
    from .dashboard_data import DashboardDataRepository
    from .mqtt_client import start_mqtt_client
except ImportError:  # pragma: no cover - used when uvicorn runs from src/api
    from dashboard_data import DashboardDataRepository
    from mqtt_client import start_mqtt_client

def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]

@asynccontextmanager
async def lifespan(app: FastAPI):
    client = start_mqtt_client()
    yield
    if client:
        client.loop_stop()

def create_app(repository: DashboardDataRepository | None = None) -> FastAPI:
    data = repository or DashboardDataRepository()
    app = FastAPI(
        title="gr_sat Watchdog API",
        description="FastAPI backend for satellite telemetry dashboard data.",
        version="0.1.0",
        lifespan=lifespan
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def read_root() -> dict:
        return {
            "status": "online",
            "message": "gr_sat Watchdog API is online.",
            "links": {
                "status": "/api/status",
                "dashboard_summary": "/api/dashboard/summary",
                "satellites": "/api/satellites",
                "recent_telemetry": "/api/telemetry/recent",
                "recent_anomalies": "/api/anomalies/recent",
                "throughput": "/api/telemetry/throughput",
            },
        }

    @app.get("/api/status")
    async def status() -> dict:
        return data.status_payload()

    @app.get("/api/dashboard/summary")
    async def dashboard_summary() -> dict:
        return data.dashboard_summary()

    @app.get("/api/satellites")
    async def satellites() -> dict:
        summaries = data.satellite_summaries()
        return {
            "count": len(summaries),
            "satellites": summaries,
        }

    @app.get("/api/satellites/{norad_id}")
    async def satellite_detail(norad_id: int) -> dict:
        try:
            return data.satellite_summary(norad_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/telemetry/recent")
    async def recent_telemetry(
        norad_id: int | None = None,
        limit: int = Query(default=20, ge=1, le=200),
    ) -> dict:
        try:
            return data.recent_frames(norad_id=norad_id, limit=limit)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/anomalies/recent")
    async def recent_anomalies(
        norad_id: int | None = None,
        limit: int = Query(default=20, ge=1, le=200),
    ) -> dict:
        try:
            return data.recent_anomalies(norad_id=norad_id, limit=limit)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/telemetry/throughput")
    async def telemetry_throughput(
        norad_id: int | None = None,
        bucket: Literal["hour", "day"] = "day",
        limit: int = Query(default=30, ge=1, le=365),
    ) -> dict:
        try:
            return data.throughput(norad_id=norad_id, bucket=bucket, limit=limit)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/operations/passes")
    async def operations_passes(
        ground_station: str = Query(default="cairo"),
        lookahead_hours: int = Query(default=24, ge=1, le=168),
        min_elevation: float = Query(default=10.0, ge=0.0, le=90.0),
        norad_id: int | None = None,
    ) -> dict:
        try:
            return data.predict_passes(
                ground_station=ground_station,
                lookahead_hours=lookahead_hours,
                min_elevation=min_elevation,
                norad_id=norad_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/ml/sensitivity")
    async def ml_sensitivity(norad_id: int) -> dict:
        try:
            return data.sensitivity_sweep(norad_id=norad_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return app


app = create_app()
