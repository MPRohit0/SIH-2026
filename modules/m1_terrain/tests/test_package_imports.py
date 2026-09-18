"""Minimal import validation for the Module 1 package foundation."""

from __future__ import annotations

from modules.m1_terrain.config import get_module1_config
from modules.m1_terrain.src import (
    build_landcover_summary,
    build_roughness_summary,
    calculate_raster_meta,
    clip_dem,
    create_domain_geojson,
    determine_utm_crs,
    generate_manning_n_grid,
    load_dem,
    load_river,
    run_terrain_pipeline,
    validate_bbox_wgs84,
    validate_dem,
    validate_river_geometry,
)


def test_module1_config_imports() -> None:
    """The config object should be importable and expose a repo-root-based config."""
    config = get_module1_config()
    assert config.module_root.name == "m1_terrain"
    assert config.data_root.name == "data"


def test_module1_package_exports_public_api() -> None:
    """The package should expose the expected public symbols without import errors."""
    assert callable(validate_bbox_wgs84)
    assert callable(determine_utm_crs)
    assert callable(load_dem)
    assert callable(load_river)
    assert callable(validate_dem)
    assert callable(calculate_raster_meta)
    assert callable(generate_manning_n_grid)
    assert callable(clip_dem)
    assert callable(validate_river_geometry)
    assert callable(create_domain_geojson)
    assert callable(build_landcover_summary)
    assert callable(build_roughness_summary)
    assert callable(run_terrain_pipeline)
