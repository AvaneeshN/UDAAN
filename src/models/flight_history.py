# models/flight_history.py
from dataclasses import dataclass
from datetime import datetime

@dataclass
class FlightHistory:
    flight_id: str
    decision_taken: str
    actual_outcome: str  # "ON_TIME", "DELAYED", "CANCELLED"
    actual_delay_min: int
    carbon_emitted: float
    incident_reported: bool
    timestamp: datetime
