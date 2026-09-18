"""Tests for Module 1 river geometry processing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from modules.m1_terrain.src.river_geometry import clip_river_to_aoi, validate_river_geometry


@pytest.fixture
def valid_river_feature() -> dict:
    """Return a simple valid river LineString in WGS84."""
    return {
        "type": "Feature",
        "properties": {"river_id": "river_001", "river_name": "Test River"},
        "geometry": {
            "type": "LineString",
            "coordinates": [
                [79.8, 30.5],
                [79.85, 30.55],
                [79.9, 30.6],
            ],
        },
    }


def test_valid_linestring_geometry(valid_river_feature: dict) -> None:
    """A valid LineString with coordinates should pass validation."""
    ok, error = validate_river_geometry(valid_river_feature["geometry"])
    assert ok is True
    assert error is None


def test_invalid_geometry_rejected() -> None:
    """Invalid geometry types and malformed coordinates should be rejected."""
    invalid = {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]]],
    }
    ok, error = validate_river_geometry(invalid)
    assert ok is False
    assert error is not None


def test_empty_geometry_rejected() -> None:
    """Empty feature collections should be rejected during processing."""
    with pytest.raises(ValueError):
        clip_river_to_aoi({"type": "FeatureCollection", "features": []}, [79.8, 30.5, 79.9, 30.6])


def test_crs_transformation_preserves_properties(valid_river_feature: dict) -> None:
    """River geometry should retain properties after reprojecting and reformatting."""
    result = clip_river_to_aoi(
        {"type": "FeatureCollection", "features": [valid_river_feature]},
        [79.79, 30.49, 79.91, 30.61],
        source_crs="EPSG:4326",
        target_crs="EPSG:4326",
    )

    assert result["type"] == "FeatureCollection"
    assert len(result["features"]) == 1
    assert result["features"][0]["properties"]["river_id"] == "river_001"
    assert result["features"][0]["properties"]["river_name"] == "Test River"
    assert result["features"][0]["geometry"]["type"] == "LineString"


def test_aoi_clipping_returns_valid_geojson(valid_river_feature: dict, tmp_path: Path) -> None:
    """Clipped rivers must remain valid GeoJSON and be written to disk."""
    output_path = tmp_path / "river_centerline.geojson"
    result = clip_river_to_aoi(
        {"type": "FeatureCollection", "features": [valid_river_feature]},
        [79.82, 30.52, 79.88, 30.58],
        output_path=output_path,
        source_crs="EPSG:4326",
        target_crs="EPSG:4326",
    )

    assert result["type"] == "FeatureCollection"
    assert len(result["features"]) == 1
    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["type"] == "FeatureCollection"
    assert payload["features"][0]["geometry"]["type"] == "LineString"


def test_no_intersection_with_aoi_rejected(valid_river_feature: dict) -> None:
    """A river outside the requested bbox should fail rather than producing invalid output."""
    with pytest.raises(ValueError):
        clip_river_to_aoi(
            {"type": "FeatureCollection", "features": [valid_river_feature]},
            [0.0, 0.0, 0.1, 0.1],
            source_crs="EPSG:4326",
            target_crs="EPSG:4326",
        )
