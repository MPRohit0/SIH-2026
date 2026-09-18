"""DEM ingestion and validation for Module 1.

This module handles safe file access, metadata extraction, and domain-specific
validation for a local DEM GeoTIFF without modifying the source raster.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import rasterio


class DEMError(ValueError):
    """Base domain error for DEM ingestion and validation."""


class DEMNotFoundError(DEMError):
    """Raised when the DEM file is missing or is not a file."""


class DEMReadError(DEMError):
    """Raised when a DEM cannot be opened or read as a raster."""


class DEMValidationError(DEMError):
    """Raised when DEM metadata fails required validation checks."""


def _validate_raster_profile(dataset: rasterio.DatasetReader) -> None:
    """Validate the raster metadata required by the Module 1 contract."""
    if dataset.width <= 0 or dataset.height <= 0:
        raise DEMValidationError(f"DEM has invalid dimensions: {dataset.width}x{dataset.height}.")

    if dataset.crs is None:
        raise DEMValidationError("DEM is missing a CRS definition.")

    if dataset.transform is None:
        raise DEMValidationError("DEM is missing an affine transform.")

    if dataset.res is None or dataset.res[0] <= 0 or dataset.res[1] <= 0:
        raise DEMValidationError("DEM resolution is invalid or missing.")

    if dataset.count < 1:
        raise DEMValidationError("DEM contains no raster bands.")

    try:
        dataset.read(1)
    except Exception as exc:  # pragma: no cover - depends on rasterio internals
        raise DEMReadError(f"DEM band 1 could not be read: {exc}") from exc


def load_dem(dem_path: str | Path) -> tuple[np.ndarray, dict[str, Any]]:
    """Open and validate a local DEM GeoTIFF.

    The function returns the raw array and a metadata dictionary containing the
    geospatial and raster properties needed downstream. The source file is not
    modified.

    Returns:
        A tuple of
        - DEM array as a NumPy array
        - metadata dictionary with CRS, shape, bounds, transform, resolution, dtype,
          nodata, etc.
    """
    dem_file = Path(dem_path).resolve()

    if not dem_file.exists():
        raise DEMNotFoundError(f"DEM file does not exist: {dem_file}")
    if not dem_file.is_file():
        raise DEMNotFoundError(f"DEM path is not a file: {dem_file}")

    try:
        with rasterio.open(dem_file, "r") as dataset:
            _validate_raster_profile(dataset)

            band_1 = dataset.read(1)
            nodata = dataset.nodata
            if nodata is not None and not np.isfinite(nodata):
                nodata = None

            metadata: dict[str, Any] = {
                "path": str(dem_file),
                "crs": str(dataset.crs),
                "width": int(dataset.width),
                "height": int(dataset.height),
                "transform": dataset.transform,
                "resolution": (float(dataset.res[0]), float(dataset.res[1])),
                "bounds": dataset.bounds,
                "dtype": str(dataset.dtypes[0]),
                "nodata": nodata,
                "count": int(dataset.count),
            }

            if band_1.size == 0:
                raise DEMValidationError(f"DEM raster is empty: {dem_file}")

            return band_1.astype(np.float32, copy=False), metadata
    except rasterio.errors.RasterioIOError as exc:
        raise DEMReadError(f"DEM file could not be opened as a GeoTIFF: {dem_file}") from exc
    except DEMError:
        raise
    except Exception as exc:  # pragma: no cover - guard for unexpected read issues
        raise DEMReadError(f"DEM file could not be read: {dem_file}") from exc


def load_river(river_path: str | Path) -> dict[str, Any]:
    """Load a river GeoJSON feature collection from disk.

    This helper remains intentionally simple and file-safe. It is not part of the
    current DEM-only scope, but the function name is kept consistent with the
    repository conventions.
    """
    path = Path(river_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"River GeoJSON file not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError("River dataset must decode to a JSON object.")

    return data
