"""River geometry helpers for Module 1.

The package foundation provides validation and API definitions without attempting
full spatial clipping or solver-boundary generation yet.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def validate_river_geometry(geom: dict[str, Any] | None) -> tuple[bool, str | None]:
    """Validate a GeoJSON LineString-like river geometry."""
    if not isinstance(geom, dict):
        return False, "River geometry must be a dictionary-like GeoJSON geometry object."

    if geom.get("type") != "LineString":
        return False, "River geometry must have type 'LineString'."

    coords = geom.get("coordinates")
    if not isinstance(coords, list) or len(coords) < 2:
        return False, "River LineString must contain at least two coordinates."

    for idx, point in enumerate(coords):
        if not isinstance(point, (list, tuple)) or len(point) < 2:
            return False, f"Point {idx} is not a valid [lon, lat] pair."
        try:
            lon = float(point[0])
            lat = float(point[1])
        except (TypeError, ValueError):
            return False, f"Point {idx} contains non-numeric coordinates."
        if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
            return False, f"Point {idx} falls outside valid longitude/latitude bounds."

    return True, None


def clip_river_to_aoi(
    river_data: dict[str, Any],
    bbox_wgs84: list[float],
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Placeholder river clipping API that marks the future implementation point."""
    if not isinstance(river_data, dict):
        raise ValueError("river_data must be a dictionary-like GeoJSON object.")
    if isinstance(output_path, (str, Path)):
        _ = Path(output_path).resolve()
    raise NotImplementedError("River clipping is not implemented in the Module 1 foundation yet.")


def create_domain_geojson(
    bbox_wgs84: list[float],
    site_id: str,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Create a basic domain GeoJSON skeleton for a site.

    This is a lightweight placeholder for the eventual full-reach domain builder.
    """
    if output_path is not None:
        output_file = Path(output_path).resolve()
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("{}", encoding="utf-8")

    return {
        "type": "FeatureCollection",
        "features": [],
        "properties": {
            "site_id": site_id,
            "bbox_wgs84": list(bbox_wgs84),
            "domain_type": "placeholder",
        },
    }
