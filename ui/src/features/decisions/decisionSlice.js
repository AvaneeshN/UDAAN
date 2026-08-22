import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { apiUrl } from "../../config/api";

const DECISION_API_URL = apiUrl("/api/decisions");

async function readResponseBody(response) {
  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    try {
      return await response.json();
    } catch {
      return null;
    }
  }

  const text = await response.text();
  return text.trim() || null;
}

function formatApiError(data, response) {
  if (Array.isArray(data?.detail)) {
    return data.detail
      .map((validationError) => {
        const location = Array.isArray(validationError.loc)
          ? validationError.loc.join(".")
          : "request";
        const message = validationError.msg || "Invalid value";

        return `${location}: ${message}`;
      })
      .join(", ");
  }

  if (typeof data?.detail === "string") {
    return data.detail;
  }

  if (typeof data?.message === "string") {
    return data.message;
  }

  if (typeof data === "string") {
    return data;
  }

  const status = [response.status, response.statusText]
    .filter(Boolean)
    .join(" ");

  return status
    ? `Unable to generate decision (${status})`
    : "Unable to generate decision";
}


export const createDecision = createAsyncThunk(
  "decision/createDecision",

  async (flightData, { rejectWithValue }) => {
    try {
      const response = await fetch(DECISION_API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(flightData),
      });

      const data = await readResponseBody(response);

      if (!response.ok) {
        return rejectWithValue(formatApiError(data, response));
      }

      return data;
    } catch {
      return rejectWithValue(
        "Unable to connect to the decision API"
      );
    }
  }
);


const initialState = {
  result: null,
  status: "idle",
  error: null,
};


const decisionSlice = createSlice({
  name: "decision",
  initialState,

  reducers: {
    clearDecision: (state) => {
      state.result = null;
      state.status = "idle";
      state.error = null;
    },
  },

  extraReducers: (builder) => {
    builder
      .addCase(createDecision.pending, (state) => {
        state.status = "loading";
        state.error = null;
      })

      .addCase(createDecision.fulfilled, (state, action) => {
        state.status = "succeeded";
        state.result = action.payload;
      })

      .addCase(createDecision.rejected, (state, action) => {
        state.status = "failed";
        state.error =
          action.payload || "Something went wrong";
      });
  },
});


export const { clearDecision } = decisionSlice.actions;

export default decisionSlice.reducer;
