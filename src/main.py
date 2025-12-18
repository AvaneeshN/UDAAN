from decision_engine.engine import DecisionEngine

def main():
    weights = {
        'delay': 0.3,
        'carbon': 0.2,
        'technical_risk': 0.25,
        'crew_compliance': 0.25
    }

    engine = DecisionEngine(weights)

    options = [
        {
            "action": "delay_flight",
            "parameters": {
                "delay": 120,
                "carbon": 200,
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
