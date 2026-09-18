"""Cache-first SRTM DEM acquisition adapter."""

from __future__ import annotations

from pathlib import Path

import httpx

from .common import AcquisitionError, acquisition_result, cache_local_file, download_to_cache


class SRTMAcquisitionError(AcquisitionError):
    """Raised when SRTM acquisition is unavailable or invalid."""


class SRTMAdapter:
    """Acquire SRTM tiles without coupling acquisition to terrain processing."""

    kind = "dem"

    def acquire(
        self,
        tile_name: str,
        url: str | None = None,
        source_path: str | Path | None = None,
        output_dir: str | Path | None = None,
        client: httpx.Client | None = None,
    ) -> dict[str, object]:
        """Return a cached SRTM tile, optionally caching a local or remote source."""
        if not tile_name or Path(tile_name).name != tile_name:
            raise SRTMAcquisitionError("tile_name must be a single filename such as N30E079.tif.")
        filename = tile_name if Path(tile_name).suffix else f"{tile_name}.tif"
        try:
            if source_path is not None:
                path = cache_local_file(source_path, filename, self.kind, output_dir)
                source = "local"
            else:
                path = download_to_cache(url or "", filename, self.kind, output_dir, client)
                source = url or "remote"
        except AcquisitionError as exc:
            raise SRTMAcquisitionError(f"SRTM acquisition unavailable for {tile_name}: {exc}") from exc
        return acquisition_result(path, source)
