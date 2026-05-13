from __future__ import annotations

import asyncio
import os
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
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
        lifespan=lifespan
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
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

    @app.websocket("/api/ws/dashboard")
    async def websocket_dashboard(websocket: WebSocket):
        await websocket.accept()
        try:
            while True:
                payload = data.dashboard_summary()
                await websocket.send_json(payload)
                await asyncio.sleep(2)
        except WebSocketDisconnect:
            pass

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
        limit: int = Query(default=20, ge=1, le=10000),
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
            return data.predict_passes(
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
    async def ml_sensitivity(norad_id: int) -> dict:
        try:
            return data.sensitivity_sweep(norad_id=norad_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return app


app = create_app()
