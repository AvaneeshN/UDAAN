class DecisionEngine:
    def __init__(self, weights: dict, constraints: list = None):
        self.weights = weights
        self.constraints = constraints or []

    def score_option(self, parameters: dict) -> float:
        """
        parameters: values for each factor
        example:
        {
            'delay': 120,
            'carbon': 300,
            'technical_risk': 0.4,
            'crew_compliance': 1
        }
        """
        score = 0.0
        for key, weight in self.weights.items():
            score += weight * parameters.get(key, 0)
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
                "reason": "All options violate constraints"
            }

        # 2️⃣ Score valid options
        scored = []
        for option in valid_options:
            score = self.score_option(option['parameters'])
            scored.append((option['action'], score))

        # 3️⃣ Normalize scores
        normalized = self._normalize_scores(scored)

        # 4️⃣ Choose best option
        recommended_action = min(normalized, key=lambda x: x[1])[0]

        return {
            "recommended_action": recommended_action,
            "normalized_scores": normalized,
            "raw_scores": scored
        }
