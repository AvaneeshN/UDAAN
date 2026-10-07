from dataclasses import dataclass

import pandas as pd

from ml.bts_target import QUARANTINE_REASON_COLUMN
from ml.data_manifest import BTSManifest, load_bts_manifest


CLEANING_QUARANTINE_REASON_COLUMN = (
    "cleaning_quarantine_reason"
)

INVALID_TARGET_LABEL = "invalid_or_missing_target_label"
INVALID_FLIGHT_DATE = "invalid_flight_date"
INVALID_REPORTING_AIRLINE = "invalid_reporting_airline"
INVALID_DOT_AIRLINE_ID = "invalid_dot_airline_id"
INVALID_FLIGHT_NUMBER = "invalid_flight_number"
INVALID_ORIGIN_AIRPORT_ID = "invalid_origin_airport_id"
INVALID_ORIGIN_AIRPORT = "invalid_origin_airport"
INVALID_DESTINATION_AIRPORT_ID = (
    "invalid_destination_airport_id"
)
INVALID_DESTINATION_AIRPORT = (
    "invalid_destination_airport"
)
INVALID_SCHEDULED_DEPARTURE_TIME = (
    "invalid_scheduled_departure_time"
)
INVALID_SCHEDULED_ARRIVAL_TIME = (
    "invalid_scheduled_arrival_time"
)
INVALID_SCHEDULED_ELAPSED_TIME = (
    "invalid_scheduled_elapsed_time"
)
INVALID_DISTANCE = "invalid_distance"
INVALID_DISTANCE_GROUP = "invalid_distance_group"


CLEANING_REQUIRED_RAW_COLUMNS = (
    "FlightDate",
    "Reporting_Airline",
    "DOT_ID_Reporting_Airline",
    "Flight_Number_Reporting_Airline",
    "OriginAirportID",
    "Origin",
    "DestAirportID",
    "Dest",
    "CRSDepTime",
    "CRSArrTime",
    "CRSElapsedTime",
    "Distance",
    "DistanceGroup",
)


PROCESSED_METADATA_COLUMNS = (
    "flight_date",
    "dot_airline_id",
    "flight_number",
    "origin_airport_id",
    "destination_airport_id",
)


MODEL_FEATURE_COLUMNS = (
    "reporting_airline",
    "origin_airport",
    "destination_airport",
    "route",
    "month",
    "day_of_week",
    "scheduled_departure_hour",
    "scheduled_arrival_hour",
    "scheduled_elapsed_minutes",
    "distance_miles",
    "distance_group",
)


PROHIBITED_PREDICTION_COLUMNS = frozenset({
    "DepTime",
    "ArrTime",
    "ActualElapsedTime",
    "AirTime",
    "TaxiOut",
    "TaxiIn",
    "WheelsOff",
    "WheelsOn",
    "DepDelay",
    "DepDelayMinutes",
    "ArrDelay",
    "ArrDelayMinutes",
    "Cancelled",
    "Diverted",
    "CancellationCode",
    "CarrierDelay",
    "WeatherDelay",
    "NASDelay",
    "SecurityDelay",
    "LateAircraftDelay",
})


@dataclass(frozen=True)
class BTSCleaningResult:
    """The two auditable outputs of BTS cleaning."""

    valid_rows: pd.DataFrame
    quarantined_rows: pd.DataFrame

    @property
    def total_row_count(self) -> int:
        return len(self.valid_rows) + len(
            self.quarantined_rows
        )


def _is_missing_text(series: pd.Series) -> pd.Series:
    """Find missing, empty, or whitespace-only values."""
    text_values = series.astype("string")

    return (
        text_values.isna()
        | text_values.str.strip().eq("").fillna(False)
    )


def _require_columns(
    frame: pd.DataFrame,
    target_column: str,
) -> None:
    required_columns = (
        *CLEANING_REQUIRED_RAW_COLUMNS,
        target_column,
        QUARANTINE_REASON_COLUMN,
    )

    missing_columns = [
        column_name
        for column_name in required_columns
        if column_name not in frame.columns
    ]

    if missing_columns:
        missing_list = ", ".join(missing_columns)
        raise ValueError(
            "BTS cleaning input is missing required columns: "
            f"{missing_list}"
        )


