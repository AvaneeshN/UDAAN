from dataclasses import dataclass

import pandas as pd


PREDICTION_HORIZON = pd.Timedelta(hours=24)


@dataclass(frozen=True)
class BTSTemporalResult:
    """Parsed temporal fields and their validation masks."""

    flight_date: pd.Series
    scheduled_departure_hour: pd.Series
    scheduled_departure_local: pd.Series
    prediction_cutoff_local: pd.Series
    invalid_flight_date: pd.Series
    missing_scheduled_departure_time: pd.Series
    invalid_scheduled_departure_time: pd.Series


def _is_missing_text(
    series: pd.Series,
) -> pd.Series:
    text_values = series.astype("string")

    return (
        text_values.isna()
        | text_values.str.strip().eq("").fillna(False)
    )


def _validate_matching_indexes(
    flight_date: pd.Series,
    scheduled_departure_time: pd.Series,
) -> None:
    if not flight_date.index.equals(
        scheduled_departure_time.index
    ):
        raise ValueError(
            "FlightDate and CRSDepTime indexes must match"
        )


def _parse_flight_date(
    series: pd.Series,
) -> tuple[pd.Series, pd.Series]:
    text_values = (
        series.astype("string")
        .str.strip()
    )

    parsed = pd.to_datetime(
        text_values,
        format="%Y-%m-%d",
        errors="coerce",
    ).rename("flight_date")

    invalid = (
        parsed.isna()
        .astype("boolean")
        .rename("invalid_flight_date")
    )

    return parsed, invalid


def _parse_scheduled_departure_time(
    series: pd.Series,
) -> tuple[
    pd.Series,
    pd.Series,
    pd.Series,
    pd.Series,
]:
    """
    Parse a BTS HHMM value.

    Returns the hour, minutes from the service-day start,
    missing-value mask and invalid-value mask.

    The value 2400 uses an offset of 1440 minutes so its
    timestamp rolls into the following calendar day.
    """
    missing = (
        _is_missing_text(series)
        .astype("boolean")
        .rename("missing_scheduled_departure_time")
    )

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

    invalid = (
        (~missing & ~valid_nonmissing)
        .astype("boolean")
        .rename("invalid_scheduled_departure_time")
    )

    parsed_hour = pd.Series(
        pd.NA,
        index=series.index,
        dtype="Int8",
        name="scheduled_departure_hour",
    )
    parsed_hour.loc[regular_time] = (
        hour.loc[regular_time].astype("Int8")
    )
    parsed_hour.loc[midnight_2400] = 0

    minute_offset = pd.Series(
        pd.NA,
        index=series.index,
        dtype="Int16",
        name="scheduled_departure_minute_offset",
    )
    minute_offset.loc[regular_time] = (
        hour.loc[regular_time].astype("Int16") * 60
        + minute.loc[regular_time].astype("Int16")
    )
    minute_offset.loc[midnight_2400] = 1440

    return (
        parsed_hour,
        minute_offset,
        missing,
        invalid,
    )


def _build_scheduled_departure_local(
    flight_date: pd.Series,
    minute_offset: pd.Series,
) -> pd.Series:
    scheduled_departure = pd.Series(
        pd.NaT,
        index=flight_date.index,
        dtype="datetime64[ns]",
        name="scheduled_departure_local",
    )

    resolvable = (
        flight_date.notna()
        & minute_offset.notna()
    )

    scheduled_departure.loc[resolvable] = (
        flight_date.loc[resolvable]
        + pd.to_timedelta(
            minute_offset.loc[
                resolvable
            ].astype("int64"),
            unit="m",
        )
    )

    return scheduled_departure


def derive_bts_temporal_fields(
    flight_date: pd.Series,
    scheduled_departure_time: pd.Series,
) -> BTSTemporalResult:
    """
    Parse BTS FlightDate and CRSDepTime without mutating them.

    The resulting timestamps are timezone-naive local airport
    times because these BTS fields do not provide timezone data.
    """
    _validate_matching_indexes(
        flight_date,
        scheduled_departure_time,
    )

    parsed_flight_date, invalid_flight_date = (
        _parse_flight_date(flight_date)
    )

    (
        scheduled_departure_hour,
        minute_offset,
        missing_departure_time,
        invalid_departure_time,
    ) = _parse_scheduled_departure_time(
        scheduled_departure_time
    )

    scheduled_departure_local = (
        _build_scheduled_departure_local(
            parsed_flight_date,
            minute_offset,
        )
    )

    prediction_cutoff_local = (
        scheduled_departure_local
        - PREDICTION_HORIZON
    ).rename("prediction_cutoff_local")

    return BTSTemporalResult(
        flight_date=parsed_flight_date,
        scheduled_departure_hour=(
            scheduled_departure_hour
        ),
        scheduled_departure_local=(
            scheduled_departure_local
        ),
        prediction_cutoff_local=(
            prediction_cutoff_local
        ),
        invalid_flight_date=invalid_flight_date,
        missing_scheduled_departure_time=(
            missing_departure_time
        ),
        invalid_scheduled_departure_time=(
            invalid_departure_time
        ),
    )