from pydantic import BaseModel, Field
#Field is used to add validation constraints to the model attributes.
from typing import Literal

class AirportInput(BaseModel):
  code: str = Field(min_length = 3 , max_length = 4)
  name: str | None = None
# | symbol is used for type hinting to indicate that the attribute can be of type str or None.

class AircraftInput(BaseModel):
  aircraft_id: str
  aircraft_type: str
  age_years: int = Field(ge = 0)
  emission_factor: float = Field(ge = 0)
  technical_failure_rate: float = Field(ge = 0, le =1)
  avg_tech_delay_min: int = Field(ge=0)

class CrewInput(BaseModel):
  crew_id: str
  duty_hours_today: float = Field(ge = 0)
  max_duty_hours: float = Field(gt = 0)

class FlightHistoryInput(BaseModel):
    past_delays: int = Field(ge=0)
    past_cancellations: int = Field(ge=0)
    technical_cancellations: int = Field(ge=0)
    recent_disruptions: int = Field(ge=0)


class FlightDecisionRequest(BaseModel):
    airline_code: Literal["indigo" , "airindia"] = "indigo"
    flight_id: str
    delay_minutes: int = Field(ge=0)
    passenger_count: int = Field(ge=0)
    distance_km: float = Field(default=1500, gt=0)
    origin: AirportInput
    destination: AirportInput
    aircraft: AircraftInput
    crew: CrewInput
    history: FlightHistoryInput