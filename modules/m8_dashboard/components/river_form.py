"""River Form Component for SIH26161 Module 8 Dashboard.

Manages inputs for adding a river centerline:
- River Name
- River ID
- Interactive Polyline Drawing on Map
- Validation and Local GeoJSON Persistence
"""

from __future__ import annotations

import json
import re
from typing import Any
import streamlit as st

try:
    from modules.m8_dashboard.components.map import render_river_map, extract_drawn_linestring
    from modules.m8_dashboard.services.river_store import (
        load_rivers,
        save_river,
        validate_river,
        river_exists,
    )
except ModuleNotFoundError:
    from components.map import render_river_map, extract_drawn_linestring
    from services.river_store import (
        load_rivers,
        save_river,
        validate_river,
        river_exists,
    )


def slugify(text: str) -> str:
    """Generate a clean slug for suggested river ID."""
    clean = re.sub(r"[^\w\s-]", "", text.strip().lower())
    return re.sub(r"[-\s]+", "_", clean)


def render_add_river_form() -> None:
    """Render the full interactive Add River workflow."""
    existing_rivers = load_rivers()

    st.markdown(
        """
        ### ➕ Define New River Centerline
        Enter the river identification details and draw its centerline directly on the map below.
        """
    )

    # Maintain session state keys
    if "drawn_coords" not in st.session_state:
        st.session_state["drawn_coords"] = []

    # Inputs layout
    col1, col2 = st.columns(2)
    with col1:
        river_name = st.text_input(
            "River Name *",
            placeholder="e.g. Alaknanda River",
            key="river_name_input",
            help="Full common name of the river or tributary",
        )

    # Suggest River ID if empty
    suggested_id = slugify(river_name) if river_name else ""
    with col2:
        river_id = st.text_input(
            "River ID *",
            value=st.session_state.get("river_id_input", suggested_id),
            placeholder="e.g. alaknanda_01",
            key="river_id_input",
            help="Unique alphanumeric ID with underscores or hyphens",
        )

    st.markdown("---")
    st.markdown(
        """
        #### 📍 Step 2: Draw River Centerline
        Use the **Polyline tool** on the top-left toolbar of the map to trace the river course.
        - Click along the river valley to add vertices.
        - Click the last vertex again to complete the line.
        """
    )

    # Render interactive map with polyline draw tool
    map_output = render_river_map(
        rivers=existing_rivers,
        enable_drawing=True,
        height=480,
        key="add_river_map_canvas",
        auto_fit=bool(existing_rivers),
    )

    # Process drawn polyline from map output
    drawn_geom = extract_drawn_linestring(map_output)
    if drawn_geom:
        st.session_state["drawn_coords"] = drawn_geom.get("coordinates", [])

    active_coords = st.session_state.get("drawn_coords", [])

    # Drawing feedback box
    if active_coords and len(active_coords) >= 2:
        st.success(f"✓ Centerline geometry captured: **{len(active_coords)} coordinate vertices**.")
        with st.expander("🔍 View Captured Coordinates (WGS84 [Lon, Lat])", expanded=False):
            st.json(active_coords)
    else:
        st.info("ℹ️ No polyline captured yet. Please click on the map using the polyline tool to draw the river.")

    # Optional manual coordinate override
    with st.expander("🛠️ Manual Coordinate Entry (Optional)", expanded=False):
        st.caption("You can paste or edit GeoJSON LineString coordinates [[lon, lat], [lon, lat], ...] below:")
        manual_text = st.text_area(
            "Coordinates JSON",
            value=json.dumps(active_coords) if active_coords else "",
            height=100,
            key="manual_coords_area",
        )
        if st.button("Apply Manual Coordinates"):
            try:
                parsed = json.loads(manual_text)
                if isinstance(parsed, list) and len(parsed) >= 2:
                    st.session_state["drawn_coords"] = parsed
                    st.success(f"Applied {len(parsed)} coordinates manually.")
                    st.rerun()
                else:
                    st.error("Manual coordinates must be a JSON array of at least 2 [lon, lat] pairs.")
            except Exception as e:
                st.error(f"Invalid JSON format: {e}")

    st.markdown("---")

    # Save button
    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        save_clicked = st.button("💾 Save River", type="primary", use_container_width=True)

    if save_clicked:
        final_name = river_name.strip()
        final_id = river_id.strip()
        final_coords = st.session_state.get("drawn_coords", [])

        # Validate inputs
        if not final_name:
            st.error("❌ River Name cannot be empty.")
            return

        if not final_id:
            st.error("❌ River ID cannot be empty.")
            return

        if river_exists(final_id):
            st.error(f"❌ River ID '{final_id}' already exists. Please specify a unique ID.")
            return

        if not final_coords or len(final_coords) < 2:
            st.error("❌ A valid LineString with at least 2 points is required. Please draw the line on the map.")
            return

        geometry = {
            "type": "LineString",
            "coordinates": final_coords,
        }

        # Perform comprehensive validation
        is_valid, err_msg = validate_river(final_name, final_id, geometry)
        if not is_valid:
            st.error(f"❌ Validation Failed: {err_msg}")
            return

        # Save to local GeoJSON
        success, msg = save_river(
            river_name=final_name,
            river_id=final_id,
            geometry=geometry,
            source="manual",
        )

        if success:
            st.success(f"✅ {msg}")
            # Reset drawn coords
            st.session_state["drawn_coords"] = []
            st.balloons()
        else:
            st.error(f"❌ Failed to save river: {msg}")
