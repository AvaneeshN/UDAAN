# models/aircraft.py
from dataclasses import dataclass

@dataclass
class Aircraft:
    aircraft_id: str
    aircraft_type: str
    age_years: int
    emission_factor: float  # kg CO₂ per km
    technical_failure_rate: float  # 0–1
    avg_tech_delay_min: int
