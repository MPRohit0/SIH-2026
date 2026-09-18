"""Land-cover helper definitions for Module 1.

The full LULC processing pipeline is intentionally left for a later stage. This
module exists to give the package a clear API surface and keep imports stable.
"""

from __future__ import annotations

from typing import Any


def build_landcover_summary(source: str | None = None, **kwargs: Any) -> dict[str, Any]:
    """Return a minimal placeholder summary for land-cover processing."""
    return {
        "source": source or "not_configured",
        "status": "placeholder",
        "details": dict(kwargs),
    }

