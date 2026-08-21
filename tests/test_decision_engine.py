import math

import pytest

from decision_engine.engine import DecisionEngine


WEIGHTS = {
    "delay": 0.6,
    "cancellation_impact": 0.4,
}


def option(action, *, delay, cancellation_impact):
    return {
        "action": action,
        "parameters": {},
        "normalized_parameters": {
            "delay": delay,
            "cancellation_impact": cancellation_impact,
        },
    }


def test_recommends_the_option_with_the_lowest_weighted_penalty():
    engine = DecisionEngine(WEIGHTS)
    options = [
        option("delay_flight", delay=0.2, cancellation_impact=0.0),
        option("cancel_flight", delay=0.0, cancellation_impact=1.0),
    ]

    decision = engine.recommend(options)

    assert decision["recommended_action"] == "delay_flight"
    assert decision["normalized_scores"] == [
        ("delay_flight", 0.0),
        ("cancel_flight", 1.0),
    ]
    assert math.isclose(decision["raw_scores"][0][1], 0.12)


def test_returns_no_recommendation_when_constraints_reject_every_option():
    class RejectAll:
        def is_allowed(self, _option):
            return False

    engine = DecisionEngine(WEIGHTS, constraints=[RejectAll()])

    decision = engine.recommend([
        option("cancel_flight", delay=0.0, cancellation_impact=1.0)
    ])

    assert decision == {
        "recommended_action": None,
        "normalized_scores": [],
        "raw_scores": [],
        "reason": "All options violate constraints",
    }


@pytest.mark.parametrize(
    "weights, message",
    [
        ({}, "must not be empty"),
        ({"delay": -0.1, "cancellation_impact": 1.1}, "non-negative"),
        ({"delay": 0.4, "cancellation_impact": 0.4}, "sum to 1.0"),
        ({"delay": math.nan, "cancellation_impact": 1.0}, "finite"),
    ],
)
def test_rejects_invalid_policy_weights(weights, message):
    with pytest.raises(ValueError, match=message):
        DecisionEngine(weights)


def test_rejects_a_missing_weighted_parameter():
    engine = DecisionEngine(WEIGHTS)

    with pytest.raises(
        ValueError,
        match="Missing normalized decision parameters: cancellation_impact",
    ):
        engine.score_option({"delay": 0.5})


@pytest.mark.parametrize("invalid_value", [-0.1, 1.1, math.inf, math.nan])
def test_rejects_invalid_normalized_values(invalid_value):
    engine = DecisionEngine(WEIGHTS)

    with pytest.raises(ValueError, match="between 0 and 1"):
        engine.score_option({
            "delay": invalid_value,
            "cancellation_impact": 0.5,
        })


def test_rejects_an_empty_option_set():
    engine = DecisionEngine(WEIGHTS)

    with pytest.raises(ValueError, match="At least one decision option"):
        engine.recommend([])
