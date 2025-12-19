# models/decision_result.py
from dataclasses import dataclass
from typing import List, Tuple
from datetime import datetime

@dataclass
class DecisionResult:
    flight_id: str
    recommended_action: str
    normalized_scores: List[Tuple[str, float]]
    raw_scores: List[Tuple[str, float]]
    explanation: dict
    decision_time: datetime


