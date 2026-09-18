"""SIH26161 Module 8 Dashboard Package."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure repository root and dashboard directory are on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD_ROOT = Path(__file__).resolve().parent

for _p in [str(REPO_ROOT), str(DASHBOARD_ROOT)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)
