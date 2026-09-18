# Module 7: Google Earth Engine Satellite Observation (`m7_gee`)

## Purpose
Acquires and processes near-real-time satellite Earth observations to detect flood extents, estimate antecedent precipitation, and provide validation footprints via Google Earth Engine (GEE).

## Current Implementation Status
- **Status:** Architectural scaffold and fallback provider defined.
- **Implemented:** Source layout (`sentinel1.py`, `sentinel2.py`, `rainfall.py`, `flood_observation.py`, `fallback.py`, `pipeline.py`).
- **Pending:** Live GEE authentication pipeline and automated Otsu thresholding on SAR backscatter.

## Inputs
- `failure_source_id` and bounding box (`bbox_wgs84`).
- Query mode (`latest` for real-time monitoring or `historical` with explicit date).

## Outputs
- `SatelliteOverlayResponse`:
  - Processed water extent overlay raster/vector artifact.
  - Sensor metadata (Sentinel-1 SAR or Sentinel-2 Optical).
  - Fallback indicator (`is_fallback: true` when offline/cached).
- `HistoricalObservationBundle`: Ground truth extent and gauging records for model validation.

## Relevant Contract Schemas
- `contracts/schemas/satellite_overlay.schema.json`
- `contracts/schemas/artifact.schema.json`

## Dependencies
- `earthengine-api`, `httpx`

## How to Run / Test
```bash
pytest modules/m7_gee/tests
```

## Known Limitations
- Live satellite querying requires configured GEE credentials (`GEE_PROJECT_ID`, `GEE_SERVICE_ACCOUNT`). In offline/demo mode, the module returns contract-compliant fallback artifacts from `data/mock/`.
