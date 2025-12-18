from decision_engine.engine import DecisionEngine
from carbon_model.carbon_estimator import CarbonEstimator
from technical_risk.technical_risk import compute_technical_risk
from risk_prediction.historical_disruption import compute_historical_disruption_score
from policies.policy_loader import load_policy
from constraints.crew_constraint import CrewDutyConstraint
from constraints.safety_constraint import SafetyRiskConstraint

import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_flight_data(path: str):
    with open(path, "r") as f:
        return json.load(f)


def main():
    # 1️⃣ Load airline policy
    airline_code = "indigo"  # can switch to "airindia"
    policy_path = os.path.join(BASE_DIR, "policies", f"{airline_code}.json")
    policy = load_policy(policy_path)

    weights = policy["weights"]
    emission_factor = policy.get("emission_factor", 0.1)

    constraints = [
    CrewDutyConstraint(max_delay_minutes=180),
    SafetyRiskConstraint(max_allowed_risk=0.7)
    ]

    # 2️⃣ Initialize decision engine (constraints can be added later)
    engine = DecisionEngine(
    weights=weights,
    constraints=constraints
    )
    # 3️⃣ Load flight input data
    flight_data_path = os.path.join(
        os.path.dirname(BASE_DIR), "data", "flight_input.json"
    )
    flight_data = load_flight_data(flight_data_path)

    # 4️⃣ Carbon estimation
    carbon_estimator = CarbonEstimator(emission_factor=emission_factor)
    estimated_carbon = carbon_estimator.estimate(
        flight_data["flight_distance_km"]
    )

    # 5️⃣ Technical risk calculation
    technical_risk = compute_technical_risk(
        **flight_data["aircraft"]
    )

    # 6️⃣ Historical disruption calculation
    historical_disruption = compute_historical_disruption_score(
        **flight_data["history"]
    )

    # 7️⃣ Aggregate operational risk (used consistently)
    overall_operational_risk = (
        0.6 * technical_risk +
        0.4 * historical_disruption
    )

    # 8️⃣ Decision options (same risk basis for fairness)
    options = [
        {
            "action": "delay_flight",
            "parameters": {
                "delay": flight_data["delay_minutes"],
                "carbon": estimated_carbon,
                "technical_risk": overall_operational_risk,
                "crew_compliance": flight_data["crew_compliance"]
            }
        },
        {
            "action": "cancel_flight",
            "parameters": {
                "delay": 0,
                "carbon": 0,
                "technical_risk": overall_operational_risk,
                "crew_compliance": flight_data["crew_compliance"]
            }
        }
    ]

    # 9️⃣ Recommendation
    decision = engine.recommend(options)

    print("\nDecision:", decision)
    print("Technical Risk:", round(technical_risk, 3))
    print("Historical Disruption:", round(historical_disruption, 3))
    print("Overall Operational Risk:", round(overall_operational_risk, 3))


if __name__ == "__main__":
    main()
