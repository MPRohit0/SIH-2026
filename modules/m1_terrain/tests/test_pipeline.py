"""End-to-end tests for the final Module 1 pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from modules.m1_terrain.src.pipeline import run_terrain_pipeline


def _write_raster(path: Path, data: np.ndarray, dtype: str, nodata: float | int) -> None:
    """Write a tiny synthetic WGS84 raster."""
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


def test_run_terrain_pipeline_end_to_end(tmp_path: Path) -> None:
    """The public pipeline should create a complete terrain hand-off."""
    dem_path = tmp_path / "source_dem.tif"
    landcover_path = tmp_path / "source_landcover.tif"
    river_path = tmp_path / "source_river.geojson"
    output_dir = tmp_path / "data" / "terrain" / "demo_site"

    _write_raster(dem_path, np.array([[10.0, 11.0], [12.0, 13.0]], dtype=np.float32), "float32", -9999.0)
    _write_raster(landcover_path, np.array([[1, 2], [1, 3]], dtype=np.int16), "int16", -9999)
    river_path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"river_id": "demo_river"},
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

    manifest = run_terrain_pipeline(
        site_id="demo_site",
        bbox_wgs84=[79.8, 30.68, 79.82, 30.7],
        dem_path=dem_path,
        river_path=river_path,
        output_dir=output_dir,
        landcover_path=landcover_path,
        target_crs="EPSG:3857",
    )

    assert (output_dir / "terrain_manifest.json").is_file()
    assert (output_dir / "dem.tif").is_file()
    assert (output_dir / "river_centerline.geojson").is_file()
    assert (output_dir / "landcover.tif").is_file()
    assert (output_dir / "manning_n.tif").is_file()
    assert (output_dir / "domain.geojson").is_file()
    assert manifest["status"] == "ok"
    assert manifest["site_id"] == "demo_site"
    assert manifest["dem"]["url"] == "dem.tif"
    assert manifest["manning_n"]["url"] == "manning_n.tif"
