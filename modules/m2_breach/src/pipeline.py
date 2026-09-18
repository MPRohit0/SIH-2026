"""Canonical Module 2 entry point for downstream scenario bundles."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .engine import BreachEngineError, run_breach_engine
from .input_validation import (
    ValidationError,
    validate_failure_source,
    validate_scenario_bundle,
)
from .scenario_builder import (
    ScenarioBuildError,
    _build_scenario_id,
    resolve_scenario_request,
)


class PipelineError(ValueError):
    """Raised when a canonical downstream scenario cannot be produced."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _methods(methods: str | Iterable[str]) -> tuple[str, ...]:
    if isinstance(methods, str):
        selected = (methods,)
    else:
        try:
            selected = tuple(methods)
        except TypeError:
            raise PipelineError("invalid_scenario_inputs", "methods must be iterable.") from None
    if not selected:
        raise PipelineError("invalid_scenario_inputs", "At least one method is required.")
    if len(set(selected)) != len(selected):
        raise PipelineError("invalid_scenario_inputs", "Methods must be unique.")
    return selected


def _finalize_scenario(
    scenario: Mapping[str, Any],
    breach: Mapping[str, Any],
) -> dict[str, Any]:
    finalized = dict(scenario)
    finalized["breach"] = dict(breach)
    prefix = str(scenario["scenario_id"]).rsplit("_", 1)[0]
    finalized["scenario_id"] = _build_scenario_id(prefix, finalized)
    return finalized


def _error_code(exc: Exception) -> str:
    if isinstance(exc, BreachEngineError):
        return "breach_formula_failed"
    if isinstance(exc, ScenarioBuildError):
        return "invalid_scenario_inputs"
    return "invalid_scenario_inputs"


def build_scenario_bundles(
    *,
    failure_source: Mapping[str, Any],
    scenario_request: Mapping[str, Any],
    methods: str | Iterable[str],
    failure_mechanism: str | None = None,
    scenario_catalog: Mapping[str, Any] | list[Mapping[str, Any]] | None = None,
    breach_engine_version: str = "demo-1.0.0",
) -> list[dict[str, Any]]:
    """Resolve and estimate canonical ScenarioBundle objects.

    One independent bundle is returned for each selected method. M2 never
    creates a DischargeSeries; every returned bundle therefore contains a
    null ``discharge_series`` unless a future approved forcing component is
    explicitly integrated.
    """
    try:
        validated_source = validate_failure_source(failure_source)
    except ValidationError as exc:
        raise PipelineError("missing_failure_source_specs", str(exc)) from exc

    selected = _methods(methods)
    bundles: list[dict[str, Any]] = []
    for method in selected:
        try:
            scenario = resolve_scenario_request(
                request=scenario_request,
                site_id=str(scenario_request.get("site_id", "")),
                failure_source_id=validated_source["failure_source_id"],
                method=method,
                breach_engine_version=breach_engine_version,
                scenario_catalog=scenario_catalog,
            )
            if scenario.get("status") == "error":
                error = scenario["error"]
                raise PipelineError(error["code"], error["message"])

            engine_result = run_breach_engine(
                failure_source=validated_source,
                scenario=scenario,
                methods=method,
                failure_mechanism=failure_mechanism,
            )
            outcome = engine_result["results"][0]
            if outcome["status"] != "ok":
                error = outcome["error"]
                raise PipelineError(error["code"], error["message"])
            breach = outcome["breach_parameters"]
            finalized_scenario = _finalize_scenario(scenario, breach)
            bundle = {
                "schema_version": "1.0.0",
                "scenario": finalized_scenario,
                "discharge_series": None,
            }
            validate_scenario_bundle(bundle)
            bundles.append(bundle)
        except PipelineError:
            raise
        except (BreachEngineError, ScenarioBuildError, ValidationError) as exc:
            raise PipelineError(_error_code(exc), str(exc)) from exc

    return bundles


run_pipeline = build_scenario_bundles


__all__ = ["PipelineError", "build_scenario_bundles", "run_pipeline"]
