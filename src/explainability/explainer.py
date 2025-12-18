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
            breakdown = {
                "action": action,
                "score": round(score, 3),
                "contributions": {}
            }

            option = next(
                opt for opt in options if opt["action"] == action
            )

            for param, weight in weights.items():
                value = option["parameters"].get(param, 0)
                breakdown["contributions"][param] = round(
                    weight * value, 3
                )

            explanation["reasoning"].append(breakdown)

        explanation["final_decision_reason"] = (
            f"{decision['recommended_action']} has the lowest overall "
            "normalized operational penalty after constraint filtering."
        )

        return explanation
