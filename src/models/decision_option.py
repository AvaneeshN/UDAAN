# models/decision_option.py
from dataclasses import dataclass
from typing import Dict
from models.flight import Flight

@dataclass
class DecisionOption:
    option_id: str
    flight: Flight
    action: str  # "DELAY", "CANCEL", "REROUTE"
    parameters: Dict[str, float]
