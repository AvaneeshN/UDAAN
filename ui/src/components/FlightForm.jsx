import { useState } from "react";

function FlightForm({ onSubmit, isSubmitting = false }) {
  const [formData, setFormData] = useState({
    airline_code: "indigo",
    flight_id: "",
    delay_minutes : "",
    passenger_count: "",
    distance_km:"",
    origin: {
      code:"",
      name:"",
    },
    destination:{
      code:"",
      name:"",
    },

    aircraft :{
      aircraft_id : "",
      aircraft_type: "",
      age_years:"",
      emission_factor:"",
      technical_failure_rate:"",
      avg_tech_delay_min:"",
    },
    crew: {
      crew_id: "",
      duty_hours_today: "",
      max_duty_hours: "",
    },
    history: {
      past_delays: "",
      past_cancellations: "",
      technical_cancellations: "",
      recent_disruptions: "",
    },
  });

  const handleChange = (event) => {
    const { name, value } = event.target;

    setFormData((currentData) => ({
      ...currentData,
      [name]: value,
    }));
  };
  const handleNestedChange = (section , event) =>{
    const { name , value } = event.target;
    setFormData((currentData) =>({
      ...currentData,
      [section]:{
        ...currentData[section],
        [name]: value,
      },
    }));
  };

  function handleSubmit(event) {
    event.preventDefault();

    const flightData = {
      ...formData,
      flight_id: formData.flight_id.trim(),
      delay_minutes: Number(formData.delay_minutes),
      passenger_count: Number(formData.passenger_count),
      distance_km: Number(formData.distance_km),
      origin: {
        code: formData.origin.code.trim().toUpperCase(),
        name: formData.origin.name.trim()
      },
      destination:{
        code: formData.destination.code.trim().toUpperCase(),
        name: formData.destination.name.trim(),
      },
      aircraft: {
        aircraft_id: formData.aircraft.aircraft_id.trim(),
        aircraft_type: formData.aircraft.aircraft.aircraft_type.trim(),
        age_years: Number(formData.aircraft.age_years),
        emission_factor: Number(formData.aircraft.emission_factor),
        technical_failure_rate: Number(formData.aircraft.technical_failure_rate),
        avg_tech_delay_min: Number(formData.aircraft.avg_tech_delay_min),
      },
      crew: {
        crew_id: formData.crew.crew_id.trim(),
        duty_hours_today: Number(
        formData.crew.duty_hours_today
      ),
      max_duty_hours: Number(
        formData.crew.max_duty_hours
      ),
      },
      history: {
        past_delays: Number(
          formData.history.past_delays
        ),
        past_cancellations: Number(
          formData.history.past_cancellations
        ),
        technical_cancellations: Number(
          formData.history.technical_cancellations
        ),
        recent_disruptions: Number(
          formData.history.recent_disruptions
        ),
      },
    };

    onSubmit(flightData);
  }
  const isBasicFlightDataComplete = Boolean(
    formData.flight_id.trim() &&
    formData.delay_minutes.trim() &&
    formData.passenger_count.trim() &&
    formData.distance_km.trim() &&
    formData.origin.code.trim() &&
    formData.origin.name.trim() &&
    formData.destination.code.trim() &&
    formData.destination.name.trim()
  )
  const isAircraftDataComplete = Boolean(
    formData.aircraft.aircraft_id.trim() &&
    formData.aircraft.aircraft_type.trim() &&
    formData.aircraft.age_years !== "" &&
    formData.aircraft.emission_factor !=="" &&
    formData.aircraft.technical_failure_rate !== "" &&
    formData.aircraft.avg_tech_delay_min !==""  )  
  const isCrewDataComplete = Boolean(
    formData.crew.crew_id.trim() &&
    formData.crew.duty_hours_today !== "" &&
    formData.crew.max_duty_hours !=""
  )
  const isHistoryDataComplete = Boolean(
  formData.history.past_delays !== "" &&
  formData.history.past_cancellations !== "" &&
  formData.history.technical_cancellations !== "" &&
  formData.history.recent_disruptions !== ""
  );
  return (
    <section>
      <h2>Flight Details</h2>

      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="airline-code">Airline</label>

          <select
            id="airline-code"
            name="airline_code"
            value={formData.airline_code}
            onChange={handleChange}
          >
            <option value="indigo">IndiGo</option>
            <option value="airindia">Air India</option>
          </select>
        </div>

        <div>
          <label htmlFor="flight-id">Flight ID</label>

          <input
            id="flight-id"
            type="text"
            name="flight_id"
            value={formData.flight_id}
            onChange={handleChange}
            placeholder="For example, 6E-203"
          />
        </div>
        <div>
          <label htmlFor="delay-minutes">Current delay in minutes</label>
          <input id = "delay-minutes"
          type="number"
          name="delay_minutes"
          value={formData.delay_minutes}
          onChange={handleChange}
          min="0"
          step="1"
          placeholder="For exapmle, 90"
          required
          />
        </div>
        <div>
          <label htmlFor="passenger-count">Passenger count
          </label>
          <input
            id="passenger-count"
            type="number"
            name="passenger_count"
            value={formData.passenger_count}
            onChange={handleChange}
            min="1"
            step="1"
            placeholder="For example, 180"
            required
          />
        </div>
        <div>
          <label htmlFor="distance-km">
            Flight distance in kilometres
          </label>
          <input
            id="distance-km"
            type="number"
            name="distance_km"
            value={formData.distance_km}
            onChange={handleChange}
            min="1"
            step="0.1"
            placeholder="For example, 1500"
            required
          />
        </div>
        <fieldset>
  <legend>Origin Airport</legend>

  <div>
    <label htmlFor="origin-code">Airport code</label>

    <input
      id="origin-code"
      type="text"
      name="code"
      value={formData.origin.code}
      onChange={(event) =>
        handleNestedChange("origin", event)
      }
      placeholder="For example, DEL"
      maxLength={3}
    />
  </div>

  <div>
    <label htmlFor="origin-name">Airport name</label>

    <input
      id="origin-name"
      type="text"
      name="name"
      value={formData.origin.name}
      onChange={(event) =>
        handleNestedChange("origin", event)
      }
      placeholder="For example, Delhi"
    />
  </div>
</fieldset>

<fieldset>
  <legend>Destination Airport</legend>

  <div>
    <label htmlFor="destination-code">Airport code</label>

    <input
      id="destination-code"
      type="text"
      name="code"
      value={formData.destination.code}
      onChange={(event) =>
        handleNestedChange("destination", event)
      }
      placeholder="For example, BOM"
      maxLength={3}
    />
  </div>

  <div>
    <label htmlFor="destination-name">Airport name</label>

    <input
      id="destination-name"
      type="text"
      name="name"
      value={formData.destination.name}
      onChange={(event) =>
        handleNestedChange("destination", event)
      }
      placeholder="For example, Mumbai"
    />
  </div>
</fieldset>
<fieldset>
  <legend>Aircraft Information</legend>

  <div>
    <label htmlFor="aircraft-id">Aircraft ID</label>

    <input
      id="aircraft-id"
      type="text"
      name="aircraft_id"
      value={formData.aircraft.aircraft_id}
      onChange={(event) =>
        handleNestedChange("aircraft", event)
      }
      placeholder="For example, VT-EXA"
      required
    />
  </div>

  <div>
    <label htmlFor="aircraft-type">Aircraft type</label>

    <select
      id="aircraft-type"
      name="aircraft_type"
      value={formData.aircraft.aircraft_type}
      onChange={(event) =>
        handleNestedChange("aircraft", event)
      }
      required
    >
      <option value="">Select aircraft type</option>
      <option value="A320">Airbus A320</option>
      <option value="A321">Airbus A321</option>
      <option value="B737">Boeing 737</option>
    </select>
  </div>

  <div>
    <label htmlFor="aircraft-age">
      Aircraft age in years
    </label>

    <input
      id="aircraft-age"
      type="number"
      name="age_years"
      value={formData.aircraft.age_years}
      onChange={(event) =>
        handleNestedChange("aircraft", event)
      }
      min="0"
      step="1"
      placeholder="For example, 8"
      required
    />
  </div>

  <div>
    <label htmlFor="emission-factor">
      Emission factor
    </label>

    <input
      id="emission-factor"
      type="number"
      name="emission_factor"
      value={formData.aircraft.emission_factor}
      onChange={(event) =>
        handleNestedChange("aircraft", event)
      }
      min="0"
      step="0.01"
      placeholder="For example, 0.09"
      required
    />
  </div>

  <div>
    <label htmlFor="technical-failure-rate">
      Technical failure rate
    </label>

    <input
      id="technical-failure-rate"
      type="number"
      name="technical_failure_rate"
      value={formData.aircraft.technical_failure_rate}
      onChange={(event) =>
        handleNestedChange("aircraft", event)
      }
      min="0"
      max="1"
      step="0.01"
      placeholder="For example, 0.04"
      required
    />
  </div>

  <div>
    <label htmlFor="average-technical-delay">
      Average technical delay in minutes
    </label>

    <input
      id="average-technical-delay"
      type="number"
      name="avg_tech_delay_min"
      value={formData.aircraft.avg_tech_delay_min}
      onChange={(event) =>
        handleNestedChange("aircraft", event)
      }
      min="0"
      step="1"
      placeholder="For example, 35"
      required
    />
  </div>
</fieldset>


<fieldset>
  <legend>Crew Information</legend>

  <div>
    <label htmlFor="crew-id">Crew ID</label>

    <input
      id="crew-id"
      type="text"
      name="crew_id"
      value={formData.crew.crew_id}
      onChange={(event) =>
        handleNestedChange("crew", event)
      }
      placeholder="For example, CREW-101"
      required
    />
  </div>

  <div>
    <label htmlFor="duty-hours-today">
      Duty hours completed today
    </label>

    <input
      id="duty-hours-today"
      type="number"
      name="duty_hours_today"
      value={formData.crew.duty_hours_today}
      onChange={(event) =>
        handleNestedChange("crew", event)
      }
      min="0"
      step="0.1"
      placeholder="For example, 7.5"
      required
    />
  </div>

  <div>
    <label htmlFor="maximum-duty-hours">
      Maximum permitted duty hours
    </label>

    <input
      id="maximum-duty-hours"
      type="number"
      name="max_duty_hours"
      value={formData.crew.max_duty_hours}
      onChange={(event) =>
        handleNestedChange("crew", event)
      }
      min="1"
      step="0.1"
      placeholder="For example, 10"
      required
    />
  </div>
</fieldset>
<fieldset>
  <legend>Historical Disruptions</legend>

  <div>
    <label htmlFor="past-delays">
      Number of past delays
    </label>

    <input
      id="past-delays"
      type="number"
      name="past_delays"
      value={formData.history.past_delays}
      onChange={(event) =>
        handleNestedChange("history", event)
      }
      min="0"
      step="1"
      placeholder="For example, 6"
      required
    />
  </div>

  <div>
    <label htmlFor="past-cancellations">
      Number of past cancellations
    </label>

    <input
      id="past-cancellations"
      type="number"
      name="past_cancellations"
      value={formData.history.past_cancellations}
      onChange={(event) =>
        handleNestedChange("history", event)
      }
      min="0"
      step="1"
      placeholder="For example, 2"
      required
    />
  </div>

  <div>
    <label htmlFor="technical-cancellations">
      Technical cancellations
    </label>

    <input
      id="technical-cancellations"
      type="number"
      name="technical_cancellations"
      value={formData.history.technical_cancellations}
      onChange={(event) =>
        handleNestedChange("history", event)
      }
      min="0"
      step="1"
      placeholder="For example, 1"
      required
    />
  </div>

  <div>
    <label htmlFor="recent-disruptions">
      Recent disruptions
    </label>

    <input
      id="recent-disruptions"
      type="number"
      name="recent_disruptions"
      value={formData.history.recent_disruptions}
      onChange={(event) =>
        handleNestedChange("history", event)
      }
      min="0"
      step="1"
      placeholder="For example, 2"
      required
    />
  </div>
</fieldset>

        <p>
          Current selection: {formData.airline_code} —{" "}
          {formData.flight_id || "No flight ID entered"}
        </p>
        <p>
  Route: {formData.origin.code || "---"} →{" "}
  {formData.destination.code || "---"}
</p>

        <button
          type="submit"
          disabled={isSubmitting ||!isBasicFlightDataComplete || !isAircraftDataComplete || !isCrewDataComplete || !isHistoryDataComplete}
        >
          {isSubmitting
            ? "Generating Decision..."
        : "Generate Decision"}
        </button>
      </form>
    </section>
  );
}

export default FlightForm;