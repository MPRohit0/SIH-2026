"""Simulation-domain generation and consistency checks for Module 1."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import rasterio
from pyproj import CRS, Transformer
from shapely.geometry import Polygon, shape
from shapely.ops import transform as shapely_transform

from .clipping import validate_bbox_wgs84
from .ingestion import DEMValidationError


class DomainConsistencyError(ValueError):
    """Raised when M1 spatial artifacts do not describe one terrain domain."""


def _crs_label(crs: CRS) -> str:
    """Return a stable human-readable CRS identifier for GeoJSON metadata."""
    epsg = crs.to_epsg()
    return f"EPSG:{epsg}" if epsg is not None else crs.to_string()


def _read_geojson(path: str | Path) -> dict[str, Any]:
    """Read a GeoJSON object from disk and validate its top-level shape."""
    source = Path(path).resolve()
    if not source.is_file():
        raise DomainConsistencyError(f"River geometry does not exist: {source}")
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DomainConsistencyError(f"GeoJSON is not readable: {source}") from exc
    if not isinstance(data, dict) or data.get("type") not in {"Feature", "FeatureCollection"}:
        raise DomainConsistencyError("GeoJSON must be a Feature or FeatureCollection.")
    return data


def _geojson_geometries(data: dict[str, Any]) -> list[Any]:
    """Extract non-empty Shapely geometries from a GeoJSON object."""
    features = [data] if data["type"] == "Feature" else data.get("features", [])
    if not isinstance(features, list) or not features:
        raise DomainConsistencyError("GeoJSON contains no features.")

    geometries = []
    for feature in features:
        if not isinstance(feature, dict) or not isinstance(feature.get("geometry"), dict):
            raise DomainConsistencyError("GeoJSON contains an invalid feature.")
        geometry = shape(feature["geometry"])
        if geometry.is_empty:
            raise DomainConsistencyError("GeoJSON contains an empty geometry.")
        geometries.append(geometry)
    return geometries


def _geometries_in_crs(data: dict[str, Any], source_crs: CRS, target_crs: CRS) -> list[Any]:
    """Extract GeoJSON geometries and transform them into the storage CRS."""
    geometries = _geojson_geometries(data)
    if source_crs == target_crs:
        return geometries
    transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)
    return [shapely_transform(transformer.transform, geometry) for geometry in geometries]


def _aoi_in_crs(bbox_wgs84: list[float], target_crs: str) -> Polygon:
    """Transform the WGS84 AOI to the storage CRS."""
    min_lon, min_lat, max_lon, max_lat = bbox_wgs84
    aoi = Polygon(
        [
            (min_lon, min_lat),
            (max_lon, min_lat),
            (max_lon, max_lat),
            (min_lon, max_lat),
            (min_lon, min_lat),
        ]
    )
    if CRS.from_user_input(target_crs) == CRS.from_epsg(4326):
        return aoi
    transformer = Transformer.from_crs("EPSG:4326", target_crs, always_xy=True)
    return shapely_transform(transformer.transform, aoi)


def _validate_optional_raster(path: str | Path, dem: rasterio.DatasetReader, name: str) -> None:
    """Require an optional raster to use the DEM CRS and exact grid."""
    with rasterio.open(path) as dataset:
        if dataset.crs is None or dataset.crs != dem.crs:
            raise DomainConsistencyError(f"{name} CRS does not match the DEM CRS.")
        if (
            dataset.width != dem.width
            or dataset.height != dem.height
            or dataset.transform != dem.transform
        ):
            raise DomainConsistencyError(f"{name} raster grid does not match the DEM grid.")


def _dem_domain(dem: rasterio.DatasetReader) -> Polygon:
    """Return the exact polygon footprint of a DEM dataset."""
    return Polygon(
        [
            (dem.bounds.left, dem.bounds.bottom),
            (dem.bounds.right, dem.bounds.bottom),
            (dem.bounds.right, dem.bounds.top),
            (dem.bounds.left, dem.bounds.top),
            (dem.bounds.left, dem.bounds.bottom),
        ]
    )


def _domain_geojson(domain: Polygon, storage_crs: CRS) -> dict[str, Any]:
    """Build the contract-facing GeoJSON representation without extra properties."""
    coordinates = [[list(map(float, point)) for point in domain.exterior.coords]]
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {"type": "Polygon", "coordinates": coordinates},
            }
        ],
        "crs": {"type": "name", "properties": {"name": _crs_label(storage_crs)}},
    }


def generate_simulation_domain(
    dem_path: str | Path,
    river_path: str | Path,
    bbox_wgs84: list[float] | tuple[float, float, float, float],
    output_path: str | Path,
    landcover_path: str | Path | None = None,
    manning_path: str | Path | None = None,
    river_crs: str = "EPSG:4326",
) -> dict[str, Any]:
    """Generate a domain polygon from the processed DEM and validate its artifacts."""
    bbox = validate_bbox_wgs84(bbox_wgs84)
    output = Path(output_path).resolve()

    try:
        river_source_crs = CRS.from_user_input(river_crs)
    except Exception as exc:
        raise DomainConsistencyError(f"Invalid river CRS: {river_crs}") from exc

    with rasterio.open(dem_path) as dem:
        if dem.crs is None or dem.transform is None:
            raise DEMValidationError("Processed DEM must have both CRS and transform metadata.")
        storage_crs = CRS.from_user_input(dem.crs)
        if landcover_path is not None:
            _validate_optional_raster(landcover_path, dem, "Land-cover")
        if manning_path is not None:
            _validate_optional_raster(manning_path, dem, "Manning")

        domain = _dem_domain(dem)
        if not domain.intersects(_aoi_in_crs(bbox, str(storage_crs))):
            raise DomainConsistencyError("AOI does not intersect the processed DEM bounds.")

        river_geometries = _geometries_in_crs(_read_geojson(river_path), river_source_crs, storage_crs)
        if not any(geometry.intersects(domain) for geometry in river_geometries):
            raise DomainConsistencyError("Processed river geometry does not intersect the DEM domain.")

        result = _domain_geojson(domain, storage_crs)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def validate_domain_consistency(
    domain_path: str | Path,
    dem_path: str | Path,
    river_path: str | Path,
    landcover_path: str | Path | None = None,
    manning_path: str | Path | None = None,
    river_crs: str = "EPSG:4326",
) -> None:
    """Validate an existing domain against its processed spatial artifacts."""
    data = _read_geojson(domain_path)
    geometries = _geojson_geometries(data)
    if len(geometries) != 1 or geometries[0].geom_type != "Polygon":
        raise DomainConsistencyError("Domain GeoJSON must contain exactly one Polygon feature.")

    with rasterio.open(dem_path) as dem:
        if dem.crs is None:
            raise DomainConsistencyError("DEM is missing a CRS.")
        storage_crs = CRS.from_user_input(dem.crs)
        domain_crs = data.get("crs", {}).get("properties", {}).get("name")
        if domain_crs != _crs_label(storage_crs):
            raise DomainConsistencyError("Domain CRS does not match the DEM CRS.")
        expected = _dem_domain(dem)
        if not geometries[0].equals(expected):
            raise DomainConsistencyError("Domain bounds do not match the DEM bounds.")
        if landcover_path is not None:
            _validate_optional_raster(landcover_path, dem, "Land-cover")
        if manning_path is not None:
            _validate_optional_raster(manning_path, dem, "Manning")

        river_source_crs = CRS.from_user_input(river_crs)
        river_geometries = _geometries_in_crs(_read_geojson(river_path), river_source_crs, storage_crs)
        if not any(geometry.intersects(expected) for geometry in river_geometries):
            raise DomainConsistencyError("River geometry does not intersect the DEM domain.")
