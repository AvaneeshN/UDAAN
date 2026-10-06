# BTS Baseline Disruption Model Contract

Status: Draft  
Contract version: 0.2  
Dataset: BTS Reporting Carrier On-Time Performance  
Model purpose: Pre-departure flight disruption risk estimation

## 1. Objective

The model estimates the probability that a scheduled flight will experience
a significant operational disruption.

The model does not directly recommend DELAY, CANCEL, or REROUTE. That decision
belongs to UDAAN's decision engine, which combines the predicted probability
with safety constraints, operational rules, and airline costs.

## 2. Unit of observation

One row represents one scheduled nonstop flight segment.

A multi-leg flight is represented by one row per origin-destination segment.

## 3. Prediction point

The baseline prediction is made 24 hours before scheduled departure.

Only schedule information and historical information available before the
prediction cutoff may be used as model input.

The BTS dataset does not contain versioned schedule snapshots. The baseline
therefore assumes that its reported scheduled fields were available at the
prediction point. This limitation must be recorded with the model.

## 4. Data source

Primary source:

Bureau of Transportation Statistics
Reporting Carrier On-Time Performance dataset.

Initial development dataset:

- Development sample: one complete month
- Baseline training period: January 2022 through December 2024
- Final test period: January 2025 through December 2025

The exact downloaded files, retrieval date, row counts, checksums, and selected
columns must be recorded in a dataset manifest.

## 5. Selected raw BTS columns

### Flight identity

- FlightDate
- Reporting_Airline
- DOT_ID_Reporting_Airline
- Flight_Number_Reporting_Airline
- Tail_Number
- OriginAirportID
- Origin
- DestAirportID
- Dest

### Scheduled information

- Year
- Quarter
- Month
- DayofMonth
- DayOfWeek
- CRSDepTime
- CRSArrTime
- CRSElapsedTime
- Distance
- DistanceGroup

### Outcome information

- DepDelayMinutes
- ArrDelayMinutes
- Cancelled
- Diverted
- CancellationCode
- CarrierDelay
- WeatherDelay
- NASDelay
- SecurityDelay
- LateAircraftDelay

Outcome information is used for labels, analysis, and auditing. It must not be
passed to the prediction model.

## 6. Prediction target

The initial binary target is `significant_disruption`.

It is calculated as:

significant_disruption =
Cancelled == 1
OR Diverted == 1
OR ArrDelayMinutes >= 15

For cancelled or diverted flights, a missing arrival delay must not cause the
target to become missing.

Class 1 means that a significant disruption occurred.
Class 0 means that no significant disruption occurred.
If `Cancelled` or `Diverted` is missing or is not a valid binary value, the
target is unresolved.

If both indicators are zero but `ArrDelayMinutes` is missing, the target is
also unresolved because the pipeline cannot prove whether the completed flight
was on time or significantly delayed.

Unresolved rows must be quarantined from supervised model training and included
in the data-quality report. They must not be assigned class 0, and they must
not be removed from the immutable raw dataset.

## 7. Direct model features

The following features are derived from scheduled information:

- reporting_airline
- origin_airport
- destination_airport
- route
- month
- day_of_week
- scheduled_departure_hour
- scheduled_arrival_hour
- scheduled_elapsed_minutes
- distance_miles
- distance_group

The `route` value is constructed as `ORIGIN-DESTINATION`.

## 8. Historical model features

The following features are calculated only from flights whose outcomes were
already known before the prediction cutoff:

- airline_disruption_rate_30d
- route_disruption_rate_30d
- route_disruption_rate_90d
- origin_disruption_rate_30d
- destination_disruption_rate_30d
- route_flight_volume_30d

Each historical calculation must use a closed-left time window so the current
flight and future flights cannot influence their own features.

When insufficient history exists, the pipeline must apply an explicitly
documented fallback rather than silently inserting arbitrary values.

## 9. Optional aircraft features

The following features may be added after validating a time-aware join between
BTS tail numbers and the FAA Aircraft Registry:

- aircraft_age_years
- aircraft_manufacturer
- aircraft_model

They are not required for the first baseline.

Tail-based and aircraft-based features must not be enabled for the 24-hour
baseline unless the aircraft assignment is confirmed to have been available
at the prediction cutoff. The BTS Tail_Number may represent the aircraft that
actually operated the flight rather than the aircraft assigned 24 hours before
departure.
Current FAA registry information must not automatically be treated as the
historical state of an aircraft.

## 10. Prohibited prediction features

The following values describe what happened during or after the flight and
must not be model inputs:

- DepTime
- ArrTime
- ActualElapsedTime
- AirTime
- TaxiOut
- TaxiIn
- WheelsOff
- WheelsOn
- DepDelay
- DepDelayMinutes
- ArrDelay
- ArrDelayMinutes
- Cancelled
- Diverted
- CancellationCode
- CarrierDelay
- WeatherDelay
- NASDelay
- SecurityDelay
- LateAircraftDelay

Using these fields as prediction inputs would create target leakage.

## 11. Missing-value policy

- Missing outcome fields for cancelled or diverted flights are expected.
- Missing Tail_Number values must be preserved and reported.
- Invalid airport or airline identifiers must be rejected or quarantined.
- Scheduled times must be parsed without treating values such as `2400` as an
  ordinary integer hour.
- Missing numerical values must be handled by a fitted preprocessing step.
- Missing categorical values must use an explicit `UNKNOWN` category.

Rows must not be silently dropped without reporting how many were removed and
why.

## 12. Data splitting

Data must be split chronologically.

Random train/test splitting is prohibited for the final evaluation because it
can allow future operational patterns to influence evaluation of past flights.

Proposed split:

- Training: January 2022 through June 2024
- Validation: July 2024 through December 2024
- Test: January 2025 through December 2025

The test set must remain untouched while models and thresholds are selected.

## 13. Baseline model

The first model will use scikit-learn LogisticRegression.

The preprocessing and classifier must be stored in one scikit-learn Pipeline.

Categorical features will use OneHotEncoder with unknown-category handling.
Numerical features will use explicit missing-value processing and scaling when
required.

A more complex model may only replace the baseline after it demonstrates a
measurable improvement on the untouched chronological test set.

## 14. Evaluation

The evaluation report must include:

- Number of rows in each split
- Disruption prevalence
- Precision
- Recall
- F1 score
- PR-AUC
- ROC-AUC
- Log loss
- Brier score
- Calibration curve
- Confusion matrix at the selected threshold

Results must also be reported by:

- Airline
- Origin airport
- Destination airport
- Route-volume group
- Month

The model must be compared with a naive baseline that always predicts the
training-set disruption rate.

## 15. Runtime output

The ML layer returns:

- disruption_probability
- model_version
- feature_schema_version
- prediction_timestamp
- prediction_cutoff
- data_source
- missing-feature indicators

The ML layer does not return the final operational action.

## 16. Decision-engine integration

UDAAN's decision engine consumes the disruption probability together with:

- Current operational status
- Safety constraints
- Crew-legality information
- Aircraft availability
- Passenger impact
- Cost estimates
- Airline-specific policies

Crew-duty and maintenance data are future airline integrations. They must not
be fabricated from BTS fields.

## 17. Model limitations

The baseline is trained on reporting United States domestic airlines.

It must not be presented as validated for Air India, IndiGo, international
operations, or a particular airline until it has been evaluated using
representative airline data.

The baseline estimates statistical disruption risk. It does not establish
causation and does not replace dispatchers, maintenance engineers, crew
controllers, or safety personnel.
