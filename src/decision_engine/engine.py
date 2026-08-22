from math import isclose, isfinite
from numbers import Real


class DecisionEngine:
    def __init__(self, weights: dict, constraints: list | None = None):
        self.weights = self._validate_weights(weights)
        self.constraints = constraints or []

    @staticmethod
    def _validate_weights(weights: dict) -> dict:
        if not weights:
            raise ValueError("Decision weights must not be empty")

        validated = {}
        # the bool check is necessary because python considers bool a subclass of int
        for parameter_name, weight in weights.items():
            if (
                not isinstance(weight, Real)
                or isinstance(weight, bool)
                or not isfinite(weight)
                or weight < 0
            ):
                raise ValueError(
                    f"Weight for '{parameter_name}' must be a finite, "
                    "non-negative number"
                )
            validated[parameter_name] = float(weight)

        if not isclose(
            sum(validated.values()),
            1.0,
            rel_tol=1e-9,
            abs_tol=1e-9,
        ):
            raise ValueError("Decision weights must sum to 1.0")

        return validated

    def score_option(self, normalized_parameters: dict) -> float:
        missing_parameters = self.weights.keys() - normalized_parameters.keys()
        if missing_parameters:
            missing = ", ".join(sorted(missing_parameters))
            raise ValueError(
                f"Missing normalized decision parameters: {missing}"
            )

        score = 0.0
        for parameter_name, weight in self.weights.items():
            normalized_value = normalized_parameters[parameter_name]
            if (
                not isinstance(normalized_value, Real)
                or isinstance(normalized_value, bool)
                or not isfinite(normalized_value)
                or not 0 <= normalized_value <= 1
            ):
                raise ValueError(
                    f"Normalized value for '{parameter_name}' must be "
                    "between 0 and 1"
                )
            score += weight * normalized_value

        return score

    def _normalize_scores(self, scored: list) -> list:
        scores = [score for _, score in scored]
        minimum_score = min(scores)
        maximum_score = max(scores)

        if maximum_score == minimum_score:
            return [(action, 0.0) for action, _ in scored]

        return [
            (
                action,
                round(
                    (score - minimum_score)
                    / (maximum_score - minimum_score),
                    3,
                ),
            )
            for action, score in scored
        ]

    def recommend(self, options: list) -> dict:
        if not options:
            raise ValueError("At least one decision option is required")

        valid_options = [
            option
            for option in options
            if all(
                constraint.is_allowed(option)
                for constraint in self.constraints
            )
        ]

        if not valid_options:
            return {
                "recommended_action": None,
                "normalized_scores": [],
                "raw_scores": [],
                "reason": "All options violate constraints",
            }

        scored = [
            (
                option["action"],
                self.score_option(option["normalized_parameters"]),
            )
            for option in valid_options
        ]
        normalized = self._normalize_scores(scored)

        recommended_action = min(scored, key=lambda item: item[1])[0]

        return {
            "recommended_action": recommended_action,
            "normalized_scores": normalized,
            "raw_scores": scored,
            "reason": None,
        }
