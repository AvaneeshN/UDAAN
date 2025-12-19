from decision_engine.engine import DecisionEngine
from carbon_model.carbon_estimator import CarbonEstimator
from technical_risk.technical_risk import compute_technical_risk
from risk_prediction.historical_disruption import compute_historical_disruption_score
from policies.policy_loader import load_policy
from constraints.crew_constraint import CrewDutyConstraint
from constraints.safety_constraint import SafetyRiskConstraint
from explainability.explainer import DecisionExplainer

from models.aircraft import Aircraft
from models.crew import Crew
from models.airport import Airport
from models.flight import Flight
from models.decision_result import DecisionResult

from datetime import datetime
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_json(path: str):
    with open(path, "r") as f:
        return json.load(f)


def main():
    # 1️⃣ Load airline policy
    airline_code = "indigo"
    policy = load_policy(os.path.join(BASE_DIR, "policies", f"{airline_code}.json"))

    weights = policy["weights"]

    constraints = [
        CrewDutyConstraint(max_delay_minutes=180),
        SafetyRiskConstraint(max_allowed_risk=0.7)
    ]

    engine = DecisionEngine(weights, constraints)
    explainer = DecisionExplainer()

    # 2️⃣ Load flight JSON
    raw = load_json(os.path.join(os.path.dirname(BASE_DIR), "data", "flight_input.json"))

    # 3️⃣ Build domain models
    aircraft = Aircraft(
        aircraft_id=raw["aircraft"]["aircraft_id"],
        aircraft_type=raw["aircraft"]["aircraft_type"],
        age_years=raw["aircraft"]["age_years"],
        emission_factor=raw["aircraft"]["emission_factor"],
        technical_failure_rate=raw["aircraft"]["technical_failure_rate"],
        avg_tech_delay_min=raw["aircraft"]["avg_tech_delay_min"]
    )

    crew = Crew(
        crew_id=raw["crew"]["crew_id"],
        duty_hours_today=raw["crew"]["duty_hours_today"],
        max_duty_hours=raw["crew"]["max_duty_hours"]
    )

    origin = Airport(
        code=raw["origin"]["code"],
        congestion_level=0.5,
        weather_severity=0.4,
        curfew_active=False
    )

    destination = Airport(
        code=raw["destination"]["code"],
        congestion_level=0.6,
        weather_severity=0.3,
        curfew_active=False
    )

    # ✅ Distance derived (not in JSON by design)
    distance_km = 1500

    flight = Flight(
        flight_id=raw["flight_id"],
        origin=origin,
        destination=destination,
        distance_km=distance_km,
        aircraft=aircraft,
        crew=crew,
        scheduled_delay_min=raw["delay_minutes"],
        passenger_count=raw["passenger_count"]
    )

    # 4️⃣ Risk calculations
    technical_risk = compute_technical_risk(
        aircraft=aircraft,
        technical_cancellations=raw["history"]["technical_cancellations"]
    )

    historical_disruption = compute_historical_disruption_score(
        **raw["history"]
    )

    overall_operational_risk = round(
        0.6 * technical_risk + 0.4 * historical_disruption, 3
    )

    # 5️⃣ Carbon
    carbon_estimator = CarbonEstimator(aircraft.emission_factor)
    carbon_emission = carbon_estimator.estimate(distance_km)

    # 6️⃣ Decision options
    options = [
        {
            "action": "delay_flight",
            "parameters": {
                "delay": flight.scheduled_delay_min,
                "carbon": carbon_emission,
                "technical_risk": overall_operational_risk,
                "crew_compliance": 1 if crew.duty_hours_today < crew.max_duty_hours else 0
            }
        },
        {
            "action": "cancel_flight",
            "parameters": {
                "delay": 0,
                "carbon": 0,
                "technical_risk": overall_operational_risk,
                "crew_compliance": 1
            }
        }
    ]

    # 7️⃣ Decision
    decision = engine.recommend(options)
    explanation = explainer.explain(decision, options, weights)

    result = DecisionResult(
        flight_id=flight.flight_id,
        recommended_action=decision["recommended_action"],
        normalized_scores=decision["normalized_scores"],
        raw_scores=decision["raw_scores"],
        explanation=explanation,
        decision_time=datetime.utcnow()
    )

    # 8️⃣ Output
    print("\n--- Decision Explanation ---")
    for r in explanation["reasoning"]:
        print(r)

    print("\nFinal Decision:", result.recommended_action)
    print("Technical Risk:", technical_risk)
    print("Historical Disruption:", historical_disruption)
    print("Overall Risk:", overall_operational_risk)


if __name__ == "__main__":
    main()
