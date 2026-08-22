import math

import pytest

from normalization.parameter_normalizer import (
    normalize_parameters,
    normalize_value,
)


def test_normalizes_and_clamps_operational_parameters():
    assert normalize_parameters({
        "delay": 90,
        "carbon": 450,
        "technical_risk": -0.2,
    }) == {
        "delay": 0.5,
        "carbon": 1.0,
        "technical_risk": 0.0,
    }


@pytest.mark.parametrize("invalid_value", [math.inf, -math.inf, math.nan])
def test_rejects_non_finite_values(invalid_value):
    with pytest.raises(ValueError, match="finite number"):
        normalize_value(invalid_value, 0, 1)


def test_rejects_unknown_operational_parameters():
    with pytest.raises(ValueError, match="No normalization range defined"):
        normalize_parameters({"unknown_factor": 0.5})


def test_rejects_an_invalid_normalization_range():
    with pytest.raises(ValueError, match="greater than minimum"):
        normalize_value(0.5, 1, 1)
