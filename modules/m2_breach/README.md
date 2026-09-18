# Module 2: Breach & Hydrograph Synthesis Engine (`m2_breach`)

## Purpose
Computes breach geometries (breach width, formation time, peak discharge) and synthesizes the time-dependent outflow hydrograph for dam failures, moraine dams (GLOF), and landslide dams.

## Current Implementation Status
- **Status:** Architectural scaffold and formula interfaces defined.
- **Implemented:** Module files (`froehlich.py`, `macdonald_langridge.py`, `hydrograph.py`, `scenario_builder.py`, `pipeline.py`).
- **Pending:** Integration of historical empirical curve fitting and full multi-method comparison.

## Inputs
- `FailureSource` object (dam height $h_d$, reservoir volume $V_w$, barrier type).
- Severity index ($0-100$) or explicit physical parameters ($B_{avg}$, $t_f$, $h_b$).
- Trigger type (`overtopping`, `piping`, `structural_collapse`).

## Outputs
- `ScenarioBundle` containing:
  - `PhysicalScenario`: Content-addressed scenario identifier, initial conditions, and breach parameters.
  - `DischargeSeries`: Synthetic time-series of discharge $Q(t)$ from $t_0$ to stabilization.

## Relevant Contract Schemas
- `contracts/schemas/failure_source.schema.json`
- `contracts/schemas/breach_parameters.schema.json`
- `contracts/schemas/hydrograph.schema.json`
- `contracts/schemas/physical_scenario.schema.json`

## Dependencies
- `numpy`, `scipy`, `pandas`

## How to Run / Test
```bash
pytest modules/m2_breach/tests
```

## Known Limitations
- Current formulas reflect Froehlich (2008) and MacDonald-Langridge (1984); dynamic erosion physics (e.g., WinDAM) is not implemented.
