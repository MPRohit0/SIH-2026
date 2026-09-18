import pytest

from modules.m2_breach.src.scenario_builder import (
    ScenarioBuildError,
    build_exact_scenario,
    build_severity_scenario,
    resolve_scenario_request,
)


@pytest.fixture
def slider_request():
    return {
        "schema_version": "1.0.0",
        "site_id": "himalayan_demo_01",
        "input_mode": "severity_slider",
        "severity_level_0_10": 6,
        "exact_values": None,
    }


@pytest.fixture
def exact_request():
    return {
        "schema_version": "1.0.0",
        "site_id": "himalayan_demo_01",
        "input_mode": "exact_values",
        "severity_level_0_10": None,
        "exact_values": {
            "initial_water_level_m": 2468.5,
            "breach_width_m": 52.3,
            "breach_depth_m": 21.1,
            "formation_time_hr": 0.6,
            "downstream_discharge_m3s": 700.0,
        },
    }


def test_build_slider_scenario_uses_contract_severity_semantics():
    scenario = build_severity_scenario(
        site_id="himalayan_demo_01",
        failure_source_id="demo_dam_01",
        severity_level_0_10=6,
        initial_water_level_m=2470.0,
        downstream_discharge_m3s=850.0,
        breach_width_m=45.2,
        breach_depth_m=18.6,
        formation_time_hr=0.8,
        peak_discharge_m3s=9400.0,
        discharge_series_id="hydro_demo_s60_froehlich",
        method="froehlich",
    )

    assert scenario["severity_index"] == 60
    assert scenario["severity_level_0_10"] == 6
    assert scenario["site_id"] == "himalayan_demo_01"
    assert scenario["breach"]["method"] == "froehlich"


def test_build_exact_scenario_preserves_exact_physical_values():
    scenario = build_exact_scenario(
        site_id="himalayan_demo_01",
        failure_source_id="demo_dam_01",
        exact_values={
            "initial_water_level_m": 2468.5,
            "breach_width_m": 52.3,
            "breach_depth_m": 21.1,
            "formation_time_hr": 0.6,
            "downstream_discharge_m3s": 700.0,
        },
        method="froehlich",
    )

    assert scenario["severity_level_0_10"] is None
    assert scenario["initial_conditions"]["initial_water_level_m"] == 2468.5
    assert scenario["breach"]["breach_width_m"] == 52.3
    assert scenario["breach"]["breach_depth_m"] == 21.1
    assert scenario["breach"]["formation_time_hr"] == 0.6


def test_boundary_severity_level_0_10_is_valid():
    scenario = build_severity_scenario(
        site_id="himalayan_demo_01",
        failure_source_id="demo_dam_01",
        severity_level_0_10=10,
        initial_water_level_m=2500.0,
        downstream_discharge_m3s=1000.0,
        breach_width_m=10.0,
        breach_depth_m=12.0,
        formation_time_hr=1.0,
        peak_discharge_m3s=5000.0,
    )
    assert scenario["severity_index"] == 100
    assert scenario["severity_level_0_10"] == 10


def test_invalid_severity_raises():
    with pytest.raises(ScenarioBuildError, match="severity_level_0_10"):
        build_severity_scenario(
            site_id="himalayan_demo_01",
            failure_source_id="demo_dam_01",
            severity_level_0_10=11,
            initial_water_level_m=2470.0,
            downstream_discharge_m3s=850.0,
            breach_width_m=45.2,
            breach_depth_m=18.6,
            formation_time_hr=0.8,
            peak_discharge_m3s=9400.0,
        )


def test_non_integral_severity_is_rejected():
    with pytest.raises(ScenarioBuildError, match="severity_level_0_10"):
        build_severity_scenario(
            site_id="himalayan_demo_01",
            failure_source_id="demo_dam_01",
            severity_level_0_10=6.5,
            initial_water_level_m=2470.0,
            downstream_discharge_m3s=850.0,
            breach_width_m=45.2,
            breach_depth_m=18.6,
            formation_time_hr=0.8,
        )


