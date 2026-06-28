# ⚠️ LEGACY ARCHIVE: AI-Enhanced Ground Station Prototype

> [!WARNING]
> **This directory contains legacy prototype code and is NOT production-ready.**
> The code in this folder represents an early experimental prototype developed separately by a different team. It contains suboptimal science/engineering shortcuts (including hardcoded values, simplified assumptions, and mock models). 

## Status & Migration
* **Do Not Deploy:** This directory is preserved strictly for historical reference.
* **Production Core:** All valid mathematical methodologies (including the Foster 1992 conjunction probability calculations) have been cleaned up, audited, and fully re-implemented in the main repository:
  - Backend Core: [src/gr_sat/](file:///home/crim/Projects/gr_sat/src/gr_sat)
  - Production API: [src/api/](file:///home/crim/Projects/gr_sat/src/api)
  - Svelte Dashboard: [frontend/src/](file:///home/crim/Projects/gr_sat/frontend/src)

## Contents
* `app.py`: Legacy FastAPI prototype web service.
* `train_collision_model.py` / `generate_conjunctions.py`: Early conjunction threat analysis scripts.
