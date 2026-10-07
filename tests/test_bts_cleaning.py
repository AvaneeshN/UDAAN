import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from ml.bts_cleaning import (
    CLEANING_QUARANTINE_REASON_COLUMN,
    INVALID_DESTINATION_AIRPORT,
    INVALID_DISTANCE,
    INVALID_DISTANCE_GROUP,
    INVALID_FLIGHT_DATE,
    INVALID_ORIGIN_AIRPORT,
    INVALID_ORIGIN_AIRPORT_ID,
    INVALID_REPORTING_AIRLINE,
    INVALID_SCHEDULED_DEPARTURE_TIME,
    MODEL_FEATURE_COLUMNS,
    PROHIBITED_PREDICTION_COLUMNS,
    clean_bts_frame,
)
from ml.bts_target import (
    MISSING_COMPLETED_ARRIVAL_DELAY,
    QUARANTINE_REASON_COLUMN,
)


TARGET_COLUMN = "significant_disruption"


def valid_labelled_frame(
    row_count: int = 1,
) -> pd.DataFrame:
    raw_values = {
        "FlightDate": "2022-01-15",
        "Reporting_Airline": " aa ",
        "DOT_ID_Reporting_Airline": "19805.00",
        "Flight_Number_Reporting_Airline": "101.00",
        "OriginAirportID": "12478.00",
        "Origin": " jfk ",
        "DestAirportID": "12892.00",
        "Dest": " lax ",
        "CRSDepTime": "730.00",
        "CRSArrTime": "2400.00",
        "CRSElapsedTime": "120.00",
        "Distance": "500.00",
        "DistanceGroup": "3.00",
    }

    frame = pd.DataFrame({
        column_name: pd.array(
            [value] * row_count,
            dtype="string",
        )
        for column_name, value in raw_values.items()
    })

    frame[TARGET_COLUMN] = pd.array(
        [0] * row_count,
        dtype="Int8",
    )
    frame[QUARANTINE_REASON_COLUMN] = pd.array(
        [pd.NA] * row_count,
        dtype="string",
    )

    return frame


def test_transforms_valid_labelled_row():
    frame = valid_labelled_frame()

    result = clean_bts_frame(frame)

    assert len(result.valid_rows) == 1
    assert result.quarantined_rows.empty
    assert result.total_row_count == 1

    row = result.valid_rows.loc[0]

    assert row["flight_date"] == pd.Timestamp(
        "2022-01-15"
    )
    assert row["reporting_airline"] == "AA"
    assert row["origin_airport"] == "JFK"
    assert row["destination_airport"] == "LAX"
    assert row["route"] == "JFK-LAX"
    assert row["month"] == 1
    assert row["day_of_week"] == 6
    assert row["scheduled_departure_hour"] == 7
    assert row["scheduled_arrival_hour"] == 0
    assert row["scheduled_elapsed_minutes"] == 120
    assert row["distance_miles"] == 500
    assert row["distance_group"] == 3
    assert row[TARGET_COLUMN] == 0


def test_uses_expected_processed_dtypes():
    result = clean_bts_frame(
        valid_labelled_frame()
    )
    valid = result.valid_rows

    assert str(valid["flight_date"].dtype) == (
        "datetime64[ns]"
    )
    assert str(valid["dot_airline_id"].dtype) == "Int64"
    assert str(valid["flight_number"].dtype) == "Int64"
    assert str(
        valid["scheduled_departure_hour"].dtype
    ) == "Int8"
    assert str(
        valid["scheduled_elapsed_minutes"].dtype
    ) == "Float64"
    assert str(valid["distance_miles"].dtype) == (
        "Float64"
    )
    assert str(valid[TARGET_COLUMN].dtype) == "Int8"


def test_preserves_missing_optional_numerical_values():
    frame = valid_labelled_frame()

    optional_columns = [
        "CRSDepTime",
        "CRSArrTime",
        "CRSElapsedTime",
        "Distance",
        "DistanceGroup",
    ]
    for column_name in optional_columns:
        frame.loc[0, column_name] = pd.NA

    result = clean_bts_frame(frame)

    assert len(result.valid_rows) == 1
    row = result.valid_rows.loc[0]

    assert pd.isna(row["scheduled_departure_hour"])
    assert pd.isna(row["scheduled_arrival_hour"])
    assert pd.isna(row["scheduled_elapsed_minutes"])
    assert pd.isna(row["distance_miles"])
    assert pd.isna(row["distance_group"])