def test_scenario_id_is_deterministic_and_excludes_generated_at():
    scenario_a = build_severity_scenario(
        site_id="himalayan_demo_01",
        failure_source_id="demo_dam_01",
        severity_level_0_10=6,
        initial_water_level_m=2470.0,
        downstream_discharge_m3s=850.0,
        breach_width_m=45.2,
        breach_depth_m=18.6,
        formation_time_hr=0.8,
        peak_discharge_m3s=9400.0,
        discharge_series_id="hydro_demo_s60_froehlich",
        generated_at="2026-09-18T16:05:00Z",
    )
    scenario_b = build_severity_scenario(
        site_id="himalayan_demo_01",
        failure_source_id="demo_dam_01",
        severity_level_0_10=6,
        initial_water_level_m=2470.0,
        downstream_discharge_m3s=850.0,
        breach_width_m=45.2,
        breach_depth_m=18.6,
        formation_time_hr=0.8,
        peak_discharge_m3s=9400.0,
        discharge_series_id="hydro_demo_s60_froehlich",
        generated_at="2026-09-18T16:50:00Z",
    )

    assert scenario_a["scenario_id"] == scenario_b["scenario_id"]


def test_resolve_request_slider_requires_catalog_resolved_physical_values(slider_request):
    result = resolve_scenario_request(
        request=slider_request,
        site_id="himalayan_demo_01",
        failure_source_id="demo_dam_01",
    )
    assert result["status"] == "error"
    assert result["error"]["code"] == "insufficient_exact_inputs"


@pytest.mark.parametrize("level", [0, 10])
def test_slider_catalog_preserves_boundary_severity(level):
    result = resolve_scenario_request(
        request={
            "input_mode": "severity_slider",
            "severity_level_0_10": level,
            "exact_values": None,
        },
        site_id="himalayan_demo_01",
        failure_source_id="demo_dam_01",
        scenario_catalog={
            str(level * 10): {
                "initial_water_level_m": 2470.0,
                "downstream_discharge_m3s": 850.0,
                "breach_width_m": 45.2,
                "breach_depth_m": 18.6,
                "formation_time_hr": 0.8,
            }
        },
    )
    assert result["severity_index"] == level * 10
    assert result["severity_level_0_10"] == level


def test_slider_catalog_missing_field_returns_contract_error(slider_request):
    result = resolve_scenario_request(
        request=slider_request,
        site_id="himalayan_demo_01",
        failure_source_id="demo_dam_01",
        scenario_catalog={"60": {"breach_width_m": 45.2}},
    )
    assert result["status"] == "error"
    assert "breach_depth_m" in result["error"]["details"]["required_fields"]


def test_method_identity_changes_content_addressed_id():
    values = {
        "initial_water_level_m": 2468.5,
        "breach_width_m": 52.3,
        "breach_depth_m": 21.1,
        "formation_time_hr": 0.6,
        "downstream_discharge_m3s": 700.0,
    }
    froehlich = build_exact_scenario(
        site_id="himalayan_demo_01",
        failure_source_id="demo_dam_01",
        exact_values=values,
        method="froehlich",
    )
    macdonald = build_exact_scenario(
        site_id="himalayan_demo_01",
        failure_source_id="demo_dam_01",
        exact_values=values,
        method="macdonald_langridge_monopolis",
    )
    assert froehlich["scenario_id"] != macdonald["scenario_id"]


def test_exact_mode_rejects_unsupported_peak_input(exact_request):
    request = dict(exact_request)
    request["peak_discharge_m3s"] = 1000.0
    with pytest.raises(ScenarioBuildError, match="Unsupported exact-mode"):
        resolve_scenario_request(
            request=request,
            site_id="himalayan_demo_01",
            failure_source_id="demo_dam_01",
        )


def test_resolve_request_exact_mode_preserves_exact_inputs(exact_request):
    scenario = resolve_scenario_request(
        request=exact_request,
        site_id="himalayan_demo_01",
        failure_source_id="demo_dam_01",
    )

    assert scenario["severity_level_0_10"] is None
    assert scenario["severity_index"] is None
    assert scenario["breach"]["peak_discharge_m3s"] is None
    assert scenario["discharge_series_id"] is None
    assert scenario["initial_conditions"]["initial_water_level_m"] == 2468.5
    assert scenario["breach"]["breach_width_m"] == 52.3
    assert scenario["breach"]["breach_depth_m"] == 21.1
