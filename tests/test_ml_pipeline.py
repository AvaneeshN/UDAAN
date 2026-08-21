import numpy as np
import pytest

from ml.features import FEATURE_NAMES, extract_features
from ml.risk_model import MLRiskPredictor
from models.factory import build_flight_from_json
from services import decision_service


@pytest.fixture
def raw_flight():
    return {
        "flight_id": "6E-203",
        "delay_minutes": 90,
        "passenger_count": 180,
        "distance_km": 1500,
        "origin": {"code": "DEL"},
        "destination": {"code": "BOM"},
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


def test_feature_contract_matches_the_model_training_order(raw_flight):
    flight = build_flight_from_json(raw_flight)

    features = extract_features(flight, raw_flight["history"])

    assert FEATURE_NAMES == (
        "aircraft_age_years",
        "technical_failure_rate",
        "average_technical_delay_minutes",
        "crew_duty_hours_today",
        "past_delays",
        "past_cancellations",
        "technical_cancellations",
        "recent_disruptions",
    )
    np.testing.assert_array_equal(
        features,
        np.array([18, 0.3, 25, 7.5, 6, 2, 1, 2]),
    )


def test_feature_extraction_rejects_incomplete_history(raw_flight):
    flight = build_flight_from_json(raw_flight)
    del raw_flight["history"]["recent_disruptions"]

    with pytest.raises(
        ValueError,
        match="Missing ML history features: recent_disruptions",
    ):
        extract_features(flight, raw_flight["history"])


def test_decision_service_uses_the_shared_feature_contract(
    monkeypatch,
    raw_flight,
):
    captured = {}

    class CapturingPredictor:
        def predict_risk(self, features):
            captured["features"] = features
            return 0.5

    monkeypatch.setattr(
        decision_service,
        "MLRiskPredictor",
        CapturingPredictor,
    )

    decision_service.generate_decision(raw_flight, "indigo")

    np.testing.assert_array_equal(
        captured["features"],
        np.array([18, 0.3, 25, 7.5, 6, 2, 1, 2]),
    )


def test_default_model_path_is_independent_of_working_directory(
    monkeypatch,
    tmp_path,
):
    monkeypatch.chdir(tmp_path)

    predictor = MLRiskPredictor()

    assert predictor.model.n_features_in_ == len(FEATURE_NAMES)


@pytest.mark.parametrize(
    "features, message",
    [
        (np.ones(7), "must have shape"),
        (np.ones((1, 8)), "must have shape"),
        (
            np.array([1, 2, 3, 4, 5, 6, 7, np.nan]),
            "only finite values",
        ),
    ],
)
def test_predictor_rejects_invalid_feature_vectors(features, message):
    predictor = MLRiskPredictor()

    with pytest.raises(ValueError, match=message):
        predictor.predict_risk(features)


def test_predictor_returns_a_bounded_probability(raw_flight):
    predictor = MLRiskPredictor()
    flight = build_flight_from_json(raw_flight)

    risk = predictor.predict_risk(
        extract_features(flight, raw_flight["history"])
    )

    assert 0 <= risk <= 1


def test_predictor_uses_the_disruption_class_by_label(monkeypatch):
    class ReversedClassModel:
        n_features_in_ = len(FEATURE_NAMES)
        classes_ = np.array([1, 0])

        def predict_proba(self, _features):
            return np.array([[0.8, 0.2]])

    monkeypatch.setattr(
        "ml.risk_model.joblib.load",
        lambda _path: ReversedClassModel(),
    )

    predictor = MLRiskPredictor("unused.pkl")

    assert predictor.predict_risk(np.ones(8)) == 0.8


def test_predictor_rejects_an_incompatible_model(monkeypatch):
    class IncompatibleModel:
        n_features_in_ = 7
        classes_ = np.array([0, 1])

        def predict_proba(self, _features):
            return np.array([[0.5, 0.5]])

    monkeypatch.setattr(
        "ml.risk_model.joblib.load",
        lambda _path: IncompatibleModel(),
    )

    with pytest.raises(ValueError, match="incompatible number of features"):
        MLRiskPredictor("unused.pkl")
