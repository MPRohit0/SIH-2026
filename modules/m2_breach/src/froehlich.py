"""Froehlich (2008) breach-parameter estimation.

Only the relationships locked in ``docs/M2_SCIENTIFIC_SPEC.md`` are
implemented here. This module does not estimate peak discharge or generate a
discharge series.
"""

from __future__ import annotations

from math import isfinite, sqrt
from numbers import Real
from typing import Any


class FroehlichInputError(ValueError):
    """Raised when Froehlich inputs are missing or physically invalid."""


_GRAVITY_M_PER_S2 = 9.80665
_SECONDS_PER_HOUR = 3600.0
_K0_BY_MECHANISM = {
    "overtopping": 1.3,
    "piping": 1.0,
    "piping/seepage": 1.0,
    "piping_seepage": 1.0,
}


def _positive_finite(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise FroehlichInputError(f"{field_name} must be a finite number.")
    result = float(value)
    if not isfinite(result) or result <= 0:
        raise FroehlichInputError(f"{field_name} must be positive and finite.")
    return result


def estimate_froehlich(
    *,
    reservoir_volume_m3: float,
    breach_height_m: float,
    failure_mechanism: str,
) -> dict[str, Any]:
    """Estimate Froehlich (2008) breach width and formation time.

    ``reservoir_volume_m3`` is Vw, the reservoir volume at failure, in m^3.
    ``breach_height_m`` is hb, the final breach height, in m.
    The equation yields formation time in seconds; the returned contract field
    is explicitly converted to hours.
    """
    volume_m3 = _positive_finite(reservoir_volume_m3, "reservoir_volume_m3")
    height_m = _positive_finite(breach_height_m, "breach_height_m")
    if not isinstance(failure_mechanism, str) or failure_mechanism not in _K0_BY_MECHANISM:
        supported = ", ".join(sorted(_K0_BY_MECHANISM))
        raise FroehlichInputError(
            f"failure_mechanism must be one of: {supported}."
        )

    k0 = _K0_BY_MECHANISM[failure_mechanism]
    average_width_m = 0.27 * k0 * volume_m3**0.32 * height_m**0.04
    formation_time_seconds = 63.2 * sqrt(
        volume_m3 / (_GRAVITY_M_PER_S2 * height_m**2)
    )
    formation_time_hr = formation_time_seconds / _SECONDS_PER_HOUR

    if average_width_m > 500:
        raise FroehlichInputError(
            "Calculated breach_width_m exceeds the contract maximum of 500 m."
        )
    if not 0.05 <= formation_time_hr <= 48:
        raise FroehlichInputError(
            "Calculated formation_time_hr is outside the contract range [0.05, 48]."
        )

    return {
        "breach_width_m": average_width_m,
        "breach_depth_m": height_m,
        "formation_time_hr": formation_time_hr,
        "peak_discharge_m3s": None,
        "method": "froehlich",
        "peak_discharge_provenance": {
            "source": "unavailable",
            "method_version": None,
            "input_basis": None,
        },
    }


__all__ = ["FroehlichInputError", "estimate_froehlich"]
