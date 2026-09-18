"""Scenario construction and resolution for Module 2.

The contract supports two scenario input modes:

1. severity_slider: the dashboard provides a 0..10 slider value and M2 resolves
   it to a canonical PhysicalScenario with severity_index = severity_level_0_10 * 10.
2. exact_values: the dashboard provides exact physical values and M2 preserves
   those values in the scenario without inventing a severity mapping.

This module does not implement empirical breach equations; it only builds the
canonical PhysicalScenario object and deterministic scenario IDs required by the
contract.
"""

from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from typing import Any, Mapping

VALID_INPUT_MODES = {"severity_slider", "exact_values"}
VALID_BREACH_METHODS = {"froehlich", "macdonald_langridge_monopolis"}
_CATALOG_FIELDS = (
    "initial_water_level_m",
    "downstream_discharge_m3s",
    "breach_width_m",
    "breach_depth_m",
    "formation_time_hr",
)


class ScenarioBuildError(ValueError):
    """Raised when a scenario cannot be constructed from the supplied input."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _coerce_float(value: Any, field_name: str) -> float:
    if value is None or isinstance(value, bool):
        raise ScenarioBuildError(f"{field_name} is required.")
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        raise ScenarioBuildError(f"{field_name} must be numeric.") from None
    if numeric != numeric or numeric in (float("inf"), float("-inf")):
        raise ScenarioBuildError(f"{field_name} must be finite.")
    return numeric


def _coerce_int(value: Any, field_name: str, *, minimum: int | None = None, maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ScenarioBuildError(f"{field_name} must be an integer.")
    numeric = value
    if minimum is not None and numeric < minimum:
        raise ScenarioBuildError(f"{field_name} must be >= {minimum}.")
    if maximum is not None and numeric > maximum:
        raise ScenarioBuildError(f"{field_name} must be <= {maximum}.")
    return numeric


def _build_scenario_id(prefix: str, scenario_payload: Mapping[str, Any]) -> str:
    """Create a deterministic content-addressed scenario ID.

    `generated_at` is intentionally excluded because the contract says the ID is
    stable and content-addressed, and generated_at is not part of the hash.
    """
    content = {key: value for key, value in scenario_payload.items() if key != "generated_at"}
    digest = hashlib.sha256(_canonical_json(content).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def _build_breach_record(
    *,
    method: str,
    breach_width_m: float,
    breach_depth_m: float,
    formation_time_hr: float,
    peak_discharge_m3s: float | None,
) -> dict[str, Any]:
    if method not in VALID_BREACH_METHODS:
        raise ScenarioBuildError(f"method must be one of: {', '.join(sorted(VALID_BREACH_METHODS))}.")
    if breach_width_m <= 0:
        raise ScenarioBuildError("breach_width_m must be positive.")
    if breach_depth_m <= 0:
        raise ScenarioBuildError("breach_depth_m must be positive.")
    if formation_time_hr <= 0:
        raise ScenarioBuildError("formation_time_hr must be positive.")
    if peak_discharge_m3s is not None and peak_discharge_m3s <= 0:
        raise ScenarioBuildError("peak_discharge_m3s must be positive.")
    peak_discharge_provenance = (
        {
            "source": "user_supplied",
            "method_version": None,
            "input_basis": "caller-supplied peak discharge",
        }
        if peak_discharge_m3s is not None
        else {"source": "unavailable", "method_version": None, "input_basis": None}
    )
    return {
        "breach_width_m": float(breach_width_m),
        "breach_depth_m": float(breach_depth_m),
        "formation_time_hr": float(formation_time_hr),
        "peak_discharge_m3s": (
            float(peak_discharge_m3s) if peak_discharge_m3s is not None else None
        ),
        "method": method,
        "peak_discharge_provenance": peak_discharge_provenance,
    }


def build_severity_scenario(
    *,
    site_id: str,
    failure_source_id: str,
    severity_level_0_10: int,
    initial_water_level_m: float,
    downstream_discharge_m3s: float,
    breach_width_m: float,
    breach_depth_m: float,
    formation_time_hr: float,
    peak_discharge_m3s: float | None = None,
    method: str = "froehlich",
    breach_engine_version: str = "demo-1.0.0",
    discharge_series_id: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build a canonical PhysicalScenario from a severity-slider request."""
    severity_level = _coerce_int(severity_level_0_10, "severity_level_0_10", minimum=0, maximum=10)
    severity_index = severity_level * 10

    scenario_payload = {
        "schema_version": "1.0.0",
        "scenario_id": "",
        "site_id": site_id,
        "failure_source_id": failure_source_id,
        "severity_index": severity_index,
        "severity_level_0_10": severity_level,
        "initial_conditions": {
            "initial_water_level_m": _coerce_float(initial_water_level_m, "initial_water_level_m"),
            "downstream_discharge_m3s": _coerce_float(downstream_discharge_m3s, "downstream_discharge_m3s"),
        },
        "breach": _build_breach_record(
            method=method,
            breach_width_m=breach_width_m,
            breach_depth_m=breach_depth_m,
            formation_time_hr=formation_time_hr,
            peak_discharge_m3s=peak_discharge_m3s,
        ),
        "discharge_series_id": discharge_series_id,
        "breach_engine_version": breach_engine_version,
        "generated_at": generated_at or _utc_now(),
    }
    scenario_payload["scenario_id"] = _build_scenario_id(
        f"demo_dam_s{severity_index}_{method}_v1",
        scenario_payload,
    )
    return scenario_payload


