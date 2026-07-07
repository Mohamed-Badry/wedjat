# Justfile for Project Wedjat

set shell := ["bash", "-c"]

# List available recipes
default:
    @just --list

# --- Local Development ---

# Run both the cloud and edge development stacks concurrently
dev:
    @echo "Starting both dev-cloud and dev-edge profiles in parallel..."
    COMPOSE_PROFILES=dev-cloud,dev-edge docker compose up --build --watch

# Run only the cloud development stack
dev-cloud:
    COMPOSE_PROFILES=dev-cloud docker compose up --build --watch

# Run only the edge development stack
dev-edge:
    COMPOSE_PROFILES=dev-edge docker compose up --build --watch

# --- Phase 1: The Lab (Data Pipeline) ---

# Fetch raw telemetry from SatNOGS DB API → data/raw/
# Usage:
#   just fetch              -> Interactive Menu
#   just fetch --all        -> Download all (default 30 days)
#   just fetch --days 7     -> Interactive (default 7 days)
fetch +args='':
    pixi run python scripts/fetch_training_data.py {{args}}

# Fetch historical TLE data from Space-Track for a satellite and insert into DB / local cache
# Usage:
#   just fetch-tle --norad 43880 --days 30
#   just fetch-tle --norad 43880 --start 2026-01-01 --end 2026-07-01
fetch-tle +args='':
    pixi run python scripts/fetch_tle_data.py {{args}}

# Process raw data through the full pipeline: raw → interim → processed
# Usage:
#   just process              -> Interactive Menu
#   just process --norad 43880 -> Specific satellite
#   just process --all        -> All satellites with data + decoder
process +args='':
    pixi run python scripts/process_data.py {{args}}

# Train per-satellite scaler + VAE + persisted metadata artifact
# Usage:
#   just train --norad 43880
#   just train --norad 43880 --epochs 150
train +args='':
    pixi run python scripts/train_model.py {{args}}

# Train the Orbit Decay Ensemble ML Models for a satellite
# Usage:
#   just train-decay --norad 43880
#   just train-decay --norad 43880 --horizons 7,14,30
train-decay +args='':
    pixi run python scripts/train_decay_model.py {{args}}

# Run offline synthetic-fault benchmark for a trained satellite artifact
# Usage:
#   just benchmark --norad 43880
benchmark +args='':
    pixi run python scripts/generate_faults.py {{args}}

# End-to-end model loop for one satellite (train -> benchmark)
# Usage:
#   just train-benchmark 43880 250
train-benchmark norad='43880' epochs='250':
    pixi run python scripts/train_model.py --norad {{norad}} --epochs {{epochs}}
    pixi run python scripts/generate_faults.py --norad {{norad}}

# --- Phase 2: Operations (Analysis, Viz, Runtime) ---

# Regenerate target analysis and selection
analyze-targets:
    pixi run python notebooks/sat_analysis.py

# Generate operational dashboards (Skyplots, Gantt)
viz-passes:
    pixi run python notebooks/pass_analysis_viz.py

# Run the full visualization pipeline (Select -> Visualize)
regenerate-all: analyze-targets viz-passes

# Minimal deterministic online wedjat runtime
# Usage:
#   just wedjat --norad 43880 --help
#   just wedjat --norad 43880 --payload-hex "AABB..." --timestamp "2026-01-01T00:00:00Z"
wedjat +args='':
    pixi run python scripts/wedjat_runtime.py {{args}}

# Run regression tests
test:
    pixi run python -m unittest discover -s tests -v

# --- Utilities ---

# Sync Jupyter Notebooks from Scripts
sync-notebooks:
    @for script in notebooks/*.py; do \
        filename=$(basename -- "$script"); \
        name="${filename%.*}"; \
        echo "Syncing notebook-script $script to notebooks/$name.ipynb"; \
        pixi run jupytext --to notebook --update "$script" --output "notebooks/$name.ipynb"; \
    done

# Convert a Python script to a Jupyter Notebook
# Usage: just convert notebooks/script.py
convert script_path:
    pixi run jupytext --to notebook "{{script_path}}"

# Clean temporary files (pycache, etc.)
clean:
    rm -rf __pycache__ .pytest_cache
    find . -name "*.pyc" -delete
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# --- Phase 3: Frontend (SvelteKit + Tailwind) ---

# Run the frontend development server
# Usage: just frontend-dev
frontend-dev:
    cd frontend && bun run dev

# Build the frontend for production
# Usage: just frontend-build
frontend-build:
    cd frontend && bun run build

# Preview the built frontend production bundle
# Usage: just frontend-preview
frontend-preview:
    cd frontend && bun run preview

# --- Documentation ---

# Compile all Typst slide decks into PDFs
docs:
    @for deck in docs/slides/*.typ; do \
        filename=$(basename -- "$deck"); \
        name="${filename%.*}"; \
        echo "Compiling $deck to docs/slides/$name.pdf"; \
        cd docs && typst compile --root .. "slides/$filename" "slides/$name.pdf" && cd ..; \
    done

# --- SDR Hardware ---

# Verify that the RTL-SDR hardware is connected and accessible
# Usage: just verify-sdr
verify-sdr:
    @echo "Checking RTL-SDR hardware connection..."
    rtl_test -t || (echo "Failed to connect to RTL-SDR. Is it plugged in?" && exit 1)
    @echo "RTL-SDR is connected and ready!"

# Capture live RF from RTL-SDR and bridge to the Edge ZMQ Demodulator
# Usage: just live-sdr 437.375M
# Or to override sample rate: just live-sdr 437.375M 57600
live-sdr freq samp_rate='57600':
    @echo "Starting live SDR bridge at {{freq}} with sample rate {{samp_rate}}..."
    rtl_sdr -f {{freq}} -s {{samp_rate}} - | pixi run python scripts/rtl_sdr_zmq_bridge.py
