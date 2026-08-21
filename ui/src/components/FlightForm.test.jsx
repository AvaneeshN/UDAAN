import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import FlightForm from "./FlightForm";


function enterRequiredFlightData() {
  const valuesByLabel = {
    "Flight ID": " AI-101 ",
    "Current delay in minutes": "90",
    "Passenger count": "180",
    "Flight distance in kilometres": "1500",
    "Aircraft ID": " VT-ABC ",
    "Aircraft age in years": "18",
    "Emission factor": "0.1",
    "Technical failure rate": "0.3",
    "Average technical delay in minutes": "25",
    "Crew ID": " CRW-77 ",
    "Duty hours completed today": "7.5",
    "Maximum permitted duty hours": "10",
    "Number of past delays": "6",
    "Number of past cancellations": "2",
    "Technical cancellations": "1",
    "Recent disruptions": "2",
  };

  for (const [label, value] of Object.entries(valuesByLabel)) {
    fireEvent.change(screen.getByLabelText(label), {
      target: { value },
    });
  }

  const airportCodeFields = screen.getAllByLabelText("Airport code");
  const airportNameFields = screen.getAllByLabelText("Airport name");

  fireEvent.change(airportCodeFields[0], { target: { value: "del" } });
  fireEvent.change(airportCodeFields[1], { target: { value: "bom" } });
  fireEvent.change(airportNameFields[0], { target: { value: "Delhi" } });
  fireEvent.change(airportNameFields[1], { target: { value: "Mumbai" } });
  fireEvent.change(screen.getByLabelText("Aircraft type"), {
    target: { value: "A320" },
  });
}


describe("FlightForm", () => {
  it("submits the selected aircraft type from the aircraft section", () => {
    const onSubmit = vi.fn();
    render(<FlightForm onSubmit={onSubmit} />);
    enterRequiredFlightData();

    fireEvent.change(screen.getByLabelText("Airline"), {
      target: { value: "airindia" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Generate Decision" })
    );

    expect(onSubmit).toHaveBeenCalledOnce();
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        airline_code: "airindia",
        flight_id: "AI-101",
        aircraft: expect.objectContaining({
          aircraft_id: "VT-ABC",
          aircraft_type: "A320",
        }),
      })
    );
  });
});
