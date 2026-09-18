"""Home Page for SIH26161 Flood Simulation Framework (Module 8 Dashboard)."""

from __future__ import annotations

import streamlit as st

try:
    from modules.m8_dashboard.components.map import render_river_map
    from modules.m8_dashboard.components.metrics import render_dashboard_metrics
    from modules.m8_dashboard.services.river_store import load_rivers
except ModuleNotFoundError:
    from components.map import render_river_map
    from components.metrics import render_dashboard_metrics
    from services.river_store import load_rivers


def render_home_page() -> None:
    """Render the Home overview page."""
    st.title("🌊 SIH26161 Flood Simulation Framework")
    st.caption("Multi-fidelity hydrodynamic flood and dam-breach digital twin platform")

    st.markdown(
        """
        Welcome to the **SIH26161 Simulation Control Center**. This framework provides an end-to-end 
        modelling pipeline for dam failures, glacial lake outburst floods (GLOFs), and landslide damming events 
        across complex river terrains.
        """
    )

    st.markdown("---")

    # 1. Metric Cards
    render_dashboard_metrics()

    st.markdown("---")

    # 2. Map Section
    st.subheader("🗺️ River Network & Spatial Overview")
    st.write("Visualizing all locally registered river centerlines across the monitoring domain.")

    rivers = load_rivers()

    if rivers:
        st.info(f"Loaded **{len(rivers)}** saved river(s) from `data/rivers/rivers.geojson`.")
    else:
        st.warning("No rivers registered yet. Navigate to **Add River** in the sidebar to trace your first river centerline.")

    # Render base folium map with all saved rivers
    render_river_map(
        rivers=rivers,
        enable_drawing=False,
        height=520,
        key="home_river_map",
        auto_fit=bool(rivers),
    )


# If executed directly
render_home_page()
