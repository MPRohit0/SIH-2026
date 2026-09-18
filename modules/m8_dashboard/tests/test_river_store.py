"""Unit tests for River Store Service (SIH26161 Module 8)."""

import json
import pytest
from pathlib import Path

from modules.m8_dashboard.services.river_store import (
    init_storage,
    load_rivers,
    load_feature_collection,
    save_river,
    get_river,
    river_exists,
    delete_river,
    count_rivers,
    validate_river,
)


@pytest.fixture
def temp_geojson(tmp_path: Path) -> Path:
    """Fixture providing a clean temporary rivers.geojson file."""
    file_path = tmp_path / "test_rivers.geojson"
    init_storage(file_path)
    return file_path


@pytest.fixture
def valid_linestring() -> dict:
    """Sample valid LineString geometry."""
    return {
        "type": "LineString",
        "coordinates": [
            [79.81, 30.58],
            [79.82, 30.59],
            [79.83, 30.60]
        ]
    }


def test_empty_river_name_rejected(temp_geojson: Path, valid_linestring: dict):
    valid, err = validate_river("", "river_01", valid_linestring, filepath=temp_geojson)
    assert not valid
    assert "River Name cannot be empty" in err

    valid, err = validate_river("   ", "river_01", valid_linestring, filepath=temp_geojson)
    assert not valid
    assert "River Name cannot be empty" in err


def test_empty_river_id_rejected(temp_geojson: Path, valid_linestring: dict):
    valid, err = validate_river("Alaknanda", "", valid_linestring, filepath=temp_geojson)
    assert not valid
    assert "River ID cannot be empty" in err

    valid, err = validate_river("Alaknanda", "   ", valid_linestring, filepath=temp_geojson)
    assert not valid
    assert "River ID cannot be empty" in err


def test_duplicate_river_id_rejected(temp_geojson: Path, valid_linestring: dict):
    success, msg = save_river("Alaknanda", "river_01", valid_linestring, filepath=temp_geojson)
    assert success

    valid, err = validate_river("Ganga", "river_01", valid_linestring, filepath=temp_geojson)
    assert not valid
    assert "already exists" in err


def test_valid_linestring_accepted(temp_geojson: Path, valid_linestring: dict):
    valid, err = validate_river("Rishiganga", "rishi_01", valid_linestring, filepath=temp_geojson)
    assert valid
    assert err is None


def test_invalid_geometry_rejected(temp_geojson: Path):
    # None geometry
    valid, err = validate_river("River A", "riv_a", None, filepath=temp_geojson)
    assert not valid
    assert "missing or invalid" in err

    # Wrong type (Polygon instead of LineString)
    polygon_geom = {
        "type": "Polygon",
        "coordinates": [[[79.8, 30.5], [79.9, 30.5], [79.9, 30.6], [79.8, 30.5]]]
    }
    valid, err = validate_river("River B", "riv_b", polygon_geom, filepath=temp_geojson)
    assert not valid
    assert "type must be 'LineString'" in err

    # Too few points (< 2)
    single_point = {
        "type": "LineString",
        "coordinates": [[79.8, 30.5]]
    }
    valid, err = validate_river("River C", "riv_c", single_point, filepath=temp_geojson)
    assert not valid
    assert "at least 2 coordinate points" in err

    # Out of range coordinates
    bad_coords = {
        "type": "LineString",
        "coordinates": [[200.0, 30.0], [79.8, 30.5]]
    }
    valid, err = validate_river("River D", "riv_d", bad_coords, filepath=temp_geojson)
    assert not valid
    assert "out of valid range" in err


def test_saving_and_loading_river(temp_geojson: Path, valid_linestring: dict):
    assert count_rivers(temp_geojson) == 0

    success, msg = save_river("Bhagirathi", "bhag_01", valid_linestring, source="manual", filepath=temp_geojson)
    assert success
    assert "saved successfully" in msg
    assert count_rivers(temp_geojson) == 1

    river = get_river("bhag_01", filepath=temp_geojson)
    assert river is not None
    assert river["properties"]["river_name"] == "Bhagirathi"
    assert river["properties"]["river_id"] == "bhag_01"
    assert river["properties"]["source"] == "manual"
    assert "created_at" in river["properties"]
    assert river["geometry"]["type"] == "LineString"
    assert len(river["geometry"]["coordinates"]) == 3


def test_deleting_river(temp_geojson: Path, valid_linestring: dict):
    save_river("River 1", "r1", valid_linestring, filepath=temp_geojson)
    save_river("River 2", "r2", valid_linestring, filepath=temp_geojson)
    assert count_rivers(temp_geojson) == 2

    # Delete existing
    deleted = delete_river("r1", filepath=temp_geojson)
    assert deleted
    assert count_rivers(temp_geojson) == 1
    assert not river_exists("r1", filepath=temp_geojson)
    assert river_exists("r2", filepath=temp_geojson)

    # Delete non-existing
    deleted_again = delete_river("r1", filepath=temp_geojson)
    assert not deleted_again
    assert count_rivers(temp_geojson) == 1
