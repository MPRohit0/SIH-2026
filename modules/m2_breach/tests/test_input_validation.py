import pytest

from modules.m2_breach.src.input_validation import (
    ValidationError,
    validate_breach_parameters,
    validate_failure_source,
    validate_hydrograph,
    validate_physical_scenario,
    validate_scenario_bundle,
)


@pytest.fixture
def valid_failure_source():
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
def valid_hydrograph():
    return {
        "hydrograph_id": "hydro_demo_s60_froehlich",
        "points": [
            {"t_min": 0, "discharge_m3s": 0.0},
            {"t_min": 15, "discharge_m3s": 4200.0},
            {"t_min": 30, "discharge_m3s": 9400.0},
            {"t_min": 60, "discharge_m3s": 5100.0},
            {"t_min": 120, "discharge_m3s": 800.0},
            {"t_min": 180, "discharge_m3s": 250.0},
        ],
    }


@pytest.fixture
def valid_scenario(valid_failure_source, valid_hydrograph):
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
            "peak_discharge_m3s": 9400.0,
            "method": "froehlich",
            "peak_discharge_provenance": {
                "source": "hydraulic_solver",
                "method_version": None,
                "input_basis": None,
            },
        },
        "discharge_series_id": "hydro_demo_s60_froehlich",
        "breach_engine_version": "demo-1.0.0",
        "generated_at": "2026-09-18T16:05:00Z",
    }


def test_valid_failure_source_passes(valid_failure_source):
    result = validate_failure_source(valid_failure_source)
    assert result["failure_source_id"] == "demo_dam_01"
    assert result["type"] == "engineered_dam"


def test_valid_hydrograph_passes(valid_hydrograph):
    result = validate_hydrograph(valid_hydrograph)
    assert result["series_id"] == "hydro_demo_s60_froehlich"
    assert len(result["points"]) == 6


def test_valid_physical_scenario_passes(valid_scenario, valid_failure_source, valid_hydrograph):
    result = validate_physical_scenario(
        valid_scenario,
        failure_source=valid_failure_source,
        hydrograph=valid_hydrograph,
    )
    assert result["scenario_id"] == "demo_dam_s60_froehlich_v1"
    assert result["breach"]["method"] == "froehlich"
    assert result["severity_index"] == 60


def test_valid_bundle_passes(valid_failure_source, valid_scenario, valid_hydrograph):
    bundle = {
        "scenario": valid_scenario,
        "failure_source": valid_failure_source,
        "discharge_series": valid_hydrograph,
    }
    result = validate_scenario_bundle(bundle)
    assert result["scenario"]["scenario_id"] == "demo_dam_s60_froehlich_v1"
    assert result["discharge_series"]["series_id"] == "hydro_demo_s60_froehlich"


def test_missing_failure_source_fields_raises():
    bad = {
        "failure_source_id": "demo_dam_01",
        "type": "engineered_dam",
        "name": "Demo Dam",
    }
    with pytest.raises(ValidationError, match="missing required fields"):
        validate_failure_source(bad)


@pytest.mark.parametrize("field", ["height_m", "storage_volume_m3", "catchment_area_km2"])
def test_failure_source_rejects_zero_physical_values(valid_failure_source, field):
    bad = dict(valid_failure_source)
    bad[field] = 0.0
    with pytest.raises(ValidationError, match=field):
        validate_failure_source(bad)


def test_scenario_requires_schema_version(valid_scenario):
    bad = dict(valid_scenario)
    bad.pop("schema_version")
    with pytest.raises(ValidationError, match="schema_version"):
        validate_physical_scenario(bad)


def test_invalid_severity_index_raises(valid_scenario):
    bad = dict(valid_scenario)
    bad["severity_index"] = 101
    with pytest.raises(ValidationError, match="severity_index"):
        validate_physical_scenario(bad)


def test_inconsistent_severity_level_raises(valid_scenario):
    bad = dict(valid_scenario)
    bad["severity_level_0_10"] = 5
    with pytest.raises(ValidationError, match="severity_index and severity_level_0_10"):
        validate_physical_scenario(bad)


