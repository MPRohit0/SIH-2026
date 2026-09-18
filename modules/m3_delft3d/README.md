# Module 3: Delft3D-FLOW / Flexible Mesh Integration (`m3_delft3d`)

## Purpose
Manages 2D hydrodynamic flood propagation modeling along the downstream river reach, generating input deck configuration (`.mdu`, `.bct`), executing the simulation, and post-processing NetCDF outputs into contract-standard rasters and vectors.

## Current Implementation Status
- **Status:** Interface and adapter architecture defined.
- **Implemented:** Source layout (`case_builder.py`, `input_generator.py`, `runner.py`, `output_parser.py`, `adapter.py`), templates, and test directory.
- **Pending:** Live execution hook to Delft3D binary and NetCDF grid extraction logic.

## Inputs
- `TerrainManifest` (DEM, roughness, boundary points).
- `ScenarioBundle` (boundary hydrograph discharge time series).

## Outputs
- Standardized `FloodSimulationResult`:
  - Temporal depth rasters ($t_0, t_{30}, t_{60} \dots$).
  - Temporal velocity rasters.
  - Maximum flood extent vector (`FeatureCollection`).
  - Arrival-time raster (minutes to threshold depth $\ge 0.30\text{ m}$).
  - Summary metrics (inundated area $\text{km}^2$, max depth $\text{m}$, peak velocity $\text{m/s}$).

## Relevant Contract Schemas
- `contracts/schemas/flood_simulation_result.schema.json`
- `contracts/schemas/domain.schema.json`

## Dependencies
- Python: `numpy`, `xarray`, `netcdf4`, `rasterio`
- External software: Delft3D Flexible Mesh / Delft3D 4.x compiled binaries (configured via `DELFT3D_PATH`).

## How to Run / Test
```bash
pytest modules/m3_delft3d/tests
```

## Known Limitations
- Solver execution requires pre-installed Delft3D binaries; in development mode, mock result fixtures from `data/mock/` should be utilized.
