"""Module 1 terrain package foundation.

This package intentionally exposes the core import surface for Module 1 while
keeping the full data-processing pipeline unimplemented until the contract and
module boundaries are finalized.
"""

from __future__ import annotations

from .clipping import clip_dem, validate_bbox_wgs84
from .acquisition import (
    BhuvanAcquisitionError,
    BhuvanAdapter,
    Sentinel2AcquisitionError,
    Sentinel2Adapter,
    SRTMAcquisitionError,
    SRTMAdapter,
)
from .dem_processing import calculate_raster_meta, generate_manning_n_grid, validate_dem
from .domain import DomainConsistencyError, generate_simulation_domain, validate_domain_consistency
from .ingestion import load_dem, load_river
from .landcover import (
    LandCoverProcessingError,
    build_landcover_and_manning,
    build_landcover_summary,
    load_landcover,
    validate_landcover_raster,
)
from .manifest import TerrainManifestError, generate_terrain_manifest, validate_terrain_manifest
from .pipeline import TerrainPipelineError, run_terrain_pipeline
from .reprojection import determine_utm_crs, reproject_dem
from .river_geometry import clip_river_to_aoi, create_domain_geojson, validate_river_geometry
from .roughness import build_roughness_summary

__all__ = [
    "clip_dem",
    "validate_bbox_wgs84",
    "BhuvanAcquisitionError",
    "BhuvanAdapter",
    "Sentinel2AcquisitionError",
    "Sentinel2Adapter",
    "SRTMAcquisitionError",
    "SRTMAdapter",
    "generate_simulation_domain",
    "validate_domain_consistency",
    "DomainConsistencyError",
    "calculate_raster_meta",
    "generate_manning_n_grid",
    "validate_dem",
    "load_dem",
    "load_river",
    "build_landcover_summary",
    "build_landcover_and_manning",
    "load_landcover",
    "validate_landcover_raster",
    "LandCoverProcessingError",
    "generate_terrain_manifest",
    "validate_terrain_manifest",
    "TerrainManifestError",
    "run_terrain_pipeline",
    "TerrainPipelineError",
    "determine_utm_crs",
    "reproject_dem",
    "clip_river_to_aoi",
    "create_domain_geojson",
    "validate_river_geometry",
    "build_roughness_summary",
]
