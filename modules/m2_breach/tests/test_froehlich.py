import math

import pytest

from modules.m2_breach.src.froehlich import (
    FroehlichInputError,
    estimate_froehlich,
)


def test_overtopping_uses_locked_k0_and_contract_fields():
    result = estimate_froehlich(
        reservoir_volume_m3=45_000_000,
        breach_height_m=20,
        failure_mechanism="overtopping",
    )

    assert result["method"] == "froehlich"
    assert result["peak_discharge_m3s"] is None
    assert result["peak_discharge_provenance"]["source"] == "unavailable"
    assert result["breach_width_m"] > 0
    assert result["breach_depth_m"] == 20.0
    assert result["formation_time_hr"] > 0


def test_piping_and_overtopping_widths_differ_only_by_locked_k0():
    overtopping = estimate_froehlich(
        reservoir_volume_m3=45_000_000,
        breach_height_m=20,
        failure_mechanism="overtopping",
    )
    piping = estimate_froehlich(
        reservoir_volume_m3=45_000_000,
        breach_height_m=20,
        failure_mechanism="piping/seepage",
    )

    assert math.isclose(
        overtopping["breach_width_m"] / piping["breach_width_m"], 1.3
    )
    assert piping["formation_time_hr"] == overtopping["formation_time_hr"]


def test_formation_time_is_explicitly_converted_from_seconds_to_hours():
    volume_m3 = 45_000_000
    height_m = 20
    result = estimate_froehlich(
        reservoir_volume_m3=volume_m3,
        breach_height_m=height_m,
        failure_mechanism="piping",
    )

    expected_seconds = 63.2 * math.sqrt(volume_m3 / (9.80665 * height_m**2))
    assert math.isclose(result["formation_time_hr"], expected_seconds / 3600.0)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("reservoir_volume_m3", 0),
        ("reservoir_volume_m3", -1),
        ("breach_height_m", 0),
        ("breach_height_m", -1),
    ],
)
def test_non_positive_physical_inputs_are_rejected(field, value):
    kwargs = {
        "reservoir_volume_m3": 45_000_000,
        "breach_height_m": 20,
        "failure_mechanism": "overtopping",
    }
    kwargs[field] = value

    with pytest.raises(FroehlichInputError, match=field):
        estimate_froehlich(**kwargs)


def test_unsupported_failure_mechanism_is_rejected():
    with pytest.raises(FroehlichInputError, match="failure_mechanism"):
        estimate_froehlich(
            reservoir_volume_m3=45_000_000,
            breach_height_m=20,
            failure_mechanism="structural_collapse",
        )


def test_output_is_deterministic():
    kwargs = {
        "reservoir_volume_m3": 45_000_000,
        "breach_height_m": 20,
        "failure_mechanism": "overtopping",
    }

    assert estimate_froehlich(**kwargs) == estimate_froehlich(**kwargs)
