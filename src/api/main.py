from __future__ import annotations
import asyncio
import os
from typing import Literal

from loguru import logger
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, Depends, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from contextlib import asynccontextmanager

from gr_sat.core.config import GS_LATITUDE, GS_LONGITUDE, GS_ELEVATION, GS_NAME

try:
    from .dashboard_data import DashboardDataRepository
    from .mqtt_client import start_mqtt_client
except ImportError:  # pragma: no cover - used when uvicorn runs from src/api
    from dashboard_data import DashboardDataRepository
    from mqtt_client import start_mqtt_client


limiter = Limiter(key_func=get_remote_address)


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = start_mqtt_client(repository=app.state.repository)
    yield
    if client:
        import api.mqtt_client as mqtt_module
        if hasattr(mqtt_module, "score_queue"):
            mqtt_module.score_queue.put(None)  # shutdown worker
        client.loop_stop()


def create_app(repository: DashboardDataRepository | None = None) -> FastAPI:
    if repository is None:
        from pathlib import Path

        project_root = Path(__file__).resolve().parents[2]
        data = DashboardDataRepository(root=project_root)
    else:
        data = repository

    app = FastAPI(
        title="gr_sat Wedjat API",
        description="FastAPI backend for satellite telemetry dashboard data.",
        version="0.1.0",
        lifespan=lifespan,
    )
    
    app.state.repository = data
    
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

    @app.middleware("http")
    async def add_cors_headers(request: Request, call_next):
        response = await call_next(request)
        if "Access-Control-Allow-Origin" not in response.headers:
            response.headers["Access-Control-Allow-Origin"] = "*"
        if "Access-Control-Allow-Methods" not in response.headers:
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS, POST, PUT, DELETE"
        if "Access-Control-Allow-Headers" not in response.headers:
            response.headers["Access-Control-Allow-Headers"] = "X-API-Key, Content-Type, Authorization, Accept"
        return response

    @app.get("/")
    def read_root() -> dict:
        return {
            "status": "online",
            "message": "gr_sat Wedjat API is online.",
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
        subscribed_norad_ids = set()

        async def message_receiver():
            try:
                while True:
                    msg = await websocket.receive_json()
                    action = msg.get("action")
                    norad_id = msg.get("norad_id")
                    if action == "subscribe":
                        subscribed_norad_ids.add(norad_id)
                        await websocket.send_json({"subscribed": True, "norad_id": norad_id})
                    elif action == "unsubscribe":
                        subscribed_norad_ids.discard(norad_id)
                        await websocket.send_json({"unsubscribed": True, "norad_id": norad_id})
            except WebSocketDisconnect:
                pass
            except Exception:
                pass

        receiver_task = asyncio.create_task(message_receiver())

        try:
            last_frame_timestamps = {}
            last_anomaly_timestamps = {}
            while True:
                for norad_id in list(subscribed_norad_ids):
                    # Push Telemetry
                    telemetry_data = await run_in_threadpool(data.recent_frames, norad_id=norad_id, limit=20)
                    if telemetry_data.get("frames"):
                        frames = telemetry_data["frames"]
                        last_ts = last_frame_timestamps.get(norad_id)
                        
                        if last_ts is None:
                            last_frame_timestamps[norad_id] = frames[0]["timestamp"]
                            await websocket.send_json({"type": "push_telemetry", "frame": frames[0]})
                        else:
                            new_frames = []
                            for frame in frames:
                                if frame["timestamp"] > last_ts:
                                    new_frames.append(frame)
                                else:
                                    break
                            for frame in reversed(new_frames):
                                await websocket.send_json({"type": "push_telemetry", "frame": frame})
                            if new_frames:
                                last_frame_timestamps[norad_id] = new_frames[0]["timestamp"]

                    # Push Anomaly Alerts
                    anomaly_data = await run_in_threadpool(data.recent_anomalies, norad_id=norad_id, limit=20)
                    if anomaly_data.get("anomalies"):
                        anomalies = anomaly_data["anomalies"]
                        last_anomaly_ts = last_anomaly_timestamps.get(norad_id)
                        
                        if last_anomaly_ts is None:
                            last_anomaly_timestamps[norad_id] = anomalies[0]["timestamp"]
                            await websocket.send_json({"type": "push_anomaly_alert", "alert": anomalies[0]})
                        else:
                            new_anomalies = []
                            for anomaly in anomalies:
                                if anomaly["timestamp"] > last_anomaly_ts:
                                    new_anomalies.append(anomaly)
                                else:
                                    break
                            for anomaly in reversed(new_anomalies):
                                await websocket.send_json({"type": "push_anomaly_alert", "alert": anomaly})
                            if new_anomalies:
                                last_anomaly_timestamps[norad_id] = new_anomalies[0]["timestamp"]
                
                await asyncio.sleep(2)
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            receiver_task.cancel()

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
        lat: float = Query(default=GS_LATITUDE, ge=-90.0, le=90.0),
        lon: float = Query(default=GS_LONGITUDE, ge=-180.0, le=180.0),
        elevation_m: float = Query(default=GS_ELEVATION, ge=-500.0, le=10000.0),
        station_label: str | None = Query(default=GS_NAME, max_length=80),
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

    @app.get("/api/tracker/state")
    @limiter.limit("30/minute")
    def tracker_state(
        request: Request,
        response: Response,
        norad_id: int = Query(default=43880),
    ) -> dict:
        """Returns the full TrackerSnapshot: live state, forecast, profiles, ground track."""
        from gr_sat.core.orbit_tracker import compute_tracker_snapshot
        try:
            snapshot = compute_tracker_snapshot(norad_id)
            response.headers["Cache-Control"] = "private, max-age=5"
            return snapshot.model_dump(mode="json")
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/tracker/conjunctions")
    @limiter.limit("5/minute")
    def tracker_conjunctions(
        request: Request,
        response: Response,
        norad_id: int = Query(default=43880),
        lookahead_hours: int = Query(default=24, ge=1, le=168),
    ) -> dict:
        """Returns upcoming conjunction events with Foster collision probabilities."""
        from gr_sat.core.conjunctions import find_conjunctions
        events = find_conjunctions(lookahead_hours=lookahead_hours, norad_id=norad_id)
        response.headers["Cache-Control"] = "private, max-age=300"
        return {
            "norad_id": norad_id,
            "lookahead_hours": lookahead_hours,
            "events": [e.model_dump(mode="json") for e in events],
        }

    @app.get("/api/tracker/tle")
    @limiter.limit("10/minute")
    def tracker_tle(request: Request, norad_id: int = Query(default=43880)) -> dict:
        """Returns the current TLE lines, source, and age for display."""
        from gr_sat.core.orbit_decay import get_satellite
        sat = get_satellite(norad_id)
        if not sat:
            raise HTTPException(status_code=503, detail="No TLE available")
        return {
            "line0": sat.name,
            "line1": sat.model.line1 if hasattr(sat.model, 'line1') else None,
            "line2": sat.model.line2 if hasattr(sat.model, 'line2') else None,
            "epoch": sat.epoch.utc_iso() if hasattr(sat, 'epoch') else None,
        }

    @app.get("/api/orbit/decay-prediction")
    @limiter.limit("10/minute")
    def orbit_decay_prediction(
        request: Request,
        response: Response,
        norad_id: int = Query(default=43880),
    ) -> dict:
        try:
            from gr_sat.core.orbit_decay import fetch_latest_space_weather, PredictOrbitDecay, compute_atmospheric_state
            weather = fetch_latest_space_weather()
            atm_state = compute_atmospheric_state(norad_id, weather)
            # If atmospheric state altitude failed, try dataset altitude as fallback
            effective_alt = atm_state.altitude_km
            if effective_alt <= 0:
                try:
                    from gr_sat.core.orbit_decay import _load_dataset
                    _df = _load_dataset()
                    effective_alt = float(_df.iloc[-1]["altitude_mean_km"])
                    atm_state.altitude_km = effective_alt
                except Exception:
                    pass
            forecasts = PredictOrbitDecay(satellite_id=norad_id, weather=weather, alt_km=atm_state.altitude_km)
            response.headers["Cache-Control"] = "private, max-age=600"
            
            return {
                "norad_id": norad_id,
                "space_weather": weather.model_dump(mode="json"),
                "atmospheric_state": atm_state.model_dump(mode="json"),
                "forecasts": [f.model_dump(mode="json") for f in forecasts]
            }
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/ml/sensitivity")
    @limiter.limit("5/minute")
    def ml_sensitivity(request: Request, norad_id: int) -> dict:
        try:
            return data.sensitivity_sweep(norad_id=norad_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/admin/reload_models")
    def reload_models() -> dict:
        data.reload_models()
        return {"status": "success", "message": "Model cache cleared. New models will be loaded on next inference."}

    return app


app = create_app()
