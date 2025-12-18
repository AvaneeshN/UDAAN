class BaseConstraint:
    def is_allowed(self, option: dict) -> bool:
        raise NotImplementedError("Constraint must implement is_allowed()")