@pytest.mark.parametrize(
    ("raw_time", "expected_reason"),
    [
        ("2360", INVALID_SCHEDULED_DEPARTURE_TIME),
        ("2401", INVALID_SCHEDULED_DEPARTURE_TIME),
        ("2500", INVALID_SCHEDULED_DEPARTURE_TIME),
        ("invalid", INVALID_SCHEDULED_DEPARTURE_TIME),
        ("-1", INVALID_SCHEDULED_DEPARTURE_TIME),
    ],
)
def test_quarantines_invalid_scheduled_departure_time(
    raw_time,
    expected_reason,
):
    frame = valid_labelled_frame()
    frame.loc[0, "CRSDepTime"] = raw_time

    result = clean_bts_frame(frame)

    assert result.valid_rows.empty
    assert len(result.quarantined_rows) == 1
    assert (
        result.quarantined_rows.loc[
            0,
            CLEANING_QUARANTINE_REASON_COLUMN,
        ]
        == expected_reason
    )


@pytest.mark.parametrize(
    ("column_name", "invalid_value", "expected_reason"),
    [
        (
            "Reporting_Airline",
            "!",
            INVALID_REPORTING_AIRLINE,
        ),
        (
            "Origin",
            "J1K",
            INVALID_ORIGIN_AIRPORT,
        ),
        (
            "Dest",
            "LA",
            INVALID_DESTINATION_AIRPORT,
        ),
        (
            "OriginAirportID",
            "0",
            INVALID_ORIGIN_AIRPORT_ID,
        ),
    ],
)
def test_quarantines_invalid_required_identifiers(
    column_name,
    invalid_value,
    expected_reason,
):
    frame = valid_labelled_frame()
    frame.loc[0, column_name] = invalid_value

    result = clean_bts_frame(frame)

    assert result.valid_rows.empty
    assert (
        result.quarantined_rows.loc[
            0,
            CLEANING_QUARANTINE_REASON_COLUMN,
        ]
        == expected_reason
    )


@pytest.mark.parametrize(
    ("column_name", "invalid_value", "expected_reason"),
    [
        (
            "Distance",
            "-10",
            INVALID_DISTANCE,
        ),
        (
            "Distance",
            "not-a-number",
            INVALID_DISTANCE,
        ),
        (
            "DistanceGroup",
            "12",
            INVALID_DISTANCE_GROUP,
        ),
        (
            "DistanceGroup",
            "2.5",
            INVALID_DISTANCE_GROUP,
        ),
    ],
)
def test_quarantines_invalid_numeric_values(
    column_name,
    invalid_value,
    expected_reason,
):
    frame = valid_labelled_frame()
    frame.loc[0, column_name] = invalid_value

    result = clean_bts_frame(frame)

    assert result.valid_rows.empty
    assert (
        result.quarantined_rows.loc[
            0,
            CLEANING_QUARANTINE_REASON_COLUMN,
        ]
        == expected_reason
    )


def test_quarantines_invalid_flight_date():
    frame = valid_labelled_frame()
    frame.loc[0, "FlightDate"] = "2022-02-31"

    result = clean_bts_frame(frame)

    assert result.valid_rows.empty
    assert (
        result.quarantined_rows.loc[
            0,
            CLEANING_QUARANTINE_REASON_COLUMN,
        ]
        == INVALID_FLIGHT_DATE
    )


def test_preserves_target_quarantine_reason():
    frame = valid_labelled_frame()
    frame[TARGET_COLUMN] = pd.array(
        [pd.NA],
        dtype="Int8",
    )
    frame[QUARANTINE_REASON_COLUMN] = pd.array(
        [MISSING_COMPLETED_ARRIVAL_DELAY],
        dtype="string",
    )

    result = clean_bts_frame(frame)

    assert result.valid_rows.empty
    assert len(result.quarantined_rows) == 1
    assert (
        result.quarantined_rows.loc[
            0,
            QUARANTINE_REASON_COLUMN,
        ]
        == MISSING_COMPLETED_ARRIVAL_DELAY
    )


def test_preserves_input_and_conserves_all_rows():
    frame = valid_labelled_frame(row_count=2)
    frame.index = [101, 205]
    frame.loc[205, "Origin"] = "??"

    original = frame.copy(deep=True)

    result = clean_bts_frame(frame)

    assert_frame_equal(frame, original)
    assert result.total_row_count == len(frame)
    assert result.valid_rows.index.tolist() == [101]
    assert result.quarantined_rows.index.tolist() == [205]
    assert (
        result.quarantined_rows.loc[205, "Origin"]
        == "??"
    )


def test_model_features_exclude_outcome_leakage():
    assert set(MODEL_FEATURE_COLUMNS).isdisjoint(
        PROHIBITED_PREDICTION_COLUMNS
    )

    result = clean_bts_frame(
        valid_labelled_frame()
    )

    assert set(result.valid_rows.columns).isdisjoint(
        PROHIBITED_PREDICTION_COLUMNS
    )
    assert TARGET_COLUMN in result.valid_rows.columns


def test_rejects_missing_required_input_column():
    frame = valid_labelled_frame().drop(
        columns=["FlightDate"]
    )

    with pytest.raises(
        ValueError,
        match="FlightDate",
    ):
        clean_bts_frame(frame)