"""Local-only API client for the dashboard skeleton.

This module intentionally reads mock JSON fixtures from the repository and exposes
lightweight functions that mimic the M0 API boundary. It does not access a
production database or perform live simulation calls.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
MOCK_JSON_DIR = REPO_ROOT / "data" / "mock" / "json"


def _read_json(filename: str) -> dict[str, Any]:
    path = MOCK_JSON_DIR / filename
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def get_site_onboarding_request() -> dict[str, Any]:
    return _read_json("13_scenario_onboarding_request.json")


def submit_site_onboarding(request: dict[str, Any]) -> dict[str, Any]:
    """Submit an onboarding request through the local M0 mock boundary."""
    return {
        "schema_version": "1.0.0",
        "status": "ok",
        "warnings": [],
        "error": None,
        "job_id": "job_demo_onboard_001",
        "request": request,
    }


def get_sites_response() -> dict[str, Any]:
    onboarding = get_site_onboarding_request()
    job = get_job_status()
    site = onboarding.get("site", {})
    failure_source = onboarding.get("failure_source", {})
    location = failure_source.get("location", {})
    bbox = site.get("bbox_wgs84", [0.0, 0.0, 0.0, 0.0])

    return {
        "schema_version": "1.0.0",
        "status": "ok",
        "warnings": [],
        "error": None,
        "sites": [{
            "site_id": site.get("site_id"),
            "name": site.get("name"),
            "location": {
                "bbox_wgs84": bbox,
                "lon": location.get("lon"),
                "lat": location.get("lat"),
            },
            "readiness": "ready" if job.get("state") == "succeeded" else job.get("state", "unknown"),
            "status": job.get("state", "unknown"),
            "failure_source_id": failure_source.get("failure_source_id"),
        }],
    }


def get_job_status(job_id: str = "job_demo_onboard_001", state: str = "succeeded") -> dict[str, Any]:
    if state == "running":
        return _read_json("14_job_status_running.json")
    return _read_json("15_job_status_succeeded.json")


def resolve_scenario(mode: str = "slider") -> dict[str, Any]:
    if mode == "exact":
        return _read_json("12_scenario_resolution_response_exact.json")
    return _read_json("12b_scenario_resolution_response_slider.json")


def get_scenario_resolve_request(mode: str) -> dict[str, Any]:
    mode = "exact" if mode in {"exact", "exact_values"} else "slider"
    filename = (
        "11_scenario_resolve_request_exact.json"
        if mode == "exact"
        else "10_scenario_resolve_request_slider.json"
    )
    return _read_json(filename)


def create_scenario_resolve_request(
    site_id: str,
    mode: str,
    severity_level_0_10: int | None,
    exact_values: dict[str, float] | None,
) -> dict[str, Any]:
    """Create the existing contract request for either scenario input mode."""
    request = get_scenario_resolve_request(mode)
    request["site_id"] = site_id
    request["severity_level_0_10"] = severity_level_0_10
    request["exact_values"] = exact_values
    return request


def create_scenario_query_request(
    site_id: str,
    mode: str,
    severity_level_0_10: int | None,
    exact_values: dict[str, float] | None,
    models: list[str],
) -> dict[str, Any]:
    """Create the canonical scenario query request sent to the M0 boundary."""
    resolved = resolve_scenario("exact" if mode == "exact_values" else mode)
    return {
        "schema_version": "1.0.0",
        "scenario_id": resolved["scenario"]["scenario_id"],
        "models": models,
    }


def get_flood_response() -> dict[str, Any]:
    return _read_json("16_flood_query_response_both.json")


def query_flood(
    site_id: str,
    scenario_query_request: dict[str, Any],
    response_fixture: str = "16_flood_query_response_both.json",
) -> dict[str, Any]:
    """Query the local M0 mock boundary using an existing response fixture."""
    response = _read_json(response_fixture)
    scenario_id = scenario_query_request.get("scenario_id")
    known_scenarios = {
        resolve_scenario("slider")["scenario"]["scenario_id"],
        resolve_scenario("exact")["scenario"]["scenario_id"],
    }
    if response.get("scenario_id") != scenario_id and scenario_id not in known_scenarios:
        return {
            "schema_version": "1.0.0",
            "status": "error",
            "warnings": [],
            "error": {
                "error_code": "scenario_not_found",
                "message": f"Scenario {scenario_id} is not available in the mock response.",
                "retryable": False,
                "details": None,
            },
        }

    models = scenario_query_request.get("models", [])
    response["results"] = {
        model: response.get("results", {}).get(model)
        for model in models
        if model in response.get("results", {})
    }
    return response


def get_impact_response() -> dict[str, Any]:
    return _read_json("18_impact_result.json")


def query_impact(
    site_id: str,
    scenario_id: str,
    model: str,
) -> dict[str, Any]:
    """Query the local M0 impact boundary using the existing mock response."""
    response = get_impact_response()
    if (
        response.get("scenario_id") != scenario_id
        or response.get("model") != model
    ):
        return {
            "schema_version": "1.0.0",
            "status": "error",
            "warnings": [],
            "error": {
                "error_code": "upstream_flood_data_unavailable",
                "message": "Impact data is unavailable for the requested scenario and model.",
                "retryable": False,
                "details": {"site_id": site_id, "scenario_id": scenario_id, "model": model},
            },
        }
    return response


def get_satellite_overlay(mode: str = "live") -> dict[str, Any]:
    if mode == "fallback":
        return _read_json("20_satellite_overlay_fallback.json")
    return _read_json("19_satellite_overlay_live.json")


def query_satellite_overlay(
    failure_source_id: str,
    mode: str = "latest",
) -> dict[str, Any]:
    """Query the local M0 satellite-observation boundary."""
    response = get_satellite_overlay("fallback" if mode == "fallback" else "live")
    if response.get("failure_source_id") != failure_source_id:
        return {
            "schema_version": "1.0.0",
            "status": "error",
            "warnings": [],
            "error": {
                "error_code": "no_observation_available",
                "message": "No satellite observation is available for this failure source.",
                "retryable": False,
                "details": {"failure_source_id": failure_source_id},
            },
        }
    return response


def get_historical_validation_response() -> dict[str, Any]:
    return _read_json("23_historical_validation_response.json")


def get_historical_observation_bundle() -> dict[str, Any]:
    return _read_json("21_historical_observation_bundle.json")


def query_historical_validation(
    failure_source_id: str,
    event_id: str,
    model: str,
) -> dict[str, Any]:
    """Query the local M0 historical-validation boundary."""
    response = get_historical_validation_response()
    results = [
        result for result in response.get("results", [])
        if (
            result.get("failure_source_id") == failure_source_id
            and result.get("event_id") == event_id
            and result.get("model") == model
        )
    ]
    return {
        **response,
        "results": results,
    }


def get_mock_route_map() -> dict[str, Any]:
    return _read_json("00_mock_route_map.json")
