"""Reprojection helpers for Module 1.

This foundation intentionally focuses on import-safe APIs and deterministic CRS
selection logic. The full raster reprojection implementation is kept for a later
phase.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def determine_utm_crs(lon: float, lat: float) -> str:
    """Return the UTM EPSG code that best matches a WGS84 longitude/latitude."""
    if not -180.0 <= float(lon) <= 180.0:
        raise ValueError("Longitude must be within [-180, 180].")
    if not -90.0 <= float(lat) <= 90.0:
        raise ValueError("Latitude must be within [-90, 90].")

    zone = int((float(lon) + 180.0) / 6.0) + 1
    zone = min(max(zone, 1), 60)
    epsg = 32600 + zone if float(lat) >= 0 else 32700 + zone
    return f"EPSG:{epsg}"


def reproject_dem(
    input_path: str | Path,
    target_crs: str,
    output_path: str | Path | None = None,
    resolution_m: float | None = None,
) -> tuple[Any, dict[str, Any]]:
    """Reproject a DEM to a target CRS.

    This is intentionally left as a foundation-level API that raises a clear
    placeholder error until the full raster reprojection workflow is implemented.
    """
    raise NotImplementedError("DEM reprojection is not implemented in the Module 1 foundation yet.")
