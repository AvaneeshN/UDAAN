class CarbonEstimator:
    def __init__(self, emission_factor: float):
        """
        emission_factor: kg CO2 emitted per km
        Typical values:
        - Narrow body aircraft: ~0.09–0.12
        """
        self.emission_factor = emission_factor

    def estimate(self, distance_km: float) -> float:
        """
        Estimates total carbon emissions for a flight
        """
        carbon_emission = distance_km * self.emission_factor
        return carbon_emission
