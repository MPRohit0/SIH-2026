"""AOI clipping helpers for Module 1.

The package foundation keeps bbox validation explicit and portable while leaving
full raster clipping to the later implementation phase.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def validate_bbox_wgs84(bbox: list[float] | tuple[float, float, float, float]) -> list[float]:
    """Validate a WGS84 bounding box in the form [min_lon, min_lat, max_lon, max_lat]."""
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        raise ValueError("bbox_wgs84 must be a 4-item list or tuple: [min_lon, min_lat, max_lon, max_lat].")

    try:
        min_lon, min_lat, max_lon, max_lat = [float(value) for value in bbox]
    except (TypeError, ValueError) as exc:  # pragma: no cover - validation branch
        raise ValueError("bbox_wgs84 values must all be numeric.") from exc

    if not (-180.0 <= min_lon <= 180.0 and -180.0 <= max_lon <= 180.0):
        raise ValueError("Longitude values must lie within [-180, 180].")
    if not (-90.0 <= min_lat <= 90.0 and -90.0 <= max_lat <= 90.0):
        raise ValueError("Latitude values must lie within [-90, 90].")
    if min_lon >= max_lon:
        raise ValueError("min_lon must be less than max_lon.")
    if min_lat >= max_lat:
        raise ValueError("min_lat must be less than max_lat.")

    return [min_lon, min_lat, max_lon, max_lat]


def clip_dem(
    dem_path: str | Path,
    bbox_wgs84: list[float],
    output_path: str | Path | None = None,
) -> tuple[Any, dict[str, Any], list[float]]:
    """Clip a DEM raster to an AOI.

    This is intentionally left as a placeholder API so the package can be imported
    without implementing the full raster-clipping workflow yet.
    """
    validate_bbox_wgs84(bbox_wgs84)
    raise NotImplementedError("DEM clipping is not implemented in the Module 1 foundation yet.")
