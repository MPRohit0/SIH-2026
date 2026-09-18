"""DEM reprojection helpers for Module 1."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.warp import calculate_default_transform, reproject

from .ingestion import DEMNotFoundError, DEMValidationError


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


def _metadata_from_dataset(dataset: rasterio.DatasetReader) -> dict[str, Any]:
    """Build a standard metadata dictionary for downstream processing."""
    if dataset.crs is None:
        raise DEMValidationError("Source DEM is missing a CRS definition.")
    if dataset.transform is None:
        raise DEMValidationError("Source DEM is missing an affine transform.")

    resolution = (abs(float(dataset.res[0])), abs(float(dataset.res[1])))
    return {
        "crs": str(dataset.crs),
        "width": int(dataset.width),
        "height": int(dataset.height),
        "transform": dataset.transform,
        "resolution": resolution,
        "bounds": dataset.bounds,
        "dtype": str(dataset.dtypes[0]),
        "nodata": dataset.nodata,
    }


def reproject_dem(
    input_path: str | Path,
    target_crs: str,
    output_path: str | Path | None = None,
    resolution_m: float | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Reproject a DEM raster to a target CRS while preserving georeferencing.

    Args:
        input_path: Path to the source DEM GeoTIFF.
        target_crs: Valid CRS string, e.g. "EPSG:3857".
        output_path: Optional output GeoTIFF path. When provided, the result is written to disk.
        resolution_m: Optional explicit target pixel size in meters.

    Returns:
        Tuple of (reprojected_data, metadata_dict)
    """
    source_path = Path(input_path).resolve()
    if not source_path.exists():
        raise DEMNotFoundError(f"DEM file does not exist: {source_path}")
    if not source_path.is_file():
        raise DEMNotFoundError(f"DEM path is not a file: {source_path}")

    if target_crs is None or str(target_crs).strip() == "":
        raise DEMValidationError("A target CRS is required for DEM reprojection.")

    try:
        dst_crs = CRS.from_user_input(target_crs)
    except Exception as exc:  # pragma: no cover - validation branch
        raise DEMValidationError(f"Invalid target CRS: {target_crs}") from exc

    with rasterio.open(source_path) as src:
        if src.crs is None:
            raise DEMValidationError(f"Source DEM is missing a CRS definition: {source_path}")
        if src.transform is None:
            raise DEMValidationError(f"Source DEM is missing an affine transform: {source_path}")
        if src.width <= 0 or src.height <= 0:
            raise DEMValidationError(f"Source DEM has invalid dimensions: {src.width}x{src.height}")
        if src.count < 1:
            raise DEMValidationError(f"Source DEM contains no raster bands: {source_path}")

        source_crs = src.crs
        src_nodata = src.nodata if src.nodata is not None else -9999.0

        if source_crs == dst_crs and resolution_m is None:
            data = src.read(1).astype(np.float32, copy=False)
            metadata = _metadata_from_dataset(src)
            metadata["dtype"] = str(data.dtype)
            metadata["nodata"] = src_nodata
            if output_path is not None:
                output_file = Path(output_path).resolve()
                output_file.parent.mkdir(parents=True, exist_ok=True)
                with rasterio.open(
                    output_file,
                    "w",
                    driver="GTiff",
                    height=data.shape[0],
                    width=data.shape[1],
                    count=1,
                    dtype=data.dtype,
                    crs=source_crs,
                    transform=src.transform,
                    nodata=src_nodata,
                ) as dst:
                    dst.write(data, 1)
            return data, metadata

        if resolution_m is not None and resolution_m <= 0:
            raise DEMValidationError(f"Target resolution must be positive: {resolution_m}")

        try:
            dst_transform, width, height = calculate_default_transform(
                source_crs,
                dst_crs,
                src.width,
                src.height,
                *src.bounds,
                resolution=resolution_m,
            )
        except Exception as exc:  # pragma: no cover - reprojection failures
            raise DEMValidationError(f"Could not compute a valid reprojection transform to {target_crs}") from exc

        dst_profile = src.profile.copy()
        dst_profile.update(
            {
                "driver": "GTiff",
                "crs": dst_crs,
                "transform": dst_transform,
                "width": width,
                "height": height,
                "nodata": src_nodata,
                "dtype": "float32",
            }
        )

        destination = np.full((height, width), src_nodata, dtype=np.float32)
        reproject(
            source=rasterio.band(src, 1),
            destination=destination,
            src_transform=src.transform,
            src_crs=source_crs,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            src_nodata=src_nodata,
            dst_nodata=src_nodata,
            resampling=Resampling.bilinear,
        )

        metadata = {
            "crs": str(dst_crs),
            "width": int(width),
            "height": int(height),
            "transform": dst_transform,
            "resolution": (abs(float(dst_transform.a)), abs(float(dst_transform.e))),
            "bounds": rasterio.transform.array_bounds(height, width, dst_transform),
            "dtype": "float32",
            "nodata": src_nodata,
        }

        if output_path is not None:
            output_file = Path(output_path).resolve()
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with rasterio.open(
                output_file,
                "w",
                **dst_profile,
            ) as dst:
                dst.write(destination, 1)

        return destination, metadata
