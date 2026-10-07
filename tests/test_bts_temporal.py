import pandas as pd
import pytest
from pandas.testing import assert_series_equal

from ml.bts_temporal import (
    PREDICTION_HORIZON,
    derive_bts_temporal_fields,
)


def raw_string_series(
    values,
    *,
    name,
    index=None,
) -> pd.Series:
    return pd.Series(
        pd.array(
            values,
            dtype="string",
        ),
        index=index,
        name=name,
    )


def test_parses_regular_bts_scheduled_times():
    flight_dates = raw_string_series(
        [
            "2022-01-15",
            "2022-01-15",
            "2022-01-15",
        ],
        name="FlightDate",
    )
    departure_times = raw_string_series(
        [
            "0730",
            "5",
            "945.00",
        ],
        name="CRSDepTime",
    )

    result = derive_bts_temporal_fields(
        flight_dates,
        departure_times,
    )

    assert result.scheduled_departure_hour.tolist() == [
        7,
        0,
        9,
    ]
    assert result.scheduled_departure_local.tolist() == [
        pd.Timestamp("2022-01-15 07:30"),
        pd.Timestamp("2022-01-15 00:05"),
        pd.Timestamp("2022-01-15 09:45"),
    ]
    assert result.prediction_cutoff_local.tolist() == [
        pd.Timestamp("2022-01-14 07:30"),
        pd.Timestamp("2022-01-14 00:05"),
        pd.Timestamp("2022-01-14 09:45"),
    ]
    assert not result.invalid_flight_date.any()
    assert not (
        result.missing_scheduled_departure_time.any()
    )
    assert not (
        result.invalid_scheduled_departure_time.any()
    )


def test_rolls_2400_into_following_calendar_day():
    flight_dates = raw_string_series(
        ["2022-01-15"],
        name="FlightDate",
    )
    departure_times = raw_string_series(
        ["2400"],
        name="CRSDepTime",
    )

    result = derive_bts_temporal_fields(
        flight_dates,
        departure_times,
    )

    assert result.scheduled_departure_hour.loc[0] == 0
    assert (
        result.scheduled_departure_local.loc[0]
        == pd.Timestamp("2022-01-16 00:00")
    )
    assert (
        result.prediction_cutoff_local.loc[0]
        == pd.Timestamp("2022-01-15 00:00")
    )


@pytest.mark.parametrize(
    "missing_value",
    [
        pd.NA,
        "",
        "   ",
    ],
)
def test_distinguishes_missing_departure_time(
    missing_value,
):
    flight_dates = raw_string_series(
        ["2022-01-15"],
        name="FlightDate",
    )
    departure_times = raw_string_series(
        [missing_value],
        name="CRSDepTime",
    )

    result = derive_bts_temporal_fields(
        flight_dates,
        departure_times,
    )

    assert bool(
        result.missing_scheduled_departure_time.loc[0]
    )
    assert not bool(
        result.invalid_scheduled_departure_time.loc[0]
    )
    assert pd.isna(
        result.scheduled_departure_hour.loc[0]
    )
    assert pd.isna(
        result.scheduled_departure_local.loc[0]
    )
    assert pd.isna(
        result.prediction_cutoff_local.loc[0]
    )


@pytest.mark.parametrize(
    "invalid_value",
    [
        "2360",
        "2401",
        "2500",
        "-1",
        "730.5",
        "inf",
        "not-a-time",
    ],
)
def test_rejects_malformed_departure_time(
    invalid_value,
):
    flight_dates = raw_string_series(
        ["2022-01-15"],
        name="FlightDate",
    )
    departure_times = raw_string_series(
        [invalid_value],
        name="CRSDepTime",
    )

    result = derive_bts_temporal_fields(
        flight_dates,
        departure_times,
    )

    assert not bool(
        result.missing_scheduled_departure_time.loc[0]
    )
    assert bool(
        result.invalid_scheduled_departure_time.loc[0]
    )
    assert pd.isna(
        result.scheduled_departure_hour.loc[0]
    )
    assert pd.isna(
        result.scheduled_departure_local.loc[0]
    )
    assert pd.isna(
        result.prediction_cutoff_local.loc[0]
    )


