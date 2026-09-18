"""Smoke tests for the local dashboard API client."""

from modules.m8_dashboard.services.api_client import (
    get_flood_response,
    get_historical_observation_bundle,
    get_historical_validation_response,
    get_job_status,
    create_scenario_query_request,
    create_scenario_resolve_request,
    get_site_onboarding_request,
    query_impact,
    query_historical_validation,
    query_flood,
    query_satellite_overlay,
    submit_site_onboarding,
)
from modules.m8_dashboard.components.map import _mock_artifact_path, _read_geojson_artifact


def test_mock_io_reads_expected_payloads():
    site = get_site_onboarding_request()
    flood = get_flood_response()
    history = get_historical_validation_response()
    job = get_job_status()

    assert site["site"]["site_id"] == "himalayan_demo_01"
    assert flood["scenario_id"] == "demo_dam_s60_froehlich_v1"
    assert history["results"]
    assert job["job_type"] == "onboard_site"


def test_valid_onboarding_submission_returns_job():
    submission = submit_site_onboarding(get_site_onboarding_request())

    assert submission["status"] == "ok"
    assert submission["job_id"] == "job_demo_onboard_001"
    assert submission["request"]["site"]["name"] == "Himalayan Demo Site"


def test_running_job_response():
    job = get_job_status(state="running")

    assert job["status"] == "ok"
    assert job["state"] == "running"
    assert job["progress_pct"] == 62.0


def test_successful_job_response():
    job = get_job_status(state="succeeded")

    assert job["status"] == "ok"
    assert job["state"] == "succeeded"
    assert job["progress_pct"] == 100.0


def test_flood_query_returns_existing_mock_metrics_and_confidence():
    request = create_scenario_query_request(
        "himalayan_demo_01", "severity_slider", 6, None, ["delft3d"]
    )
    response = query_flood("himalayan_demo_01", request)
    result = response["results"]["delft3d"]

    assert response["status"] == "ok"
    assert result["peak_discharge_m3s"] == 9400.0
    assert result["max_depth_m"] == 6.2
    assert result["max_velocity_ms"] == 4.8
    assert result["arrival_time"]["available"] is True
    assert result["confidence"]["overall"] == "HIGH"


def test_flood_query_uses_contract_error_for_unknown_scenario():
    response = query_flood(
        "himalayan_demo_01",
        {"schema_version": "1.0.0", "scenario_id": "unknown", "models": ["delft3d"]},
    )

    assert response["status"] == "error"
    assert response["error"]["error_code"] == "scenario_not_found"


def test_slider_input_flow_creates_existing_resolve_request():
    request = create_scenario_resolve_request(
        "himalayan_demo_01", "severity_slider", 6, None
    )

    assert request["input_mode"] == "severity_slider"
    assert request["severity_level_0_10"] == 6
    assert request["exact_values"] is None


def test_exact_input_flow_creates_existing_resolve_request():
    exact_values = {
        "initial_water_level_m": 2468.5,
        "breach_width_m": 52.3,
        "breach_depth_m": 21.1,
        "formation_time_hr": 0.6,
        "downstream_discharge_m3s": 700.0,
    }
    request = create_scenario_resolve_request(
        "himalayan_demo_01", "exact_values", None, exact_values
    )

    assert request["input_mode"] == "exact_values"
    assert request["severity_level_0_10"] is None
    assert request["exact_values"] == exact_values


def test_exact_input_flow_creates_query_request():
    request = create_scenario_query_request(
        "himalayan_demo_01", "exact_values", None, {
            "initial_water_level_m": 2468.5,
            "breach_width_m": 52.3,
            "breach_depth_m": 21.1,
            "formation_time_hr": 0.6,
            "downstream_discharge_m3s": 700.0,
        }, ["sph", "delft3d"]
    )

    assert request["scenario_id"] == "demo_dam_exact_001"
    assert request["models"] == ["sph", "delft3d"]


def test_partial_flood_query_preserves_unavailable_model():
    request = {
        "schema_version": "1.0.0",
        "scenario_id": "demo_dam_s60_froehlich_v1",
        "models": ["sph", "delft3d"],
    }
    response = query_flood(
        "himalayan_demo_01",
        request,
        response_fixture="17_flood_query_response_partial.json",
    )

    assert response["status"] == "partial"
    assert response["results"]["sph"] is None
    assert response["results"]["delft3d"] is not None


def test_mock_geojson_artifact_is_resolved_and_read():
    response = get_flood_response()
    artifact = response["results"]["delft3d"]["max_extent"]

    path = _mock_artifact_path(artifact["url"])
    geojson = _read_geojson_artifact(artifact)

    assert path is not None
    assert path.is_file()
    assert geojson["type"] == "FeatureCollection"
    assert geojson["features"]


def test_flood_result_exposes_supported_raster_artifacts():
    result = get_flood_response()["results"]["delft3d"]

    assert result["timesteps"][-1]["depth"]["kind"] == "raster"
    assert result["timesteps"][-1]["velocity"]["kind"] == "raster"
    assert result["arrival_time"]["kind"] == "raster"


def test_impact_query_returns_existing_mock_metrics_and_exports():
    response = query_impact(
        "himalayan_demo_01",
        "demo_dam_s60_froehlich_v1",
        "delft3d",
    )

    assert response["status"] == "ok"
    assert response["affected_population"] == 31284
    assert response["affected_buildings"] == 4128
    assert response["affected_roads_km"] == 83.2
    assert response["exports"]["shp"]["available"] is True
    assert response["exports"]["kml"]["available"] is True


def test_impact_query_uses_contract_error_for_wrong_model():
    response = query_impact(
        "himalayan_demo_01",
        "demo_dam_s60_froehlich_v1",
        "sph",
    )

    assert response["status"] == "error"
    assert response["error"]["error_code"] == "upstream_flood_data_unavailable"


def test_live_satellite_observation_response():
    response = query_satellite_overlay("demo_dam_01", "latest")

    assert response["status"] == "ok"
    assert response["is_fallback"] is False
    assert response["source"] == "sentinel1_sar"
    assert response["overlay"]["available"] is True


def test_fallback_satellite_observation_response():
    response = query_satellite_overlay("demo_dam_01", "fallback")

    assert response["status"] == "partial"
    assert response["is_fallback"] is True
    assert response["fallback_reason"] == "gee_unreachable"
    assert response["overlay"]["available"] is True


def test_historical_validation_response_contains_supported_metrics_and_observations():
    bundle = get_historical_observation_bundle()
    response = query_historical_validation(
        bundle["failure_source_id"],
        bundle["event_id"],
        "delft3d",
    )
    result = response["results"][0]

    assert response["status"] == "ok"
    assert result["metrics"]["flood_extent_iou"] == 0.84
    assert result["metric_availability"]["nse"] == "computed"
    assert result["observations"]["extent"]["available"] is True
    assert result["observations"]["arrival_time_points"]


def test_historical_validation_returns_no_result_for_unsupported_event():
    response = query_historical_validation("demo_dam_01", "unknown_event", "delft3d")

    assert response["status"] == "ok"
    assert response["results"] == []
