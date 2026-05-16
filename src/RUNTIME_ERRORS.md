## [Severity: CRITICAL] - [Blocking Synchronous Calls in Async FastAPI Routes]
- **File(s):** `src/api/main.py` (Lines 74-148)
- **Category:** FastAPI Concurrency
- **The Flaw:** Standard HTTP routes (like `/api/dashboard/summary` and `/api/status`) are defined with `async def`, yet they invoke fully synchronous `DashboardDataRepository` methods. These repository methods perform blocking disk I/O (`pd.read_csv`), synchronous PostgreSQL queries, and heavy CPU-bound PyTorch ML inference. 
- **The Impact:** Event Loop Blocked / Denial of Service. Because FastAPI executes `async def` routes on the main event loop thread, any concurrent requests will hang completely while these synchronous operations run. The `websocket_dashboard` route is critically dangerous because it calls the blocking `data.dashboard_summary()` every 2 seconds in an infinite loop, starving the event loop and effectively crippling the server.
- **The Fix:** Convert all purely synchronous HTTP endpoints from `async def` to regular `def` (which FastAPI automatically runs in an isolated thread pool). For endpoints that must remain async (like WebSockets), delegate the blocking call to `run_in_threadpool`.

```python
# Fix for standard HTTP routes: Remove 'async'
@app.get("/api/dashboard/summary")
def dashboard_summary() -> dict:
    return data.dashboard_summary()

# Fix for WebSockets: Use run_in_threadpool
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
```

---

## [Severity: HIGH] - [Dangling Database Transactions and Split Commits]
- **File(s):** `src/api/mqtt_client.py` (Lines 70-111)
- **Category:** DB Transaction
- **The Flaw:** The MQTT `on_message` handler performs two distinct `session.commit()` calls within the same context manager. It commits `RawFrame` first, then runs ML scoring logic, and finally commits `TelemetryFrame`. There is no `try/except/rollback` block wrapping the transaction.
- **The Impact:** Data Corruption and Transaction Leaks. If the PyTorch ML inference fails or the `TelemetryFrame` insertion raises an `IntegrityError`, the `RawFrame` is already durably committed to the database. This leaves orphaned, dangling records in the database, breaking referential assumptions and dirtying the telemetry dataset.
- **The Fix:** Consolidate the database inserts into a single, atomic transaction wrapped in a `try...except` block with an explicit rollback.

```python
        with Session(engine, expire_on_commit=False) as session:
            try:
                raw_record = RawFrame(...)
                session.add(raw_record)
                
                # ... [ML Scoring Logic] ...
                
                telem_record = TelemetryFrame(..., raw_frame_id=raw_record.id)
                session.add(telem_record)
                
                # Single atomic commit
                session.commit()
                logger.info(f"Persisted frame for NORAD {norad_id}")
            except Exception as e:
                session.rollback()
                logger.error(f"Transaction failed, rolled back: {e}", exc_info=True)
```

---

## [Severity: HIGH] - [Swallowed Database Exceptions / Silent Failure on Live Telemetry]
- **File(s):** `src/api/dashboard_data.py` (Lines 618-623)
- **Category:** Silent Failure
- **The Flaw:** When querying the live PostgreSQL database via `session.exec()`, any exception (such as `OperationalError`, `DataError`, or connection drops) is caught using a blind `except Exception as e:` block. The error is logged as a warning, and execution blindly continues without appending any live data.
- **The Impact:** Silent Failure / State Inconsistency. If the database goes offline, the dashboard API silently falls back to using only old CSV artifacts. The client receives an HTTP 200 OK with severely stale data, masking critical database outages from operators and failing to expose the internal error boundary.
- **The Fix:** Catch specific database errors and explicitly re-raise them so the FastAPI exception handlers can correctly surface a 5xx HTTP response.

```python
            from sqlalchemy.exc import SQLAlchemyError

            try:
                # ... session.exec(statement)
            except SQLAlchemyError as e:
                import logging
                logging.getLogger("DashboardDataRepository").error(
                    f"Critical database query failure for {sat_id}: {e}"
                )
                # Re-raise to ensure API returns a 500 error instead of stale data
                raise RuntimeError(f"Database query failed: {e}") from e
```
