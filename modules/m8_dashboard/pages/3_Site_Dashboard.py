"""Site dashboard skeleton backed by the M0 flood-query boundary."""

from __future__ import annotations

import streamlit as st

from components.map import render_flood_result_map, render_historical_validation_map
from services.api_client import (
    create_scenario_query_request,
    create_scenario_resolve_request,
    get_scenario_resolve_request,
    get_historical_observation_bundle,
    get_sites_response,
    query_historical_validation,
    query_impact,
    query_flood,
    query_satellite_overlay,
)


def render_site_dashboard_page() -> None:
    sites_response = get_sites_response()
    sites = sites_response.get("sites", [])
    if not sites:
        st.title("Site dashboard")
        st.info("No site is available.")
        return

    site_ids = [site.get("site_id") for site in sites]
    selected_id = st.session_state.get("selected_site_id", site_ids[0])
    selected_index = site_ids.index(selected_id) if selected_id in site_ids else 0
    selected_id = st.selectbox("Selected site", site_ids, index=selected_index)
    st.session_state["selected_site_id"] = selected_id
    site = next(site for site in sites if site.get("site_id") == selected_id)

    st.title(site.get("name", selected_id))
    location = site.get("location", {})
    st.write(f"Location: ({location.get('lon')}, {location.get('lat')})")
    st.write(f"Readiness: {site.get('readiness', 'unknown')}")
    st.write(f"Status: {site.get('status', 'unknown')}")

    st.subheader("Flood simulation controls")
    input_mode = st.radio(
        "Scenario input mode",
        ["severity_slider", "exact_values"],
        format_func=lambda value: "Severity slider" if value == "severity_slider" else "Exact physical parameters",
    )
    request_fixture = get_scenario_resolve_request(
        "exact" if input_mode == "exact_values" else "slider"
    )
    severity_level = None
    exact_values = None
    if input_mode == "severity_slider":
        severity_level = st.slider("Severity level", min_value=0, max_value=10, value=6)
    else:
        exact_values = {
            "initial_water_level_m": st.number_input(
                "Initial water level (m)",
                value=float(request_fixture["exact_values"]["initial_water_level_m"]),
            ),
            "breach_width_m": st.number_input(
                "Breach width (m)",
                value=float(request_fixture["exact_values"]["breach_width_m"]),
            ),
            "breach_depth_m": st.number_input(
                "Breach depth (m)",
                value=float(request_fixture["exact_values"]["breach_depth_m"]),
            ),
            "formation_time_hr": st.number_input(
                "Formation time (hr)",
                value=float(request_fixture["exact_values"]["formation_time_hr"]),
            ),
            "downstream_discharge_m3s": st.number_input(
                "Downstream discharge (m³/s)",
                value=float(request_fixture["exact_values"]["downstream_discharge_m3s"]),
            ),
        }
    models = st.multiselect("Models", ["sph", "delft3d"], default=["sph", "delft3d"])
    simulate = st.button("Simulate", type="primary")

    if simulate:
        scenario_query_request = create_scenario_query_request(
            selected_id,
            input_mode,
            severity_level,
            exact_values,
            models,
        )
        st.session_state["scenario_resolve_request"] = create_scenario_resolve_request(
            selected_id,
            input_mode,
            severity_level,
            exact_values,
        )
        st.session_state["scenario_query_request"] = scenario_query_request
        st.session_state["flood_response"] = query_flood(
            selected_id,
            scenario_query_request,
        )

    response = st.session_state.get("flood_response")
    if not response:
        st.info("Choose a scenario and model, then select Simulate.")
        return
    st.subheader("Requested scenario")
    st.json(st.session_state.get("scenario_resolve_request", {}))
    st.json(st.session_state.get("scenario_query_request", {}))
    if response.get("status") == "error":
        st.error(response.get("error", {}).get("message", "Flood query failed."))
        return

    results = response.get("results", {})
    if response.get("status") == "partial":
        st.warning("The requested scenario returned partial simulation data.")
        for warning in response.get("warnings", []):
            st.write(warning.get("message", "Unavailable output"))
    model = next((name for name in models if results.get(name)), None)
    if not model:
        st.warning("No selected model result is available.")
        return
    result = results[model]

    st.subheader("Simulation metrics")
    st.caption(f"Returned simulation data: {model} / {response.get('scenario_id')}")
    metric_columns = st.columns(4)
    metric_columns[0].metric("Peak discharge", f"{result.get('peak_discharge_m3s')} m³/s")
    metric_columns[1].metric("Maximum flood depth", f"{result.get('max_depth_m')} m")
    metric_columns[2].metric("Maximum velocity", f"{result.get('max_velocity_ms')} m/s")
    arrival = result.get("arrival_time")
    metric_columns[3].metric(
        "Arrival time",
        "Available" if arrival and arrival.get("available") else "Unavailable",
    )

    st.subheader("Flood map")
    bbox = location.get("bbox_wgs84")
    if bbox:
        render_flood_result_map(
            site_location={"lon": location.get("lon"), "lat": location.get("lat")},
            site_bbox_wgs84=bbox,
            flood_result=result,
        )
    st.write("Maximum extent artifact")
    st.json(result.get("max_extent"))
    st.write("Arrival-time artifact")
    st.json(arrival)

    unavailable = [name for name, value in results.items() if value is None]
    if unavailable:
        st.subheader("Unavailable outputs")
        for name in unavailable:
            st.warning(f"{name} simulation output is unavailable.")

    confidence = result.get("confidence")
    if confidence:
        st.subheader("Confidence and validation")
        st.write(f"Overall confidence: {confidence.get('overall')}")
        st.json(confidence)

    st.subheader("Impact Analysis")
    st.caption("Impact results are returned by M0/M6; M8 does not calculate them.")
    if st.button("Run Impact Analysis", type="secondary"):
        st.session_state["impact_response"] = query_impact(
            selected_id,
            response.get("scenario_id"),
            model,
        )

    impact = st.session_state.get("impact_response")
    if impact:
        if impact.get("status") == "error":
            st.error(impact.get("error", {}).get("message", "Impact query failed."))
        else:
            st.caption(
                f"Returned impact data: {impact.get('scenario_id')} / {impact.get('model')}"
            )
            impact_columns = st.columns(4)
            impact_columns[0].metric(
                "Affected population",
                str(impact.get("affected_population"))
                if impact.get("population_data_availability") == "computed"
                else "Unavailable",
            )
            impact_columns[1].metric(
                "Affected buildings",
                str(impact.get("affected_buildings"))
                if impact.get("buildings_data_availability") == "computed"
                else "Unavailable",
            )
            impact_columns[2].metric(
                "Affected roads",
                f"{impact.get('affected_roads_km')} km"
                if impact.get("roads_data_availability") == "computed"
                else "Unavailable",
            )
            impact_columns[3].metric(
                "Affected agriculture",
                f"{impact.get('affected_agriculture_km2')} km²"
                if impact.get("agriculture_data_availability") == "computed"
                else "Unavailable",
            )

            st.write(
                "Critical infrastructure",
                impact.get("critical_infrastructure", [])
                if impact.get("critical_infrastructure_data_availability") == "computed"
                else "Unavailable",
            )
            exports = impact.get("exports", {})
            export_columns = st.columns(3)
            for column, label in zip(export_columns, ["SHP export", "KML export", "GeoJSON export"]):
                key = {"SHP export": "shp", "KML export": "kml", "GeoJSON export": "geojson"}[label]
                artifact = exports.get(key)
                if artifact and artifact.get("available") and artifact.get("url"):
                    column.link_button(label, artifact["url"])

    st.subheader("Satellite / Observation")
    st.caption("Satellite observations are returned by M0/M7; M8 does not call GEE or analyze imagery.")
    observation_mode = st.radio(
        "Observation source",
        ["latest", "fallback"],
        format_func=lambda value: "Current/live observation" if value == "latest" else "Fallback/static observation",
        horizontal=True,
    )
    if st.button("Load Observation"):
        st.session_state["satellite_response"] = query_satellite_overlay(
            site.get("failure_source_id"),
            observation_mode,
        )

    satellite = st.session_state.get("satellite_response")
    if satellite:
        if satellite.get("status") == "error":
            st.error(satellite.get("error", {}).get("message", "Observation query failed."))
        else:
            is_fallback = satellite.get("is_fallback", False)
            if is_fallback:
                st.warning("Displayed observation is FALLBACK/STATIC.")
            else:
                st.success("Displayed observation is LIVE.")
            st.write(f"Status: {satellite.get('status')}")
            st.write(f"Observation date: {satellite.get('observation_date')}")
            st.write(f"Source: {satellite.get('source')}")
            st.write(f"Fetched at: {satellite.get('fetched_at')}")
            if satellite.get("fallback_reason"):
                st.write(f"Fallback reason: {satellite.get('fallback_reason')}")
            overlay = satellite.get("overlay")
            if overlay and overlay.get("available") and overlay.get("url"):
                st.link_button("Open observation overlay", overlay["url"])

    st.subheader("Historical Validation")
    st.caption("Comparison results are returned by M0; M8 does not calculate validation metrics.")
    historical_bundle = get_historical_observation_bundle()
    historical_event_id = historical_bundle.get("event_id")
    historical_event_date = historical_bundle.get("historical_event_date")
    st.selectbox(
        "Historical event",
        [historical_event_id],
        format_func=lambda _: f"{historical_event_id} ({historical_event_date})",
    )
    validation_model = st.selectbox(
        "Validation model",
        ["delft3d"],
        index=0,
    )
    if st.button("Request historical comparison"):
        st.session_state["historical_validation_response"] = query_historical_validation(
            site.get("failure_source_id"),
            historical_event_id,
            validation_model,
        )

    historical_response = st.session_state.get("historical_validation_response")
    if historical_response:
        validation_results = historical_response.get("results", [])
        if not validation_results:
            st.info("No historical validation result is available for the selected event and model.")
        else:
            validation_result = validation_results[0]
            st.write(
                f"Model result: {validation_result.get('model')} "
                f"({validation_result.get('validation_id')})"
            )
            st.write(
                f"Observed historical data: {validation_result.get('event_id')} "
                f"({validation_result.get('historical_event_date')})"
            )
            st.subheader("Comparison / validation metrics")
            metrics = validation_result.get("metrics", {})
            availability = validation_result.get("metric_availability", {})
            metric_columns = st.columns(4)
            metric_names = [
                ("Flood extent IoU", "flood_extent_iou"),
                ("Flood extent F1", "flood_extent_f1"),
                ("Relative area error (%)", "relative_area_error_pct"),
                ("Arrival-time MAE (min)", "arrival_time_mae_min"),
                ("Peak discharge error (%)", "peak_discharge_error_pct"),
                ("NSE", "nse"),
                ("KGE", "kge"),
            ]
            for index, (label, key) in enumerate(metric_names):
                column = metric_columns[index % len(metric_columns)]
                value = metrics.get(key) if availability.get(key) == "computed" else "Unavailable"
                column.metric(label, value)

            observed_result = {
                "observations": validation_result.get("observations", {}),
            }
            st.subheader("Historical observation vs simulated result")
            render_historical_validation_map(
                site_location={"lon": location.get("lon"), "lat": location.get("lat")},
                site_bbox_wgs84=location.get("bbox_wgs84"),
                historical_result=observed_result,
                flood_result=result,
            )


if __name__ == "__main__":
    render_site_dashboard_page()
