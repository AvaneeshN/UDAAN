from models.flight import Flight
from models.aircraft import Aircraft
from models.crew import Crew
from models.airport import Airport


def build_flight_from_json(data: dict) -> Flight:

    # 1. Create Aircraft object
    aircraft = Aircraft(**data["aircraft"])

    # 2. Create Crew object
    crew = Crew(**data["crew"])

    # 3. Create Origin Airport
    origin = Airport(
        code=data["origin"]["code"],
        congestion_level=data["origin"].get("congestion_level", 0.5),
        weather_severity=data["origin"].get("weather_severity", 0.4),
        curfew_active=data["origin"].get("curfew_active", False)
    )

    # 4. Create Destination Airport
    destination = Airport(
        code=data["destination"]["code"],
        congestion_level=data["destination"].get("congestion_level", 0.6),
        weather_severity=data["destination"].get("weather_severity", 0.3),
        curfew_active=data["destination"].get("curfew_active", False)
    )

    # 5. Create and return Flight object
    flight = Flight(
        flight_id=data["flight_id"],
        origin=origin,
        destination=destination,
        distance_km=data.get("distance_km", 1500),
        aircraft=aircraft,
        crew=crew,
        scheduled_delay_min=data["delay_minutes"],
        passenger_count=data["passenger_count"]
    )

    return flight