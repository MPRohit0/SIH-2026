"""Integration tests for Module 1 simulation-domain generation."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from modules.m1_terrain.src.domain import generate_simulation_domain, validate_domain_consistency


def _write_raster(path: Path, data: np.ndarray, dtype: str, nodata: float | int) -> None:
    """Write a small WGS84 raster on the shared synthetic terrain grid."""
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=data.shape[0],
        width=data.shape[1],
        count=1,
        dtype=dtype,
        crs="EPSG:4326",
        transform=from_origin(79.8, 30.7, 0.01, 0.01),
        nodata=nodata,
    ) as dataset:
        dataset.write(data, 1)


def test_small_synthetic_site_generates_consistent_domain(tmp_path: Path) -> None:
    """A synthetic site should produce one domain matching all processed artifacts."""
    dem_path = tmp_path / "dem.tif"
    landcover_path = tmp_path / "landcover.tif"
    manning_path = tmp_path / "manning_n.tif"
    river_path = tmp_path / "river_centerline.geojson"
    domain_path = tmp_path / "terrain" / "domain.geojson"

    _write_raster(
        dem_path,
        np.array([[10.0, 11.0], [12.0, 13.0]], dtype=np.float32),
        "float32",
        -9999.0,
    )
    _write_raster(
        landcover_path,
        np.array([[1, 2], [1, 3]], dtype=np.int16),
        "int16",
        -9999,
    )
    _write_raster(
        manning_path,
        np.array([[0.035, 0.045], [0.035, 0.060]], dtype=np.float32),
        "float32",
        -9999.0,
    )
    river_path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {},
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [[79.801, 30.699], [79.809, 30.691]],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = generate_simulation_domain(
        dem_path=dem_path,
        river_path=river_path,
        bbox_wgs84=[79.8, 30.68, 79.82, 30.7],
        output_path=domain_path,
        landcover_path=landcover_path,
        manning_path=manning_path,
        river_crs="EPSG:4326",
    )

    assert domain_path.exists()
    assert result["type"] == "FeatureCollection"
    assert result["crs"]["properties"]["name"] == "EPSG:4326"
    assert result["features"][0]["geometry"]["type"] == "Polygon"

    validate_domain_consistency(
        domain_path=domain_path,
        dem_path=dem_path,
        river_path=river_path,
        landcover_path=landcover_path,
        manning_path=manning_path,
        river_crs="EPSG:4326",
    )

    with rasterio.open(dem_path) as dem:
        ring = result["features"][0]["geometry"]["coordinates"][0]
        assert ring[0] == [dem.bounds.left, dem.bounds.bottom]
        assert ring[2] == [dem.bounds.right, dem.bounds.top]
