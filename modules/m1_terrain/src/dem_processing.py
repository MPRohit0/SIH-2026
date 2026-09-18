"""DEM processing helpers for Module 1.

The full terrain-processing pipeline remains intentionally out of scope for this
foundation stage. These functions define the API surface expected by downstream
modules while keeping the package import-safe and easy to extend.
"""

from __future__ import annotations

from typing import Any

try:
    import numpy as np
except Exception:  # pragma: no cover - import safety for minimal envs
    np = None  # type: ignore


def validate_dem(data: Any, profile: dict[str, Any]) -> dict[str, Any]:
    """Validate a DEM-like array and profile.

    This placeholder remains intentionally lightweight. The future implementation
    will check raster shape, nodata handling, elevation bounds, and CRS validity.
    """
    if np is None:
        raise ImportError("numpy is required to validate DEM arrays.")

    if getattr(data, "ndim", None) != 2:
        raise ValueError("DEM validation is not implemented yet; expected a 2D array.")

    return {
        "crs": str(profile.get("crs", "unknown")),
        "shape": tuple(getattr(data, "shape", (0, 0))),
        "nodata": profile.get("nodata", -9999.0),
    }


def calculate_raster_meta(
    profile: dict[str, Any],
    band_name: str = "elevation",
    unit: str = "m",
) -> dict[str, Any]:
    """Return a minimal raster metadata dictionary.

    The real implementation will produce the contract-compliant RasterMeta object
    used by later modules and the dashboard.
    """
    return {
        "dtype": str(profile.get("dtype", "float32")),
        "bands": [{"name": band_name, "unit": unit}],
        "nodata_value": profile.get("nodata", -9999.0),
        "pixel_size_m": float(profile.get("pixel_size_m", 30.0)),
    }


def generate_manning_n_grid(
    dem_data: Any,
    dem_profile: dict[str, Any],
    default_n: float = 0.035,
) -> tuple[Any, dict[str, Any]]:
    """Create a placeholder Manning's n grid for the terrain package.

    This remains intentionally non-production and simply defines the expected API.
    """
    if np is None:
        raise ImportError("numpy is required for roughness-grid generation.")

    grid = np.asarray(dem_data, dtype=np.float32)
    profile = dict(dem_profile)
    profile.setdefault("dtype", "float32")
    profile.setdefault("nodata", -9999.0)
    profile["default_n"] = float(default_n)
    return grid, profile
