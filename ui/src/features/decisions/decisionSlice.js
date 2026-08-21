import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { apiUrl } from "../../config/api";

const DECISION_API_URL = apiUrl("/api/decisions");


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

      const data = await response.json();

      if (!response.ok) {
        const errorMessage = Array.isArray(data.detail)
          ? data.detail
              .map(
                (validationError) =>
                  `${validationError.loc.join(".")}: ${
                    validationError.msg
                  }`
              )
              .join(", ")
          : data.detail || "Unable to generate decision";

        return rejectWithValue(errorMessage);
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
