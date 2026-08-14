import { configureStore } from "@reduxjs/toolkit";

import decisionReducer from "../features/decisions/decisionSlice";


export const store = configureStore({
  reducer: {
    decision: decisionReducer,
  },
});