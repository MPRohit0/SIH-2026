"""Isolated Bhuvan acquisition adapter.

No Bhuvan endpoint or credentials are defined in this repository. This adapter
therefore requires an explicit caller-provided endpoint or a local cached file;
it never invents a service URL.
"""

from __future__ import annotations

from pathlib import Path

import httpx

from .common import AcquisitionError, acquisition_result, cache_local_file, download_to_cache


class BhuvanAcquisitionError(AcquisitionError):
    """Raised when Bhuvan acquisition is unavailable or unconfigured."""


class BhuvanAdapter:
    """Acquire Bhuvan data only from an explicit local source or endpoint."""

    kind = "bhuvan"

    def acquire(
        self,
        filename: str,
        endpoint: str | None = None,
        source_path: str | Path | None = None,
        output_dir: str | Path | None = None,
        client: httpx.Client | None = None,
    ) -> dict[str, object]:
        """Return cached Bhuvan data or clearly report missing configuration."""
        try:
            if source_path is not None:
                path = cache_local_file(source_path, filename, self.kind, output_dir)
                source = "local"
            elif endpoint:
                path = download_to_cache(endpoint, filename, self.kind, output_dir, client)
                source = endpoint
            else:
                raise BhuvanAcquisitionError(
                    "Bhuvan acquisition is unavailable: no approved endpoint is configured; "
                    "provide an existing local source or an explicit endpoint."
                )
        except AcquisitionError as exc:
            raise BhuvanAcquisitionError(f"Bhuvan acquisition unavailable: {exc}") from exc
        return acquisition_result(path, source)
