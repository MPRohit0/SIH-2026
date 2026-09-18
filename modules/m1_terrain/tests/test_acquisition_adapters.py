"""Offline and mocked tests for Module 1 acquisition adapters."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from modules.m1_terrain.src.acquisition import (
    BhuvanAcquisitionError,
    BhuvanAdapter,
    Sentinel2Adapter,
    SRTMAdapter,
)


def test_srtm_local_source_is_cached_under_raw_without_overwrite(tmp_path: Path) -> None:
    """A local SRTM input should work offline and preserve an existing cache."""
    source = tmp_path / "source.tif"
    source.write_bytes(b"original-dem")
    raw_dir = tmp_path / "data" / "raw" / "dem"

    first = SRTMAdapter().acquire("N30E079.tif", source_path=source, output_dir=raw_dir)
    assert Path(first["path"]).parent == raw_dir
    assert Path(first["path"]).read_bytes() == b"original-dem"

    source.write_bytes(b"changed-source")
    second = SRTMAdapter().acquire("N30E079.tif", source_path=source, output_dir=raw_dir)
    assert second["cached"] is True
    assert Path(second["path"]).read_bytes() == b"original-dem"


def test_sentinel2_mocked_remote_download_is_cached(tmp_path: Path) -> None:
    """Sentinel-2 remote acquisition should be testable without real network access."""
    raw_dir = tmp_path / "data" / "raw" / "sentinel"

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://example.test/B02.tif"
        return httpx.Response(200, content=b"sentinel-payload", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = Sentinel2Adapter().acquire(
        "B02.tif",
        url="https://example.test/B02.tif",
        output_dir=raw_dir,
        client=client,
    )
    client.close()

    assert Path(result["path"]).read_bytes() == b"sentinel-payload"
    assert Path(result["path"]).parent == raw_dir


def test_bhuvan_requires_explicit_source_or_endpoint() -> None:
    """Bhuvan must not invent an endpoint when none is configured."""
    with pytest.raises(BhuvanAcquisitionError, match="no approved endpoint"):
        BhuvanAdapter().acquire("bhuvan.tif", output_dir=Path("data") / "raw" / "bhuvan")


def test_remote_failure_is_clear_and_does_not_leave_partial_file(tmp_path: Path) -> None:
    """Remote errors should surface clearly and clean up partial cache output."""
    raw_dir = tmp_path / "data" / "raw" / "dem"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(Exception, match="SRTM acquisition unavailable"):
        SRTMAdapter().acquire(
            "N30E079.tif",
            url="https://example.test/N30E079.tif",
            output_dir=raw_dir,
            client=client,
        )
    client.close()

    assert not (raw_dir / "N30E079.tif").exists()
    assert not (raw_dir / "N30E079.tif.part").exists()
