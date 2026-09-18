"""Rivers Management Page for SIH26161 Module 8 Dashboard.

Displays all registered rivers, coordinate point summaries, provides map inspection,
and supports deletion with user confirmation.
"""

from __future__ import annotations

import json
import streamlit as st

try:
    from modules.m8_dashboard.components.map import render_river_map
    from modules.m8_dashboard.services.river_store import (
        load_rivers,
        load_feature_collection,
        delete_river,
        get_river,
    )
except ModuleNotFoundError:
    from components.map import render_river_map
    from services.river_store import (
        load_rivers,
        load_feature_collection,
        delete_river,
        get_river,
    )


def render_rivers_page() -> None:
    st.title("🌊 Registered Rivers")
    st.caption("Manage, inspect, and delete local river centerlines")

    rivers = load_rivers()

    if "highlighted_river_id" not in st.session_state:
        st.session_state["highlighted_river_id"] = None

    if not rivers:
        st.info("No rivers registered yet. Use the **Add River** page to draw and save your first river centerline.")
        return

    st.markdown(f"Currently managing **{len(rivers)}** river centerline(s) in `data/rivers/rivers.geojson`.")

    # Layout: River cards and map
    col_list, col_map = st.columns([1, 1], gap="medium")

    with col_list:
        st.subheader("📋 River Registry")

        for idx, feature in enumerate(rivers):
            props = feature.get("properties", {})
            r_id = props.get("river_id", f"river_{idx}")
            r_name = props.get("river_name", "Unnamed")
            r_source = props.get("source", "manual")
            r_date = props.get("created_at", "N/A")
            coords = feature.get("geometry", {}).get("coordinates", [])

            is_selected = st.session_state.get("highlighted_river_id") == r_id

            with st.container(border=True):
                # Header with status
                title_prefix = "📍 Selected: " if is_selected else "🌊 "
                st.markdown(f"### {title_prefix}{r_name}")
                st.markdown(
                    f"""
                    - **ID:** ` {r_id} `
                    - **Source:** `{r_source}`
                    - **Vertices:** {len(coords)} points
                    - **Created:** {r_date[:19].replace('T', ' ')} UTC
                    """
                )

                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button("👁️ View on Map", key=f"view_{r_id}", use_container_width=True):
                        st.session_state["highlighted_river_id"] = r_id
                        st.rerun()

                with btn_col2:
                    # Deletion state management
                    confirm_key = f"confirm_del_{r_id}"
                    if st.session_state.get(confirm_key, False):
                        st.warning("⚠️ Delete this river?")
                        del_c1, del_c2 = st.columns(2)
                        with del_c1:
                            if st.button("Yes, Delete", key=f"do_del_{r_id}", type="primary"):
                                if delete_river(r_id):
                                    st.success(f"Deleted '{r_name}'.")
                                    st.session_state[confirm_key] = False
                                    if st.session_state.get("highlighted_river_id") == r_id:
                                        st.session_state["highlighted_river_id"] = None
                                    st.rerun()
                                else:
                                    st.error("Failed to delete river.")
                        with del_c2:
                            if st.button("Cancel", key=f"cancel_del_{r_id}"):
                                st.session_state[confirm_key] = False
                                st.rerun()
                    else:
                        if st.button("🗑️ Delete", key=f"btn_del_{r_id}", use_container_width=True):
                            st.session_state[confirm_key] = True
                            st.rerun()

        # Download GeoJSON button
        st.markdown("---")
        fc_data = load_feature_collection()
        st.download_button(
            label="📥 Download rivers.geojson",
            data=json.dumps(fc_data, indent=2),
            file_name="rivers.geojson",
            mime="application/geo+json",
            use_container_width=True,
        )

    with col_map:
        highlight_id = st.session_state.get("highlighted_river_id")
        if highlight_id:
            h_river = get_river(highlight_id)
            h_name = h_river["properties"].get("river_name") if h_river else highlight_id
            st.subheader(f"🗺️ Viewing: {h_name}")
            if st.button("Reset Focus to All Rivers"):
                st.session_state["highlighted_river_id"] = None
                st.rerun()
        else:
            st.subheader("🗺️ Network View")

        render_river_map(
            rivers=rivers,
            enable_drawing=False,
            highlight_id=highlight_id,
            height=580,
            key=f"rivers_view_map_{highlight_id}",
            auto_fit=True,
        )


render_rivers_page()
