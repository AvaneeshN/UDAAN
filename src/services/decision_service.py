from datetime import datetime, timezone
import os

import numpy as np

from carbon_model.carbon_estimator import CarbonEstimator
from constraints.carbon_constraint import CarbonConstraint
from constraints.crew_constraint import CrewDutyConstraint
from constraints.safety_constraint import SafetyRiskConstraint
from decision_engine.engine import DecisionEngine
from explainability.explainer import DecisionExplainer
from ml.risk_model import MLRiskPredictor
from models.decision_result import DecisionResult
from models.factory import build_flight_from_json
from normalization.parameter_normalizer import normalize_parameters
from policies.policy_loader import load_policy
from risk_prediction.historical_disruption import (
    compute_historical_disruption_score,
)
from technical_risk.technical_risk import compute_technical_risk


SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def generate_decision(
    raw: dict,
    airline_code: str = "indigo"
) -> DecisionResult:
    """
    Generate a flight recommendation from raw flight input data.

    This function contains the complete business pipeline and does not
    read files or print output.
    """

    # 1. Load airline policy
    policy_path = os.path.join(
        SRC_DIR,
        "policies",
        f"{airline_code}.json"
    )

    policy = load_policy(policy_path)
    weights = policy["weights"]

    # 2. Configure hard constraints
    constraints = [
        CrewDutyConstraint(max_delay_minutes=180),
        SafetyRiskConstraint(max_allowed_risk=0.7),
        CarbonConstraint(max_carbon_kg=300.0),
    ]

    engine = DecisionEngine(weights, constraints)
    explainer = DecisionExplainer()

    # 3. Convert raw input into domain models
    flight = build_flight_from_json(raw)

    aircraft = flight.aircraft
    crew = flight.crew
    distance_km = flight.distance_km

    # 4. Calculate rule-based risks
    technical_risk = compute_technical_risk(
        aircraft=aircraft,
        technical_cancellations=(
            raw["history"]["technical_cancellations"]
        ),
    )

    historical_disruption = compute_historical_disruption_score(
        **raw["history"]
    )

    rule_based_risk = round(
        0.6 * technical_risk
        + 0.4 * historical_disruption,
        3,
    )

    # 5. Calculate ML risk
    ml_predictor = MLRiskPredictor()

    ml_features = np.array([
        aircraft.age_years,
        aircraft.technical_failure_rate,
        aircraft.avg_tech_delay_min,
        raw["history"]["past_delays"],
        raw["history"]["past_cancellations"],
        raw["history"]["technical_cancellations"],
        crew.duty_hours_today / crew.max_duty_hours,
        flight.scheduled_delay_min,
    ])

    ml_risk = ml_predictor.predict_risk(ml_features)

    # 6. Combine rule-based and ML risks
    overall_operational_risk = round(
        0.7 * rule_based_risk + 0.3 * ml_risk,
        3,
    )

    # 7. Estimate carbon emissions
    carbon_emission = CarbonEstimator(
        aircraft.emission_factor
    ).estimate(distance_km)

    # 8. Build decision options
    options = [
        {
            "action": "delay_flight",
            "parameters": {
                "delay": flight.scheduled_delay_min,
                "carbon": carbon_emission,
                "technical_risk": overall_operational_risk,
                "crew_compliance": (
                    1
                    if crew.duty_hours_today < crew.max_duty_hours
                    else 0
                ),
                "cancellation_impact": 0,
            },
        },
        {
            "action": "cancel_flight",
            "parameters": {
                "delay": 0,
                "carbon": 0,
                "technical_risk": overall_operational_risk,
                "crew_compliance": 1,
                "cancellation_impact": 1,
            },
        },
    ]

    # 9. Normalize parameters for weighted scoring
    for option in options:
        option["normalized_parameters"] = normalize_parameters(
            option["parameters"]
        )

    # 10. Generate recommendation and explanation
    decision = engine.recommend(options)
    explanation = explainer.explain(
        decision,
        options,
        weights,
    )

    # 11. Return the final structured result
    return DecisionResult(
        flight_id=flight.flight_id,
        recommended_action=decision["recommended_action"],
        normalized_scores=decision["normalized_scores"],
        raw_scores=decision["raw_scores"],
        explanation={
            **explanation,
            "ml_risk": ml_risk,
            "rule_based_risk": rule_based_risk,
            "overall_operational_risk": overall_operational_risk,
        },
        decision_time=datetime.now(timezone.utc),
    )