def test_breach_depth_exceeds_dam_height_raises(valid_scenario, valid_failure_source):
    bad = dict(valid_scenario)
    bad["breach"] = dict(valid_scenario["breach"]) 
    bad["breach"]["breach_depth_m"] = 30.0
    with pytest.raises(ValidationError, match="breach_depth_m"):
        validate_physical_scenario(bad, failure_source=valid_failure_source)


def test_initial_water_level_must_be_positive(valid_scenario):
    bad = dict(valid_scenario)
    bad["initial_conditions"] = dict(valid_scenario["initial_conditions"])
    bad["initial_conditions"]["initial_water_level_m"] = 0.0
    with pytest.raises(ValidationError, match="initial_water_level_m"):
        validate_physical_scenario(bad)


def test_breach_width_and_formation_time_must_be_positive(valid_scenario):
    bad = dict(valid_scenario)
    bad["breach"] = dict(valid_scenario["breach"])
    bad["breach"]["breach_width_m"] = 0.0
    with pytest.raises(ValidationError, match="breach_width_m"):
        validate_physical_scenario(bad)

    bad2 = dict(valid_scenario)
    bad2["breach"] = dict(valid_scenario["breach"])
    bad2["breach"]["formation_time_hr"] = 0.0
    with pytest.raises(ValidationError, match="formation_time_hr"):
        validate_physical_scenario(bad2)


@pytest.mark.parametrize(
    ("field", "value"),
    [("breach_width_m", 500.1), ("formation_time_hr", 0.049), ("formation_time_hr", 48.1)],
)
def test_breach_contract_bounds_are_enforced(valid_scenario, field, value):
    bad = dict(valid_scenario)
    bad["breach"] = dict(valid_scenario["breach"])
    bad["breach"][field] = value
    with pytest.raises(ValidationError, match=field):
        validate_physical_scenario(bad)


def test_missing_provenance_is_rejected(valid_scenario):
    bad = dict(valid_scenario)
    bad["breach"] = dict(valid_scenario["breach"])
    bad["breach"].pop("peak_discharge_provenance")
    with pytest.raises(ValidationError, match="provenance"):
        validate_breach_parameters(bad["breach"])


@pytest.mark.parametrize(
    ("field", "value"),
    [("breach_width_m", True), ("breach_depth_m", False), ("formation_time_hr", True)],
)
def test_boolean_breach_values_are_rejected(valid_scenario, field, value):
    bad = dict(valid_scenario["breach"])
    bad[field] = value
    with pytest.raises(ValidationError, match=field):
        validate_breach_parameters(bad)


def test_invalid_hydrograph_points_raises(valid_hydrograph):
    bad = {"hydrograph_id": valid_hydrograph["hydrograph_id"], "points": [
        {"t_min": 0, "discharge_m3s": 10.0},
        {"t_min": 0, "discharge_m3s": 12.0},
    ]}
    with pytest.raises(ValidationError, match="strictly increasing"):
        validate_hydrograph(bad)


def test_scenario_hydrograph_mismatch_raises(valid_scenario, valid_hydrograph):
    bad = dict(valid_scenario)
    bad["discharge_series_id"] = "different_series"
    with pytest.raises(ValidationError, match="discharge_series_id"):
        validate_physical_scenario(bad, hydrograph=valid_hydrograph)


def test_breach_peak_discharge_must_match_hydrograph_max(valid_scenario, valid_hydrograph):
    bad = dict(valid_scenario)
    bad["breach"] = dict(valid_scenario["breach"])
    bad["breach"]["peak_discharge_m3s"] = 9999.0
    with pytest.raises(ValidationError, match="peak_discharge_m3s"):
        validate_physical_scenario(bad, hydrograph=valid_hydrograph)


def test_breach_parameters_reject_invalid_method(valid_scenario):
    bad = dict(valid_scenario)
    bad["breach"] = dict(valid_scenario["breach"])
    bad["breach"]["method"] = "unknown_method"
    with pytest.raises(ValidationError, match="method"):
        validate_physical_scenario(bad)


def test_breach_parameters_validate_directly(valid_scenario):
    result = validate_breach_parameters(valid_scenario["breach"])
    assert result["method"] == "froehlich"
