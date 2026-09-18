import math

import pytest

from modules.m2_breach.src.macdonald_langridge import (
    MacDonaldCalculationError,
    estimate_macdonald,
)


@pytest.fixture
def inputs():
    return {
        "material_classification": "earthfill",
        "V_out_m3": 2500000.0,
        "h_w_m": 12.0,
        "Vw_m3": 1200000.0,
        "hw_m": 15.0,
        "crest_width_C_m": 8.0,
        "upstream_slope_Z1": 2.5,
        "downstream_slope_Z2": 2.0,
        "peak_discharge_relationship": "best_fit",
    }


def test_earthfill_best_fit_calculation(inputs):
    result = estimate_macdonald(macdonald_inputs=inputs, breach_height_m=18.6)
    eroded = 0.0261 * (inputs["V_out_m3"] * inputs["h_w_m"]) ** 0.769
    expected_time = 0.0179 * eroded**0.364
    expected_peak = 1.154 * (inputs["Vw_m3"] * inputs["hw_m"]) ** 0.412
    assert result["formation_time_hr"] == pytest.approx(expected_time)
    assert result["peak_discharge_m3s"] == pytest.approx(expected_peak)
    assert result["method"] == "macdonald_langridge_monopolis"
    assert result["peak_discharge_provenance"]["method_version"].endswith("best_fit")


def test_earthfill_envelope_is_distinct(inputs):
    best = estimate_macdonald(macdonald_inputs=inputs, breach_height_m=18.6)
    envelope_inputs = {**inputs, "peak_discharge_relationship": "envelope"}
    envelope = estimate_macdonald(
        macdonald_inputs=envelope_inputs, breach_height_m=18.6
    )
    expected = 3.85 * (inputs["Vw_m3"] * inputs["hw_m"]) ** 0.411
    assert envelope["peak_discharge_m3s"] == pytest.approx(expected)
    assert envelope["peak_discharge_m3s"] != best["peak_discharge_m3s"]
    assert envelope["peak_discharge_provenance"]["method_version"].endswith("envelope")


def test_earthfill_geometry_calculation(inputs):
    result = estimate_macdonald(macdonald_inputs=inputs, breach_height_m=18.6)
    eroded = 0.0261 * (inputs["V_out_m3"] * inputs["h_w_m"]) ** 0.769
    z3 = inputs["upstream_slope_Z1"] + inputs["downstream_slope_Z2"]
    expected = (
        eroded
        - 18.6**2 * (inputs["crest_width_C_m"] * 0.5 + 18.6 * 0.5 * z3 / 3)
    ) / (18.6 * (inputs["crest_width_C_m"] + 18.6 * z3 / 2))
    assert result["breach_width_m"] == pytest.approx(expected)


def test_missing_input_is_rejected(inputs):
    missing = dict(inputs)
    del missing["V_out_m3"]
    with pytest.raises(MacDonaldCalculationError, match="V_out_m3"):
        estimate_macdonald(macdonald_inputs=missing, breach_height_m=18.6)


def test_nonpositive_input_is_rejected(inputs):
    invalid = {**inputs, "h_w_m": 0}
    with pytest.raises(MacDonaldCalculationError, match="h_w_m"):
        estimate_macdonald(macdonald_inputs=invalid, breach_height_m=18.6)


def test_clay_core_calculates_no_unsupported_formation_time(inputs):
    clay = {**inputs, "material_classification": "earthfill_clay_core_rockfill"}
    with pytest.raises(MacDonaldCalculationError, match="Formation time"):
        estimate_macdonald(macdonald_inputs=clay, breach_height_m=18.6)


def test_no_hydrograph_is_generated(inputs):
    result = estimate_macdonald(macdonald_inputs=inputs, breach_height_m=18.6)
    assert "discharge_series" not in result
    assert "points" not in result
