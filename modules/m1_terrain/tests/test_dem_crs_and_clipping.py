"""Tests for DEM CRS handling and AOI clipping."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import rasterio
from pyproj import CRS, Transformer
from rasterio.transform import from_origin

from modules.m1_terrain.src.clipping import clip_dem
from modules.m1_terrain.src.reprojection import reproject_dem


@pytest.fixture
def synthetic_dem_path(tmp_path: Path) -> Path:
    """Create a small synthetic DEM in EPSG:4326."""
    path = tmp_path / "synthetic_dem.tif"
    data = np.array(
        [
            [10.0, 11.0, 12.0],
            [13.0, 14.0, 15.0],
            [16.0, 17.0, 18.0],
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
        "transform": from_origin(0.0, 3.0, 1.0, 1.0),
        "nodata": -9999.0,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data, 1)
    return path


def test_same_crs_clipping(synthetic_dem_path: Path, tmp_path: Path) -> None:
    """Clipping in the same CRS should preserve the raster and metadata."""
    out_path = tmp_path / "clipped_same_crs.tif"
    data, meta, bbox = clip_dem(
        synthetic_dem_path,
        [0.0, 1.0, 2.0, 3.0],
        output_path=out_path,
    )

    assert data.shape[0] > 0
    assert data.shape[1] > 0
    assert meta["crs"] == "EPSG:4326"
    assert meta["nodata"] == -9999.0
    assert meta["transform"] is not None
    assert meta["resolution"][0] > 0
    assert bbox[0] >= 0.0
    assert out_path.exists()


def test_reprojection_to_utm(synthetic_dem_path: Path, tmp_path: Path) -> None:
    """A DEM can be reprojected to a projected CRS without losing georeferencing metadata."""
    out_path = tmp_path / "reprojected_dem.tif"
    data, meta = reproject_dem(
        synthetic_dem_path,
        "EPSG:3857",
        output_path=out_path,
    )

    assert data.shape[0] > 0
    assert data.shape[1] > 0
    assert meta["crs"] == "EPSG:3857"
    assert meta["transform"] is not None
    assert meta["resolution"][0] > 0
    assert meta["bounds"] is not None
    assert out_path.exists()


def test_aoi_outside_raster_raises(synthetic_dem_path: Path) -> None:
    """An AOI outside the DEM bounds should fail cleanly."""
    with pytest.raises(ValueError):
        clip_dem(synthetic_dem_path, [100.0, 100.0, 101.0, 101.0])


def test_partially_overlapping_aoi_clips(synthetic_dem_path: Path, tmp_path: Path) -> None:
    """Partial overlap should still produce a valid clipped raster."""
    out_path = tmp_path / "partial_clip.tif"
    data, meta, bbox = clip_dem(
        synthetic_dem_path,
        [0.5, 1.5, 2.5, 3.5],
        output_path=out_path,
    )

    assert data.size > 0
    assert meta["width"] > 0
    assert meta["height"] > 0
    assert bbox[0] <= bbox[2]
    assert bbox[1] <= bbox[3]
    assert out_path.exists()


def test_invalid_crs_raises(tmp_path: Path) -> None:
    """An invalid CRS string must not be silently accepted."""
    path = tmp_path / "invalid_crs_dem.tif"
    data = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
    profile = {
        "driver": "GTiff",
        "height": 2,
        "width": 2,
        "count": 1,
        "dtype": "float32",
        "transform": from_origin(0.0, 2.0, 1.0, 1.0),
        "nodata": -9999.0,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data, 1)

    with pytest.raises(ValueError):
        reproject_dem(path, "NOT_A_VALID_CRS")