def _set_first_reason(
    reasons: pd.Series,
    mask: pd.Series,
    reason: str,
) -> None:
    """Set a reason only when the row has no earlier reason."""
    available_rows = (
        reasons.isna()
        & mask.fillna(False)
    )
    reasons.loc[available_rows] = reason


def _normalize_required_code(
    series: pd.Series,
    pattern: str,
) -> tuple[pd.Series, pd.Series]:
    normalized = (
        series.astype("string")
        .str.strip()
        .str.upper()
    )

    valid = normalized.str.fullmatch(
        pattern,
        na=False,
    )

    return normalized.where(valid), ~valid


def _parse_required_positive_integer(
    series: pd.Series,
) -> tuple[pd.Series, pd.Series]:
    numeric = pd.to_numeric(
        series,
        errors="coerce",
    )

    finite = (
        numeric.notna()
        & numeric.abs().ne(float("inf")).fillna(False)
    )
    whole_number = (
        numeric.mod(1).eq(0).fillna(False)
    )
    positive = numeric.gt(0).fillna(False)

    valid = finite & whole_number & positive

    parsed = numeric.where(valid).astype("Int64")

    return parsed, ~valid


def _parse_optional_positive_number(
    series: pd.Series,
) -> tuple[pd.Series, pd.Series]:
    missing = _is_missing_text(series)

    numeric = pd.to_numeric(
        series,
        errors="coerce",
    )

    finite = (
        numeric.notna()
        & numeric.abs().ne(float("inf")).fillna(False)
    )
    positive = numeric.gt(0).fillna(False)

    valid_nonmissing = finite & positive
    invalid = ~missing & ~valid_nonmissing

    parsed = numeric.where(
        valid_nonmissing
    ).astype("Float64")

    return parsed, invalid


def _parse_optional_distance_group(
    series: pd.Series,
) -> tuple[pd.Series, pd.Series]:
    missing = _is_missing_text(series)

    numeric = pd.to_numeric(
        series,
        errors="coerce",
    )

    finite = (
        numeric.notna()
        & numeric.abs().ne(float("inf")).fillna(False)
    )
    whole_number = (
        numeric.mod(1).eq(0).fillna(False)
    )
    in_range = numeric.between(
        1,
        11,
    ).fillna(False)

    valid_nonmissing = (
        finite
        & whole_number
        & in_range
    )
    invalid = ~missing & ~valid_nonmissing

    parsed = numeric.where(
        valid_nonmissing
    ).astype("Int8")

    return parsed, invalid


def _parse_scheduled_hour(
    series: pd.Series,
) -> tuple[pd.Series, pd.Series]:
    """
    Convert BTS HHMM values into an hour.

    Missing values remain missing for the future model imputer.
    The BTS special value 2400 is converted to hour 0.
    """
    missing = _is_missing_text(series)

    numeric = pd.to_numeric(
        series,
        errors="coerce",
    )

    finite = (
        numeric.notna()
        & numeric.abs().ne(float("inf")).fillna(False)
    )
    whole_number = (
        numeric.mod(1).eq(0).fillna(False)
    )
    numeric_is_usable = finite & whole_number

    hhmm = numeric.where(
        numeric_is_usable
    ).astype("Int64")

    hour = hhmm.floordiv(100)
    minute = hhmm.mod(100)

    regular_time = (
        numeric_is_usable
        & hhmm.between(0, 2359).fillna(False)
        & minute.between(0, 59).fillna(False)
    )
    midnight_2400 = (
        numeric_is_usable
        & hhmm.eq(2400).fillna(False)
    )

    valid_nonmissing = regular_time | midnight_2400
    invalid = ~missing & ~valid_nonmissing

    parsed_hour = pd.Series(
        pd.NA,
        index=series.index,
        dtype="Int8",
    )
    parsed_hour.loc[regular_time] = (
        hour.loc[regular_time].astype("Int8")
    )
    parsed_hour.loc[midnight_2400] = 0

    return parsed_hour, invalid


