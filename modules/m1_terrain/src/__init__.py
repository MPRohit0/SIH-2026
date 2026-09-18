"""Module 1 terrain package foundation.

This package intentionally exposes the core import surface for Module 1 while
keeping the full data-processing pipeline unimplemented until the contract and
module boundaries are finalized.
"""

from __future__ import annotations

from .clipping import clip_dem, validate_bbox_wgs84
from .dem_processing import calculate_raster_meta, generate_manning_n_grid, validate_dem
from .ingestion import load_dem, load_river
from .landcover import build_landcover_summary
from .pipeline import run_terrain_pipeline
from .reprojection import determine_utm_crs, reproject_dem
from .river_geometry import clip_river_to_aoi, create_domain_geojson, validate_river_geometry
from .roughness import build_roughness_summary

__all__ = [
    "clip_dem",
    "validate_bbox_wgs84",
    "calculate_raster_meta",
    "generate_manning_n_grid",
    "validate_dem",
    "load_dem",
    "load_river",
    "build_landcover_summary",
    "run_terrain_pipeline",
    "determine_utm_crs",
    "reproject_dem",
    "clip_river_to_aoi",
    "create_domain_geojson",
    "validate_river_geometry",
    "build_roughness_summary",
]
