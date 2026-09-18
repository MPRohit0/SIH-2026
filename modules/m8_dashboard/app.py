"""SIH26161 Flood Simulation Framework - Module 8 Dashboard.

Main application entrypoint. Configures import paths and multi-page navigation across:
- Home: Overview, metric cards, and river network map
- Add River: Interactive centerline drawing and local GeoJSON persistence
- Rivers: River registry, map inspection, and deletion
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure repository root and dashboard directory are on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD_ROOT = Path(__file__).resolve().parent

for _p in [str(REPO_ROOT), str(DASHBOARD_ROOT)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import streamlit as st

# Global application configuration
st.set_page_config(
    page_title="SIH26161 Flood Simulation Framework",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Configure navigation pages
home_page = st.Page(
    "pages/1_Home.py",
    title="Home",
    icon="🏠",
    default=True,
)
add_river_page = st.Page(
    "pages/2_Add_River.py",
    title="Add River",
    icon="➕",
)
rivers_page = st.Page(
    "pages/3_Rivers.py",
    title="Rivers",
    icon="🌊",
)

pg = st.navigation(
    {
        "Navigation": [home_page, add_river_page, rivers_page]
    }
)

pg.run()
