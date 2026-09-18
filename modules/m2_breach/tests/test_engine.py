import pytest

from modules.m2_breach.src.engine import BreachEngineError, run_breach_engine


@pytest.fixture
def failure_source():
    return {
        "failure_source_id": "demo_dam_01",
        "type": "engineered_dam",
        "name": "Demo Dam",
        "location": {"lon": 84.2, "lat": 28.1},
        "height_m": 20.0,
        "storage_volume_m3": 1_200_000.0,
        "catchment_area_km2": 120.0,
        "data_source": "mock",
    }


@pytest.fixture
def scenario():
    return {
        "schema_version": "1.0.0",
        "scenario_id": "demo_dam_s60_froehlich_v1",
        "site_id": "himalayan_demo_01",
        "failure_source_id": "demo_dam_01",
        "severity_index": 60,
        "severity_level_0_10": 6,
        "initial_conditions": {
            "initial_water_level_m": 2470.0,
            "downstream_discharge_m3s": 850.0,
        },
        "breach": {
            "breach_width_m": 45.2,
            "breach_depth_m": 18.6,
            "formation_time_hr": 0.8,
            "peak_discharge_m3s": None,
            "method": "froehlich",
            "peak_discharge_provenance": {
                "source": "unavailable",
                "method_version": None,
                "input_basis": None,
            },
        },
        "discharge_series_id": None,
        "breach_engine_version": "demo-1.0.0",
        "generated_at": "2026-09-18T16:05:00Z",
    }


def macdonald_inputs(*, relationship="best_fit"):
    return {
        "material_classification": "earthfill",
        "V_out_m3": 2_500_000.0,
        "h_w_m": 12.0,
        "Vw_m3": 1_200_000.0,
        "hw_m": 15.0,
        "crest_width_C_m": 8.0,
        "upstream_slope_Z1": 2.5,
        "downstream_slope_Z2": 2.0,
        "peak_discharge_relationship": relationship,
    }


def test_froehlich_only_preserves_identity_and_provenance(failure_source, scenario):
    result = run_breach_engine(
        failure_source=failure_source,
        scenario=scenario,
        methods="froehlich",
        failure_mechanism="overtopping",
    )

    assert result["scenario_id"] == scenario["scenario_id"]
    assert result["site_id"] == scenario["site_id"]
    assert result["failure_source_id"] == failure_source["failure_source_id"]
    assert len(result["results"]) == 1
    outcome = result["results"][0]
    assert outcome["method"] == "froehlich"
    assert outcome["status"] == "ok"
    assert outcome["breach_parameters"]["peak_discharge_m3s"] is None
    assert outcome["breach_parameters"]["peak_discharge_provenance"]["source"] == "unavailable"


def test_macdonald_only_succeeds_with_explicit_inputs(failure_source, scenario):
    result = run_breach_engine(
        failure_source=failure_source,
        scenario={
            **scenario,
            "breach": {**scenario["breach"], "method": "macdonald_langridge_monopolis"},
            "macdonald_inputs": macdonald_inputs(),
        },
        methods="macdonald_langridge_monopolis",
    )
    assert result["status"] == "ok"
    assert result["results"][0]["status"] == "ok"
    assert result["results"][0]["breach_parameters"]["method"] == "macdonald_langridge_monopolis"


def test_macdonald_envelope_selection_is_preserved(failure_source, scenario):
    result = run_breach_engine(
        failure_source=failure_source,
        scenario={
            **scenario,
            "breach": {
                **scenario["breach"],
                "method": "macdonald_langridge_monopolis",
            },
            "macdonald_inputs": macdonald_inputs(relationship="envelope"),
        },
        methods="macdonald_langridge_monopolis",
    )
    outcome = result["results"][0]
    assert outcome["status"] == "ok"
    assert (
        outcome["breach_parameters"]["peak_discharge_provenance"]["method_version"]
        == "macdonald_1984_envelope"
    )


def test_both_methods_succeed_independently(failure_source, scenario):
    scenario_with_inputs = {**scenario, "macdonald_inputs": macdonald_inputs()}
    result = run_breach_engine(
        failure_source=failure_source,
        scenario=scenario_with_inputs,
        methods=["froehlich", "macdonald_langridge_monopolis"],
        failure_mechanism="piping",
    )
    assert result["status"] == "ok"
    assert result["results"][0]["status"] == "ok"
    assert result["results"][1]["status"] == "ok"
    assert result["results"][0]["breach_parameters"]["method"] == "froehlich"
    assert (
        result["results"][1]["breach_parameters"]["method"]
        == "macdonald_langridge_monopolis"
    )
    assert result["results"][0]["breach_parameters"] != result["results"][1]["breach_parameters"]