def build_exact_scenario(
    *,
    site_id: str,
    failure_source_id: str,
    exact_values: Mapping[str, Any],
    method: str = "froehlich",
    breach_engine_version: str = "demo-1.0.0",
    discharge_series_id: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build a canonical PhysicalScenario from exact physical values.

    The exact input values are preserved in the scenario itself. The contract
    does not define a mathematical mapping from exact values to severity.
    """
    if not isinstance(exact_values, Mapping):
        raise ScenarioBuildError("exact_values must be a mapping.")

    required_fields = [
        "initial_water_level_m",
        "breach_width_m",
        "breach_depth_m",
        "formation_time_hr",
        "downstream_discharge_m3s",
    ]
    missing = [field for field in required_fields if field not in exact_values or exact_values.get(field) is None]
    if missing:
        raise ScenarioBuildError(f"exact_values is missing required fields: {', '.join(sorted(missing))}.")

    initial_water_level_m = _coerce_float(exact_values["initial_water_level_m"], "exact_values.initial_water_level_m")
    downstream_discharge_m3s = _coerce_float(
        exact_values["downstream_discharge_m3s"], "exact_values.downstream_discharge_m3s"
    )
    breach_width_m = _coerce_float(exact_values["breach_width_m"], "exact_values.breach_width_m")
    breach_depth_m = _coerce_float(exact_values["breach_depth_m"], "exact_values.breach_depth_m")
    formation_time_hr = _coerce_float(exact_values["formation_time_hr"], "exact_values.formation_time_hr")
    scenario_payload = {
        "schema_version": "1.0.0",
        "scenario_id": "",
        "site_id": site_id,
        "failure_source_id": failure_source_id,
        "severity_index": None,
        "severity_level_0_10": None,
        "initial_conditions": {
            "initial_water_level_m": initial_water_level_m,
            "downstream_discharge_m3s": downstream_discharge_m3s,
        },
        "breach": _build_breach_record(
            method=method,
            breach_width_m=breach_width_m,
            breach_depth_m=breach_depth_m,
            formation_time_hr=formation_time_hr,
            peak_discharge_m3s=None,
        ),
        "discharge_series_id": discharge_series_id,
        "breach_engine_version": breach_engine_version,
        "generated_at": generated_at or _utc_now(),
    }
    scenario_payload["scenario_id"] = _build_scenario_id(
        "demo_dam_exact",
        scenario_payload,
    )
    return scenario_payload


def resolve_scenario_request(
    *,
    request: Mapping[str, Any],
    site_id: str,
    failure_source_id: str,
    method: str = "froehlich",
    breach_engine_version: str = "demo-1.0.0",
    scenario_catalog: Mapping[str, Any] | list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Resolve a request without inventing physical values.

    Slider requests require a catalog entry containing all physical fields
    needed to construct a scenario. Without one, a contract-shaped error
    response is returned instead of applying placeholder defaults.
    """
    if not isinstance(request, Mapping):
        raise ScenarioBuildError("request must be a mapping.")

    input_mode = request.get("input_mode")
    if input_mode not in VALID_INPUT_MODES:
        raise ScenarioBuildError(f"input_mode must be one of: {', '.join(sorted(VALID_INPUT_MODES))}.")

    if input_mode == "severity_slider":
        severity_level = request.get("severity_level_0_10")
        if severity_level is None:
            raise ScenarioBuildError("severity_level_0_10 is required when input_mode='severity_slider'.")
        severity_index = _coerce_int(
            severity_level, "severity_level_0_10", minimum=0, maximum=10
        ) * 10
        catalog_entry = _catalog_entry_for_severity(scenario_catalog, severity_index)
        if catalog_entry is None:
            return _insufficient_information_result(
                site_id=site_id,
                code="insufficient_exact_inputs",
                required_fields=list(_CATALOG_FIELDS),
                message="No approved physical scenario catalog entry exists for the requested severity.",
            )
        missing = [field for field in _CATALOG_FIELDS if catalog_entry.get(field) is None]
        if missing:
            return _insufficient_information_result(
                site_id=site_id,
                code="insufficient_exact_inputs",
                required_fields=missing,
                message="The approved scenario catalog entry is missing required physical fields.",
            )
        return build_severity_scenario(
            site_id=site_id,
            failure_source_id=failure_source_id,
            severity_level_0_10=severity_level,
            initial_water_level_m=catalog_entry["initial_water_level_m"],
            downstream_discharge_m3s=catalog_entry["downstream_discharge_m3s"],
            breach_width_m=catalog_entry["breach_width_m"],
            breach_depth_m=catalog_entry["breach_depth_m"],
            formation_time_hr=catalog_entry["formation_time_hr"],
            peak_discharge_m3s=catalog_entry.get("peak_discharge_m3s"),
            method=method,
            breach_engine_version=breach_engine_version,
            discharge_series_id=catalog_entry.get("discharge_series_id"),
        )

    exact_values = request.get("exact_values")
    if not isinstance(exact_values, Mapping):
        raise ScenarioBuildError("exact_values is required when input_mode='exact_values'.")
    unsupported = {"peak_discharge_m3s"} & set(request)
    unsupported.update({"peak_discharge_m3s"} & set(exact_values))
    if unsupported:
        raise ScenarioBuildError(
            "Unsupported exact-mode field(s): " + ", ".join(sorted(unsupported))
        )
    return build_exact_scenario(
        site_id=site_id,
        failure_source_id=failure_source_id,
        exact_values=exact_values,
        method=method,
        breach_engine_version=breach_engine_version,
    )


def _catalog_entry_for_severity(
    catalog: Mapping[str, Any] | list[Mapping[str, Any]] | None,
    severity_index: int,
) -> Mapping[str, Any] | None:
    if catalog is None:
        return None
    if isinstance(catalog, Mapping):
        entry = catalog.get(str(severity_index), catalog.get(severity_index))
        return entry if isinstance(entry, Mapping) else None
    for entry in catalog:
        if isinstance(entry, Mapping) and entry.get("severity_index") == severity_index:
            return entry
    return None


def _insufficient_information_result(
    *,
    site_id: str,
    code: str,
    required_fields: list[str],
    message: str,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "status": "error",
        "warnings": [],
        "error": {
            "code": code,
            "message": message,
            "details": {"required_fields": required_fields},
        },
        "scenario": None,
        "site_id": site_id,
    }


def resolve_and_run_breach_engine(
    *,
    request: Mapping[str, Any],
    failure_source: Mapping[str, Any],
    methods: str | list[str],
    failure_mechanism: str | None = None,
    scenario_catalog: Mapping[str, Any] | list[Mapping[str, Any]] | None = None,
    breach_engine_version: str = "demo-1.0.0",
) -> dict[str, Any]:
    """Resolve a request, then run only explicitly selected empirical methods."""
    if isinstance(methods, str):
        scenario_method = methods
    else:
        if not methods:
            raise ScenarioBuildError("At least one breach method must be selected.")
        scenario_method = methods[0]
    resolved = resolve_scenario_request(
        request=request,
        site_id=str(request.get("site_id", "")),
        failure_source_id=str(failure_source.get("failure_source_id", "")),
        method=scenario_method,
        breach_engine_version=breach_engine_version,
        scenario_catalog=scenario_catalog,
    )
    if resolved.get("status") == "error":
        return resolved

    from .engine import run_breach_engine

    engine_result = run_breach_engine(
        failure_source=failure_source,
        scenario=resolved,
        methods=methods,
        failure_mechanism=failure_mechanism,
    )
    return {"scenario": resolved, "breach_engine": engine_result}


__all__ = [
    "ScenarioBuildError",
    "build_severity_scenario",
    "build_exact_scenario",
    "resolve_scenario_request",
    "resolve_and_run_breach_engine",
]
