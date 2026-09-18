"""Approved MacDonald-Langridge-Monopolis (1984) breach relationships."""

from __future__ import annotations

from math import isfinite
from typing import Any, Mapping


class MacDonaldCalculationError(ValueError):
    """Raised when approved MacDonald inputs cannot produce a result."""


_ZB = 0.5


def _positive(value: Any, name: str) -> float:
    if isinstance(value, bool):
        raise MacDonaldCalculationError(f"{name} must be a positive finite number.")
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        raise MacDonaldCalculationError(f"{name} must be a positive finite number.") from None
    if not isfinite(numeric) or numeric <= 0:
        raise MacDonaldCalculationError(f"{name} must be a positive finite number.")
    return numeric


def estimate_macdonald(
    *,
    macdonald_inputs: Mapping[str, Any],
    breach_height_m: float,
) -> dict[str, Any]:
    """Calculate the approved MacDonald result for an earthfill source."""
    if not isinstance(macdonald_inputs, Mapping):
        raise MacDonaldCalculationError("macdonald_inputs must be an object.")

    required = (
        "material_classification",
        "V_out_m3",
        "h_w_m",
        "Vw_m3",
        "hw_m",
        "crest_width_C_m",
        "upstream_slope_Z1",
        "downstream_slope_Z2",
        "peak_discharge_relationship",
    )
    missing = [field for field in required if field not in macdonald_inputs]
    if missing:
        raise MacDonaldCalculationError(
            "macdonald_inputs is missing required fields: " + ", ".join(missing)
        )

    material = macdonald_inputs["material_classification"]
    if material not in {"earthfill", "earthfill_clay_core_rockfill"}:
        raise MacDonaldCalculationError("Unsupported MacDonald material classification.")
    relationship = macdonald_inputs["peak_discharge_relationship"]
    if relationship not in {"best_fit", "envelope"}:
        raise MacDonaldCalculationError(
            "peak_discharge_relationship must be 'best_fit' or 'envelope'."
        )

    v_out = _positive(macdonald_inputs["V_out_m3"], "macdonald_inputs.V_out_m3")
    h_w = _positive(macdonald_inputs["h_w_m"], "macdonald_inputs.h_w_m")
    v_w = _positive(macdonald_inputs["Vw_m3"], "macdonald_inputs.Vw_m3")
    h_w_peak = _positive(macdonald_inputs["hw_m"], "macdonald_inputs.hw_m")
    crest_width = _positive(
        macdonald_inputs["crest_width_C_m"], "macdonald_inputs.crest_width_C_m"
    )
    z1 = _positive(macdonald_inputs["upstream_slope_Z1"], "macdonald_inputs.upstream_slope_Z1")
    z2 = _positive(
        macdonald_inputs["downstream_slope_Z2"], "macdonald_inputs.downstream_slope_Z2"
    )
    hb = _positive(breach_height_m, "breach_height_m")

    if material == "earthfill":
        eroded_volume = 0.0261 * (v_out * h_w) ** 0.769
        formation_time_hr = 0.0179 * eroded_volume**0.364
    else:
        eroded_volume = 0.00348 * (v_out * h_w) ** 0.852
        raise MacDonaldCalculationError(
            "Formation time is not scientifically defined for "
            "earthfill_clay_core_rockfill."
        )

    z3 = z1 + z2
    denominator = hb * (crest_width + hb * z3 / 2)
    if denominator == 0:
        raise MacDonaldCalculationError("MacDonald geometry denominator must be non-zero.")
    width_numerator = eroded_volume - hb**2 * (
        crest_width * _ZB + hb * _ZB * z3 / 3
    )
    breach_width_m = width_numerator / denominator
    if not isfinite(breach_width_m) or breach_width_m <= 0 or breach_width_m > 500:
        raise MacDonaldCalculationError(
            "Calculated MacDonald breach width is physically invalid or outside the contract bound."
        )

    if relationship == "best_fit":
        peak_discharge_m3s = 1.154 * (v_w * h_w_peak) ** 0.412
    else:
        peak_discharge_m3s = 3.85 * (v_w * h_w_peak) ** 0.411
    if not isfinite(peak_discharge_m3s) or peak_discharge_m3s <= 0:
        raise MacDonaldCalculationError("Calculated peak discharge is nonphysical.")
    if not 0.05 <= formation_time_hr <= 48:
        raise MacDonaldCalculationError(
            "Calculated formation_time_hr is outside the contract range [0.05, 48]."
        )
    if peak_discharge_m3s > 100000:
        raise MacDonaldCalculationError("Calculated peak discharge exceeds the contract bound.")

    return {
        "breach_width_m": breach_width_m,
        "breach_depth_m": hb,
        "formation_time_hr": formation_time_hr,
        "peak_discharge_m3s": peak_discharge_m3s,
        "method": "macdonald_langridge_monopolis",
        "peak_discharge_provenance": {
            "source": "macdonald_langridge_monopolis",
            "method_version": f"macdonald_1984_{relationship}",
            "input_basis": "explicit PhysicalScenario.macdonald_inputs",
        },
    }


__all__ = ["MacDonaldCalculationError", "estimate_macdonald"]
