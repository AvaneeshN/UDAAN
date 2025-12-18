from decision_engine.engine import DecisionEngine
from carbon_model.carbon_estimator import CarbonEstimator
from technical_risk.technical_risk import compute_technical_risk
from risk_prediction.historical_disruption import compute_historical_disruption_score
from policies.policy_loader import load_policy
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_flight_data(path: str):
    with open(path, "r") as f:
        return json.load(f)


def main():
    # 1️⃣ Load airline policy
    airline_code = "indigo"  # can be changed to "airindia"
    policy_path = os.path.join(BASE_DIR, "policies", f"{airline_code}.json")
    policy = load_policy(policy_path)
    policy = load_policy(policy_path)
    weights = policy["weights"] 



    engine = DecisionEngine(weights)

    # 2️⃣ Load flight input data
    flight_data_path = os.path.join(os.path.dirname(BASE_DIR), "data", "flight_input.json")
    flight_data = load_flight_data(flight_data_path)


    # 3️⃣ Carbon estimation
    carbon_estimator = CarbonEstimator(emission_factor=0.1)
    estimated_carbon = carbon_estimator.estimate(
        flight_data["flight_distance_km"]
    )

    # 4️⃣ Technical risk calculation
    technical_risk = compute_technical_risk(
        **flight_data["aircraft"]
    )

    # 5️⃣ Historical disruption calculation
    historical_disruption = compute_historical_disruption_score(
        **flight_data["history"]
    )

    # 6️⃣ Aggregate operational risk
    overall_operational_risk = (
        0.6 * technical_risk +
        0.4 * historical_disruption
    )

    # 7️⃣ Decision options
    options = [
        {
            "action": "delay_flight",
            "parameters": {
                "delay": flight_data["delay_minutes"],
                "carbon": estimated_carbon,
                "technical_risk": technical_risk,
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

    # 8️⃣ Recommendation
    decision = engine.recommend(options)

    print("\nDecision:", decision)
    print("Technical Risk:", round(technical_risk, 3))
    print("Historical Disruption:", round(historical_disruption, 3))
    print("Overall Operational Risk:", round(overall_operational_risk, 3))


if __name__ == "__main__":
    main()
