"""End-to-end tests for the Module 1 TerrainManifest hand-off."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from jsonschema import validate
from rasterio.transform import from_origin

from modules.m1_terrain.src.manifest import generate_terrain_manifest, validate_terrain_manifest


GRID_TRANSFORM = from_origin(79.8, 30.7, 0.01, 0.01)


def _write_raster(path: Path, data: np.ndarray, dtype: str, nodata: float | int) -> None:
    """Write a synthetic raster with shared geospatial metadata."""
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=data.shape[0],
        width=data.shape[1],
        count=1,
        dtype=dtype,
        crs="EPSG:4326",
        transform=GRID_TRANSFORM,
        nodata=nodata,
    ) as dataset:
        dataset.write(data, 1)


def test_generate_complete_terrain_manifest(tmp_path: Path) -> None:
    """A synthetic site should produce a schema-valid, fully linked manifest."""
    dem_path = tmp_path / "dem.tif"
    landcover_path = tmp_path / "landcover.tif"
    manning_path = tmp_path / "manning_n.tif"
    river_path = tmp_path / "river_centerline.geojson"
    output_dir = tmp_path / "data" / "terrain" / "synthetic_site"
    schema_path = Path(__file__).resolve().parents[3] / "contracts" / "schemas" / "terrain_manifest.schema.json"

    _write_raster(dem_path, np.array([[10.0, 11.0], [12.0, 13.0]], dtype=np.float32), "float32", -9999.0)
    _write_raster(landcover_path, np.array([[1, 2], [1, 3]], dtype=np.int16), "int16", -9999)
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
                        "properties": {"river_id": "synthetic_river"},
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

    manifest = generate_terrain_manifest(
        site_id="synthetic_site",
        dem_path=dem_path,
        river_path=river_path,
        bbox_wgs84=[79.8, 30.68, 79.82, 30.7],
        output_dir=output_dir,
        failure_source_id="synthetic_failure_source",
        landcover_path=landcover_path,
        manning_path=manning_path,
        river_crs="EPSG:4326",
        schema_path=schema_path,
    )

    manifest_path = output_dir / "terrain_manifest.json"
    domain_path = output_dir / "domain.geojson"
    assert manifest_path.exists()
    assert domain_path.exists()
    assert manifest["status"] == "ok"
    assert manifest["storage_crs"] == "EPSG:4326"
    assert manifest["api_crs"] == "EPSG:4326"
    assert manifest["dem"]["url"] == "../../../dem.tif"
    assert manifest["landcover_classes"]["url"] == "../../../landcover.tif"
    assert manifest["manning_n"]["url"] == "../../../manning_n.tif"
    assert manifest["river_centerline"]["url"] == "../../../river_centerline.geojson"
    assert manifest["sph_boundary_geometry"]["url"] == "domain.geojson"

    persisted = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_terrain_manifest(persisted, schema_path=schema_path)
    validate(instance=persisted, schema=json.loads(schema_path.read_text(encoding="utf-8")))

    for artifact_name in (
        "dem",
        "landcover_classes",
        "manning_n",
        "river_centerline",
        "sph_boundary_geometry",
    ):
        assert (output_dir / persisted[artifact_name]["url"]).resolve().is_file()

    assert persisted["dem"]["raster_meta"]["bands"][0]["unit"] == "m"
    assert persisted["landcover_classes"]["raster_meta"]["bands"][0]["unit"] == "class"
    assert persisted["manning_n"]["raster_meta"]["bands"][0]["unit"] == "dimensionless"
    assert persisted["dem"]["bbox_wgs84"] == persisted["manning_n"]["bbox_wgs84"]
