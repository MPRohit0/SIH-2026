"""Land-cover processing for Module 1.

This stage intentionally does not perform acquisition or ML classification. It
loads a local raster, validates it against the terrain domain, reprojects and
clips it to the DEM grid, and converts class IDs into Manning roughness values
using an explicit configuration lookup table.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.mask import mask
from rasterio.warp import reproject
from shapely.geometry import box, mapping

from modules.m1_terrain.config.settings import DEFAULT_MODULE1_CONFIG

from .clipping import validate_bbox_wgs84
from .ingestion import load_dem


class LandCoverProcessingError(ValueError):
    """Raised when a land-cover raster cannot be validated or mapped safely."""


def build_landcover_summary(source: str | None = None, **kwargs: Any) -> dict[str, Any]:
    """Return a minimal land-cover processing summary."""
    return {
        "source": source or "not_configured",
        "status": "ok",
        "details": dict(kwargs),
    }


def load_landcover(landcover_path: str | Path) -> tuple[np.ndarray, dict[str, Any]]:
    """Load a local categorical land-cover raster and return its pixel data and metadata."""
    source_path = Path(landcover_path).resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"Land-cover raster not found: {source_path}")
    if not source_path.is_file():
        raise FileNotFoundError(f"Land-cover path is not a file: {source_path}")

    try:
        with rasterio.open(source_path, "r") as dataset:
            if dataset.width <= 0 or dataset.height <= 0:
                raise LandCoverProcessingError(f"Land-cover raster has invalid dimensions: {source_path}")
            if dataset.crs is None:
                raise LandCoverProcessingError(f"Land-cover raster is missing a CRS definition: {source_path}")
            if dataset.transform is None:
                raise LandCoverProcessingError(f"Land-cover raster is missing a transform: {source_path}")
            if dataset.count < 1:
                raise LandCoverProcessingError(f"Land-cover raster has no bands: {source_path}")

            band = dataset.read(1)
            if band.size == 0:
                raise LandCoverProcessingError(f"Land-cover raster is empty: {source_path}")
            if not np.issubdtype(band.dtype, np.integer):
                raise LandCoverProcessingError(
                    f"Land-cover raster must contain integer class IDs, got {band.dtype} in {source_path}."
                )

            metadata: dict[str, Any] = {
                "path": str(source_path),
                "crs": str(dataset.crs),
                "width": int(dataset.width),
                "height": int(dataset.height),
                "transform": dataset.transform,
                "resolution": (float(abs(dataset.res[0])), float(abs(dataset.res[1]))),
                "bounds": dataset.bounds,
                "dtype": str(dataset.dtypes[0]),
                "nodata": dataset.nodata,
                "count": int(dataset.count),
            }
            return band.astype(np.int32, copy=False), metadata
    except rasterio.errors.RasterioIOError as exc:
        raise LandCoverProcessingError(f"Land-cover raster could not be opened: {source_path}") from exc


def validate_landcover_raster(data: np.ndarray, metadata: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate a land-cover raster against the terrain-domain expectations."""
    issues: list[str] = []
    if not isinstance(data, np.ndarray):
        issues.append("Land-cover data must be a NumPy array.")
        return False, issues
    if data.ndim != 2:
        issues.append("Land-cover raster must be 2D.")
    if data.size == 0:
        issues.append("Land-cover raster is empty.")
    if metadata.get("crs") in (None, ""):
        issues.append("Land-cover raster is missing a CRS.")
    if metadata.get("transform") is None:
        issues.append("Land-cover raster is missing a transform.")
    if metadata.get("width", 0) <= 0 or metadata.get("height", 0) <= 0:
        issues.append("Land-cover raster dimensions are invalid.")
    if not np.issubdtype(data.dtype, np.integer):
        issues.append("Land-cover raster must store integer class IDs.")
    return not issues, issues


def _normalize_lookup_table(lookup_table: dict[int, float] | None) -> dict[int, float]:
    """Return a validated Manning lookup table, raising on missing or invalid values."""
    mapping = lookup_table if lookup_table is not None else DEFAULT_MODULE1_CONFIG.landcover_to_manning_n
    if not isinstance(mapping, dict) or not mapping:
        raise LandCoverProcessingError("Land-cover lookup table must be a non-empty dictionary.")

    normalized: dict[int, float] = {}
    for raw_key, raw_value in mapping.items():
        try:
            key = int(raw_key)
            value = float(raw_value)
        except (TypeError, ValueError) as exc:
            raise LandCoverProcessingError(f"Invalid land-cover lookup entry: {raw_key} -> {raw_value}") from exc
        if value <= 0:
            raise LandCoverProcessingError(f"Manning value for class {key} must be positive, got {value}.")
        normalized[key] = value
    return normalized


def _clip_to_aoi(raster_path: str | Path, bbox_wgs84: list[float] | tuple[float, float, float, float]) -> tuple[np.ndarray, dict[str, Any]]:
    """Clip a raster to the requested WGS84 bounding box while preserving transform and CRS."""
    bbox = validate_bbox_wgs84(bbox_wgs84)
    with rasterio.open(raster_path) as src:
        geom = [mapping(box(bbox[0], bbox[1], bbox[2], bbox[3]))]
        clipped, transform = mask(src, geom, crop=True, nodata=src.nodata if src.nodata is not None else -9999)
    if clipped.size == 0:
        raise LandCoverProcessingError(f"Land-cover raster clip to AOI produced empty output: {bbox}")
    metadata = {
        "path": str(raster_path),
        "crs": str(src.crs),
        "width": int(clipped.shape[2]),
        "height": int(clipped.shape[1]),
        "transform": transform,
        "resolution": (abs(float(transform.a)), abs(float(transform.e))),
        "bounds": rasterio.transform.array_bounds(clipped.shape[1], clipped.shape[2], transform),
        "dtype": str(clipped.dtype),
        "nodata": src.nodata if src.nodata is not None else -9999,
        "count": 1,
    }
    return clipped[0].astype(np.int32, copy=False), metadata