def test_froehlich_success_macdonald_missing_inputs_preserves_success(
    failure_source, scenario
):
    result = run_breach_engine(
        failure_source=failure_source,
        scenario=scenario,
        methods=["froehlich", "macdonald_langridge_monopolis"],
        failure_mechanism="overtopping",
    )
    assert result["status"] == "partial"
    assert result["results"][0]["status"] == "ok"
    assert result["results"][1]["status"] == "error"
    assert result["results"][0]["breach_parameters"]["method"] == "froehlich"
    assert result["results"][1]["breach_parameters"] is None


def test_froehlich_failure_macdonald_success_preserves_success(
    failure_source, scenario
):
    macdonald_scenario = {
        **scenario,
        "breach": {
            **scenario["breach"],
            "method": "macdonald_langridge_monopolis",
        },
        "macdonald_inputs": macdonald_inputs(),
    }
    result = run_breach_engine(
        failure_source=failure_source,
        scenario=macdonald_scenario,
        methods=["froehlich", "macdonald_langridge_monopolis"],
    )
    assert result["status"] == "partial"
    assert result["results"][0]["status"] == "error"
    assert result["results"][1]["status"] == "ok"
    assert result["results"][0]["breach_parameters"] is None
    assert (
        result["results"][1]["breach_parameters"]["method"]
        == "macdonald_langridge_monopolis"
    )


def test_both_methods_fail_preserves_both_structured_errors(failure_source, scenario):
    invalid_macdonald_inputs = {
        **macdonald_inputs(),
        "V_out_m3": 250_000.0,
    }
    failing_scenario = {
        **scenario,
        "breach": {
            **scenario["breach"],
            "method": "macdonald_langridge_monopolis",
        },
        "macdonald_inputs": invalid_macdonald_inputs,
    }
    result = run_breach_engine(
        failure_source=failure_source,
        scenario=failing_scenario,
        methods=["froehlich", "macdonald_langridge_monopolis"],
    )
    assert result["status"] == "partial"
    assert [item["status"] for item in result["results"]] == ["error", "error"]
    assert result["results"][0]["error"]["code"] == "breach_formula_failed"
    assert result["results"][1]["error"]["code"] == "breach_formula_failed"


def test_multi_method_provenance_remains_method_specific(failure_source, scenario):
    result = run_breach_engine(
        failure_source=failure_source,
        scenario={**scenario, "macdonald_inputs": macdonald_inputs()},
        methods=["froehlich", "macdonald_langridge_monopolis"],
        failure_mechanism="overtopping",
    )
    froehlich = result["results"][0]["breach_parameters"]
    macdonald = result["results"][1]["breach_parameters"]
    assert froehlich["method"] == "froehlich"
    assert froehlich["peak_discharge_provenance"]["source"] == "unavailable"
    assert macdonald["method"] == "macdonald_langridge_monopolis"
    assert (
        macdonald["peak_discharge_provenance"]["source"]
        == "macdonald_langridge_monopolis"
    )


def test_missing_required_method_input_is_rejected(failure_source, scenario):
    result = run_breach_engine(
        failure_source=failure_source,
        scenario=scenario,
        methods="froehlich",
    )
    assert result["status"] == "partial"
    assert result["results"][0]["status"] == "error"
    assert "failure_mechanism" in result["results"][0]["error"]["message"]


def test_selected_method_must_match_scenario_method(failure_source, scenario):
    with pytest.raises(BreachEngineError, match="must match"):
        run_breach_engine(
            failure_source=failure_source,
            scenario=scenario,
            methods="macdonald_langridge_monopolis",
            failure_mechanism="piping",
        )


def test_invalid_failure_source_is_rejected(scenario):
    with pytest.raises(BreachEngineError, match="missing required fields"):
        run_breach_engine(
            failure_source={"failure_source_id": "demo_dam_01"},
            scenario=scenario,
            methods="froehlich",
            failure_mechanism="overtopping",
        )


def test_scenario_and_failure_source_ids_must_match(failure_source, scenario):
    mismatched = dict(scenario)
    mismatched["failure_source_id"] = "other_source"
    with pytest.raises(BreachEngineError, match="does not match"):
        run_breach_engine(
            failure_source=failure_source,
            scenario=mismatched,
            methods="froehlich",
            failure_mechanism="overtopping",
        )
