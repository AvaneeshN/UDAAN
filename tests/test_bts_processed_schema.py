import pandas as pd
import pandera.pandas as pa
import pytest
from pandas.testing import assert_frame_equal

from ml.bts_cleaning import (
    MODEL_FEATURE_COLUMNS,
    PROCESSED_METADATA_COLUMNS,
)
from ml.bts_processed_schema import (
    PROCESSED_BTS_SCHEMA_NAME,
    build_processed_bts_schema,
    processed_bts_columns,
    validate_processed_bts_frame,
)
from ml.data_manifest import load_bts_manifest


TARGET_COLUMN = "significant_disruption"


def valid_processed_frame() -> pd.DataFrame:
    return pd.DataFrame({
        "flight_date": pd.Series(
            pd.to_datetime(["2022-01-15"])
        ),
        "dot_airline_id": pd.Series(
            [19805],
            dtype="Int64",
        ),
        "flight_number": pd.Series(
            [101],
            dtype="Int64",
        ),
        "origin_airport_id": pd.Series(
            [12478],
            dtype="Int64",
        ),
        "destination_airport_id": pd.Series(
            [12892],
            dtype="Int64",
        ),
        "reporting_airline": pd.Series(
            ["AA"],
            dtype="string",
        ),
        "origin_airport": pd.Series(
            ["JFK"],
            dtype="string",
        ),
        "destination_airport": pd.Series(
            ["LAX"],
            dtype="string",
        ),
        "route": pd.Series(
            ["JFK-LAX"],
            dtype="string",
        ),
        "month": pd.Series(
            [1],
            dtype="Int8",
        ),
        "day_of_week": pd.Series(
            [6],
            dtype="Int8",
        ),
        "scheduled_departure_hour": pd.Series(
            [7],
            dtype="Int8",
        ),
        "scheduled_arrival_hour": pd.Series(
            [0],
            dtype="Int8",
        ),
        "scheduled_elapsed_minutes": pd.Series(
            [120.0],
            dtype="Float64",
        ),
        "distance_miles": pd.Series(
            [500.0],
            dtype="Float64",
        ),
        "distance_group": pd.Series(
            [3],
            dtype="Int8",
        ),
        TARGET_COLUMN: pd.Series(
            [0],
            dtype="Int8",
        ),
    })


def test_schema_uses_processed_column_contract():
    manifest = load_bts_manifest()
    schema = build_processed_bts_schema(manifest)

    expected_columns = (
        *PROCESSED_METADATA_COLUMNS,
        *MODEL_FEATURE_COLUMNS,
        manifest.target.name,
    )

    assert schema.name == PROCESSED_BTS_SCHEMA_NAME
    assert tuple(schema.columns) == expected_columns
    assert processed_bts_columns(manifest) == (
        expected_columns
    )
    assert (
        schema.metadata["dataset_id"]
        == manifest.dataset_id
    )
    assert (
        schema.metadata["target_column"]
        == manifest.target.name
    )


def test_accepts_valid_processed_dataframe():
    frame = valid_processed_frame()
    original = frame.copy(deep=True)

    validated = validate_processed_bts_frame(frame)

    assert_frame_equal(validated, original)
    assert_frame_equal(frame, original)


def test_accepts_empty_processed_dataframe():
    frame = valid_processed_frame().iloc[0:0]

    validated = validate_processed_bts_frame(frame)

    assert validated.empty
    assert tuple(validated.columns) == tuple(
        frame.columns
    )


def test_accepts_missing_optional_model_values():
    frame = valid_processed_frame()

    optional_columns = [
        "scheduled_departure_hour",
        "scheduled_arrival_hour",
        "scheduled_elapsed_minutes",
        "distance_miles",
        "distance_group",
    ]
    for column_name in optional_columns:
        frame.loc[0, column_name] = pd.NA

    validated = validate_processed_bts_frame(frame)

    assert validated.loc[
        0,
        optional_columns,
    ].isna().all()


