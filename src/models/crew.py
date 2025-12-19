# models/crew.py
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Crew:
    crew_id: str
    role: str  # Captain / FO / Cabin
    duty_hours_today: float
    last_rest_end: datetime
    compliance_score: int  # 1 = legal, 0 = violation
