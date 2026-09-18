"""Form helpers for the contract-defined site onboarding request."""

from __future__ import annotations

import streamlit as st

from services.api_client import get_job_status, submit_site_onboarding


def render_site_form() -> dict | None:
    """Collect and submit only fields from SiteOnboardingRequest."""
    with st.form("site_submission"):
        st.subheader("Onboard a site")

        site_id = st.text_input("Site ID", value="himalayan_demo_01")
        site_name = st.text_input("Site name", value="Himalayan Demo Site")
        min_lon = st.number_input("Min lon", value=79.72, step=0.01)
        min_lat = st.number_input("Min lat", value=30.50, step=0.01)
        max_lon = st.number_input("Max lon", value=79.90, step=0.01)
        max_lat = st.number_input("Max lat", value=30.65, step=0.01)

        failure_type = st.selectbox(
            "Failure source type",
            ["engineered_dam", "natural_lake_glof", "landslide_dam"],
        )
        failure_source_id = st.text_input("Failure source ID", value="demo_dam_01")
        source_name = st.text_input("Failure source name", value="Himalayan Demo Dam")
        source_lon = st.number_input("Failure source longitude", value=79.81, step=0.01)
        source_lat = st.number_input("Failure source latitude", value=30.58, step=0.01)
        height_m = st.number_input("Barrier height (m)", value=85.0, step=0.1)
        storage_volume_m3 = st.number_input("Storage volume (m³)", value=8500000.0, step=1000.0)
        catchment_area_km2 = st.number_input("Catchment area (km²)", value=125.0, step=1.0)
        data_source = st.text_input("Data source", value="synthetic_demo_dataset")
        severity_levels = st.multiselect(
            "Severity levels",
            options=[0, 20, 40, 60, 80, 100],
            default=[0, 20, 40, 60, 80, 100],
        )

        demo_mode = st.checkbox("Demo mode", value=True)
        submitted = st.form_submit_button("Submit to M0")

        if submitted:
            if not site_id.strip() or not site_name.strip() or len(severity_levels) < 2:
                st.error("Provide a site ID, site name, and at least two severity levels.")
                return None

            payload = {
                "schema_version": "1.0.0",
                "site": {
                    "site_id": site_id,
                    "name": site_name,
                    "bbox_wgs84": [min_lon, min_lat, max_lon, max_lat],
                },
                "failure_source": {
                    "schema_version": "1.0.0",
                    "failure_source_id": failure_source_id,
                    "type": failure_type,
                    "name": source_name,
                    "location": {"lon": source_lon, "lat": source_lat},
                    "height_m": height_m,
                    "storage_volume_m3": storage_volume_m3,
                    "catchment_area_km2": catchment_area_km2,
                    "data_source": data_source,
                },
                "severity_levels": sorted(severity_levels),
                "demo_mode": demo_mode,
            }
            submission = submit_site_onboarding(payload)
            st.session_state["onboarding_job_id"] = submission["job_id"]
            st.session_state["onboarding_request"] = payload
            return submission

    return None


def render_onboarding_lifecycle(job_id: str, state: str) -> None:
    """Display the mock job lifecycle without running any backend module."""
    job = get_job_status(job_id, state=state)
    st.subheader("Onboarding lifecycle")
    st.write("Submitted")
    st.write("↓")
    st.write("Processing")
    st.progress(int(job.get("progress_pct") or 0) / 100)
    st.caption(job.get("current_step") or "Waiting for processing")
    st.write("↓")
    if job["state"] == "succeeded":
        st.success("Completed / READY")
    else:
        st.info("Processing")
    st.json(job)
