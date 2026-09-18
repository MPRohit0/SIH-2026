"""Module 1 terrain pipeline entry point.

This is intentionally a foundation stub. The package is being prepared for the
full terrain workflow, but the implementation is intentionally deferred until the
contract, config, and import boundaries are in place.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def get_repo_root() -> Path:
    """Return the repository root for Module 1 relative lookups."""
    return Path(__file__).resolve().parents[3]


def run_terrain_pipeline(
    site_id: str,
    bbox_wgs84: list[float] | tuple[float, float, float, float],
    dem_path: str | Path,
    river_path: str | Path | None = None,
    failure_source_id: str | None = None,
    output_dir: str | Path | None = None,
    target_crs: str | None = None,
) -> dict[str, Any]:
    """Placeholder API for the future terrain-processing pipeline."""
    raise NotImplementedError("The full Module 1 terrain pipeline is not implemented yet.")


def main() -> None:
    """CLI entry point stub for the future Module 1 pipeline."""
    raise SystemExit("Module 1 terrain pipeline is not implemented yet.")
    parser.add_argument("--site-id", type=str, required=True, help="Site identifier (e.g. himalayan_demo_01)")
    parser.add_argument(
        "--bbox",
        type=float,
        nargs=4,
        required=True,
        metavar=("MIN_LON", "MIN_LAT", "MAX_LON", "MAX_LAT"),
        help="Bounding box in WGS84: min_lon min_lat max_lon max_lat",
    )
    parser.add_argument("--dem", type=str, default=None, help="Path to input DEM GeoTIFF")
    parser.add_argument("--river", type=str, default=None, help="Path to input River GeoJSON")
    parser.add_argument("--failure-source-id", type=str, default=None, help="Associated failure source ID")
    parser.add_argument("--output-dir", type=str, default=None, help="Custom output directory")
    parser.add_argument("--target-crs", type=str, default=None, help="Target projected CRS (e.g. EPSG:32644)")

    args = parser.parse_args()

    repo_root = get_repo_root()
    default_dem = repo_root / "data" / "mock" / "artifacts" / "terrain" / "dem.tif"
    dem_path = args.dem or str(default_dem)

    print(f"Running M1 Terrain Pipeline for site: {args.site_id}")
    print(f"AOI bbox: {args.bbox}")
    print(f"Source DEM: {dem_path}")

    manifest = run_terrain_pipeline(
        site_id=args.site_id,
        bbox_wgs84=args.bbox,
        dem_path=dem_path,
        river_path=args.river,
        failure_source_id=args.failure_source_id,
        output_dir=args.output_dir,
        target_crs=args.target_crs,
    )

    out_folder = args.output_dir or str(repo_root / "data" / "terrain" / args.site_id)
    print("\n✓ Pipeline completed successfully!")
    print(f"Output Directory: {out_folder}")
    print(f"Terrain Manifest ID: {manifest['terrain_manifest_id']}")
    print(f"Storage CRS: {manifest['storage_crs']}")
    print(f"Resolution: {manifest['dem_resolution_m']}m")


if __name__ == "__main__":
    main()
