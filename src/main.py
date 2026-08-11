from decision_engine.engine import DecisionEngine
from carbon_model.carbon_estimator import CarbonEstimator
from technical_risk.technical_risk import compute_technical_risk
from risk_prediction.historical_disruption import compute_historical_disruption_score
from policies.policy_loader import load_policy
from constraints.crew_constraint import CrewDutyConstraint
from constraints.carbon_constraint import CarbonConstraint
from constraints.safety_constraint import SafetyRiskConstraint
from explainability.explainer import DecisionExplainer
from ingestion.json_ingestor import load_json_data
from models.factory import build_flight_from_json
from models.decision_result import DecisionResult
from normalization.parameter_normalizer import normalize_parameters
from ml.risk_model import MLRiskPredictor

from datetime import datetime, timezone
import numpy as np
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))



def main():
    # 1️⃣ Policy
    airline_code = "indigo"
    policy = load_policy(os.path.join(BASE_DIR, "policies", f"{airline_code}.json"))

    weights = policy["weights"]

    constraints = [
        CrewDutyConstraint(max_delay_minutes=180),
        SafetyRiskConstraint(max_allowed_risk=0.7)
    ]

    engine = DecisionEngine(weights, constraints)
    explainer = DecisionExplainer()

    # 2️⃣ Load raw input data
    input_path = os.path.join(
        os.path.dirname(BASE_DIR), 
        "data",
        "flight_input.json"
    )

    raw = load_json_data(input_path)

    # 3️⃣ Convert raw data into domain models
    flight = build_flight_from_json(raw)
    aircraft = flight.aircraft
    crew = flight.crew
    distance_km = flight.distance_km

    # 4️⃣ Rule-based risks
    technical_risk = compute_technical_risk(
        aircraft=aircraft,
        technical_cancellations=raw["history"]["technical_cancellations"]
    )

    historical_disruption = compute_historical_disruption_score(**raw["history"])

    rule_based_risk = round(
        0.6 * technical_risk + 0.4 * historical_disruption, 3
    )

    # 5️⃣ ML Risk (Step 14)
    ml_predictor = MLRiskPredictor()

    ml_features = np.array([
        aircraft.age_years,
        aircraft.technical_failure_rate,
        aircraft.avg_tech_delay_min,
        raw["history"]["past_delays"],
        raw["history"]["past_cancellations"],
        raw["history"]["technical_cancellations"],
        crew.duty_hours_today / crew.max_duty_hours,
        flight.scheduled_delay_min
    ])

    ml_risk = ml_predictor.predict_risk(ml_features)

    # 6️⃣ Hybrid risk (ML assists, does not decide)
    overall_operational_risk = round(
        0.7 * rule_based_risk + 0.3 * ml_risk, 3
    )

    # 7️⃣ Carbon
    carbon_emission = CarbonEstimator(aircraft.emission_factor).estimate(distance_km)

    # 8️⃣ Options
    options = [
        {
            "action": "delay_flight",
            "parameters": {
                "delay": flight.scheduled_delay_min,
                "carbon": carbon_emission,
                "technical_risk": overall_operational_risk,
                "crew_compliance": 1 if crew.duty_hours_today < crew.max_duty_hours else 0,
                "cancellation_impact": 0
            }
        },
        {
            "action": "cancel_flight",
            "parameters": {
                "delay": 0,
                "carbon": 0,
                "technical_risk": overall_operational_risk,
                "crew_compliance": 1,
                "cancellation_impact":1
            }
        }
    ]

    #Normalize parametres for fair weighted scoring
    
    for option in options:
        option["normalized_parameters"] = normalize_parameters(option["parameters"])

    # 9️⃣ Decision
    decision = engine.recommend(options)
    explanation = explainer.explain(decision, options, weights)

    result = DecisionResult(
        flight_id=flight.flight_id,
        recommended_action=decision["recommended_action"],
        normalized_scores=decision["normalized_scores"],
        raw_scores=decision["raw_scores"],
        explanation={
            **explanation,
            "ml_risk": ml_risk,
            "rule_based_risk": rule_based_risk,
            "overall_operational_risk": overall_operational_risk
        },
        decision_time=datetime.now(timezone.utc)
    )

    # 🔟 Output
    print("\n--- Decision Explanation ---")
    for r in explanation["reasoning"]:
        print(r)

    print("\nFinal Decision:", result.recommended_action)
    print("Rule-Based Risk:", rule_based_risk)
    print("ML Risk:", ml_risk)
    print("Overall Risk:", overall_operational_risk)


if __name__ == "__main__":
    main()
