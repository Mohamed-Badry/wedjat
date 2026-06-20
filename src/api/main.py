from __future__ import annotations

import asyncio
import os
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, Depends, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from contextlib import asynccontextmanager

try:
    from .dashboard_data import DashboardDataRepository
    from .mqtt_client import start_mqtt_client
except ImportError:  # pragma: no cover - used when uvicorn runs from src/api
    from dashboard_data import DashboardDataRepository
    from mqtt_client import start_mqtt_client

try:
    from .auth import verify_api_key, seed_master_key
except ImportError:
    from auth import verify_api_key, seed_master_key

logger = logging.getLogger("api")
limiter = Limiter(key_func=get_remote_address)


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Seed the master API key from environment before starting services
    seed_master_key()
    client = start_mqtt_client(repository=app.state.repository)
    yield
    if client:
        client.loop_stop()


def create_app(repository: DashboardDataRepository | None = None) -> FastAPI:
    if repository is None:
        from pathlib import Path

        project_root = Path(__file__).resolve().parents[2]
        data = DashboardDataRepository(root=project_root)
    else:
        data = repository

    app = FastAPI(
        title="gr_sat Watchdog API",
        description="FastAPI backend for satellite telemetry dashboard data.",
        version="0.1.0",
        lifespan=lifespan,
        dependencies=[Depends(verify_api_key)],
    )
    
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    # Compress massive JSON payloads (like 10k telemetry frames) to save bandwidth
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=True,
        allow_methods=["GET", "OPTIONS", "POST"],
        allow_headers=["X-API-Key", "Content-Type", "Authorization", "Accept"],
    )

    @app.get("/")
    def read_root() -> dict:
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
    def status() -> dict:
        return data.status_payload()

    @app.get("/api/dashboard/summary")
    def dashboard_summary() -> dict:
        return data.dashboard_summary()

    @app.websocket("/api/ws/dashboard")
    async def websocket_dashboard(websocket: WebSocket):
        await websocket.accept()
        try:
            while True:
                payload = await run_in_threadpool(data.dashboard_summary)
                await websocket.send_json(payload)
                await asyncio.sleep(2)
        except WebSocketDisconnect:
            pass

    @app.get("/api/satellites")
    def satellites() -> dict:
        summaries = data.satellite_summaries()
        return {
            "count": len(summaries),
            "satellites": summaries,
        }

    @app.get("/api/satellites/{norad_id}")
    def satellite_detail(norad_id: int) -> dict:
        try:
            return data.satellite_summary(norad_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/telemetry/recent")
    def recent_telemetry(
        norad_id: int | None = None,
        limit: int = Query(default=20, ge=1, le=10000),
    ) -> dict:
        try:
            return data.recent_frames(norad_id=norad_id, limit=limit)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/anomalies/recent")
    def recent_anomalies(
        norad_id: int | None = None,
        limit: int = Query(default=20, ge=1, le=200),
    ) -> dict:
        try:
            return data.recent_anomalies(norad_id=norad_id, limit=limit)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/telemetry/throughput")
    def telemetry_throughput(
        norad_id: int | None = None,
        bucket: Literal["hour", "day"] = "day",
        limit: int = Query(default=30, ge=1, le=365),
    ) -> dict:
        try:
            return data.throughput(norad_id=norad_id, bucket=bucket, limit=limit)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/analytics")
    @limiter.limit("10/minute")
    def analytics_report(request: Request, norad_id: int | None = None) -> dict:
        try:
            return data.analytics_report(norad_id=norad_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/operations/passes")
    @limiter.limit("20/minute")
    async def operations_passes(
        request: Request,
        lat: float = Query(..., ge=-90.0, le=90.0),
        lon: float = Query(..., ge=-180.0, le=180.0),
        elevation_m: float = Query(default=0.0, ge=-500.0, le=10000.0),
        station_label: str | None = Query(default=None, max_length=80),
        lookahead_hours: int = Query(default=24, ge=1, le=168),
        min_elevation: float = Query(default=10.0, ge=0.0, le=90.0),
        norad_id: int | None = None,
        include_tracks: bool = Query(default=True),
    ) -> dict:
        try:
            return await run_in_threadpool(
                data.predict_passes,
                lat=lat,
                lon=lon,
                elevation_m=elevation_m,
                station_label=station_label,
                lookahead_hours=lookahead_hours,
                min_elevation=min_elevation,
                norad_id=norad_id,
                include_tracks=include_tracks,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/ml/sensitivity")
    @limiter.limit("5/minute")
    def ml_sensitivity(request: Request, norad_id: int) -> dict:
        try:
            return data.sensitivity_sweep(norad_id=norad_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return app


app = create_app()
