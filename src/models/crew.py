# models/crew.py
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Crew:
    crew_id: str
    duty_hours_today: float
    max_duty_hours: float   # add this
