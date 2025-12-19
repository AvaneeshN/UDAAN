import numpy as np
from models.flight import Flight

def extract_features(
    flight: Flight,
    technical_risk: float,
    historical_disruption: float
) -> np.ndarray:
    """
    Feature vector MUST match training order exactly
    """

    return np.array([
        flight.distance_km,                          # 1
        flight.aircraft.age_years,                   # 2
        flight.aircraft.technical_failure_rate,      # 3
        flight.aircraft.avg_tech_delay_min,          # 4
        flight.crew.duty_hours_today,                # 5
        technical_risk,                              # 6
        historical_disruption,                       # 7
        flight.passenger_count                       # 8
    ], dtype=float)
