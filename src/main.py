from decision_engine.engine import DecisionEngine
from carbon_model.carbon_estimator import CarbonEstimator


def main():
    weights = {
        'delay': 0.3,
        'carbon': 0.2,
        'technical_risk': 0.25,
        'crew_compliance': 0.25
    }

    engine = DecisionEngine(weights)
    carbon_estimator = CarbonEstimator(emission_factor=0.1)

    flight_distance_km = 1500  # example distance
    estimated_carbon = carbon_estimator.estimate(flight_distance_km)

    options = [
        {
            "action": "delay_flight",
            "parameters": {
                "delay": 120,
                "carbon": estimated_carbon,
                "technical_risk": 0.3,
                "crew_compliance": 1
            }
        },
        {
            "action": "cancel_flight",
            "parameters": {
                "delay": 0,
                "carbon": 0,
                "technical_risk": 0.6,
                "crew_compliance": 1
            }
        }
    ]

    decision = engine.recommend(options)
    print(decision)

if __name__ == "__main__":
    main()
