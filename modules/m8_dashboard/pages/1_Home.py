"""Home page for the SIH26161 dashboard demo."""

from __future__ import annotations

import streamlit as st

from services.api_client import get_sites_response


def render_home_page() -> None:
    st.title("SIH26161")
    st.caption("Flood simulation and dam-breach decision support for monitored sites")
    st.markdown(
        "Monitor site readiness, open a site, and move to site onboarding from a single local dashboard."
    )

    st.page_link("pages/2_Add_Site.py", label="Add Site", icon="➕")

    response = get_sites_response()
    sites = response.get("sites", [])

    if not sites:
        st.info("No sites available from the mock /sites response.")
        return

    st.subheader("Available sites")
    for site in sites:
        name = site.get("name", site.get("site_id", "Unnamed site"))
        site_id = site.get("site_id", "unknown")
        location = site.get("location", {})
        lon = location.get("lon")
        lat = location.get("lat")
        bbox = location.get("bbox_wgs84", [])
        status = site.get("status", "unknown")
        readiness = site.get("readiness", "unknown")

        with st.container():
            st.markdown(f"### {name}")
            st.write(f"Site ID: {site_id}")
            if lon is not None and lat is not None:
                st.write(f"Location: ({lon}, {lat})")
            if bbox:
                st.write(f"Bounding box: {bbox}")
            st.write(f"Status: {status}")
            st.write(f"Readiness: {readiness}")

            if st.button(f"Open {site_id}", key=f"open_{site_id}"):
                st.session_state["selected_site_id"] = site_id
                st.success(f"Opened site {site_id}")

            st.markdown("---")


if __name__ == "__main__":
    render_home_page()
