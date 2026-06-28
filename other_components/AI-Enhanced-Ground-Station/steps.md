# UWE-4 Dashboard - Operating Guide

## First-Time Setup

Open PowerShell in the project folder and install dependencies:

```powershell
cd "E:\My-Study\Semester-10\Graduation Project\final_project\v12"
python -m pip install -r requirements.txt
```

## Start The System

```powershell
python app.py
```

Wait until the terminal shows:

```text
INFO:     Application startup complete.
```

Then open:

```text
http://localhost:8000
```

## Stop The System

Press `Ctrl + C` in the terminal running the server.

If the server is running in another terminal and port `8000` is busy:

```powershell
Get-Process python | Stop-Process
```

## Run On Another Port

```powershell
$env:PORT="8001"
python app.py
```

Then open:

```text
http://localhost:8001
```

## Refresh Conjunction Events

```powershell
python generate_conjunctions.py
```

## Validate The Backend

```powershell
python test_pipeline.py
```

## Important Files

| File | Purpose |
|------|---------|
| `app.py` | FastAPI backend and SGP4 calculations |
| `static/dashboard.html` | Main dashboard UI |
| `data/43880.tle` | Cached TLE fallback |
| `data/43880.csv` | Telemetry dataset |
| `data/conjunction_events.csv` | Conjunction-event catalog |
| `data/visible_passes.csv` | Visible pass schedule |
| `models/orbit_ai_model.pkl` | Orbit-correction model bundle |
| `models/collision_ai_model.pkl` | Collision-probability model bundle |
