# Module 5: Fast Scenario Engine, Interpolation & Validation (`m5_scenario_engine`)

## Purpose
Provides sub-second retrieval of flood inundation predictions for arbitrary scenarios by combining precomputed solver runs with multi-dimensional spatial interpolation (RBF / Kriging). Computes dynamic confidence scores and historical validation metrics.

## Current Implementation Status
- **Status:** Architectural scaffold defined.
- **Implemented:** Modular interfaces (`api.py`, `database.py`, `models.py`, `cache.py`, `interpolation.py`, `validation.py`, `confidence.py`, `historical.py`, `service.py`).
- **Pending:** Implementation of RBF interpolation algorithms, spatial weight calculation, and historical event benchmark runner.

## Inputs
- `ScenarioQueryRequest` (target `scenario_id`, requested models: `sph`, `delft3d`).
- Stored library of precomputed `FloodSimulationResult` grids across calibrated severity levels.

## Outputs
- `FloodQueryResponse` containing `PerModelFloodResult` for requested models:
  - Interpolated depth, velocity, arrival time, and extent layers.
  - Neighbor provenance (source scenario IDs and non-negative normalized weights).
  - `ConfidenceResult` (`HIGH`, `MODERATE`, `LOW`).
- `ValidationResult`: Holdout validation metrics (IoU, MAE, area error %).
- `HistoricalValidationResult`: Historical benchmark comparison (Chamoli 2021, Kedarnath 2013).

## Relevant Contract Schemas
- `contracts/schemas/scenario_query_request.schema.json`
- `contracts/schemas/flood_query_response.schema.json`
- `contracts/schemas/validation_result.schema.json`
- `contracts/schemas/confidence_result.schema.json`
- `contracts/schemas/historical_validation_result.schema.json`

## Dependencies
- `numpy`, `scipy`, `pydantic`

## How to Run / Test
```bash
pytest modules/m5_scenario_engine/tests
```

## Known Limitations
- Interpolation is strictly constrained to the validated convex envelope of precomputed scenarios; extrapolation requests return `interpolation_out_of_valid_range`.
