class CarbonEstimator:
    def __init__(self, emission_factor: float):
        self.emission_factor = emission_factor

    def estimate(self, distance_km: float) -> float:
        return round(distance_km * self.emission_factor, 3)