@pytest.mark.parametrize(
    "invalid_date",
    [
        pd.NA,
        "",
        "2022-02-30",
        "15-01-2022",
        "not-a-date",
    ],
)
def test_marks_invalid_flight_date(
    invalid_date,
):
    flight_dates = raw_string_series(
        [invalid_date],
        name="FlightDate",
    )
    departure_times = raw_string_series(
        ["0730"],
        name="CRSDepTime",
    )

    result = derive_bts_temporal_fields(
        flight_dates,
        departure_times,
    )

    assert bool(result.invalid_flight_date.loc[0])
    assert (
        result.scheduled_departure_hour.loc[0]
        == 7
    )
    assert pd.isna(
        result.scheduled_departure_local.loc[0]
    )
    assert pd.isna(
        result.prediction_cutoff_local.loc[0]
    )
    assert not bool(
        result.invalid_scheduled_departure_time.loc[0]
    )


def test_prediction_cutoff_is_exactly_24_hours():
    flight_dates = raw_string_series(
        [
            "2022-01-15",
            "2022-01-16",
        ],
        name="FlightDate",
    )
    departure_times = raw_string_series(
        [
            "1234",
            "2400",
        ],
        name="CRSDepTime",
    )

    result = derive_bts_temporal_fields(
        flight_dates,
        departure_times,
    )

    differences = (
        result.scheduled_departure_local
        - result.prediction_cutoff_local
    )

    assert differences.eq(
        PREDICTION_HORIZON
    ).all()


def test_preserves_indexes_and_does_not_modify_inputs():
    index = pd.Index(
        [101, 205],
        name="source_row",
    )
    flight_dates = raw_string_series(
        [
            "2022-01-15",
            "2022-01-16",
        ],
        name="FlightDate",
        index=index,
    )
    departure_times = raw_string_series(
        [
            "0730",
            "1815",
        ],
        name="CRSDepTime",
        index=index,
    )

    original_dates = flight_dates.copy(deep=True)
    original_times = departure_times.copy(deep=True)

    result = derive_bts_temporal_fields(
        flight_dates,
        departure_times,
    )

    assert_series_equal(
        flight_dates,
        original_dates,
    )
    assert_series_equal(
        departure_times,
        original_times,
    )

    for output_series in (
        result.flight_date,
        result.scheduled_departure_hour,
        result.scheduled_departure_local,
        result.prediction_cutoff_local,
        result.invalid_flight_date,
        result.missing_scheduled_departure_time,
        result.invalid_scheduled_departure_time,
    ):
        assert output_series.index.equals(index)


def test_rejects_mismatched_input_indexes():
    flight_dates = raw_string_series(
        ["2022-01-15"],
        name="FlightDate",
        index=[10],
    )
    departure_times = raw_string_series(
        ["0730"],
        name="CRSDepTime",
        index=[20],
    )

    with pytest.raises(
        ValueError,
        match="indexes must match",
    ):
        derive_bts_temporal_fields(
            flight_dates,
            departure_times,
        )


def test_uses_expected_output_dtypes():
    flight_dates = raw_string_series(
        ["2022-01-15"],
        name="FlightDate",
    )
    departure_times = raw_string_series(
        ["0730"],
        name="CRSDepTime",
    )

    result = derive_bts_temporal_fields(
        flight_dates,
        departure_times,
    )

    assert str(result.flight_date.dtype) == (
        "datetime64[ns]"
    )
    assert str(
        result.scheduled_departure_hour.dtype
    ) == "Int8"
    assert str(
        result.scheduled_departure_local.dtype
    ) == "datetime64[ns]"
    assert str(
        result.prediction_cutoff_local.dtype
    ) == "datetime64[ns]"
    assert str(result.invalid_flight_date.dtype) == (
        "boolean"
    )
    assert str(
        result.missing_scheduled_departure_time.dtype
    ) == "boolean"
    assert str(
        result.invalid_scheduled_departure_time.dtype
    ) == "boolean"
    assert result.scheduled_departure_local.dt.tz is None