import os

from ingestion.json_ingestor import load_json_data
from services.decision_service import generate_decision


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def main():
    input_path = os.path.join(
        os.path.dirname(BASE_DIR),
        "data",
        "flight_input.json",
    )

    raw = load_json_data(input_path)
    result = generate_decision(raw, airline_code="indigo")

    print("\n--- Decision Explanation ---")

    for reasoning in result.explanation["reasoning"]:
        print(reasoning)

    print("\nFinal Decision:", result.recommended_action)
    print(
        "Rule-Based Risk:",
        result.explanation["rule_based_risk"],
    )
    print(
        "ML Risk:",
        result.explanation["ml_risk"],
    )
    print(
        "Overall Risk:",
        result.explanation["overall_operational_risk"],
    )


if __name__ == "__main__":
    main()