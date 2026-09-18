# Module 8: Operations & Visualization Dashboard (`m8_dashboard`)

## Purpose
Provides the primary user interface for the SIH26161 framework. Enables operators to inspect the river network, trace and register new river centerlines on an interactive map, view scenario metrics, and manage geospatial assets.

## Current Implementation Status
- **Status:** Fully functional basic dashboard and river management engine.
- **Implemented:**
  - **Multi-page Navigation:** Home, Add River, and Rivers registry.
  - **Home Dashboard (`pages/1_Home.py`):** System overview, 3 metric cards (Rivers, Sites, Scenarios), interactive India map.
  - **Add River (`pages/2_Add_River.py`):** Interactive Leaflet.Draw polyline centerline tracing, input validation, and local GeoJSON persistence.
  - **Rivers Registry (`pages/3_Rivers.py`):** River listing, map inspection with highlight zoom, safe deletion with two-step confirmation, and GeoJSON export.
  - **Local Persistence (`services/river_store.py`):** Stores rivers in `data/rivers/rivers.geojson` as valid GeoJSON `FeatureCollection`.
  - **Test Suite (`tests/`):** 14 unit tests covering persistence, validation, GeoJSON compliance, and import integrity.

## Inputs
- User form inputs (River Name, River ID).
- Drawn vector geometries from Folium map interface.
- Contract fixtures and mock data from `contracts/fixtures/` and `data/mock/`.

## Outputs
- Updated `data/rivers/rivers.geojson` with registered `LineString` features.
- Interactive cartographic visualization layers.

## Relevant Contract Schemas
- `contracts/schemas/domain.schema.json`
- `contracts/schemas/artifact.schema.json`

## Dependencies
- `streamlit>=1.36.0`
- `folium>=0.16.0`
- `streamlit-folium>=0.20.0`
- `branca>=0.7.0`

## How to Run
From the repository root:
```bash
streamlit run modules/m8_dashboard/app.py
```
The application will open in your default browser at `http://localhost:8501`.

## How to Test
Execute unit tests without launching the Streamlit server:
```bash
pytest modules/m8_dashboard/tests -v
```

## Known Limitations
- Initial version supports centerline registration and spatial inspection; hydraulic boundary parameter assignment (inflow hydrographs, bathymetric roughness) will be linked via M1/M2 integrations.
