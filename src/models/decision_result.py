# models/decision_result.py
from dataclasses import dataclass
from typing import List, Tuple, Optional
from datetime import datetime

@dataclass
class DecisionResult:
    flight_id: str
    recommended_action: Optional[str]  # "DELAY", "CANCEL", "REROUTE", or None if no valid action
    normalized_scores: List[Tuple[str, float]]
    raw_scores: List[Tuple[str, float]]
    explanation: dict
    decision_time: datetime


