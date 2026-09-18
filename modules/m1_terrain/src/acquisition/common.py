"""Shared cache-first acquisition utilities for Module 1 adapters."""

from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path
from typing import Any

import httpx


class AcquisitionError(RuntimeError):
    """Base error for local or remote acquisition failures."""


def repo_raw_dir(kind: str) -> Path:
    """Return the repository-relative raw-data directory for an acquisition kind."""
    if not kind or Path(kind).name != kind:
        raise ValueError("Acquisition kind must be a single directory name.")
    root = Path(__file__).resolve().parents[4]
    destination = root / "data" / "raw" / kind
    destination.mkdir(parents=True, exist_ok=True)
    return destination


def _safe_target(output_dir: str | Path | None, kind: str, filename: str) -> Path:
    """Resolve a target under data/raw and reject traversal outside it."""
    base = repo_raw_dir(kind) if output_dir is None else Path(output_dir).resolve()
    raw_parts = base.parts
    if "raw" not in raw_parts or raw_parts[raw_parts.index("raw") - 1] != "data":
        raise AcquisitionError("Acquisition output must be under a data/raw directory.")
    base.mkdir(parents=True, exist_ok=True)
    target = (base / filename).resolve()
    if output_dir is None and repo_raw_dir(kind) not in target.parents:
        raise AcquisitionError(f"Acquisition target escapes data/raw/{kind}: {target}")
    if target.name != filename or not target.name:
        raise AcquisitionError(f"Invalid acquisition filename: {filename}")
    return target


def checksum(path: str | Path) -> str:
    """Return the SHA-256 checksum of a cached file."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cache_local_file(
    source_path: str | Path,
    filename: str,
    kind: str,
    output_dir: str | Path | None = None,
) -> Path:
    """Copy a local source into data/raw without replacing an existing cache."""
    source = Path(source_path).resolve()
    if not source.is_file():
        raise AcquisitionError(f"Local acquisition source does not exist: {source}")
    target = _safe_target(output_dir, kind, filename)
    if target.exists():
        return target
    if source == target:
        return target
    temporary = target.with_suffix(target.suffix + ".part")
    try:
        shutil.copyfile(source, temporary)
        os.replace(temporary, target)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise AcquisitionError(f"Could not cache local acquisition source: {source}") from exc
    return target


def download_to_cache(
    url: str,
    filename: str,
    kind: str,
    output_dir: str | Path | None = None,
    client: httpx.Client | None = None,
    timeout: float = 60.0,
) -> Path:
    """Download one remote asset into a cache, reusing existing files unchanged."""
    if not url or not url.strip():
        raise AcquisitionError("A remote acquisition URL is required when no local cache exists.")
    target = _safe_target(output_dir, kind, filename)
    if target.exists():
        return target
    owns_client = client is None
    http_client = client or httpx.Client(timeout=timeout, follow_redirects=True)
    temporary = target.with_suffix(target.suffix + ".part")
    try:
        response = http_client.get(url)
        response.raise_for_status()
        temporary.write_bytes(response.content)
        os.replace(temporary, target)
    except (httpx.HTTPError, OSError) as exc:
        temporary.unlink(missing_ok=True)
        raise AcquisitionError(f"Remote acquisition failed for {url}: {exc}") from exc
    finally:
        if owns_client:
            http_client.close()
    return target


def acquisition_result(path: Path, source: str, cached: bool = True) -> dict[str, Any]:
    """Return a small adapter result without introducing contract fields."""
    return {
        "path": path,
        "source": source,
        "cached": cached,
        "checksum": checksum(path),
        "size_bytes": path.stat().st_size,
    }
