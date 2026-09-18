import pytest

from modules.m2_breach.src.pipeline import (
    PipelineError,
    build_scenario_bundles,
)


@pytest.fixture
def source():
    return {
        "failure_source_id": "demo_dam_01",
        "type": "engineered_dam",
        "name": "Demo Dam",
        "location": {"lon": 84.2, "lat": 28.1},
        "height_m": 30.0,
        "storage_volume_m3": 1_200_000.0,
        "catchment_area_km2": 120.0,
        "data_source": "mock",
    }


@pytest.fixture
def scenario_request():
    return {
        "schema_version": "1.0.0",
        "site_id": "himalayan_demo_01",
        "input_mode": "exact_values",
        "severity_level_0_10": None,
        "exact_values": {
            "initial_water_level_m": 2470.0,
            "breach_width_m": 45.2,
            "breach_depth_m": 18.6,
            "formation_time_hr": 0.8,
            "downstream_discharge_m3s": 850.0,
        },
    }


def test_pipeline_returns_contract_bundle_for_froehlich(source, scenario_request):
    bundles = build_scenario_bundles(
        failure_source=source,
        scenario_request=scenario_request,
        methods="froehlich",
        failure_mechanism="overtopping",
    )

    assert len(bundles) == 1
    bundle = bundles[0]
    scenario = bundle["scenario"]
    assert bundle["schema_version"] == "1.0.0"
    assert bundle["discharge_series"] is None
    assert scenario["site_id"] == scenario_request["site_id"]
    assert scenario["failure_source_id"] == source["failure_source_id"]
    assert scenario["breach"]["method"] == "froehlich"
    assert scenario["breach"]["peak_discharge_m3s"] is None
    assert scenario["breach"]["peak_discharge_provenance"]["source"] == "unavailable"


def test_pipeline_is_deterministic_except_generated_at(source, scenario_request):
    first = build_scenario_bundles(
        failure_source=source,
        scenario_request=scenario_request,
        methods="froehlich",
        failure_mechanism="piping",
    )[0]["scenario"]
    second = build_scenario_bundles(
        failure_source=source,
        scenario_request=scenario_request,
        methods="froehlich",
        failure_mechanism="piping",
    )[0]["scenario"]

    assert first["scenario_id"] == second["scenario_id"]
    assert first["breach"] == second["breach"]


def test_slider_requires_catalog(source):
    slider_request = {
        "schema_version": "1.0.0",
        "site_id": "himalayan_demo_01",
        "input_mode": "severity_slider",
        "severity_level_0_10": 6,
        "exact_values": None,
    }
    with pytest.raises(PipelineError) as error:
        build_scenario_bundles(
            failure_source=source,
            scenario_request=slider_request,
            methods="froehlich",
            failure_mechanism="overtopping",
        )
    assert error.value.code == "insufficient_exact_inputs"


def test_invalid_failure_source_is_rejected(scenario_request):
    with pytest.raises(PipelineError) as error:
        build_scenario_bundles(
            failure_source={"failure_source_id": "demo_dam_01"},
            scenario_request=scenario_request,
            methods="froehlich",
            failure_mechanism="overtopping",
        )
    assert error.value.code == "missing_failure_source_specs"


def test_macdonald_is_not_fabricated(source, scenario_request):
    with pytest.raises(PipelineError, match="macdonald_inputs is required"):
        build_scenario_bundles(
            failure_source=source,
            scenario_request=scenario_request,
            methods="macdonald_langridge_monopolis",
        )
