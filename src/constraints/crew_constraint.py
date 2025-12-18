from .base_constraint import BaseConstraint

class CrewDutyConstraint(BaseConstraint):
    def __init__(self, max_delay_minutes: int):
        self.max_delay_minutes = max_delay_minutes

    def is_allowed(self, option: dict) -> bool:
        delay = option["parameters"].get("delay", 0)
        crew_ok = option["parameters"].get("crew_compliance", 0)

        # Crew already illegal
        if crew_ok == 0:
            return False

        # Delay exceeds allowed crew buffer
        if delay > self.max_delay_minutes:
            return False

        return True
