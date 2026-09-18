"""Roughness helper definitions for Module 1.

The full Manning's n generation workflow is intentionally deferred. This module
provides a lightweight placeholder structure that keeps the package import-safe.
"""

from __future__ import annotations

from typing import Any


def build_roughness_summary(source: str | None = None, **kwargs: Any) -> dict[str, Any]:
    """Return a minimal placeholder summary for roughness generation."""
    return {
        "source": source or "not_configured",
        "status": "placeholder",
        "details": dict(kwargs),
    }

