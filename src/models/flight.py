# models/flight.py
from dataclasses import dataclass
from models.aircraft import Aircraft
from models.crew import Crew
from models.airport import Airport

@dataclass
class Flight:
    flight_id: str
    origin: Airport
    destination: Airport
    distance_km: int
    aircraft: Aircraft
    crew: Crew
    scheduled_delay_min: int
    passenger_count: int
