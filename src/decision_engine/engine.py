class DecisionEngine:
    def __init__(self, weights: dict):
        """
        weights: importance of each factor in decision making
        example:
        {
            'delay': 0.3,
            'carbon': 0.2,
            'technical_risk': 0.25,
            'crew_compliance': 0.25
        }
        """
        self.weights = weights

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

    def recommend(self, options: list) -> dict:
        """
        options: list of possible actions with parameters
        """
        scored = []
        for option in options:
            score = self.score_option(option['parameters'])
            scored.append((option['action'], score))

        scored.sort(key=lambda x: x[1])
        return {
            "recommended_action": scored[0][0],
            "all_scores": scored
        }
