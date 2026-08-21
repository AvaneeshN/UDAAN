from collections.abc import Mapping

import numpy as np

from models.flight import Flight


FEATURE_NAMES = (
    "aircraft_age_years",
    "technical_failure_rate",
    "average_technical_delay_minutes",
    "crew_duty_hours_today",
    "past_delays",
    "past_cancellations",
    "technical_cancellations",
    "recent_disruptions",
)

HISTORY_FEATURE_NAMES = FEATURE_NAMES[4:]


def extract_features(
    flight: Flight,
    history: Mapping[str, int],
) -> np.ndarray:
    """Build the feature vector in the model's training order."""
    missing_history = set(HISTORY_FEATURE_NAMES) - history.keys()
    if missing_history:
        missing = ", ".join(sorted(missing_history))
        raise ValueError(f"Missing ML history features: {missing}")

    return np.array([
        flight.aircraft.age_years,
        flight.aircraft.technical_failure_rate,
        flight.aircraft.avg_tech_delay_min,
        flight.crew.duty_hours_today,
        history["past_delays"],
        history["past_cancellations"],
        history["technical_cancellations"],
        history["recent_disruptions"],
    ], dtype=float)
