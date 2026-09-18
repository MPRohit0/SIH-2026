"""Dashboard Metric Cards Component for SIH26161 Module 8.

Displays 3 key indicators:
1. Saved Rivers (from local GeoJSON store)
2. Sites (from contract mock fixtures)
3. Scenarios (from contract mock fixtures)
"""

from __future__ import annotations

from pathlib import Path
import streamlit as st

try:
    from modules.m8_dashboard.services.river_store import count_rivers
except ModuleNotFoundError:
    from services.river_store import count_rivers


def get_mock_counts() -> tuple[int, int]:
    """Retrieve counts for Sites and Scenarios from mock contract packages without inventing data."""
    base_dir = Path(__file__).resolve().parent.parent.parent.parent
    
    # Check failure sources (sites) in contracts/fixtures or data/mock
    sites_count = 0
    fixtures_sites = base_dir / "contracts" / "fixtures" / "failure_sources"
    if fixtures_sites.exists():
        sites_count = len(list(fixtures_sites.glob("*.json")))
    elif (base_dir / "data" / "mock" / "json" / "00_failure_source.json").exists():
        sites_count = 1

    # Check physical scenarios in contracts/fixtures or data/mock
    scenarios_count = 0
    fixtures_scenarios = base_dir / "contracts" / "fixtures" / "scenarios"
    if fixtures_scenarios.exists():
        scenarios_count = len(list(fixtures_scenarios.glob("*.json")))
    elif (base_dir / "data" / "mock" / "json").exists():
        scenarios_count = len(list((base_dir / "data" / "mock" / "json").glob("*scenario*.json")))

    return sites_count, scenarios_count


def render_dashboard_metrics() -> None:
    """Render the 3 required metric cards: Rivers, Sites, Scenarios."""
    rivers_count = count_rivers()
    sites_count, scenarios_count = get_mock_counts()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="🌊 Saved Rivers",
            value=rivers_count,
            help="Number of locally persisted river centerline geometries in data/rivers/rivers.geojson",
        )

    with col2:
        st.metric(
            label="📍 Monitoring Sites",
            value=sites_count,
            help="Calibrated dam/lake failure sources available in contract mock package",
        )

    with col3:
        st.metric(
            label="⚡ Simulation Scenarios",
            value=scenarios_count,
            help="Calibrated physical scenarios available in contract mock package",
        )
