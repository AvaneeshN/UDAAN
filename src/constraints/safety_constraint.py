from .base_constraint import BaseConstraint

class SafetyRiskConstraint(BaseConstraint):
    def __init__(self, max_allowed_risk: float):
        self.max_allowed_risk = max_allowed_risk

    def is_allowed(self, option: dict) -> bool:
        #cancellation does not operate the aircraft
        if option.get("action") == "cancel_flight":
            return True
        risk = option["parameters"].get("technical_risk", 0)

        return risk <= self.max_allowed_risk
