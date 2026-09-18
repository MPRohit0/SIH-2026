"""Configuration values for the Module 1 terrain package.

This module intentionally stays free of runtime processing logic. It centralizes
paths and defaults so that the rest of the package can remain import-safe and
portable across machines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Module1Config:
    """Simple configuration model for Module 1 file locations and defaults."""

    repo_root: Path
    module_root: Path
    src_root: Path
    data_root: Path
    raw_dem_dir: Path
    rivers_path: Path
    terrain_output_dir: Path
    landcover_to_manning_n: dict[int, float] = field(
        default_factory=lambda: {
            1: 0.035,
            2: 0.045,
            3: 0.060,
            4: 0.080,
            5: 0.120,
        }
    )
    default_dem_crs: str = "EPSG:4326"
    default_raster_nodata: float = -9999.0
    default_manning_n: float = 0.035

    @classmethod
    def from_repo_root(cls, repo_root: str | Path | None = None) -> "Module1Config":
        """Build the default Module 1 configuration from the repository root."""
        root = Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[3]
        module_root = root / "modules" / "m1_terrain"
        return cls(
            repo_root=root,
            module_root=module_root,
            src_root=module_root / "src",
            data_root=root / "data",
            raw_dem_dir=root / "data" / "raw" / "dem",
            rivers_path=root / "data" / "rivers" / "rivers.geojson",
            terrain_output_dir=root / "data" / "terrain",
            landcover_to_manning_n={
                1: 0.035,
                2: 0.045,
                3: 0.060,
                4: 0.080,
                5: 0.120,
            },
        )


def get_module1_config(repo_root: str | Path | None = None) -> Module1Config:
    """Return the configured Module 1 settings."""
    return Module1Config.from_repo_root(repo_root)


DEFAULT_MODULE1_CONFIG = get_module1_config()
