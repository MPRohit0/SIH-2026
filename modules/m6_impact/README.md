# Module 6: Exposure & Impact Analysis Engine (`m6_impact`)

## Purpose
Intersects maximum flood extent and depth rasters with socio-economic layers (population, buildings, critical infrastructure, road networks, and agricultural land) to estimate damages and export GIS packages.

## Current Implementation Status
- **Status:** Architectural scaffold defined.
- **Implemented:** Source layout (`population.py`, `infrastructure.py`, `overlay.py`, `statistics.py`, `export.py`, `pipeline.py`).
- **Pending:** Implementation of zonal statistics raster-vector intersection and zip package export generator.

## Inputs
- `PerModelFloodResult` from M5 (depth raster and max flood extent vector).
- Population density raster (WorldPop / LandScan) under `data/raw/worldpop/`.
- Infrastructure vector layers (OpenStreetMap buildings, highways, hospitals) under `data/raw/osm/`.

## Outputs
- `ImpactResult`:
  - Exposed population count and availability status.
  - Inundated buildings count.
  - Disrupted road length (km).
  - List of affected critical facilities (schools, hospitals).
  - Export artifacts: Zipped Shapefile package (`.shp`, `.shx`, `.dbf`, `.prj`), KML, and GeoJSON.

## Relevant Contract Schemas
- `contracts/schemas/impact_response.schema.json`
- `contracts/schemas/artifact.schema.json`

## Dependencies
- `numpy`, `pandas`, `shapely`

## How to Run / Test
```bash
pytest modules/m6_impact/tests
```

## Known Limitations
- Data availability is reported granularly: if an underlying dataset is missing, the response reports `status="partial"` with `dataset_unavailable` rather than reporting a false zero.
