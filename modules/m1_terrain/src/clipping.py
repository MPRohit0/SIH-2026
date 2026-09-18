"""AOI clipping helpers for Module 1."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from pyproj import Transformer
from shapely.geometry import box
from shapely.ops import transform as shapely_transform
from shapely.geometry import mapping
from rasterio.mask import mask

from .ingestion import DEMNotFoundError, DEMValidationError


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


def _bbox_to_source_crs(bbox_wgs84: list[float], src_crs: str) -> Any:
    """Convert a WGS84 AOI polygon into the source raster CRS."""
    if src_crs is None:
        raise DEMValidationError("Source DEM CRS is required for AOI clipping.")

    min_lon, min_lat, max_lon, max_lat = bbox_wgs84
    aoi = box(min_lon, min_lat, max_lon, max_lat)

    if str(src_crs) == "EPSG:4326":
        return aoi

    transformer = Transformer.from_crs("EPSG:4326", str(src_crs), always_xy=True)
    return shapely_transform(transformer.transform, aoi)


def clip_dem(
    dem_path: str | Path,
    bbox_wgs84: list[float],
    output_path: str | Path | None = None,
) -> tuple[np.ndarray, dict[str, Any], list[float]]:
    """Clip a DEM to the requested AOI while preserving georeferencing and NoData semantics."""
    clean_bbox = validate_bbox_wgs84(bbox_wgs84)
    source_path = Path(dem_path).resolve()

    if not source_path.exists():
        raise DEMNotFoundError(f"DEM file does not exist: {source_path}")
    if not source_path.is_file():
        raise DEMNotFoundError(f"DEM path is not a file: {source_path}")

    with rasterio.open(source_path) as src:
        if src.crs is None:
            raise DEMValidationError(f"Source DEM is missing a CRS definition: {source_path}")
        if src.transform is None:
            raise DEMValidationError(f"Source DEM is missing an affine transform: {source_path}")
        if src.width <= 0 or src.height <= 0:
            raise DEMValidationError(f"Source DEM has invalid dimensions: {src.width}x{src.height}")

        aoi_geometry = _bbox_to_source_crs(clean_bbox, src.crs)
        src_bounds = box(*src.bounds)
        if not aoi_geometry.intersects(src_bounds):
            raise ValueError(f"AOI does not overlap the source DEM bounds: {clean_bbox}")

        try:
            clipped, out_transform = mask(
                src,
                [mapping(aoi_geometry)],
                crop=True,
                nodata=src.nodata if src.nodata is not None else -9999.0,
            )
        except ValueError as exc:
            raise ValueError(f"DEM clipping failed for AOI {clean_bbox}: {exc}") from exc

        if clipped.size == 0 or clipped.shape[1] == 0 or clipped.shape[2] == 0:
            raise ValueError(f"Clipped DEM has zero dimensions for AOI {clean_bbox}")

        data = clipped[0].astype(np.float32, copy=False)
        nodata_value = src.nodata if src.nodata is not None else -9999.0
        profile = src.profile.copy()
        profile.update(
            {
                "driver": "GTiff",
                "height": data.shape[0],
                "width": data.shape[1],
                "count": 1,
                "dtype": "float32",
                "crs": src.crs,
                "transform": out_transform,
                "nodata": nodata_value,
            }
        )

        bounds = rasterio.transform.array_bounds(data.shape[0], data.shape[1], out_transform)
        if str(src.crs) == "EPSG:4326":
            actual_bbox = [float(bounds[0]), float(bounds[1]), float(bounds[2]), float(bounds[3])]
        else:
            to_wgs84 = Transformer.from_crs(str(src.crs), "EPSG:4326", always_xy=True)
            min_x, min_y = to_wgs84.transform(bounds[0], bounds[1])
            max_x, max_y = to_wgs84.transform(bounds[2], bounds[3])
            actual_bbox = [
                float(min(min_x, max_x)),
                float(min(min_y, max_y)),
                float(max(min_x, max_x)),
                float(max(min_y, max_y)),
            ]

        if output_path is not None:
            out_file = Path(output_path).resolve()
            out_file.parent.mkdir(parents=True, exist_ok=True)
            with rasterio.open(out_file, "w", **profile) as dst:
                dst.write(data, 1)

        metadata = {
            "crs": str(src.crs),
            "width": int(data.shape[1]),
            "height": int(data.shape[0]),
            "transform": out_transform,
            "resolution": (abs(float(out_transform.a)), abs(float(out_transform.e))),
            "bounds": bounds,
            "dtype": str(profile["dtype"]),
            "nodata": nodata_value,
        }
        return data, metadata, actual_bbox