def _resample_landcover_to_dem(landcover_path: str | Path, dem_meta: dict[str, Any], nodata_value: float | int = -9999) -> tuple[np.ndarray, dict[str, Any]]:
    """Reproject and resample a local land-cover raster to the DEM grid without silent fallback."""
    with rasterio.open(landcover_path, "r") as src:
        width = int(dem_meta["width"])
        height = int(dem_meta["height"])
        transform = dem_meta["transform"]
        crs = dem_meta["crs"]

        destination = np.full((height, width), int(nodata_value), dtype=np.int32)
        reproject(
            source=src.read(1),
            destination=destination,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=transform,
            dst_crs=crs,
            src_nodata=src.nodata if src.nodata is not None else nodata_value,
            dst_nodata=int(nodata_value),
            resampling=Resampling.nearest,
        )

        metadata = {
            "path": str(landcover_path),
            "crs": str(crs),
            "width": width,
            "height": height,
            "transform": transform,
            "resolution": dem_meta["resolution"],
            "bounds": dem_meta["bounds"],
            "dtype": "int32",
            "nodata": int(nodata_value),
            "count": 1,
        }
        return destination.astype(np.int32, copy=False), metadata


def build_landcover_and_manning(
    site_id: str,
    dem_path: str | Path,
    landcover_path: str | Path,
    bbox_wgs84: list[float] | tuple[float, float, float, float],
    output_dir: str | Path,
    lookup_table: dict[int, float] | None = None,
) -> dict[str, Any]:
    """Create contract-compliant land-cover and Manning rasters aligned to the DEM grid."""
    clean_bbox = validate_bbox_wgs84(bbox_wgs84)
    lookup = _normalize_lookup_table(lookup_table)

    _, dem_meta = load_dem(dem_path)
    landcover_array, landcover_meta = load_landcover(landcover_path)
    landcover_ok, issues = validate_landcover_raster(landcover_array, landcover_meta)
    if not landcover_ok:
        raise LandCoverProcessingError("Land-cover raster validation failed: " + "; ".join(issues))

    if (
        dem_meta["crs"] == landcover_meta["crs"]
        and (dem_meta["width"], dem_meta["height"]) == (landcover_meta["width"], landcover_meta["height"])
        and dem_meta["transform"] == landcover_meta["transform"]
    ):
        aligned_landcover = landcover_array.astype(np.int32, copy=False)
        aligned_meta = dict(landcover_meta)
        aligned_meta["transform"] = dem_meta["transform"]
        aligned_meta["bounds"] = dem_meta["bounds"]
        aligned_meta["resolution"] = dem_meta["resolution"]
    else:
        aligned_landcover, aligned_meta = _resample_landcover_to_dem(landcover_path, dem_meta)

    valid_mask = aligned_landcover != aligned_meta.get("nodata", -9999)
    unknown_classes = sorted({int(value) for value in np.unique(aligned_landcover[valid_mask]) if int(value) not in lookup})
    if unknown_classes:
        raise LandCoverProcessingError(
            "Unknown land-cover classes are not allowed in the terrain processing stage: "
            f"{unknown_classes}. Update the configuration lookup table explicitly."
        )

    nodata_value = dem_meta.get("nodata", -9999.0)
    if nodata_value is None:
        nodata_value = -9999.0

    manning = np.empty_like(aligned_landcover, dtype=np.float32)
    manning.fill(float(nodata_value))
    for class_id, value in lookup.items():
        manning[aligned_landcover == int(class_id)] = float(value)

    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    landcover_out = output_dir / "landcover.tif"
    manning_out = output_dir / "manning_n.tif"

    landcover_profile = {
        "driver": "GTiff",
        "height": aligned_landcover.shape[0],
        "width": aligned_landcover.shape[1],
        "count": 1,
        "dtype": "int32",
        "crs": dem_meta["crs"],
        "transform": dem_meta["transform"],
        "nodata": int(nodata_value),
    }
    with rasterio.open(landcover_out, "w", **landcover_profile) as dst:
        dst.write(aligned_landcover.astype(np.int32, copy=False), 1)

    manning_profile = {
        "driver": "GTiff",
        "height": manning.shape[0],
        "width": manning.shape[1],
        "count": 1,
        "dtype": "float32",
        "crs": dem_meta["crs"],
        "transform": dem_meta["transform"],
        "nodata": float(nodata_value),
    }
    with rasterio.open(manning_out, "w", **manning_profile) as dst:
        dst.write(manning.astype(np.float32, copy=False), 1)

    return {
        "site_id": str(site_id),
        "bbox_wgs84": list(clean_bbox),
        "dem_path": str(Path(dem_path).resolve()),
        "landcover_path": str(landcover_out),
        "manning_path": str(manning_out),
        "lookup_table": lookup,
    }


def main() -> None:
    """Command-line entry point for the land-cover and Manning stage."""
    raise SystemExit("The M1 land-cover/Manning stage is a library function, not an executable script.")


