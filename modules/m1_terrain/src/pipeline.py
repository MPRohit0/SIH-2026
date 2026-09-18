"""Final Module 1 terrain pipeline orchestration and CLI entry point."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import rasterio
from pyproj import CRS

from .clipping import clip_dem, validate_bbox_wgs84
from .domain import generate_simulation_domain, validate_domain_consistency
from .ingestion import load_dem, load_river
from .landcover import build_landcover_and_manning
from .manifest import TerrainManifestError, generate_terrain_manifest, validate_terrain_manifest
from .reprojection import reproject_dem
from .river_geometry import clip_river_to_aoi


class TerrainPipelineError(ValueError):
    """Raised when a required M1 pipeline stage fails."""


def get_repo_root() -> Path:
    """Return the repository root for Module 1 relative lookups."""
    return Path(__file__).resolve().parents[3]


def _require_file(path: str | Path, label: str) -> Path:
    """Resolve and require a local input file."""
    resolved = Path(path).resolve()
    if not resolved.is_file():
        raise TerrainPipelineError(f"{label} input does not exist: {resolved}")
    return resolved


def _validate_final_outputs(manifest: dict[str, Any], output_folder: Path) -> None:
    """Validate persisted manifest links and expected output location."""
    manifest_path = output_folder / "terrain_manifest.json"
    if not manifest_path.is_file():
        raise TerrainManifestError(f"TerrainManifest was not written: {manifest_path}")
    persisted = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_terrain_manifest(persisted)
    if persisted != manifest:
        raise TerrainManifestError("Persisted TerrainManifest differs from the generated manifest.")

    required = ("dem", "manning_n", "river_centerline", "sph_boundary_geometry")
    for artifact_name in required:
        artifact = persisted.get(artifact_name)
        if not isinstance(artifact, dict) or artifact.get("available") is not True:
            raise TerrainManifestError(f"Required artifact is unavailable: {artifact_name}")
        url = artifact.get("url")
        if not isinstance(url, str) or not (output_folder / url).resolve().is_file():
            raise TerrainManifestError(f"Manifest artifact path does not exist: {artifact_name}")

    landcover = persisted.get("landcover_classes")
    if landcover is not None and not (output_folder / landcover["url"]).resolve().is_file():
        raise TerrainManifestError("Manifest land-cover artifact path does not exist.")


def run_terrain_pipeline(
    site_id: str,
    bbox_wgs84: list[float] | tuple[float, float, float, float],
    dem_path: str | Path,
    river_path: str | Path,
    failure_source_id: str | None = None,
    output_dir: str | Path | None = None,
    target_crs: str | None = None,
    landcover_path: str | Path | None = None,
    manning_path: str | Path | None = None,
    river_crs: str = "EPSG:4326",
) -> dict[str, Any]:
    """Run the complete M1 terrain hand-off from source inputs to manifest."""
    if not isinstance(site_id, str) or not site_id.strip():
        raise TerrainPipelineError("site_id is required and must be non-empty.")
    bbox = validate_bbox_wgs84(bbox_wgs84)
    dem_source = _require_file(dem_path, "DEM")
    river_source = _require_file(river_path, "River")
    try:
        load_dem(dem_source)
    except Exception as exc:
        raise TerrainPipelineError(f"DEM ingestion failed: {exc}") from exc

    output_folder = (
        Path(output_dir).resolve()
        if output_dir is not None
        else get_repo_root() / "data" / "terrain" / site_id
    )
    output_folder.mkdir(parents=True, exist_ok=True)
    dem_normalized = output_folder / "dem_normalized.tif"
    dem_processed = output_folder / "dem.tif"
    river_processed = output_folder / "river_centerline.geojson"
    landcover_processed = output_folder / "landcover.tif"
    manning_processed = output_folder / "manning_n.tif"
    domain_processed = output_folder / "domain.geojson"

    with rasterio.open(dem_source) as source_dem:
        if source_dem.crs is None:
            raise TerrainPipelineError("DEM CRS normalization failed: source DEM has no CRS.")
        source_crs = CRS.from_user_input(source_dem.crs)
    try:
        storage_crs = CRS.from_user_input(target_crs) if target_crs else source_crs
    except Exception as exc:
        raise TerrainPipelineError(f"Invalid target CRS: {target_crs}") from exc

    try:
        reproject_dem(dem_source, str(storage_crs), output_path=dem_normalized)
    except Exception as exc:
        raise TerrainPipelineError(f"DEM CRS normalization failed: {exc}") from exc
    try:
        clip_dem(dem_normalized, bbox, output_path=dem_processed)
    except Exception as exc:
        raise TerrainPipelineError(f"DEM AOI clipping failed: {exc}") from exc

    try:
        river_data = load_river(river_source)
        clip_river_to_aoi(
            river_data,
            bbox,
            output_path=river_processed,
            source_crs=river_crs,
            target_crs=str(storage_crs),
        )
    except Exception as exc:
        raise TerrainPipelineError(f"River ingestion/normalization/clipping failed: {exc}") from exc

    if landcover_path is not None:
        landcover_source = _require_file(landcover_path, "Land-cover")
        try:
            build_landcover_and_manning(
                site_id=site_id,
                dem_path=dem_processed,
                landcover_path=landcover_source,
                bbox_wgs84=bbox,
                output_dir=output_folder,
            )
        except Exception as exc:
            raise TerrainPipelineError(f"Land-cover/Manning processing failed: {exc}") from exc
    elif manning_path is not None:
        manning_source = _require_file(manning_path, "Manning")
        manning_processed.write_bytes(manning_source.read_bytes())

    if not manning_processed.is_file():
        raise TerrainPipelineError(
            "Manning roughness generation failed: provide landcover_path or a preprocessed manning_path."
        )

    try:
        generate_simulation_domain(
            dem_path=dem_processed,
            river_path=river_processed,
            bbox_wgs84=bbox,
            output_path=domain_processed,
            landcover_path=landcover_processed if landcover_processed.is_file() else None,
            manning_path=manning_processed,
            river_crs=str(storage_crs),
        )
        validate_domain_consistency(
            domain_path=domain_processed,
            dem_path=dem_processed,
            river_path=river_processed,
            landcover_path=landcover_processed if landcover_processed.is_file() else None,
            manning_path=manning_processed,
            river_crs=str(storage_crs),
        )
    except Exception as exc:
        raise TerrainPipelineError(f"Simulation-domain generation failed: {exc}") from exc

    try:
        manifest = generate_terrain_manifest(
            site_id=site_id,
            dem_path=dem_processed,
            river_path=river_processed,
            bbox_wgs84=bbox,
            output_dir=output_folder,
            failure_source_id=failure_source_id,
            landcover_path=landcover_processed if landcover_processed.is_file() else None,
            manning_path=manning_processed,
            domain_path=domain_processed,
            river_crs=str(storage_crs),
        )
        _validate_final_outputs(manifest, output_folder)
        return manifest
    except Exception as exc:
        raise TerrainPipelineError(f"TerrainManifest generation/validation failed: {exc}") from exc


def main() -> None:
    """Run the M1 pipeline from command-line arguments."""
    parser = argparse.ArgumentParser(description="Generate the Module 1 terrain hand-off.")
    parser.add_argument("--site-id", type=str, required=True, help="Site identifier")
    parser.add_argument(
        "--bbox",
        type=float,
        nargs=4,
        required=True,
        metavar=("MIN_LON", "MIN_LAT", "MAX_LON", "MAX_LAT"),
        help="Bounding box in WGS84",
    )
    parser.add_argument("--dem", type=str, required=True, help="Path to input DEM GeoTIFF")
    parser.add_argument("--river", type=str, required=True, help="Path to input River GeoJSON")
    parser.add_argument("--landcover", type=str, default=None, help="Path to input land-cover GeoTIFF")
    parser.add_argument("--manning", type=str, default=None, help="Path to preprocessed Manning GeoTIFF")
    parser.add_argument("--failure-source-id", type=str, default=None, help="Associated failure source ID")
    parser.add_argument("--output-dir", type=str, default=None, help="Output directory")
    parser.add_argument("--target-crs", type=str, default=None, help="Target storage CRS")
    parser.add_argument("--river-crs", type=str, default="EPSG:4326", help="Input river CRS")
    args = parser.parse_args()

    try:
        manifest = run_terrain_pipeline(
            site_id=args.site_id,
            bbox_wgs84=args.bbox,
            dem_path=args.dem,
            river_path=args.river,
            failure_source_id=args.failure_source_id,
            output_dir=args.output_dir,
            target_crs=args.target_crs,
            landcover_path=args.landcover,
            manning_path=args.manning,
            river_crs=args.river_crs,
        )
    except Exception as exc:
        parser.error(str(exc))
        return

    output_folder = args.output_dir or str(get_repo_root() / "data" / "terrain" / args.site_id)
    print(f"TerrainManifest written to {Path(output_folder).resolve() / 'terrain_manifest.json'}")
    print(f"Terrain manifest ID: {manifest['terrain_manifest_id']}")
    print(f"Storage CRS: {manifest['storage_crs']}")


if __name__ == "__main__":
    main()