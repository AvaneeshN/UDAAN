class DecisionEngine:
    def __init__(self, weights: dict, constraints: list = None):
        self.weights = weights
        self.constraints = constraints or []

    def score_option(self, normalized_parameters: dict) -> float:
        """
        normalized_parameters: values for each factor (normalized to 0-1)
        example:
        {
            'delay': 0.5,
            'carbon': 0.8,
            'technical_risk': 0.3,
            'crew_compliance': 1.0
        }
        """
        score = 0.0
        for parameter_name, weight in self.weights.items():
            normalized_value = normalized_parameters.get(parameter_name , 0)
            score += weight * normalized_value
        return score

    def _normalize_scores(self, scored: list) -> list:
        """
        scored: list of (action, raw_score)
        returns: list of (action, normalized_score)
        """
        scores = [score for _, score in scored]
        min_score = min(scores)
        max_score = max(scores)

        if max_score == min_score:
            return [(action, 0.0) for action, _ in scored]

        normalized = []
        for action, score in scored:
            norm = (score - min_score) / (max_score - min_score)
            normalized.append((action, round(norm, 3)))

        return normalized

    def recommend(self, options: list) -> dict:
        valid_options = []

        # 1️⃣ Apply constraints FIRST
        for option in options:
            if all(c.is_allowed(option) for c in self.constraints):
                valid_options.append(option)

        if not valid_options:
            return {
                "recommended_action": None,
                "normalized_scores": [],
                "raw_scores":[],
                "reason": "All options violate constraints"
            }

        # 2️⃣ Score valid options
        scored = []
        for option in valid_options:
            score = self.score_option(option["normalized_parameters"])
            scored.append((option["action"], score))

        # 3️⃣ Normalize scores
        normalized = self._normalize_scores(scored)

        # 4️⃣ Choose best option
        recommended_action = min(normalized, key=lambda x: x[1])[0]

        return {
            "recommended_action": recommended_action,
            "normalized_scores": normalized,
            "raw_scores": scored,
            "reason": None
        }
