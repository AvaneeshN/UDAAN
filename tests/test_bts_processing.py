import pandas as pd
import pandera.pandas as pa
import pytest
from pandas.testing import assert_frame_equal

import ml.bts_processing as bts_processing
from ml.bts_cleaning import (
    INVALID_ORIGIN_AIRPORT,
)
from ml.bts_processed_schema import (
    processed_bts_columns,
)
from ml.bts_target import (
    MISSING_COMPLETED_ARRIVAL_DELAY,
)
from ml.data_manifest import load_bts_manifest


TARGET_COLUMN = "significant_disruption"


def valid_raw_frame(
    row_count: int = 1,
) -> pd.DataFrame:
    manifest = load_bts_manifest()

    frame = pd.DataFrame({
        column_name: pd.array(
            [""] * row_count,
            dtype="string",
        )
        for column_name in manifest.required_columns
    })

    values = {
        "FlightDate": "2022-01-15",
        "Reporting_Airline": "AA",
        "DOT_ID_Reporting_Airline": "19805.00",
        "Tail_Number": "N123AA",
        "OriginAirportID": "12478.00",
        "Origin": "JFK",
        "DestAirportID": "12892.00",
        "Dest": "LAX",
        "Year": "2022",
        "Quarter": "1",
        "Month": "1",
        "DayofMonth": "15",
        "DayOfWeek": "6",
        "CRSDepTime": "730.00",
        "CRSArrTime": "1030.00",
        "CRSElapsedTime": "120.00",
        "Distance": "500.00",
        "DistanceGroup": "3.00",
        "DepDelayMinutes": "5.00",
        "ArrDelayMinutes": "10.00",
        "Cancelled": "0.00",
        "Diverted": "0.00",
    }

    for column_name, value in values.items():
        frame[column_name] = pd.array(
            [value] * row_count,
            dtype="string",
        )

    frame["Flight_Number_Reporting_Airline"] = (
        pd.array(
            [
                str(101 + position)
                for position in range(row_count)
            ],
            dtype="string",
        )
    )

    return frame


def test_processes_valid_rows_end_to_end():
    frame = valid_raw_frame(row_count=2)
    frame["ArrDelayMinutes"] = pd.array(
        ["10.00", "15.00"],
        dtype="string",
    )

    result = bts_processing.process_bts_frame(
        frame
    )

    assert len(result.valid_rows) == 2
    assert result.quarantined_rows.empty
    assert tuple(result.valid_rows.columns) == (
        processed_bts_columns()
    )

    assert result.valid_rows[
        TARGET_COLUMN
    ].tolist() == [0, 1]

    assert result.summary.input_row_count == 2
    assert result.summary.valid_row_count == 2
    assert result.summary.quarantined_row_count == 0
    assert result.summary.target_class_counts == {
        0: 1,
        1: 1,
    }
    assert (
        result.summary.target_quarantine_reason_counts
        == {}
    )
    assert (
        result.summary.cleaning_quarantine_reason_counts
        == {}
    )


def test_reports_target_and_cleaning_quarantines():
    frame = valid_raw_frame(row_count=4)

    frame["ArrDelayMinutes"] = pd.array(
        [
            "10.00",
            "20.00",
            pd.NA,
            "5.00",
        ],
        dtype="string",
    )
    frame.loc[3, "Origin"] = "??"

    original = frame.copy(deep=True)

    result = bts_processing.process_bts_frame(
        frame
    )

    assert_frame_equal(frame, original)

    assert result.valid_rows.index.tolist() == [0, 1]
    assert result.quarantined_rows.index.tolist() == [
        2,
        3,
    ]

    assert result.summary.input_row_count == 4
    assert result.summary.valid_row_count == 2
    assert result.summary.quarantined_row_count == 2
    assert result.summary.target_class_counts == {
        0: 1,
        1: 1,
    }

    assert (
        result.summary.target_quarantine_reason_counts
        == {
            MISSING_COMPLETED_ARRIVAL_DELAY: 1,
        }
    )
    assert (
        result.summary.cleaning_quarantine_reason_counts
        == {
            INVALID_ORIGIN_AIRPORT: 1,
        }
    )


def test_summary_contains_manifest_identity():
    manifest = load_bts_manifest()
    frame = valid_raw_frame()

    result = bts_processing.process_bts_frame(
        frame,
        manifest=manifest,
    )

    assert (
        result.summary.dataset_id
        == manifest.dataset_id
    )
    assert (
        result.summary.manifest_schema_version
        == manifest.manifest_schema_version
    )


def test_rejects_invalid_raw_dataframe_before_processing():
    frame = valid_raw_frame().drop(
        columns=["FlightDate"]
    )

    with pytest.raises(
        pa.errors.SchemaErrors,
        match="FlightDate",
    ):
        bts_processing.process_bts_frame(frame)


def test_calls_processed_schema_validation(
    monkeypatch,
):
    frame = valid_raw_frame()
    original_validator = (
        bts_processing.validate_processed_bts_frame
    )
    calls = []

    def recording_validator(
        processed_frame,
        manifest=None,
    ):
        calls.append(processed_frame.copy(deep=True))

        return original_validator(
            processed_frame,
            manifest=manifest,
        )

    monkeypatch.setattr(
        bts_processing,
        "validate_processed_bts_frame",
        recording_validator,
    )

    result = bts_processing.process_bts_frame(
        frame
    )

    assert len(calls) == 1
    assert_frame_equal(
        calls[0],
        result.valid_rows,
    )


def test_does_not_suppress_processed_validation_failure(
    monkeypatch,
):
    frame = valid_raw_frame()

    def failing_validator(
        processed_frame,
        manifest=None,
    ):
        raise RuntimeError(
            "processed validation failed"
        )

    monkeypatch.setattr(
        bts_processing,
        "validate_processed_bts_frame",
        failing_validator,
    )

    with pytest.raises(
        RuntimeError,
        match="processed validation failed",
    ):
        bts_processing.process_bts_frame(frame)