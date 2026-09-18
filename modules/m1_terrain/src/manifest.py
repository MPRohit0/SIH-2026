"""TerrainManifest generation and validation for Module 1."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import rasterio
from jsonschema import validate
from pyproj import CRS, Geod, Transformer
from shapely.geometry import shape

from .domain import generate_simulation_domain, validate_domain_consistency
from .river_geometry import validate_river_geometry


class TerrainManifestError(ValueError):
    """Raised when a TerrainManifest cannot be built from consistent artifacts."""


def _schema_path(schema_path: str | Path | None = None) -> Path:
    """Resolve the repository TerrainManifest schema."""
    if schema_path is not None:
        return Path(schema_path).resolve()
    return Path(__file__).resolve().parents[3] / "contracts" / "schemas" / "terrain_manifest.schema.json"


def _checksum(path: Path) -> str:
    """Return a stable SHA-256 checksum for an artifact file."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _crs_label(crs: CRS) -> str:
    """Return a stable CRS identifier."""
    epsg = crs.to_epsg()
    return f"EPSG:{epsg}" if epsg is not None else crs.to_string()


def _bbox_wgs84(bounds: Any, source_crs: CRS) -> list[float]:
    """Transform all raster-bound corners to a WGS84 bounding box."""
    transformer = Transformer.from_crs(source_crs, "EPSG:4326", always_xy=True)
    corners = [
        (bounds.left, bounds.bottom),
        (bounds.left, bounds.top),
        (bounds.right, bounds.bottom),
        (bounds.right, bounds.top),
    ]
    transformed = [transformer.transform(x, y) for x, y in corners]
    lons = [point[0] for point in transformed]
    lats = [point[1] for point in transformed]
    return [float(min(lons)), float(min(lats)), float(max(lons)), float(max(lats))]


def _pixel_size_m(dataset: rasterio.DatasetReader) -> float:
    """Convert the first raster pixel width to metres for RasterMeta."""
    crs = CRS.from_user_input(dataset.crs)
    x0, y0 = dataset.transform * (0.5, 0.5)
    x1, y1 = dataset.transform * (1.5, 0.5)
    if crs.is_geographic:
        geod = Geod(ellps="WGS84")
        _, _, distance = geod.inv(x0, y0, x1, y1)
        return float(abs(distance))
    return float(abs(x1 - x0))


def _raster_meta(dataset: rasterio.DatasetReader, band_name: str, unit: str) -> dict[str, Any]:
    """Build the contract RasterMeta object from an open raster."""
    dtype = str(dataset.dtypes[0])
    allowed = {"float32", "float64", "int16", "int32", "uint8"}
    if dtype not in allowed:
        raise TerrainManifestError(f"Unsupported raster dtype for the contract: {dtype}")
    return {
        "dtype": dtype,
        "bands": [{"name": band_name, "unit": unit}],
        "nodata_value": dataset.nodata,
        "pixel_size_m": _pixel_size_m(dataset),
    }


def _artifact_url(path: Path, url_base: Path) -> str:
    """Return a portable path relative to the manifest directory."""
    return Path(os.path.relpath(path, url_base)).as_posix()


