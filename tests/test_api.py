from dataclasses import dataclass
import importlib

from fastapi.testclient import TestClient
import pytest


api_module = importlib.import_module("api.app")
client = TestClient(api_module.app)


@pytest.fixture
def flight_payload():
    return {
        "airline_code": "airindia",
        "flight_id": "AI-101",
        "delay_minutes": 90,
        "passenger_count": 180,
        "distance_km": 1500,
        "origin": {"code": "DEL", "name": "Delhi"},
        "destination": {"code": "BOM", "name": "Mumbai"},
        "aircraft": {
            "aircraft_id": "VT-ABC",
            "aircraft_type": "A320",
            "age_years": 18,
            "emission_factor": 0.1,
            "technical_failure_rate": 0.3,
            "avg_tech_delay_min": 25,
        },
        "crew": {
            "crew_id": "CRW-77",
            "duty_hours_today": 7.5,
            "max_duty_hours": 10,
        },
        "history": {
            "past_delays": 6,
            "past_cancellations": 2,
            "technical_cancellations": 1,
            "recent_disruptions": 2,
        },
    }


def test_health_endpoint():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "UDAAN decision API",
    }


def test_decision_endpoint_passes_selected_airline(monkeypatch, flight_payload):
    captured = {}

    @dataclass
    class FakeDecision:
        flight_id: str

    def fake_generate_decision(*, raw, airline_code):
        captured["raw"] = raw
        captured["airline_code"] = airline_code
        return FakeDecision(flight_id=raw["flight_id"])

    monkeypatch.setattr(
        api_module,
        "generate_decision",
        fake_generate_decision,
    )

    response = client.post("/api/decisions", json=flight_payload)

    assert response.status_code == 200
    assert captured["airline_code"] == "airindia"
    assert "airline_code" not in captured["raw"]
    assert response.json() == {"flight_id": "AI-101"}


@pytest.mark.parametrize("invalid_limit", [0, -1])
def test_max_duty_hours_must_be_positive(flight_payload, invalid_limit):
    flight_payload["crew"]["max_duty_hours"] = invalid_limit

    response = client.post("/api/decisions", json=flight_payload)

    assert response.status_code == 422
    assert any(
        error["loc"][-2:] == ["crew", "max_duty_hours"]
        and error["type"] == "greater_than"
        for error in response.json()["detail"]
    )
