from models.flight import Flight
from models.aircraft import Aircraft
from models.crew import Crew
from models.airport import Airport

def build_flight_from_json(data: dict) -> Flight:
    aircraft = Aircraft(**data["aircraft"])
    crew = Crew(**data["crew"])
    origin = Airport(**data["origin"])
    destination = Airport(**data["destination"])

    return Flight(
        flight_id=data["flight_id"],
        origin=origin,
        destination=destination,
        distance_km=data["distance_km"],
        aircraft=aircraft,
        crew=crew,
        scheduled_delay_min=data["scheduled_delay_min"],
        passenger_count=data["passenger_count"]
    )
