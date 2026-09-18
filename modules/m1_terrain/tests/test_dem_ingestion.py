"""Tests for Module 1 DEM ingestion and validation."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from modules.m1_terrain.src.ingestion import (
    DEMNotFoundError,
    DEMReadError,
    DEMValidationError,
    load_dem,
)


@pytest.fixture
def valid_dem_path(tmp_path: Path) -> Path:
    """Create a small valid DEM GeoTIFF fixture."""
    path = tmp_path / "valid_dem.tif"
    data = np.array([[10.0, 12.0], [15.0, 20.0]], dtype=np.float32)
    profile = {
        "driver": "GTiff",
        "height": data.shape[0],
        "width": data.shape[1],
        "count": 1,
        "dtype": "float32",
        "crs": "EPSG:4326",
        "transform": from_origin(0.0, 2.0, 1.0, 1.0),
        "nodata": -9999.0,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data, 1)
    return path


def test_load_dem_success(valid_dem_path: Path) -> None:
    """A valid DEM should load and return readable metadata."""
    data, meta = load_dem(valid_dem_path)

    assert data.shape == (2, 2)
    assert data.dtype == np.float32
    assert meta["crs"] == "EPSG:4326"
    assert meta["width"] == 2
    assert meta["height"] == 2
    assert meta["resolution"] == (1.0, 1.0)
    assert meta["nodata"] == -9999.0
    assert meta["transform"] is not None
    assert meta["bounds"] is not None


def test_load_dem_missing_file_raises(tmp_path: Path) -> None:
    """Missing files must raise a domain-specific error."""
    missing = tmp_path / "missing_dem.tif"
    with pytest.raises(DEMNotFoundError):
        load_dem(missing)


def test_load_dem_missing_crs_raises(tmp_path: Path) -> None:
    """DEM files without CRS metadata are invalid for the terrain contract."""
    path = tmp_path / "missing_crs_dem.tif"
    data = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
    profile = {
        "driver": "GTiff",
        "height": 2,
        "width": 2,
        "count": 1,
        "dtype": "float32",
        "transform": from_origin(10.0, 20.0, 1.0, 1.0),
        "nodata": -9999.0,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data, 1)

    with pytest.raises(DEMValidationError):
        load_dem(path)


def test_load_dem_invalid_raster_raises(tmp_path: Path) -> None:
    """Corrupted or unreadable GeoTIFF data must fail clearly."""
    path = tmp_path / "invalid_dem.tif"
    path.write_text("not a GeoTIFF file", encoding="utf-8")

    with pytest.raises((DEMReadError, DEMValidationError, ValueError)):
        load_dem(path)


def test_load_dem_metadata_is_readable(valid_dem_path: Path) -> None:
    """The metadata dictionary should expose the shape and geospatial details needed downstream."""
    _, meta = load_dem(valid_dem_path)

    assert meta["crs"] == "EPSG:4326"
    assert meta["width"] > 0
    assert meta["height"] > 0
    assert meta["resolution"][0] > 0
    assert meta["resolution"][1] > 0
    assert meta["dtype"] in {"float32", "float64", "int16", "int32", "uint8"}
    assert meta["bounds"]
