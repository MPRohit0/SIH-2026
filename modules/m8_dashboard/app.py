"""Entry point for the local-only M8 dashboard skeleton."""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="SIH26161 Dashboard",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

home_page = st.Page("pages/1_Home.py", title="Home", icon="🏠", default=True)
add_site_page = st.Page("pages/2_Add_Site.py", title="Add Site", icon="➕")
site_dashboard_page = st.Page("pages/3_Site_Dashboard.py", title="Site Dashboard", icon="📊")

nav = st.navigation({"Navigation": [home_page, add_site_page, site_dashboard_page]})
nav.run()
