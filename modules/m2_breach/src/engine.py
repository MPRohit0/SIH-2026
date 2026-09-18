"""Unified orchestration for the Module 2 empirical breach methods."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .froehlich import estimate_froehlich
from .macdonald_langridge import estimate_macdonald, MacDonaldCalculationError
from .input_validation import (
    VALID_BREACH_METHODS,
    ValidationError,
    validate_failure_source,
    validate_physical_scenario,
)


class BreachEngineError(ValueError):
    """Raised when the breach engine cannot produce a contract-valid result."""


def _selected_methods(methods: str | Iterable[str]) -> tuple[str, ...]:
    if isinstance(methods, str):
        selected = (methods,)
    else:
        try:
            selected = tuple(methods)
        except TypeError:
            raise BreachEngineError("methods must be a method name or iterable of names.") from None

    if not selected:
        raise BreachEngineError("At least one breach method must be selected.")
    if len(set(selected)) != len(selected):
        raise BreachEngineError("Each breach method may be selected only once.")
    unsupported = [method for method in selected if method not in VALID_BREACH_METHODS]
    if unsupported:
        raise BreachEngineError(
            "Unsupported breach method(s): " + ", ".join(map(str, unsupported))
        )
    return selected


def _run_method(
    method: str,
    *,
    failure_source: Mapping[str, Any],
    scenario: Mapping[str, Any],
    failure_mechanism: str | None,
) -> dict[str, Any]:
    if method == "froehlich":
        if failure_mechanism is None:
            raise BreachEngineError(
                "failure_mechanism is required for Froehlich (2008); "
                "the FailureSource contract does not define a trigger field."
            )
        volume_m3 = failure_source.get("storage_volume_m3")
        breach_height_m = scenario["breach"]["breach_depth_m"]
        try:
            return estimate_froehlich(
                reservoir_volume_m3=volume_m3,
                breach_height_m=breach_height_m,
                failure_mechanism=failure_mechanism,
            )
        except (TypeError, ValueError) as exc:
            raise BreachEngineError(str(exc)) from exc
    if method == "macdonald_langridge_monopolis":
        try:
            return estimate_macdonald(
                macdonald_inputs=scenario["macdonald_inputs"],
                breach_height_m=scenario["breach"]["breach_depth_m"],
            )
        except (KeyError, MacDonaldCalculationError, TypeError, ValueError) as exc:
            raise BreachEngineError(str(exc)) from exc
    raise BreachEngineError(f"Unsupported breach method: {method}.")


def _method_error(method: str, exc: Exception) -> dict[str, Any]:
    return {
        "method": method,
        "status": "error",
        "breach_parameters": None,
        "error": {
            "code": "breach_formula_failed",
            "message": str(exc),
        },
    }


def run_breach_engine(
    *,
    failure_source: Mapping[str, Any],
    scenario: Mapping[str, Any],
    methods: str | Iterable[str],
    failure_mechanism: str | None = None,
) -> dict[str, Any]:
    """Validate inputs and independently run each selected breach method.

    The returned ``results`` list preserves selection order and keeps each
    method's BreachParameters record independent. No hydrograph or solver
    result is produced.
    """
    try:
        validated_source = validate_failure_source(failure_source)
        validated_scenario = validate_physical_scenario(
            scenario,
            failure_source=validated_source,
        )
    except ValidationError as exc:
        raise BreachEngineError(str(exc)) from exc

    if validated_scenario["failure_source_id"] != validated_source["failure_source_id"]:
        raise BreachEngineError(
            "scenario.failure_source_id does not match failure_source.failure_source_id."
        )

    selected = _selected_methods(methods)
    scenario_method = validated_scenario["breach"]["method"]
    if len(selected) == 1 and selected[0] != scenario_method:
        raise BreachEngineError(
            "selected breach method must match scenario.breach.method."
        )
    if len(selected) > 1 and scenario_method not in selected:
        raise BreachEngineError(
            "scenario.breach.method must be included in the selected methods."
        )

    outcomes = []
    for method in selected:
        try:
            breach = _run_method(
                method,
                failure_source=validated_source,
                scenario=validated_scenario,
                failure_mechanism=failure_mechanism,
            )
        except BreachEngineError as exc:
            outcomes.append(_method_error(method, exc))
        else:
            outcomes.append(
                {
                    "method": method,
                    "status": "ok",
                    "breach_parameters": breach,
                    "error": None,
                }
            )

    return {
        "scenario_id": validated_scenario["scenario_id"],
        "site_id": validated_scenario["site_id"],
        "failure_source_id": validated_source["failure_source_id"],
        "results": outcomes,
        "status": "ok" if all(item["status"] == "ok" for item in outcomes) else "partial",
    }


def estimate_breach_parameters(**kwargs: Any) -> dict[str, Any]:
    """Compatibility entry point for callers naming the engine by its output."""
    return run_breach_engine(**kwargs)


__all__ = ["BreachEngineError", "estimate_breach_parameters", "run_breach_engine"]
