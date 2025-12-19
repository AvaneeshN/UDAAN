import json
from models.aircraft import Aircraft
from models.crew import Crew
from models.airport import Airport
from models.flight import Flight


def load_flight_data(path: str) -> Flight:
    with open(path, "r") as f:
        raw = json.load(f)

    aircraft = Aircraft(
        aircraft_id=raw["aircraft"]["aircraft_id"],
        aircraft_type=raw["aircraft"]["aircraft_type"],
        age_years=raw["aircraft"]["age_years"],
        emission_factor=raw["aircraft"]["emission_factor"],
        technical_failure_rate=raw["aircraft"]["technical_failure_rate"],
        avg_tech_delay_min=raw["aircraft"]["avg_tech_delay_min"]
    )

    crew = Crew(
        crew_id=raw["crew"]["crew_id"],
        duty_hours_today=raw["crew"]["duty_hours_today"],
        max_duty_hours=raw["crew"]["max_duty_hours"]
    )

    origin = Airport(
        code=raw["origin"]["code"],
        congestion_level=0.5,
        weather_severity=0.4,
        curfew_active=False
    )

    destination = Airport(
        code=raw["destination"]["code"],
        congestion_level=0.6,
        weather_severity=0.3,
        curfew_active=False
    )

    return Flight(
        flight_id=raw["flight_id"],
        origin=origin,
        destination=destination,
        distance_km=raw.get("distance_km", 1500),
        aircraft=aircraft,
        crew=crew,
        scheduled_delay_min=raw["delay_minutes"],
        passenger_count=raw["passenger_count"]
    )
