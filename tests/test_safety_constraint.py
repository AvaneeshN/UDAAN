from constraints.safety_constraint import SafetyRiskConstraint


def test_cancellation_is_allowed_when_technical_risk_is_high():
    constraint = SafetyRiskConstraint(max_allowed_risk=0.7)
    cancellation = {
        "action": "cancel_flight",
        "parameters": {"technical_risk": 1.0},
    }
    delay = {
        "action": "delay_flight",
        "parameters": {"technical_risk": 1.0},
    }

    assert constraint.is_allowed(cancellation) is True
    assert constraint.is_allowed(delay) is False
