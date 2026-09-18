"""Unit tests for GeoJSON structure and compliance (SIH26161 Module 8)."""

import json
import pytest
from pathlib import Path

from modules.m8_dashboard.services.river_store import (
    init_storage,
    save_river,
    load_feature_collection,
    load_rivers,
    get_river,
)


@pytest.fixture
def temp_geojson(tmp_path: Path) -> Path:
    file_path = tmp_path / "test_rivers.geojson"
    init_storage(file_path)
    return file_path


def test_empty_storage_is_valid_feature_collection(temp_geojson: Path):
    with open(temp_geojson, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert isinstance(data, dict)
    assert data.get("type") == "FeatureCollection"
    assert isinstance(data.get("features"), list)
    assert len(data["features"]) == 0


def test_resulting_geojson_is_valid_feature_collection(temp_geojson: Path):
    coords = [[78.5, 30.2], [78.6, 30.3], [78.7, 30.4]]
    save_river(
        river_name="Mandakini",
        river_id="manda_01",
        geometry={"type": "LineString", "coordinates": coords},
        source="manual",
        filepath=temp_geojson,
    )

    with open(temp_geojson, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 1
    feature = data["features"][0]
    assert feature["type"] == "Feature"
    assert "properties" in feature
    assert "geometry" in feature


def test_feature_properties_match_contract(temp_geojson: Path):
    coords = [[78.5, 30.2], [78.6, 30.3]]
    save_river(
        river_name="Pindar River",
        river_id="pindar_01",
        geometry={"type": "LineString", "coordinates": coords},
        source="manual",
        filepath=temp_geojson,
    )

    feature = get_river("pindar_01", filepath=temp_geojson)
    props = feature["properties"]

    assert props["river_id"] == "pindar_01"
    assert props["river_name"] == "Pindar River"
    assert props["source"] == "manual"
    assert "created_at" in props
    assert isinstance(props["created_at"], str)


def test_feature_geometry_is_linestring(temp_geojson: Path):
    coords = [[79.0, 30.0], [79.1, 30.1], [79.2, 30.2]]
    save_river(
        river_name="Dhauliganga",
        river_id="dhauli_01",
        geometry={"type": "LineString", "coordinates": coords},
        filepath=temp_geojson,
    )

    feature = get_river("dhauli_01", filepath=temp_geojson)
    geom = feature["geometry"]

    assert geom["type"] == "LineString"
    assert geom["coordinates"] == coords


def test_persisted_file_survives_reload(temp_geojson: Path):
    coords_1 = [[79.1, 30.1], [79.2, 30.2]]
    coords_2 = [[79.3, 30.3], [79.4, 30.4]]

    save_river("River One", "r_01", {"type": "LineString", "coordinates": coords_1}, filepath=temp_geojson)
    save_river("River Two", "r_02", {"type": "LineString", "coordinates": coords_2}, filepath=temp_geojson)

    # Re-read fresh from disk
    rivers = load_rivers(temp_geojson)
    assert len(rivers) == 2

    ids = [r["properties"]["river_id"] for r in rivers]
    assert "r_01" in ids
    assert "r_02" in ids
