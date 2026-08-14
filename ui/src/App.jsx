import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import FlightForm from "./components/FlightForm";
import SystemStatus from "./components/SystemStatus";
import {
  clearDecision,
  createDecision,
} from "./features/decisions/decisionSlice";

import "./App.css";


const sampleFlightData = {
  airline_code: "indigo",
  flight_id: "6E-203",
  delay_minutes: 90,
  passenger_count: 180,
  distance_km: 1500,

  origin: {
    code: "DEL",
    name: "Delhi",
  },

  destination: {
    code: "BOM",
    name: "Mumbai",
  },

  aircraft: {
    aircraft_id: "VT-ABC",
    aircraft_type: "A320",
    age_years: 18,
    emission_factor: 0.1,
    technical_failure_rate: 0.3,
    avg_tech_delay_min: 25,
  },

  crew: {
    crew_id: "CRW-77",
    duty_hours_today: 7.5,
    max_duty_hours: 10,
  },

  history: {
    past_delays: 6,
    past_cancellations: 2,
    technical_cancellations: 1,
    recent_disruptions: 2,
  },
};


function App() {
  const dispatch = useDispatch();

  const { result, status, error } = useSelector(
    (state) => state.decision
  );

  const [backendStatus, setBackendStatus] =
    useState("Checking backend...");

  useEffect(() => {
    async function checkBackend() {
      try {
        const response = await fetch(
          "http://127.0.0.1:8000/api/health"
        );

        if (!response.ok) {
          throw new Error("Health check failed");
        }

        const data = await response.json();
        setBackendStatus(`${data.service}: ${data.status}`);
      } catch {
        setBackendStatus("Backend unavailable");
      }
    }

    checkBackend();
  }, []);

  function handleShowStatusDetails() {
  alert(`Current backend status: ${backendStatus}`);
}

  function handleFlightSubmit(flightData) {
    console.log("Submitted flight data:", flightData);

    alert(
      `Airline: ${flightData.airline_code}\n` +
     `Flight: ${flightData.flight_id}`
    );
}

  function handleGenerateDecision() {
    dispatch(createDecision(sampleFlightData));
  }

  return (
    <main>
      <h1>UDAAN</h1>
      <p>Intelligent Flight Decision Support System</p>

      <section>
        <SystemStatus
        status={backendStatus}
        onShowDetails={handleShowStatusDetails}
      />
      </section>
      <FlightForm onSubmit={handleFlightSubmit} />

      <section>
        <h2>Decision Engine Test</h2>

        <button
          onClick={handleGenerateDecision}
          disabled={status === "loading"}
        >
          {status === "loading"
            ? "Generating..."
            : "Generate Sample Decision"}
        </button>

        {error && <p className="error">{error}</p>}

        {result && (
          <div>
            <h3>Decision Result</h3>

            <p>
              Flight: <strong>{result.flight_id}</strong>
            </p>

            <p>
              Recommended action:{" "}
              <strong>{result.recommended_action}</strong>
            </p>

            <p>
              Overall risk:{" "}
              <strong>
                {
                  result.explanation
                    .overall_operational_risk
                }
              </strong>
            </p>

            <button onClick={() => dispatch(clearDecision())}>
              Clear Result
            </button>
          </div>
        )}
      </section>
    </main>
  );
}

export default App;