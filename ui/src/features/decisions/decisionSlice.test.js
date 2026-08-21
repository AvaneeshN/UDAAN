import { configureStore } from "@reduxjs/toolkit";
import { afterEach, describe, expect, it, vi } from "vitest";

import decisionReducer, { createDecision } from "./decisionSlice";


function createStore() {
  return configureStore({
    reducer: { decision: decisionReducer },
  });
}


function apiResponse({
  body,
  contentType = "application/json",
  ok = false,
  status = 400,
  statusText = "Bad Request",
}) {
  return {
    ok,
    status,
    statusText,
    headers: {
      get: (name) => name === "content-type" ? contentType : null,
    },
    json: vi.fn().mockImplementation(async () => {
      if (body instanceof Error) {
        throw body;
      }

      return body;
    }),
    text: vi.fn().mockResolvedValue(body || ""),
  };
}


async function dispatchDecision(response) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));
  const store = createStore();

  await store.dispatch(createDecision({ flight_id: "AI-101" }));

  return store.getState().decision;
}


afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});


describe("createDecision errors", () => {
  it("formats FastAPI validation errors", async () => {
    const state = await dispatchDecision(apiResponse({
      body: {
        detail: [
          {
            loc: ["body", "crew", "max_duty_hours"],
            msg: "Input should be greater than 0",
          },
        ],
      },
      status: 422,
      statusText: "Unprocessable Entity",
    }));

    expect(state.status).toBe("failed");
    expect(state.error).toBe(
      "body.crew.max_duty_hours: Input should be greater than 0"
    );
  });

  it("shows plain-text backend errors", async () => {
    const state = await dispatchDecision(apiResponse({
      body: "Service temporarily unavailable",
      contentType: "text/plain",
      status: 503,
      statusText: "Service Unavailable",
    }));

    expect(state.error).toBe("Service temporarily unavailable");
  });

  it("falls back to the HTTP status for malformed JSON", async () => {
    const state = await dispatchDecision(apiResponse({
      body: new SyntaxError("Unexpected token"),
      status: 502,
      statusText: "Bad Gateway",
    }));

    expect(state.error).toBe(
      "Unable to generate decision (502 Bad Gateway)"
    );
  });

  it("distinguishes network failures from backend responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("Failed"))
    );
    const store = createStore();

    await store.dispatch(createDecision({ flight_id: "AI-101" }));

    expect(store.getState().decision.error).toBe(
      "Unable to connect to the decision API"
    );
  });
});