def _raster_artifact(
    path: Path,
    artifact_id: str,
    band_name: str,
    unit: str,
    url_base: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Create a raster Artifact and return its internal consistency metadata."""
    if not path.is_file():
        raise TerrainManifestError(f"Referenced raster artifact does not exist: {path}")
    with rasterio.open(path) as dataset:
        if dataset.crs is None:
            raise TerrainManifestError(f"Raster artifact is missing CRS metadata: {path}")
        if dataset.count < 1 or dataset.width <= 0 or dataset.height <= 0:
            raise TerrainManifestError(f"Raster artifact has invalid dimensions: {path}")
        crs = CRS.from_user_input(dataset.crs)
        artifact = {
            "artifact_id": artifact_id,
            "kind": "raster",
            "media_type": "image/tiff",
            "url": _artifact_url(path, url_base),
            "crs": _crs_label(crs),
            "raster_meta": _raster_meta(dataset, band_name, unit),
            "bbox_wgs84": _bbox_wgs84(dataset.bounds, crs),
            "checksum": _checksum(path),
            "available": True,
        }
        grid = {
            "crs": crs,
            "width": dataset.width,
            "height": dataset.height,
            "transform": dataset.transform,
            "bounds": dataset.bounds,
        }
    return artifact, grid


def _geojson_artifact(path: Path, artifact_id: str, crs: CRS, url_base: Path) -> dict[str, Any]:
    """Create and validate a vector Artifact for a GeoJSON file."""
    if not path.is_file():
        raise TerrainManifestError(f"Referenced vector artifact does not exist: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TerrainManifestError(f"Vector artifact is not readable GeoJSON: {path}") from exc
    if data.get("type") != "FeatureCollection":
        raise TerrainManifestError(f"GeoJSON artifact must be a FeatureCollection: {path}")
    features = data.get("features")
    if not isinstance(features, list) or not features:
        raise TerrainManifestError(f"GeoJSON artifact contains no features: {path}")
    geometries = []
    for feature in features:
        geometry = feature.get("geometry") if isinstance(feature, dict) else None
        if not isinstance(geometry, dict):
            raise TerrainManifestError(f"GeoJSON artifact contains an invalid feature: {path}")
        if artifact_id == "river_centerline":
            valid, error = validate_river_geometry(geometry, coordinate_crs=_crs_label(crs))
            if not valid:
                raise TerrainManifestError(f"River geometry is invalid: {error}")
        parsed = shape(geometry)
        if parsed.is_empty:
            raise TerrainManifestError(f"GeoJSON artifact contains empty geometry: {path}")
        geometries.append(parsed)

    all_bounds = [geometry.bounds for geometry in geometries]
    min_x = min(bounds[0] for bounds in all_bounds)
    min_y = min(bounds[1] for bounds in all_bounds)
    max_x = max(bounds[2] for bounds in all_bounds)
    max_y = max(bounds[3] for bounds in all_bounds)
    transformer = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    corners = [
        transformer.transform(min_x, min_y),
        transformer.transform(min_x, max_y),
        transformer.transform(max_x, min_y),
        transformer.transform(max_x, max_y),
    ]
    bbox = [
        float(min(point[0] for point in corners)),
        float(min(point[1] for point in corners)),
        float(max(point[0] for point in corners)),
        float(max(point[1] for point in corners)),
    ]
    return {
        "artifact_id": artifact_id,
        "kind": "vector",
        "media_type": "application/geo+json",
        "url": _artifact_url(path, url_base),
        "crs": _crs_label(crs),
        "raster_meta": None,
        "bbox_wgs84": bbox,
        "checksum": _checksum(path),
        "available": True,
    }


def _null_artifact() -> None:
    """Return the contract representation for an unavailable optional artifact."""
    return None


def validate_terrain_manifest(
    manifest: dict[str, Any],
    schema_path: str | Path | None = None,
) -> None:
    """Validate a manifest against the repository schema."""
    schema_file = _schema_path(schema_path)
    if not schema_file.is_file():
        raise TerrainManifestError(f"TerrainManifest schema does not exist: {schema_file}")
    try:
        schema = json.loads(schema_file.read_text(encoding="utf-8"))
        validate(instance=manifest, schema=schema)
    except Exception as exc:
        raise TerrainManifestError(f"TerrainManifest schema validation failed: {exc}") from exc


def generate_terrain_manifest(
    site_id: str,
    dem_path: str | Path,
    river_path: str | Path,
    bbox_wgs84: list[float] | tuple[float, float, float, float],
    output_dir: str | Path,
    failure_source_id: str | None = None,
    landcover_path: str | Path | None = None,
    manning_path: str | Path | None = None,
    domain_path: str | Path | None = None,
    river_crs: str = "EPSG:4326",
    schema_path: str | Path | None = None,
) -> dict[str, Any]:
    """Generate, validate, and persist the final contract TerrainManifest."""
    output_folder = Path(output_dir).resolve()
    output_folder.mkdir(parents=True, exist_ok=True)
    manifest_path = output_folder / "terrain_manifest.json"
    domain_file = Path(domain_path).resolve() if domain_path is not None else output_folder / "domain.geojson"

    if not Path(dem_path).is_file() or not Path(river_path).is_file():
        raise TerrainManifestError("DEM and river artifacts are required and must exist.")
    if landcover_path is not None and not Path(landcover_path).is_file():
        raise TerrainManifestError(f"Land-cover artifact does not exist: {landcover_path}")
    if manning_path is not None and not Path(manning_path).is_file():
        raise TerrainManifestError(f"Manning artifact does not exist: {manning_path}")
    if manning_path is None:
        raise TerrainManifestError("Manning artifact is required for a complete terrain hand-off.")

    dem_artifact, dem_grid = _raster_artifact(
        Path(dem_path).resolve(), "dem", "elevation", "m", output_folder
    )
    landcover_artifact = None
    if landcover_path is not None:
        landcover_artifact, landcover_grid = _raster_artifact(
            Path(landcover_path).resolve(), "landcover", "landcover_class", "class", output_folder
        )
        if landcover_grid != dem_grid:
            raise TerrainManifestError("Land-cover raster metadata is inconsistent with the DEM grid.")
    manning_artifact, manning_grid = _raster_artifact(
        Path(manning_path).resolve(), "manning_n", "manning_n", "dimensionless", output_folder
    )
    if manning_grid != dem_grid:
        raise TerrainManifestError("Manning raster metadata is inconsistent with the DEM grid.")

    dem_crs = dem_grid["crs"]
    domain = generate_simulation_domain(
        dem_path=dem_path,
        river_path=river_path,
        bbox_wgs84=bbox_wgs84,
        output_path=domain_file,
        landcover_path=landcover_path,
        manning_path=manning_path,
        river_crs=river_crs,
    )
    del domain
    validate_domain_consistency(
        domain_path=domain_file,
        dem_path=dem_path,
        river_path=river_path,
        landcover_path=landcover_path,
        manning_path=manning_path,
        river_crs=river_crs,
    )

    river_artifact = _geojson_artifact(
        Path(river_path).resolve(), "river_centerline", CRS.from_user_input(river_crs), output_folder
    )
    domain_artifact = _geojson_artifact(domain_file, "domain", dem_crs, output_folder)

    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    terrain_manifest_id = f"terrain_manifest_{site_id}"
    manifest = {
        "id": terrain_manifest_id,
        "schema_version": "1.0.0",
        "terrain_manifest_id": terrain_manifest_id,
        "site_id": site_id,
        "failure_source_id": failure_source_id,
        "status": "ok",
        "warnings": [],
        "error": None,
        "dem": dem_artifact,
        "landcover_classes": landcover_artifact,
        "manning_n": manning_artifact,
        "river_centerline": river_artifact,
        "cross_sections": None,
        "sph_boundary_geometry": domain_artifact,
        "bbox_wgs84": list(bbox_wgs84),
        "storage_crs": _crs_label(dem_crs),
        "api_crs": "EPSG:4326",
        "dem_resolution_m": float(dem_artifact["raster_meta"]["pixel_size_m"]),
        "generated_at": generated_at,
    }
    validate_terrain_manifest(manifest, schema_path=schema_path)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
