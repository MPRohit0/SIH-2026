import copy
import json
from pathlib import Path

import jsonschema
import pytest

from modules.m2_breach.src.engine import BreachEngineError, run_breach_engine
from modules.m2_breach.src.froehlich import estimate_froehlich
from modules.m2_breach.src.input_validation import (
    ValidationError,
    validate_breach_parameters,
    validate_failure_source,
)
from modules.m2_breach.src.pipeline import build_scenario_bundles
from modules.m2_breach.src.scenario_builder import (
    ScenarioBuildError,
    build_exact_scenario,
    resolve_scenario_request,
)


@pytest.fixture
def source():
    return {
        "failure_source_id": "source-01",
        "type": "engineered_dam",
        "name": "Reference Dam",
        "location": {"lon": 84.2, "lat": 28.1},
        "height_m": 30.0,
        "storage_volume_m3": 1_200_000.0,
        "catchment_area_km2": 120.0,
        "data_source": "fixture",
    }


@pytest.fixture
def exact_request():
    return {
        "schema_version": "1.0.0",
        "site_id": "site-01",
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


def test_failure_source_rejects_invalid_coordinates(source):
    for field, value in (("lon", 181.0), ("lat", -91.0)):
        invalid = copy.deepcopy(source)
        invalid["location"][field] = value
        with pytest.raises(ValidationError, match=field):
            validate_failure_source(invalid)


@pytest.mark.parametrize(
    ("field", "value"),
    [("height_m", -1.0), ("storage_volume_m3", -1.0)],
)
def test_failure_source_rejects_invalid_physical_values(source, field, value):
    invalid = copy.deepcopy(source)
    invalid[field] = value
    with pytest.raises(ValidationError, match=field):
        validate_failure_source(invalid)


def test_failure_source_rejects_incompatible_type(source):
    invalid = copy.deepcopy(source)
    invalid["type"] = "unsupported_source_type"
    with pytest.raises(ValidationError, match="type"):
        validate_failure_source(invalid)


def test_froehlich_width_and_formation_time_match_locked_relationships():
    volume = 1_200_000.0
    height = 18.6
    result = estimate_froehlich(
        reservoir_volume_m3=volume,
        breach_height_m=height,
        failure_mechanism="overtopping",
    )
    expected_width = 0.27 * 1.3 * volume**0.32 * height**0.04
    expected_hours = (
        63.2 * (volume / (9.80665 * height**2)) ** 0.5
    ) / 3600.0
    assert result["breach_width_m"] == pytest.approx(expected_width)
    assert result["formation_time_hr"] == pytest.approx(expected_hours)


def test_froehlich_piping_k0_is_one():
    result = estimate_froehlich(
        reservoir_volume_m3=1_200_000.0,
        breach_height_m=18.6,
        failure_mechanism="piping/seepage",
    )
    expected_width = 0.27 * 1.0 * 1_200_000.0**0.32 * 18.6**0.04
    assert result["breach_width_m"] == pytest.approx(expected_width)
    assert result["peak_discharge_m3s"] is None
    assert result["peak_discharge_provenance"]["source"] == "unavailable"


def test_froehlich_is_deterministic():
    kwargs = {
        "reservoir_volume_m3": 1_200_000.0,
        "breach_height_m": 18.6,
        "failure_mechanism": "overtopping",
    }
    assert estimate_froehlich(**kwargs) == estimate_froehlich(**kwargs)


def test_breach_validation_rejects_dimensions_formation_and_method():
    valid = {
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
    }
    for field, value in (
        ("breach_width_m", 0),
        ("breach_depth_m", 0),
        ("formation_time_hr", 0),
        ("method", "unknown"),
    ):
        invalid = copy.deepcopy(valid)
        invalid[field] = value
        with pytest.raises(ValidationError, match=field):
            validate_breach_parameters(invalid)


def test_macdonald_relationships_are_explicitly_blocked_until_implemented():
    with pytest.raises(BreachEngineError, match="macdonald_inputs is required"):
        run_breach_engine(
            failure_source={
                "failure_source_id": "source-01",
                "type": "engineered_dam",
                "name": "Reference Dam",
                "location": {"lon": 84.2, "lat": 28.1},
                "height_m": 30.0,
                "storage_volume_m3": 1_200_000.0,
                "catchment_area_km2": 120.0,
                "data_source": "fixture",
            },
            scenario={
                **{
                    "schema_version": "1.0.0",
                    "scenario_id": "scenario-01",
                    "site_id": "site-01",
                    "failure_source_id": "source-01",
                    "severity_index": None,
                    "severity_level_0_10": None,
                    "initial_conditions": {
                        "initial_water_level_m": 2470.0,
                        "downstream_discharge_m3s": 850.0,
                    },
                    "breach": {
                        "breach_width_m": 45.2,
                        "breach_depth_m": 18.6,
                        "formation_time_hr": 0.8,
                        "peak_discharge_m3s": None,
                        "method": "macdonald_langridge_monopolis",
                        "peak_discharge_provenance": {
                            "source": "unavailable",
                            "method_version": None,
                            "input_basis": None,
                        },
                    },
                    "discharge_series_id": None,
                    "breach_engine_version": "test",
                    "generated_at": "2026-09-18T16:05:00Z",
                }
            },
            methods="macdonald_langridge_monopolis",
        )


def test_exact_values_and_unsupported_severity_mapping(source, exact_request):
    scenario = build_exact_scenario(
        site_id="site-01",
        failure_source_id=source["failure_source_id"],
        exact_values=exact_request["exact_values"],
    )
    assert scenario["severity_index"] is None
    assert scenario["breach"]["breach_width_m"] == 45.2
    assert scenario["breach"]["breach_depth_m"] == 18.6

    slider = dict(exact_request)
    slider["input_mode"] = "severity_slider"
    slider["severity_level_0_10"] = 6
    slider["exact_values"] = None
    result = resolve_scenario_request(
        request=slider,
        site_id="site-01",
        failure_source_id=source["failure_source_id"],
    )
    assert result["status"] == "error"
    assert result["error"]["code"] == "insufficient_exact_inputs"


def test_physical_changes_and_method_change_modify_scenario_id(source, exact_request):
    first = build_exact_scenario(
        site_id="site-01",
        failure_source_id=source["failure_source_id"],
        exact_values=exact_request["exact_values"],
        generated_at="2026-09-18T16:05:00Z",
        method="froehlich",
    )
    later = build_exact_scenario(
        site_id="site-01",
        failure_source_id=source["failure_source_id"],
        exact_values={**exact_request["exact_values"], "breach_width_m": 46.2},
        generated_at="2026-09-19T16:05:00Z",
        method="froehlich",
    )
    other_method = build_exact_scenario(
        site_id="site-01",
        failure_source_id=source["failure_source_id"],
        exact_values=exact_request["exact_values"],
        method="macdonald_langridge_monopolis",
    )
    assert first["scenario_id"] != later["scenario_id"]
    assert first["scenario_id"] != other_method["scenario_id"]


def test_pipeline_output_validates_against_machine_schema(source, exact_request):
    bundles = build_scenario_bundles(
        failure_source=source,
        scenario_request=exact_request,
        methods="froehlich",
        failure_mechanism="overtopping",
    )
    schemas_dir = Path(__file__).parents[3] / "contracts" / "schemas"
    bundle_schema = json.loads(
        (schemas_dir / "scenario_bundle.schema.json").read_text(encoding="utf-8")
    )
    breach_schema = json.loads(
        (schemas_dir / "breach_parameters.schema.json").read_text(encoding="utf-8")
    )
    resolver = jsonschema.RefResolver.from_schema(
        bundle_schema,
        store={
            "https://schemas.sih26161.org/physical_scenario.schema.json": json.loads(
                (schemas_dir / "physical_scenario.schema.json").read_text(encoding="utf-8")
            ),
            "https://schemas.sih26161.org/breach_parameters.schema.json": breach_schema,
            "https://schemas.sih26161.org/hydrograph.schema.json": json.loads(
                (schemas_dir / "hydrograph.schema.json").read_text(encoding="utf-8")
            ),
        },
    )
    for bundle in bundles:
        jsonschema.validate(bundle, bundle_schema, resolver=resolver)
