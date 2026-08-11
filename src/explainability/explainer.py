class DecisionExplainer:
    def explain(
        self,
        decision: dict,
        options: list,
        weights: dict
    ) -> dict:
        explanation = {
            "recommended_action": decision["recommended_action"],
            "reasoning": []
        }

        if decision["recommended_action"] is None:
            explanation["reasoning"].append(
                "All available options violated safety or regulatory constraints."
            )
            return explanation

        for action, score in decision["raw_scores"]:
            option = next(option for option in options if option["action"] == action)

            raw_parameters = option["parameters"]
            normalized_parameters = option["normalized_parameters"]

            breakdown = {
                "action": action,
                "score": round(score, 3),
                "raw_parameters": raw_parameters,
                "normalized_parameters": normalized_parameters,
                "contributions": {}
            }
            for parameter_name, weight in weights.items():
                normalized_value = normalized_parameters.get(parameter_name, 0)
                contribution = weight* normalized_value
                breakdown["contributions"][parameter_name] = round(contribution, 3)
            explanation["reasoning"].append(breakdown)
        explanation["final_decision_reason"] = (
            f"{decision['recommended_action']} has the lowest overall "
            "normalized operational penalty after constraint filtering."
        )

        return explanation
