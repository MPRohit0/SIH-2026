# Module 1: Terrain & River Processing Engine (`m1_terrain`)

## Purpose
Preprocesses digital elevation models (DEMs), land use / land cover (LULC) data, Manning's roughness coefficients, and river geometry to construct the standardized `TerrainManifest` required by downstream hydraulic solvers.

## Current Implementation Status
- **Status:** Architecture skeleton and pipeline interfaces defined.
- **Implemented:** Source file skeleton (`ingestion.py`, `dem_processing.py`, `reprojection.py`, `clipping.py`, `landcover.py`, `roughness.py`, `river_geometry.py`, `pipeline.py`).
- **Pending:** Implementation of full GDAL/Rasterio raster operations and automated River centerline generation from DEM drainage networks.

## Inputs
- Raw elevation rasters (GeoTIFF, SRTM / Copernicus 30m) under `data/raw/dem/`.
- Site bounding box (`bbox_wgs84`: `[min_lon, min_lat, max_lon, max_lat]`).
- Optional LULC rasters (ESA WorldCover / Copernicus).

## Outputs
- Standardized `TerrainManifest` payload referencing:
  - Projected DEM raster artifact (`EPSG:32644` or UTM equivalent).
  - Manning's $n$ roughness grid artifact.
  - River centerline GeoJSON LineString artifact.
  - Optional cross-sections vector artifact.

## Relevant Contract Schemas
- `contracts/schemas/terrain_manifest.schema.json`
- `contracts/schemas/artifact.schema.json`

## Dependencies
- `numpy`, `rasterio`, `shapely`, `geopandas`, `pyproj`
- Optional system dependency: `gdal-bin`

## How to Run / Test
```bash
pytest modules/m1_terrain/tests
```

## Known Limitations
- Offline processing depends on local DEM availability; automatic downloading from elevation APIs is not yet active.
- River cross-section bathymetry approximation is planned for subsequent iterations.
