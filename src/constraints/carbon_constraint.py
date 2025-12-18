from .base_constraint import Constraint

class CarbonConstraint(Constraint):
    def __init__(self, max_carbon_kg: float):
        self.max_carbon_kg = max_carbon_kg

    def is_allowed(self, option: dict) -> bool:
        carbon = option["parameters"].get("carbon", 0)
        return carbon <= self.max_carbon_kg
