"""Add River Page for SIH26161 Module 8 Dashboard."""

from __future__ import annotations

import streamlit as st

try:
    from modules.m8_dashboard.components.river_form import render_add_river_form
except ModuleNotFoundError:
    from components.river_form import render_add_river_form


def render_page() -> None:
    st.title("➕ Add River Centerline")
    st.caption("Trace and register river centerlines locally as GeoJSON LineStrings")
    render_add_river_form()


render_page()
