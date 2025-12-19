# models/airport.py
from dataclasses import dataclass

@dataclass
class Airport:
    code: str
    congestion_level: float  # 0–1
    weather_severity: float  # 0–1
    curfew_active: bool
