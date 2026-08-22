import pytest

from services import decision_service


@pytest.fixture
def low_risk_flight():
    return {
        "flight_id": "AI-101",
        "delay_minutes": 90,
        "passenger_count": 180,
        "distance_km": 1500,
        "origin": {"code": "DEL"},
        "destination": {"code": "BOM"},
        "aircraft": {
            "aircraft_id": "VT-ABC",
            "aircraft_type": "A320",
            "age_years": 5,
            "emission_factor": 0.1,
            "technical_failure_rate": 0.1,
            "avg_tech_delay_min": 5,
        },
        "crew": {
            "crew_id": "CRW-77",
            "duty_hours_today": 9.5,
            "max_duty_hours": 10,
        },
        "history": {
            "past_delays": 1,
            "past_cancellations": 0,
            "technical_cancellations": 0,
            "recent_disruptions": 0,
        },
    }


@pytest.fixture(autouse=True)
def predictable_ml_risk(monkeypatch):
    class LowRiskPredictor:
        def predict_risk(self, _features):
            return 0.05

    monkeypatch.setattr(
        decision_service,
        "MLRiskPredictor",
        LowRiskPredictor,
    )


def test_delay_is_filtered_when_it_exceeds_remaining_crew_duty(
    low_risk_flight,
):
    result = decision_service.generate_decision(
        low_risk_flight,
        "airindia",
    )

    assert result.recommended_action == "cancel_flight"
    assert [action for action, _score in result.raw_scores] == [
        "cancel_flight"
    ]


def test_delay_is_allowed_at_the_crew_duty_limit(low_risk_flight):
    low_risk_flight["crew"]["duty_hours_today"] = 8
    low_risk_flight["delay_minutes"] = 120

    result = decision_service.generate_decision(
        low_risk_flight,
        "airindia",
    )

    assert [action for action, _score in result.raw_scores] == [
        "delay_flight",
        "cancel_flight",
    ]
