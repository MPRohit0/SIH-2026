"""Cache-first Sentinel-2 acquisition adapter for optional M1 inputs."""

from __future__ import annotations

from pathlib import Path

import httpx

from .common import AcquisitionError, acquisition_result, cache_local_file, download_to_cache


class Sentinel2AcquisitionError(AcquisitionError):
    """Raised when Sentinel-2 acquisition is unavailable or invalid."""


class Sentinel2Adapter:
    """Acquire Sentinel-2 assets without performing classification or M1 processing."""

    kind = "sentinel"

    def acquire(
        self,
        asset_name: str,
        url: str | None = None,
        source_path: str | Path | None = None,
        output_dir: str | Path | None = None,
        client: httpx.Client | None = None,
    ) -> dict[str, object]:
        """Return a cached Sentinel-2 asset from local or explicit remote input."""
        if not asset_name or Path(asset_name).name != asset_name:
            raise Sentinel2AcquisitionError("asset_name must be a single filename.")
        try:
            if source_path is not None:
                path = cache_local_file(source_path, asset_name, self.kind, output_dir)
                source = "local"
            else:
                path = download_to_cache(url or "", asset_name, self.kind, output_dir, client)
                source = url or "remote"
        except AcquisitionError as exc:
            raise Sentinel2AcquisitionError(f"Sentinel-2 acquisition unavailable for {asset_name}: {exc}") from exc
        return acquisition_result(path, source)
