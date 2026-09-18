"""River Storage Service for SIH26161 Module 8 Dashboard.

Manages persistence, retrieval, and validation of river centerlines
stored locally as GeoJSON FeatureCollection in data/rivers/rivers.geojson.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def get_default_rivers_filepath() -> Path:
    """Resolve the default data/rivers/rivers.geojson path relative to project root."""
    # modules/m8_dashboard/services/river_store.py -> project root is 4 levels up
    base_dir = Path(__file__).resolve().parent.parent.parent.parent
    return base_dir / "data" / "rivers" / "rivers.geojson"


def _resolve_path(filepath: Path | str | None = None) -> Path:
    """Resolve provided or default path."""
    if filepath is None:
        return get_default_rivers_filepath()
    return Path(filepath).resolve()


def init_storage(filepath: Path | str | None = None) -> Path:
    """Ensure data/rivers/ directory and rivers.geojson exist with valid GeoJSON structure."""
    target = _resolve_path(filepath)
    target.parent.mkdir(parents=True, exist_ok=True)

    if not target.exists() or target.stat().st_size == 0:
        empty_fc = {
            "type": "FeatureCollection",
            "features": []
        }
        with open(target, "w", encoding="utf-8") as f:
            json.dump(empty_fc, f, indent=2)
    else:
        # Verify valid JSON
        try:
            with open(target, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict) or data.get("type") != "FeatureCollection":
                raise ValueError("Invalid FeatureCollection structure")
        except Exception:
            empty_fc = {
                "type": "FeatureCollection",
                "features": []
            }
            with open(target, "w", encoding="utf-8") as f:
                json.dump(empty_fc, f, indent=2)

    return target


def load_feature_collection(filepath: Path | str | None = None) -> dict[str, Any]:
    """Load the full GeoJSON FeatureCollection dictionary."""
    target = init_storage(filepath)
    try:
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and data.get("type") == "FeatureCollection" and isinstance(data.get("features"), list):
            return data
    except Exception:
        pass

    return {"type": "FeatureCollection", "features": []}


def load_rivers(filepath: Path | str | None = None) -> list[dict[str, Any]]:
    """Load all river features from local GeoJSON storage."""
    fc = load_feature_collection(filepath)
    return fc.get("features", [])


def count_rivers(filepath: Path | str | None = None) -> int:
    """Return total number of saved rivers."""
    return len(load_rivers(filepath))


def get_river(river_id: str, filepath: Path | str | None = None) -> dict[str, Any] | None:
    """Retrieve a single river feature by its unique river_id."""
    if not river_id:
        return None
    target_id = river_id.strip()
    rivers = load_rivers(filepath)
    for feature in rivers:
        props = feature.get("properties", {})
        if props.get("river_id") == target_id:
            return feature
    return None


def river_exists(river_id: str, filepath: Path | str | None = None) -> bool:
    """Check if a river with given river_id already exists."""
    return get_river(river_id, filepath) is not None


def validate_river(
    river_name: str,
    river_id: str,
    geometry: dict[str, Any] | None,
    filepath: Path | str | None = None,
    allow_existing_id: bool = False,
) -> tuple[bool, str | None]:
    """Validate river inputs against requirements.

    Returns:
        (True, None) if valid, or (False, error_message) if invalid.
    """
    if not river_name or not river_name.strip():
        return False, "River Name cannot be empty."

    if not river_id or not river_id.strip():
        return False, "River ID cannot be empty."

    clean_id = river_id.strip()

    # ID format check: alphanumeric with underscores and hyphens
    if not re.match(r"^[A-Za-z0-9_-]+$", clean_id):
        return False, "River ID must contain only letters, numbers, hyphens, or underscores."

    if not allow_existing_id and river_exists(clean_id, filepath):
        return False, f"River ID '{clean_id}' already exists. Please choose a unique ID."

    if not geometry or not isinstance(geometry, dict):
        return False, "River geometry is missing or invalid. Please draw a line on the map."

    geom_type = geometry.get("type")
    if geom_type != "LineString":
        return False, f"Geometry type must be 'LineString', got '{geom_type}'."

    coords = geometry.get("coordinates")
    if not isinstance(coords, list) or len(coords) < 2:
        return False, "LineString geometry must contain at least 2 coordinate points."

    for idx, pt in enumerate(coords):
        if not isinstance(pt, (list, tuple)) or len(pt) < 2:
            return False, f"Coordinate point at index {idx} must be a pair [lon, lat]."
        try:
            lon = float(pt[0])
            lat = float(pt[1])
        except (ValueError, TypeError):
            return False, f"Non-numeric coordinates at point index {idx}: {pt}."

        if not (-180.0 <= lon <= 180.0):
            return False, f"Longitude {lon} at point {idx} out of valid range [-180, 180]."
        if not (-90.0 <= lat <= 90.0):
            return False, f"Latitude {lat} at point {idx} out of valid range [-90, 90]."

    return True, None


def save_river(
    river_name: str,
    river_id: str,
    geometry: dict[str, Any],
    source: str = "manual",
    created_at: str | None = None,
    filepath: Path | str | None = None,
) -> tuple[bool, str]:
    """Save a river feature to the GeoJSON store.

    Returns:
        (True, "River saved successfully") or (False, error_message).
    """
    valid, err_msg = validate_river(river_name, river_id, geometry, filepath=filepath)
    if not valid:
        return False, err_msg or "Validation failed"

    target = init_storage(filepath)
    clean_name = river_name.strip()
    clean_id = river_id.strip()
    now_iso = created_at or datetime.now(timezone.utc).isoformat()

    # Normalise coordinates to float pairs [lon, lat]
    raw_coords = geometry.get("coordinates", [])
    clean_coords = [[float(pt[0]), float(pt[1])] for pt in raw_coords]

    new_feature: dict[str, Any] = {
        "type": "Feature",
        "properties": {
            "river_id": clean_id,
            "river_name": clean_name,
            "created_at": now_iso,
            "source": source,
        },
        "geometry": {
            "type": "LineString",
            "coordinates": clean_coords,
        },
    }

    fc = load_feature_collection(target)
    features = fc.get("features", [])
    features.append(new_feature)
    fc["features"] = features

    try:
        # Atomic file write via temp file in same directory
        temp_file = target.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(fc, f, indent=2)
        temp_file.replace(target)
        return True, f"River '{clean_name}' ({clean_id}) saved successfully."
    except Exception as exc:
        return False, f"Failed to write to file: {exc}"


def delete_river(river_id: str, filepath: Path | str | None = None) -> bool:
    """Delete a river by its ID.

    Returns True if deleted, False if not found.
    """
    if not river_id:
        return False

    clean_id = river_id.strip()
    target = init_storage(filepath)
    fc = load_feature_collection(target)
    features = fc.get("features", [])

    new_features = [
        feat for feat in features
        if feat.get("properties", {}).get("river_id") != clean_id
    ]

    if len(new_features) == len(features):
        return False

    fc["features"] = new_features
    temp_file = target.with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(fc, f, indent=2)
    temp_file.replace(target)
    return True
