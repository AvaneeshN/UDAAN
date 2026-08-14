from dataclasses import asdict
from fastapi import FastAPI
from api.schemas import FlightDecisionRequest
from services.decision_service import generate_decision
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI(
  title="UDAAN decision api",
  description="Operational flight decision-support API",
  version="0.1.0",
)
app.add_middleware(CORSMiddleware, allow_origins = ["http://localhost:5173",
        "http://127.0.0.1:5173",], allow_credentials = True, allow_methods = ["*"] , allow_headers = ["*"]
)
@app.get("/api/health", tags=["System"])
def health_check():
  return {"status":"ok",
          "service":"UDAAN decision API",}

@app.post("/api/decisions", tags=["Decisions"])
def create_decision(request_data: FlightDecisionRequest):
    raw_data = request_data.model_dump()
    airline_code = raw_data.pop("airline_code")

    result = generate_decision(
        raw=raw_data,
        airline_code="indigo",
    )

    return asdict(result)