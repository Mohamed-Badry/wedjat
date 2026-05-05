from fastapi import FastAPI

app = FastAPI(
    title="gr_sat Watchdog API",
    description="FastAPI Backend for Satellite Telemetry Streaming and ML Inference"
)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Backend scaffolding complete. Ready to build the API endpoints!"
    }
