import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from ml.bts_target import (
    INVALID_CANCELLED_INDICATOR,
    INVALID_COMPLETED_ARRIVAL_DELAY,
    INVALID_DIVERTED_INDICATOR,
    MISSING_COMPLETED_ARRIVAL_DELAY,
    QUARANTINE_REASON_COLUMN,
    derive_bts_target,
)
from ml.data_manifest import load_bts_manifest


TARGET_COLUMN = "significant_disruption"


def target_input_frame(
    cancelled,
    diverted,
    arrival_delay,
    index=None,
) -> pd.DataFrame:
    """Build raw string inputs similar to values read from the BTS CSV."""
    return pd.DataFrame(
        {
            "Cancelled": pd.array(
                cancelled,
                dtype="string",
            ),
            "Diverted": pd.array(
                diverted,
                dtype="string",
            ),
            "ArrDelayMinutes": pd.array(
                arrival_delay,
                dtype="string",
            ),
        },
        index=index,
    )


def test_labels_completed_flights_around_delay_threshold():
    frame = target_input_frame(
        cancelled=["0.00", "0.00", "0.00"],
        diverted=["0.00", "0.00", "0.00"],
        arrival_delay=["14.99", "15.00", "45.00"],
    )

    result = derive_bts_target(frame)

    assert result[TARGET_COLUMN].tolist() == [0, 1, 1]
    assert result[QUARANTINE_REASON_COLUMN].isna().all()


def test_cancelled_and_diverted_flights_are_positive():
    frame = target_input_frame(
        cancelled=["1.00", "0.00"],
        diverted=["0.00", "1.00"],
        arrival_delay=[pd.NA, pd.NA],
    )

    result = derive_bts_target(frame)

    assert result[TARGET_COLUMN].tolist() == [1, 1]
    assert result[QUARANTINE_REASON_COLUMN].isna().all()


@pytest.mark.parametrize(
    "cancelled",
    [
        pd.NA,
        "",
        "2.00",
        "invalid",
    ],
)
def test_quarantines_invalid_cancelled_indicator(cancelled):
    frame = target_input_frame(
        cancelled=[cancelled],
        diverted=["0.00"],
        arrival_delay=["30.00"],
    )

    result = derive_bts_target(frame)

    assert pd.isna(result.loc[0, TARGET_COLUMN])
    assert (
        result.loc[0, QUARANTINE_REASON_COLUMN]
        == INVALID_CANCELLED_INDICATOR
    )


@pytest.mark.parametrize(
    "diverted",
    [
        pd.NA,
        "",
        "2.00",
        "invalid",
    ],
)
def test_quarantines_invalid_diverted_indicator(diverted):
    frame = target_input_frame(
        cancelled=["0.00"],
        diverted=[diverted],
        arrival_delay=["30.00"],
    )

    result = derive_bts_target(frame)

    assert pd.isna(result.loc[0, TARGET_COLUMN])
    assert (
        result.loc[0, QUARANTINE_REASON_COLUMN]
        == INVALID_DIVERTED_INDICATOR
    )


@pytest.mark.parametrize(
    "arrival_delay",
    [
        pd.NA,
        "",
        "   ",
    ],
)
def test_quarantines_missing_arrival_delay_for_completed_flight(
    arrival_delay,
):
    frame = target_input_frame(
        cancelled=["0.00"],
        diverted=["0.00"],
        arrival_delay=[arrival_delay],
    )

    result = derive_bts_target(frame)

    assert pd.isna(result.loc[0, TARGET_COLUMN])
    assert (
        result.loc[0, QUARANTINE_REASON_COLUMN]
        == MISSING_COMPLETED_ARRIVAL_DELAY
    )


@pytest.mark.parametrize(
    "arrival_delay",
    [
        "not-a-number",
        "-1.00",
        "inf",
    ],
)
def test_quarantines_invalid_arrival_delay_for_completed_flight(
    arrival_delay,
):
    frame = target_input_frame(
        cancelled=["0.00"],
        diverted=["0.00"],
        arrival_delay=[arrival_delay],
    )

    result = derive_bts_target(frame)

    assert pd.isna(result.loc[0, TARGET_COLUMN])
    assert (
        result.loc[0, QUARANTINE_REASON_COLUMN]
        == INVALID_COMPLETED_ARRIVAL_DELAY
    )


def test_reads_delay_threshold_from_manifest():
    manifest = load_bts_manifest()
    custom_target = manifest.target.model_copy(
        update={"delay_threshold_minutes": 20}
    )
    custom_manifest = manifest.model_copy(
        update={"target": custom_target}
    )

    frame = target_input_frame(
        cancelled=["0.00", "0.00"],
        diverted=["0.00", "0.00"],
        arrival_delay=["19.00", "20.00"],
    )

    result = derive_bts_target(
        frame,
        manifest=custom_manifest,
    )

    assert result[TARGET_COLUMN].tolist() == [0, 1]


def test_preserves_rows_index_and_original_dataframe():
    frame = target_input_frame(
        cancelled=["0.00", "1.00"],
        diverted=["0.00", "0.00"],
        arrival_delay=["5.00", pd.NA],
        index=[101, 205],
    )
    original = frame.copy(deep=True)

    result = derive_bts_target(frame)

    assert_frame_equal(frame, original)
    assert result.index.tolist() == [101, 205]
    assert len(result) == len(frame)
    assert result is not frame


def test_uses_nullable_target_and_reason_dtypes():
    frame = target_input_frame(
        cancelled=["0.00", "0.00"],
        diverted=["0.00", "0.00"],
        arrival_delay=["10.00", pd.NA],
    )

    result = derive_bts_target(frame)

    assert str(result[TARGET_COLUMN].dtype) == "Int8"
    assert (
        str(result[QUARANTINE_REASON_COLUMN].dtype)
        == "string"
    )


def test_rejects_missing_target_source_column():
    frame = target_input_frame(
        cancelled=["0.00"],
        diverted=["0.00"],
        arrival_delay=["10.00"],
    ).drop(columns=["ArrDelayMinutes"])

    with pytest.raises(
        ValueError,
        match="ArrDelayMinutes",
    ):
        derive_bts_target(frame)


def test_rejects_existing_generated_columns():
    frame = target_input_frame(
        cancelled=["0.00"],
        diverted=["0.00"],
        arrival_delay=["10.00"],
    )
    frame[TARGET_COLUMN] = pd.Series(
        [1],
        dtype="Int8",
    )

    with pytest.raises(
        ValueError,
        match=TARGET_COLUMN,
    ):
        derive_bts_target(frame)