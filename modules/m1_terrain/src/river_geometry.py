"""River geometry processing for Module 1.

This module validates LineString river features, reprojects them into the terrain
CRS, clips them to the requested AOI, and persists a valid GeoJSON output without
any hydraulic-property calculation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pyproj import Transformer
from shapely.geometry import LineString, box, mapping
from shapely.ops import transform as shapely_transform


def validate_river_geometry(
    geom: dict[str, Any] | None,
    coordinate_crs: str = "EPSG:4326",
) -> tuple[bool, str | None]:
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
        if coordinate_crs == "EPSG:4326" and not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
            return False, f"Point {idx} falls outside valid longitude/latitude bounds."

    return True, None


def _coerce_feature_collection(river_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalise a GeoJSON FeatureCollection or single Feature into a feature list."""
    if not isinstance(river_data, dict):
        raise ValueError("river_data must be a dictionary-like GeoJSON object.")

    if river_data.get("type") == "FeatureCollection":
        features = river_data.get("features")
        if not isinstance(features, list):
            raise ValueError("FeatureCollection is missing a valid 'features' list.")
        if len(features) == 0:
            raise ValueError("River FeatureCollection is empty.")
        return features

    if river_data.get("type") == "Feature":
        return [river_data]

    raise ValueError("River data must be a GeoJSON FeatureCollection or Feature.")


def _reproject_line(coords: list[list[float]], source_crs: str, target_crs: str) -> list[list[float]]:
    """Reproject a LineString coordinate list from source CRS to target CRS."""
    if source_crs == target_crs:
        return [[float(x), float(y)] for x, y in coords]

    transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)
    transformed = transformer.transform([x for x, _ in coords], [y for _, y in coords])
    return [[float(x), float(y)] for x, y in zip(transformed[0], transformed[1], strict=False)]


def clip_river_to_aoi(
    river_data: dict[str, Any],
    bbox_wgs84: list[float],
    output_path: str | Path | None = None,
    source_crs: str = "EPSG:4326",
    target_crs: str = "EPSG:4326",
) -> dict[str, Any]:
    """Validate, reproject, clip, and persist river geometry for the terrain AOI.

    The initial M1 implementation only supports LineString geometries. Invalid,
    empty, or non-intersecting inputs are rejected with clear ValueErrors.
    """
    if not isinstance(bbox_wgs84, (list, tuple)) or len(bbox_wgs84) != 4:
        raise ValueError("bbox_wgs84 must be [min_lon, min_lat, max_lon, max_lat].")

    try:
        min_lon, min_lat, max_lon, max_lat = [float(value) for value in bbox_wgs84]
    except (TypeError, ValueError) as exc:
        raise ValueError("bbox_wgs84 values must all be numeric.") from exc

    if min_lon >= max_lon or min_lat >= max_lat:
        raise ValueError("bbox_wgs84 must satisfy min < max for both axes.")

    features_out: list[dict[str, Any]] = []
    aoi_box = box(min_lon, min_lat, max_lon, max_lat)
    if source_crs != target_crs:
        aoi_transformer = Transformer.from_crs("EPSG:4326", target_crs, always_xy=True)
        aoi_box = shapely_transform(aoi_transformer.transform, aoi_box)

    for feature in _coerce_feature_collection(river_data):
        if not isinstance(feature, dict):
            raise ValueError("River feature entries must be dictionary objects.")

        geometry = feature.get("geometry")
        valid, error = validate_river_geometry(geometry)
        if not valid:
            raise ValueError(f"Invalid river geometry: {error}")

        original_coords = geometry["coordinates"]
        projected_coords = _reproject_line(original_coords, source_crs, target_crs)
        line = LineString(projected_coords)

        if not line.intersects(aoi_box):
            continue

        clipped = line.intersection(aoi_box)
        if clipped.is_empty:
            continue

        if clipped.geom_type == "LineString":
            clipped_coords = list(clipped.coords)
        elif clipped.geom_type == "MultiLineString":
            parts = []
            for part in clipped.geoms:
                parts.extend(list(part.coords))
            clipped_coords = parts
        else:
            raise ValueError("Only LineString-based river geometry is supported in M1.")

        properties = feature.get("properties", {}).copy()
        if not isinstance(properties, dict):
            raise ValueError("River feature properties must be a dictionary.")

        features_out.append(
            {
                "type": "Feature",
                "properties": properties,
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[float(x), float(y)] for x, y in clipped_coords],
                },
            }
        )

    if not features_out:
        raise ValueError(f"River geometry does not intersect the requested AOI bbox {bbox_wgs84}.")

    result = {"type": "FeatureCollection", "features": features_out}

    if output_path is not None:
        out_path = Path(output_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2)

    return result


def create_domain_geojson(
    bbox_wgs84: list[float],
    site_id: str,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Create a minimal WGS84 AOI polygon for callers without a processed DEM.

    The DEM-driven ``generate_simulation_domain`` function is the canonical
    processed-terrain path. This compatibility helper only represents the
    supplied AOI and adds no domain-specific properties.
    """
    del site_id
    if not isinstance(bbox_wgs84, (list, tuple)) or len(bbox_wgs84) != 4:
        raise ValueError("bbox_wgs84 must be [min_lon, min_lat, max_lon, max_lat].")
    min_lon, min_lat, max_lon, max_lat = [float(value) for value in bbox_wgs84]
    if min_lon >= max_lon or min_lat >= max_lat:
        raise ValueError("bbox_wgs84 must satisfy min < max for both axes.")

    result = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [min_lon, min_lat],
                            [max_lon, min_lat],
                            [max_lon, max_lat],
                            [min_lon, max_lat],
                            [min_lon, min_lat],
                        ]
                    ],
                },
            }
        ],
        "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
    }

    if output_path is not None:
        output_file = Path(output_path).resolve()
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json.dumps(result, indent=2), encoding="utf-8")

    return result