def test_rejects_missing_required_column():
    frame = valid_processed_frame().drop(
        columns=["flight_date"]
    )

    with pytest.raises(
        pa.errors.SchemaErrors,
        match="flight_date",
    ):
        validate_processed_bts_frame(frame)


def test_rejects_unexpected_column():
    frame = valid_processed_frame()
    frame["unexpected"] = pd.Series(
        ["value"],
        dtype="string",
    )

    with pytest.raises(
        pa.errors.SchemaErrors,
        match="unexpected",
    ):
        validate_processed_bts_frame(frame)


def test_rejects_incorrect_column_order():
    frame = valid_processed_frame()
    columns = list(frame.columns)

    columns[0], columns[1] = (
        columns[1],
        columns[0],
    )
    frame = frame[columns]

    with pytest.raises(pa.errors.SchemaErrors):
        validate_processed_bts_frame(frame)


def test_rejects_incorrect_dtype():
    frame = valid_processed_frame()
    frame["month"] = frame["month"].astype(
        "int64"
    )

    with pytest.raises(
        pa.errors.SchemaErrors,
        match="month",
    ):
        validate_processed_bts_frame(frame)


@pytest.mark.parametrize(
    ("column_name", "invalid_value"),
    [
        ("dot_airline_id", 0),
        ("flight_number", 0),
        ("origin_airport_id", -1),
        ("destination_airport_id", 0),
        ("month", 13),
        ("day_of_week", 0),
        ("scheduled_departure_hour", 24),
        ("scheduled_arrival_hour", -1),
        ("scheduled_elapsed_minutes", 0),
        ("distance_miles", -1),
        ("distance_group", 12),
        (TARGET_COLUMN, 2),
    ],
)
def test_rejects_values_outside_allowed_ranges(
    column_name,
    invalid_value,
):
    frame = valid_processed_frame()
    frame.loc[0, column_name] = invalid_value

    with pytest.raises(
        pa.errors.SchemaErrors,
        match=column_name,
    ):
        validate_processed_bts_frame(frame)


@pytest.mark.parametrize(
    ("column_name", "invalid_value"),
    [
        ("reporting_airline", "A!"),
        ("reporting_airline", "AAA"),
        ("origin_airport", "J1K"),
        ("origin_airport", "JF"),
        ("destination_airport", "la"),
        ("destination_airport", "LAXX"),
        ("route", "JFK/LAX"),
    ],
)
def test_rejects_invalid_code_formats(
    column_name,
    invalid_value,
):
    frame = valid_processed_frame()
    frame.loc[0, column_name] = invalid_value

    with pytest.raises(
        pa.errors.SchemaErrors,
        match=column_name,
    ):
        validate_processed_bts_frame(frame)


def test_rejects_route_inconsistent_with_airports():
    frame = valid_processed_frame()
    frame.loc[0, "route"] = "LAX-JFK"

    with pytest.raises(pa.errors.SchemaErrors):
        validate_processed_bts_frame(frame)


def test_rejects_month_inconsistent_with_flight_date():
    frame = valid_processed_frame()
    frame.loc[0, "month"] = 2

    with pytest.raises(pa.errors.SchemaErrors):
        validate_processed_bts_frame(frame)


def test_rejects_weekday_inconsistent_with_flight_date():
    frame = valid_processed_frame()
    frame.loc[0, "day_of_week"] = 5

    with pytest.raises(pa.errors.SchemaErrors):
        validate_processed_bts_frame(frame)


def test_rejects_prohibited_outcome_column():
    frame = valid_processed_frame()
    frame["ArrDelayMinutes"] = pd.Series(
        ["20.00"],
        dtype="string",
    )

    with pytest.raises(
        pa.errors.SchemaErrors,
        match="ArrDelayMinutes",
    ):
        validate_processed_bts_frame(frame)