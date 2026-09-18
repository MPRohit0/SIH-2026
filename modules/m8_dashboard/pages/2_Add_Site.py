"""Page for adding a new site through the M0 API boundary."""

from __future__ import annotations

import streamlit as st

from components.site_form import render_onboarding_lifecycle, render_site_form


def render_add_site_page() -> None:
    st.title("Add Site")
    st.caption("Submit the contract-defined onboarding request to M0.")
    submission = render_site_form()
    if submission:
        st.success(f"Submitted onboarding job {submission['job_id']}.")

    job_id = st.session_state.get("onboarding_job_id")
    if job_id:
        state = st.selectbox(
            "Mock lifecycle state",
            options=["running", "succeeded"],
            index=1,
            key="onboarding_mock_state",
        )
        render_onboarding_lifecycle(job_id, state)


if __name__ == "__main__":
    render_add_site_page()
