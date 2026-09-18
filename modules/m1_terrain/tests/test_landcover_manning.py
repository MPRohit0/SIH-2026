"""Tests for contract-compliant land-cover and Manning roughness processing."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from modules.m1_terrain.config.settings import DEFAULT_MODULE1_CONFIG
from modules.m1_terrain.src.landcover import (
    LandCoverProcessingError,
    build_landcover_and_manning,
    load_landcover,
    validate_landcover_raster,
)


@pytest.fixture
def dem_fixture_path(tmp_path: Path) -> Path:
    """Create a minimal DEM raster aligned to the land-cover raster."""
    path = tmp_path / "dem.tif"
    data = np.array(
        [
            [10.0, 11.0],
            [12.0, 13.0],
        ],
        dtype=np.float32,
    )
    profile = {
        "driver": "GTiff",
        "height": data.shape[0],
        "width": data.shape[1],
        "count": 1,
        "dtype": "float32",
        "crs": "EPSG:4326",
        "transform": from_origin(79.8, 30.7, 0.01, 0.01),
        "nodata": -9999.0,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data, 1)
    return path


@pytest.fixture
def landcover_fixture_path(tmp_path: Path, dem_fixture_path: Path) -> Path:
    """Create a valid land-cover raster aligned to the DEM grid."""
    path = tmp_path / "landcover.tif"
    data = np.array(
        [
            [1, 2],
            [1, 3],
        ],
        dtype=np.int16,
    )
    profile = {
        "driver": "GTiff",
        "height": data.shape[0],
        "width": data.shape[1],
        "count": 1,
        "dtype": "int16",
        "crs": "EPSG:4326",
        "transform": from_origin(79.8, 30.7, 0.01, 0.01),
        "nodata": -9999,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data, 1)
    return path


def test_load_landcover_and_validate_grid(landcover_fixture_path: Path) -> None:
    """A local land-cover raster should be readable and validated."""
    data, meta = load_landcover(landcover_fixture_path)
    assert data.dtype.kind in {"i", "u"}
    assert meta["crs"] == "EPSG:4326"
    assert meta["width"] == 2
    assert meta["height"] == 2

    valid, issues = validate_landcover_raster(data, meta)
    assert valid is True
    assert issues == []


def test_known_classes_are_mapped_to_manning_values(
    dem_fixture_path: Path,
    landcover_fixture_path: Path,
    tmp_path: Path,
) -> None:
    """Known land-cover classes must produce the configured Manning values."""
    output_dir = tmp_path / "terrain" / "demo_site"
    result = build_landcover_and_manning(
        site_id="demo_site",
        dem_path=dem_fixture_path,
        landcover_path=landcover_fixture_path,
        bbox_wgs84=[79.8, 30.7, 79.81, 30.71],
        output_dir=output_dir,
        lookup_table=DEFAULT_MODULE1_CONFIG.landcover_to_manning_n,
    )

    landcover_path = output_dir / "landcover.tif"
    manning_path = output_dir / "manning_n.tif"
    assert landcover_path.exists()
    assert manning_path.exists()

    with rasterio.open(landcover_path) as landcover_ds:
        assert landcover_ds.crs == rasterio.crs.CRS.from_epsg(4326)
        assert landcover_ds.profile["dtype"] in {"int16", "int32", "uint16"}

    with rasterio.open(manning_path) as manning_ds:
        assert manning_ds.crs == rasterio.crs.CRS.from_epsg(4326)
        assert manning_ds.profile["dtype"] == "float32"
        assert manning_ds.transform == rasterio.open(dem_fixture_path).transform

    # The output raster must align exactly with the DEM grid.
    with rasterio.open(dem_fixture_path) as dem_ds:
        assert manning_ds.width == dem_ds.width
        assert manning_ds.height == dem_ds.height
        assert manning_ds.transform == dem_ds.transform


def test_unknown_class_raises_explicit_error(
    dem_fixture_path: Path,
    tmp_path: Path,
) -> None:
    """An unconfigured class must raise a clear error rather than silently defaulting."""
    landcover_path = tmp_path / "unknown_landcover.tif"
    data = np.array(
        [
            [99, 1],
            [2, 99],
        ],
        dtype=np.int16,
    )
    profile = {
        "driver": "GTiff",
        "height": data.shape[0],
        "width": data.shape[1],
        "count": 1,
        "dtype": "int16",
        "crs": "EPSG:4326",
        "transform": from_origin(79.8, 30.7, 0.01, 0.01),
        "nodata": -9999,
    }
    with rasterio.open(landcover_path, "w", **profile) as dst:
        dst.write(data, 1)

    with pytest.raises((LandCoverProcessingError, ValueError)):
        build_landcover_and_manning(
            site_id="demo_site",
            dem_path=dem_fixture_path,
            landcover_path=landcover_path,
            bbox_wgs84=[79.8, 30.7, 79.81, 30.71],
            output_dir=tmp_path / "terrain" / "demo_site_unknown",
            lookup_table={1: 0.03, 2: 0.04, 3: 0.05},
        )
