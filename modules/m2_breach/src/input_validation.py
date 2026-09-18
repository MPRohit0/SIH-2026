"""Input validation for Module 2 breach and hydrograph generation."""

from __future__ import annotations

from math import isfinite
from numbers import Integral, Real
from typing import Any, Mapping

VALID_FAILURE_TYPES = {
    "engineered_dam",
    "natural_lake_glof",
    "landslide_dam",
}
VALID_BREACH_METHODS = {"froehlich", "macdonald_langridge_monopolis"}
VALID_MACDONALD_MATERIALS = {"earthfill", "earthfill_clay_core_rockfill"}
VALID_MACDONALD_RELATIONSHIPS = {"best_fit", "envelope"}


class ValidationError(ValueError):
    """Raised when a Module 2 input does not satisfy the contract."""


def _is_finite_number(value: Any) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool) and isfinite(float(value))


def _require_mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{field_name} must be an object.")
    return value


def _require_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return value


def _require_numeric(value: Any, field_name: str, *, allow_none: bool = False) -> float | None:
    if value is None:
        if allow_none:
            return None
        raise ValidationError(f"{field_name} is required.")
    if not _is_finite_number(value):
        raise ValidationError(f"{field_name} must be a finite number.")
    return float(value)


def _require_int(value: Any, field_name: str, *, minimum: int | None = None, maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValidationError(f"{field_name} must be an integer.")
    int_value = int(value)
    if minimum is not None and int_value < minimum:
        raise ValidationError(f"{field_name} must be >= {minimum}.")
    if maximum is not None and int_value > maximum:
        raise ValidationError(f"{field_name} must be <= {maximum}.")
    return int_value


def _validate_location(location: Any) -> dict[str, float]:
    loc = _require_mapping(location, "location")
    lon = _require_numeric(loc.get("lon"), "location.lon")
    lat = _require_numeric(loc.get("lat"), "location.lat")
    if not (-180.0 <= lon <= 180.0):
        raise ValidationError("location.lon must be within [-180, 180].")
    if not (-90.0 <= lat <= 90.0):
        raise ValidationError("location.lat must be within [-90, 90].")
    return {"lon": lon, "lat": lat}


def validate_failure_source(data: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a FailureSource object against the canonical contract."""
    failure_source = _require_mapping(data, "failure_source")

    required_fields = [
        "failure_source_id",
        "type",
        "name",
        "location",
        "height_m",
        "storage_volume_m3",
        "catchment_area_km2",
        "data_source",
    ]
    missing = [field for field in required_fields if field not in failure_source]
    if missing:
        raise ValidationError(f"failure_source is missing required fields: {', '.join(missing)}")

    failure_source_id = _require_string(failure_source.get("failure_source_id"), "failure_source_id")
    failure_type = _require_string(failure_source.get("type"), "type")
    if failure_type not in VALID_FAILURE_TYPES:
        raise ValidationError(
            "type must be one of: " + ", ".join(sorted(VALID_FAILURE_TYPES)) + "."
        )

    name = _require_string(failure_source.get("name"), "name")
    location = _validate_location(failure_source.get("location"))

    height_m = _require_numeric(failure_source.get("height_m"), "height_m", allow_none=True)
    storage_volume_m3 = _require_numeric(
        failure_source.get("storage_volume_m3"), "storage_volume_m3", allow_none=True
    )
    catchment_area_km2 = _require_numeric(
        failure_source.get("catchment_area_km2"), "catchment_area_km2", allow_none=True
    )
    data_source = failure_source.get("data_source")
    if data_source is not None and (not isinstance(data_source, str) or not data_source.strip()):
        raise ValidationError("data_source, when provided, must be a non-empty string.")

    for field_name, value in {
        "height_m": height_m,
        "storage_volume_m3": storage_volume_m3,
        "catchment_area_km2": catchment_area_km2,
    }.items():
        if value is not None and value <= 0:
            raise ValidationError(f"{field_name} must be positive when supplied.")

    if height_m is None and storage_volume_m3 is None and catchment_area_km2 is None:
        raise ValidationError(
            "At least one of height_m, storage_volume_m3, or catchment_area_km2 must be present."
        )

    return {
        "failure_source_id": failure_source_id,
        "type": failure_type,
        "name": name,
        "location": location,
        "height_m": height_m,
        "storage_volume_m3": storage_volume_m3,
        "catchment_area_km2": catchment_area_km2,
        "data_source": data_source,
    }


def validate_breach_parameters(data: Mapping[str, Any], *, failure_source: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Validate a single BreachParameters object."""
    breach = _require_mapping(data, "breach")

    required_fields = [
        "breach_width_m",
        "breach_depth_m",
        "formation_time_hr",
        "peak_discharge_m3s",
        "method",
    ]
    missing = [field for field in required_fields if field not in breach]
    if missing:
        raise ValidationError(f"breach is missing required fields: {', '.join(missing)}")

    breach_width_m = _require_numeric(breach.get("breach_width_m"), "breach.breach_width_m")
    breach_depth_m = _require_numeric(breach.get("breach_depth_m"), "breach.breach_depth_m")
    formation_time_hr = _require_numeric(breach.get("formation_time_hr"), "breach.formation_time_hr")
    peak_discharge_m3s = _require_numeric(
        breach.get("peak_discharge_m3s"), "breach.peak_discharge_m3s", allow_none=True
    )
    method = _require_string(breach.get("method"), "breach.method")
    if "peak_discharge_provenance" not in breach:
        raise ValidationError(
            "breach.peak_discharge_provenance must explicitly identify unavailable provenance."
        )
    provenance = _require_mapping(
        breach.get("peak_discharge_provenance"),
        "breach.peak_discharge_provenance",
    )
    source = _require_string(provenance.get("source"), "breach.peak_discharge_provenance.source")
    if source not in {
        "froehlich_2008",
        "macdonald_langridge_monopolis",
        "user_supplied",
        "hydraulic_solver",
        "unavailable",
    }:
        raise ValidationError("breach.peak_discharge_provenance.source is not supported.")
    method_version = provenance.get("method_version")
    input_basis = provenance.get("input_basis")
    if method_version is not None:
        _require_string(method_version, "breach.peak_discharge_provenance.method_version")
    if input_basis is not None:
        _require_string(input_basis, "breach.peak_discharge_provenance.input_basis")

    if breach_width_m <= 0:
        raise ValidationError("breach.breach_width_m must be positive.")
    if breach_depth_m <= 0:
        raise ValidationError("breach.breach_depth_m must be positive.")
    if not 0.05 <= formation_time_hr <= 48:
        raise ValidationError("breach.formation_time_hr must be within [0.05, 48].")
    if breach_width_m > 500:
        raise ValidationError("breach.breach_width_m must be <= 500.")
    if peak_discharge_m3s is not None and peak_discharge_m3s <= 0:
        raise ValidationError("breach.peak_discharge_m3s must be positive.")
    if method not in VALID_BREACH_METHODS:
        raise ValidationError(
            "breach.method must be one of: " + ", ".join(sorted(VALID_BREACH_METHODS)) + "."
        )

    if failure_source is not None:
        source_height = failure_source.get("height_m")
        if source_height is not None:
            height = _require_numeric(source_height, "failure_source.height_m")
            if breach_depth_m > height:
                raise ValidationError(
                    "breach.breach_depth_m must not exceed failure_source.height_m when height_m is supplied."
                )

    return {
        "breach_width_m": breach_width_m,
        "breach_depth_m": breach_depth_m,
        "formation_time_hr": formation_time_hr,
        "peak_discharge_m3s": peak_discharge_m3s,
        "method": method,
        "peak_discharge_provenance": provenance,
    }


def _validate_macdonald_inputs(data: Any) -> dict[str, Any]:
    inputs = _require_mapping(data, "macdonald_inputs")
    required = [
        "material_classification",
        "V_out_m3",
        "h_w_m",
        "Vw_m3",
        "hw_m",
        "crest_width_C_m",
        "upstream_slope_Z1",
        "downstream_slope_Z2",
        "peak_discharge_relationship",
    ]
    missing = [field for field in required if field not in inputs]
    if missing:
        raise ValidationError(
            "macdonald_inputs is missing required fields: " + ", ".join(missing)
        )
    material = _require_string(inputs.get("material_classification"), "macdonald_inputs.material_classification")
    if material not in VALID_MACDONALD_MATERIALS:
        raise ValidationError("macdonald_inputs.material_classification is not supported.")
    relationship = _require_string(
        inputs.get("peak_discharge_relationship"),
        "macdonald_inputs.peak_discharge_relationship",
    )
    if relationship not in VALID_MACDONALD_RELATIONSHIPS:
        raise ValidationError("macdonald_inputs.peak_discharge_relationship is not supported.")
    numeric = {
        field: _require_numeric(inputs.get(field), f"macdonald_inputs.{field}")
        for field in required[1:-1]
    }
    for field, value in numeric.items():
        if value <= 0:
            raise ValidationError(f"macdonald_inputs.{field} must be positive.")
    return {
        "material_classification": material,
        **numeric,
        "peak_discharge_relationship": relationship,
    }


def validate_hydrograph(data: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a hydrograph / discharge series."""
    hydrograph = _require_mapping(data, "hydrograph")

    series_id = hydrograph.get("series_id")
    hydrograph_id = hydrograph.get("hydrograph_id")
    if series_id is None and hydrograph_id is None:
        raise ValidationError("hydrograph must include either 'series_id' or 'hydrograph_id'.")

    if series_id is not None:
        _require_string(series_id, "series_id")
        final_id = series_id
    else:
        _require_string(hydrograph_id, "hydrograph_id")
        final_id = hydrograph_id

    points = hydrograph.get("points")
    if not isinstance(points, list) or len(points) < 2:
        raise ValidationError("hydrograph.points must be a list with at least 2 points.")

    last_t_min = None
    for idx, point in enumerate(points):
        point_map = _require_mapping(point, f"hydrograph.points[{idx}]")
        t_min = _require_numeric(point_map.get("t_min"), f"hydrograph.points[{idx}].t_min")
        discharge_m3s = _require_numeric(
            point_map.get("discharge_m3s"), f"hydrograph.points[{idx}].discharge_m3s"
        )
        if t_min < 0:
            raise ValidationError(f"hydrograph.points[{idx}].t_min must be >= 0.")
        if discharge_m3s < 0:
            raise ValidationError(f"hydrograph.points[{idx}].discharge_m3s must be >= 0.")
        if last_t_min is not None and t_min <= last_t_min:
            raise ValidationError("hydrograph.points must have strictly increasing t_min values.")
        last_t_min = t_min

    if points and points[0].get("t_min") is not None and float(points[0]["t_min"]) != 0.0:
        raise ValidationError("hydrograph.points[0].t_min must be 0 for model-generated hydrographs.")

    return {"series_id": final_id, "points": points}


def validate_physical_scenario(
    data: Mapping[str, Any], *, failure_source: Mapping[str, Any] | None = None, hydrograph: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Validate a PhysicalScenario object and its relationship to the failure source and hydrograph."""
    scenario = _require_mapping(data, "scenario")

    required_fields = [
        "schema_version",
        "scenario_id",
        "site_id",
        "failure_source_id",
        "severity_index",
        "initial_conditions",
        "breach",
        "discharge_series_id",
        "breach_engine_version",
        "generated_at",
    ]
    missing = [field for field in required_fields if field not in scenario]
    if missing:
        raise ValidationError(f"scenario is missing required fields: {', '.join(missing)}")

    scenario_id = _require_string(scenario.get("scenario_id"), "scenario_id")
    site_id = _require_string(scenario.get("site_id"), "site_id")
    failure_source_id = _require_string(scenario.get("failure_source_id"), "failure_source_id")
    discharge_series_id = scenario.get("discharge_series_id")
    if discharge_series_id is not None:
        discharge_series_id = _require_string(discharge_series_id, "discharge_series_id")
    breach_engine_version = _require_string(scenario.get("breach_engine_version"), "breach_engine_version")
    generated_at = _require_string(scenario.get("generated_at"), "generated_at")

    severity_index = scenario.get("severity_index")
    if severity_index is not None:
        severity_index = _require_int(severity_index, "severity_index", minimum=0, maximum=100)

    if "severity_level_0_10" in scenario and scenario["severity_level_0_10"] is not None:
        severity_level = _require_int(
            scenario.get("severity_level_0_10"), "severity_level_0_10", minimum=0, maximum=10
        )
        if severity_index is not None and severity_index != severity_level * 10:
            raise ValidationError(
                "severity_index and severity_level_0_10 are inconsistent; severity_index should equal severity_level_0_10 * 10."
            )

    initial_conditions = _require_mapping(scenario.get("initial_conditions"), "initial_conditions")
    initial_water_level_m = _require_numeric(
        initial_conditions.get("initial_water_level_m"), "initial_conditions.initial_water_level_m", allow_none=True
    )
    downstream_discharge_m3s = _require_numeric(
        initial_conditions.get("downstream_discharge_m3s"),
        "initial_conditions.downstream_discharge_m3s",
        allow_none=True,
    )

    if initial_water_level_m is not None and initial_water_level_m <= 0:
        raise ValidationError("initial_conditions.initial_water_level_m must be positive when supplied.")
    if downstream_discharge_m3s is not None and downstream_discharge_m3s < 0:
        raise ValidationError("initial_conditions.downstream_discharge_m3s must be non-negative when supplied.")

    if failure_source is not None:
        if failure_source.get("failure_source_id") != failure_source_id:
            raise ValidationError("scenario.failure_source_id does not match failure_source.failure_source_id.")
        if failure_source.get("height_m") is not None:
            source_height = _require_numeric(failure_source.get("height_m"), "failure_source.height_m")
            breach_depth = _require_numeric(scenario["breach"].get("breach_depth_m"), "breach.breach_depth_m")
            if breach_depth > source_height:
                raise ValidationError(
                    "breach.breach_depth_m must not exceed failure_source.height_m when height_m is supplied."
                )

    breach = validate_breach_parameters(scenario.get("breach"), failure_source=failure_source)
    macdonald_inputs = scenario.get("macdonald_inputs")
    if breach["method"] == "macdonald_langridge_monopolis":
        if macdonald_inputs is None:
            raise ValidationError(
                "macdonald_inputs is required for macdonald_langridge_monopolis."
            )
        macdonald_inputs = _validate_macdonald_inputs(macdonald_inputs)
    elif macdonald_inputs is not None:
        macdonald_inputs = _validate_macdonald_inputs(macdonald_inputs)
    if hydrograph is not None:
        hydrograph_info = validate_hydrograph(hydrograph)
        hydrograph_id = hydrograph_info["series_id"]
        if hydrograph_id != discharge_series_id:
            raise ValidationError(
                "scenario.discharge_series_id must match the supplied hydrograph series_id/hydrograph_id."
            )
        peak_discharge = breach["peak_discharge_m3s"]
        max_series_discharge = max(point["discharge_m3s"] for point in hydrograph_info["points"])
        if not isfinite(max_series_discharge):
            raise ValidationError("Hydrograph discharge values must be finite.")
        if peak_discharge is not None and abs(peak_discharge - max_series_discharge) > 1e-9:
            raise ValidationError(
                "breach.peak_discharge_m3s must equal the maximum discharge_m3s in the hydrograph."
            )

    return {
        "schema_version": scenario["schema_version"],
        "scenario_id": scenario_id,
        "site_id": site_id,
        "failure_source_id": failure_source_id,
        "severity_index": severity_index,
        "severity_level_0_10": scenario.get("severity_level_0_10"),
        "initial_conditions": {
            "initial_water_level_m": initial_water_level_m,
            "downstream_discharge_m3s": downstream_discharge_m3s,
        },
        "breach": breach,
        "macdonald_inputs": macdonald_inputs,
        "discharge_series_id": discharge_series_id,
        "breach_engine_version": breach_engine_version,
        "generated_at": generated_at,
    }


def validate_scenario_bundle(data: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a ScenarioBundle object from the mock payload format."""
    bundle = _require_mapping(data, "scenario_bundle")
    if "scenario" not in bundle:
        raise ValidationError("scenario_bundle is missing 'scenario'.")
    scenario = bundle["scenario"]
    hydrograph = bundle.get("discharge_series")
    if hydrograph is None:
        hydrograph = bundle.get("hydrograph")
    if "discharge_series" not in bundle and "hydrograph" not in bundle:
        raise ValidationError("scenario_bundle is missing 'discharge_series'.")

    failure_source = bundle.get("failure_source")
    if failure_source is not None:
        validated_failure_source = validate_failure_source(failure_source)
    else:
        validated_failure_source = None

    validated_scenario = validate_physical_scenario(
        scenario, failure_source=validated_failure_source, hydrograph=hydrograph
    )
    validated_hydrograph = validate_hydrograph(hydrograph) if hydrograph is not None else None
    if validated_hydrograph is None and validated_scenario["discharge_series_id"] is not None:
        raise ValidationError("scenario.discharge_series_id must be null when discharge_series is null.")

    return {"scenario": validated_scenario, "discharge_series": validated_hydrograph}


def validate_module2_inputs(
    *,
    failure_source: Mapping[str, Any] | None = None,
    scenario: Mapping[str, Any] | None = None,
    hydrograph: Mapping[str, Any] | None = None,
    bundle: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Convenience entry point for validating Module 2 payloads."""
    if bundle is not None:
        return validate_scenario_bundle(bundle)
    if failure_source is None and scenario is None and hydrograph is None:
        raise ValidationError("At least one Module 2 input must be provided.")

    validated_failure_source = validate_failure_source(failure_source) if failure_source is not None else None
    validated_hydrograph = validate_hydrograph(hydrograph) if hydrograph is not None else None
    validated_scenario = (
        validate_physical_scenario(scenario, failure_source=validated_failure_source, hydrograph=validated_hydrograph)
        if scenario is not None
        else None
    )
    return {
        "failure_source": validated_failure_source,
        "scenario": validated_scenario,
        "hydrograph": validated_hydrograph,
    }


__all__ = [
    "ValidationError",
    "validate_failure_source",
    "validate_breach_parameters",
    "validate_hydrograph",
    "validate_physical_scenario",
    "validate_scenario_bundle",
    "validate_module2_inputs",
]
