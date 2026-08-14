import { useState } from "react";


function FlightForm({ onSubmit }) {
  const [airlineCode, setAirlineCode] = useState("indigo");
  const [flightId, setFlightId] = useState("");

  function handleSubmit(event) {
    event.preventDefault();

    const flightData = {
      airline_code: airlineCode,
      flight_id: flightId.trim(),
    };

    onSubmit(flightData);
  }

  return (
    <section>
      <h2>Flight Details</h2>

      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="airline-code">
            Airline
          </label>

          <select
            id="airline-code"
            name="airline_code"
            value={airlineCode}
            onChange={(event) =>
              setAirlineCode(event.target.value)
            }
          >
            <option value="indigo">IndiGo</option>
            <option value="airindia">Air India</option>
          </select>
        </div>

        <div>
          <label htmlFor="flight-id">
            Flight ID
          </label>

          <input
            id="flight-id"
            name="flight_id"
            type="text"
            placeholder="For example, 6E-203"
            value={flightId}
            onChange={(event) =>
              setFlightId(event.target.value)
            }
          />
        </div>

        <p>
          Current selection: {airlineCode} —{" "}
          {flightId || "No flight ID entered"}
        </p>

        <button
          type="submit"
          disabled={!flightId.trim()}
        >
          Continue
        </button>
      </form>
    </section>
  );
}


export default FlightForm;