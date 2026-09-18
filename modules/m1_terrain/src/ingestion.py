"""Ingestion helpers for Module 1 terrain inputs.

This package intentionally keeps the full DEM/river-loading logic out of scope for
now. The public functions exist to make the package import cleanly and to define
where the actual implementation will live.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import numpy as np
except Exception:  # pragma: no cover - import safety for minimal envs
    np = None  # type: ignore


def load_dem(dem_path: str | Path) -> tuple[Any, dict[str, Any]]:
    """Load a DEM raster from disk.

    This is intentionally a placeholder until the full raster ingestion pipeline is
    implemented. The function signature follows the repository contract so the
    package can be imported and extended without machine-specific assumptions.
    """
    raise NotImplementedError("DEM ingestion is not implemented in the Module 1 foundation yet.")


def load_river(river_path: str | Path) -> dict[str, Any]:
    """Load a river GeoJSON feature collection from disk.

    The function is reserved for future implementation. It follows the same
    pathlib-based API style as the rest of the package.
    """
    path = Path(river_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"River GeoJSON file not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError("River dataset must decode to a JSON object.")

    return data
