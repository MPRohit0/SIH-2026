# Module 4: DualSPHysics 3D Particle Hydrodynamics (`m4_sph`)

## Purpose
Simulates 3D violent free-surface flow and surge dynamics in the immediate near-field of a dam breach or moraine collapse using Smoothed Particle Hydrodynamics (SPH).

## Current Implementation Status
- **Status:** Interface and adapter architecture defined.
- **Implemented:** Source layout (`case_builder.py`, `input_generator.py`, `runner.py`, `output_parser.py`, `adapter.py`), templates, and test directory.
- **Pending:** DualSPHysics XML Case generation and particle-to-surface grid post-processor.

## Inputs
- `TerrainManifest` with `sph_boundary_geometry` (near-field DEM converted to boundary geometry / STL).
- `ScenarioBundle` with initial water column volume and breach geometry.

## Outputs
- Standardized `FloodSimulationResult` (strictly identical schema to Delft3D, ensuring model symmetry).

## Relevant Contract Schemas
- `contracts/schemas/flood_simulation_result.schema.json`
- `contracts/schemas/domain.schema.json`

## Dependencies
- Python: `numpy`, `scipy`
- External software: DualSPHysics v5.2 executable (`DualSPHysics5.2_Linux64` or Windows executable, configured via `DUALSPHYSICS_PATH`).
- Hardware: NVIDIA CUDA-capable GPU recommended.

## How to Run / Test
```bash
pytest modules/m4_sph/tests
```

## Known Limitations
- SPH is computationally intensive and restricted to the near-field region (< 5 km from breach). Downstream reach propagation is delegated to M3 (Delft3D).