def clean_bts_frame(
    frame: pd.DataFrame,
    manifest: BTSManifest | None = None,
) -> BTSCleaningResult:
    """
    Transform a labelled BTS dataframe into valid and quarantined rows.

    The input dataframe is not modified. Outcome columns are excluded from
    the processed model data, except for the generated target.
    """
    resolved_manifest = manifest or load_bts_manifest()
    target_column = resolved_manifest.target.name

    _require_columns(
        frame,
        target_column,
    )

    leaked_features = (
        set(MODEL_FEATURE_COLUMNS)
        & PROHIBITED_PREDICTION_COLUMNS
    )
    if leaked_features:
        leaked_list = ", ".join(
            sorted(leaked_features)
        )
        raise RuntimeError(
            "Model feature contract contains prohibited columns: "
            f"{leaked_list}"
        )

    flight_date_text = (
        frame["FlightDate"]
        .astype("string")
        .str.strip()
    )
    flight_date = pd.to_datetime(
        flight_date_text,
        format="%Y-%m-%d",
        errors="coerce",
    )
    invalid_flight_date = flight_date.isna()

    reporting_airline, invalid_reporting_airline = (
        _normalize_required_code(
            frame["Reporting_Airline"],
            r"[A-Z0-9]{2}",
        )
    )

    origin_airport, invalid_origin_airport = (
        _normalize_required_code(
            frame["Origin"],
            r"[A-Z]{3}",
        )
    )

    destination_airport, invalid_destination_airport = (
        _normalize_required_code(
            frame["Dest"],
            r"[A-Z]{3}",
        )
    )

    dot_airline_id, invalid_dot_airline_id = (
        _parse_required_positive_integer(
            frame["DOT_ID_Reporting_Airline"]
        )
    )

    flight_number, invalid_flight_number = (
        _parse_required_positive_integer(
            frame["Flight_Number_Reporting_Airline"]
        )
    )

    origin_airport_id, invalid_origin_airport_id = (
        _parse_required_positive_integer(
            frame["OriginAirportID"]
        )
    )

    destination_airport_id, invalid_destination_airport_id = (
        _parse_required_positive_integer(
            frame["DestAirportID"]
        )
    )

    scheduled_departure_hour, invalid_departure_time = (
        _parse_scheduled_hour(
            frame["CRSDepTime"]
        )
    )

    scheduled_arrival_hour, invalid_arrival_time = (
        _parse_scheduled_hour(
            frame["CRSArrTime"]
        )
    )

    scheduled_elapsed_minutes, invalid_elapsed_time = (
        _parse_optional_positive_number(
            frame["CRSElapsedTime"]
        )
    )

    distance_miles, invalid_distance = (
        _parse_optional_positive_number(
            frame["Distance"]
        )
    )

    distance_group, invalid_distance_group = (
        _parse_optional_distance_group(
            frame["DistanceGroup"]
        )
    )

    target_numeric = pd.to_numeric(
        frame[target_column],
        errors="coerce",
    )
    target_is_valid = target_numeric.isin([
        resolved_manifest.target.negative_class,
        resolved_manifest.target.positive_class,
    ])
    cleaned_target = target_numeric.where(
        target_is_valid
    ).astype("Int8")

    target_reason_is_present = ~_is_missing_text(
        frame[QUARANTINE_REASON_COLUMN]
    )

    cleaning_reasons = pd.Series(
        pd.NA,
        index=frame.index,
        dtype="string",
        name=CLEANING_QUARANTINE_REASON_COLUMN,
    )

    invalid_target_without_reason = (
        ~target_is_valid
        & ~target_reason_is_present
    )

    _set_first_reason(
        cleaning_reasons,
        invalid_target_without_reason,
        INVALID_TARGET_LABEL,
    )
    _set_first_reason(
        cleaning_reasons,
        invalid_flight_date,
        INVALID_FLIGHT_DATE,
    )
    _set_first_reason(
        cleaning_reasons,
        invalid_reporting_airline,
        INVALID_REPORTING_AIRLINE,
    )
    _set_first_reason(
        cleaning_reasons,
        invalid_dot_airline_id,
        INVALID_DOT_AIRLINE_ID,
    )
    _set_first_reason(
        cleaning_reasons,
        invalid_flight_number,
        INVALID_FLIGHT_NUMBER,
    )
    _set_first_reason(
        cleaning_reasons,
        invalid_origin_airport_id,
        INVALID_ORIGIN_AIRPORT_ID,
    )
    _set_first_reason(
        cleaning_reasons,
        invalid_origin_airport,
        INVALID_ORIGIN_AIRPORT,
    )
    _set_first_reason(
        cleaning_reasons,
        invalid_destination_airport_id,
        INVALID_DESTINATION_AIRPORT_ID,
    )
    _set_first_reason(
        cleaning_reasons,
        invalid_destination_airport,
        INVALID_DESTINATION_AIRPORT,
    )
    _set_first_reason(
        cleaning_reasons,
        invalid_departure_time,
        INVALID_SCHEDULED_DEPARTURE_TIME,
    )
    _set_first_reason(
        cleaning_reasons,
        invalid_arrival_time,
        INVALID_SCHEDULED_ARRIVAL_TIME,
    )
    _set_first_reason(
        cleaning_reasons,
        invalid_elapsed_time,
        INVALID_SCHEDULED_ELAPSED_TIME,
    )
    _set_first_reason(
        cleaning_reasons,
        invalid_distance,
        INVALID_DISTANCE,
    )
    _set_first_reason(
        cleaning_reasons,
        invalid_distance_group,
        INVALID_DISTANCE_GROUP,
    )

    route = origin_airport.str.cat(
        destination_airport,
        sep="-",
    )

    processed = pd.DataFrame(
        {
            "flight_date": flight_date,
            "dot_airline_id": dot_airline_id,
            "flight_number": flight_number,
            "origin_airport_id": origin_airport_id,
            "destination_airport_id": (
                destination_airport_id
            ),
            "reporting_airline": reporting_airline,
            "origin_airport": origin_airport,
            "destination_airport": destination_airport,
            "route": route,
            "month": flight_date.dt.month.astype("Int8"),
            "day_of_week": (
                flight_date.dt.dayofweek
                .add(1)
                .astype("Int8")
            ),
            "scheduled_departure_hour": (
                scheduled_departure_hour
            ),
            "scheduled_arrival_hour": (
                scheduled_arrival_hour
            ),
            "scheduled_elapsed_minutes": (
                scheduled_elapsed_minutes
            ),
            "distance_miles": distance_miles,
            "distance_group": distance_group,
            target_column: cleaned_target,
        },
        index=frame.index,
    )

    processed_output_columns = (
        *PROCESSED_METADATA_COLUMNS,
        *MODEL_FEATURE_COLUMNS,
        target_column,
    )
    processed = processed.loc[
        :,
        processed_output_columns,
    ]

    quarantine_mask = (
        target_reason_is_present
        | cleaning_reasons.notna()
        | ~target_is_valid
    )

    valid_rows = processed.loc[
        ~quarantine_mask
    ].copy(deep=True)

    quarantined_rows = frame.loc[
        quarantine_mask
    ].copy(deep=True)
    quarantined_rows[
        CLEANING_QUARANTINE_REASON_COLUMN
    ] = cleaning_reasons.loc[quarantine_mask]

    result = BTSCleaningResult(
        valid_rows=valid_rows,
        quarantined_rows=quarantined_rows,
    )

    if result.total_row_count != len(frame):
        raise RuntimeError(
            "BTS cleaning violated row-count conservation"
        )

    return result