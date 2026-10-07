import json
from dataclasses import replace

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from ml.bts_cleaning import INVALID_ORIGIN_AIRPORT
from ml.bts_processing import process_bts_frame
from ml.bts_quality_report import (
    build_bts_quality_report,
)
from ml.bts_target import (
    MISSING_COMPLETED_ARRIVAL_DELAY,
)
from ml.data_manifest import load_bts_manifest


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


def test_builds_expected_quality_report():
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

    processing_result = process_bts_frame(frame)

    report = build_bts_quality_report(
        frame,
        processing_result,
    )

    assert report.input_row_count == 4
    assert report.valid_row_count == 2
    assert report.quarantined_row_count == 2
    assert report.valid_percentage == 50.0
    assert report.quarantined_percentage == 50.0

    assert report.target_class_counts == {
        0: 1,
        1: 1,
    }
    assert report.target_class_percentages == {
        0: 50.0,
        1: 50.0,
    }

    assert report.target_quarantine_reason_counts == {
        MISSING_COMPLETED_ARRIVAL_DELAY: 1,
    }
    assert report.cleaning_quarantine_reason_counts == {
        INVALID_ORIGIN_AIRPORT: 1,
    }

    assert (
        report.raw_missing_values[
            "ArrDelayMinutes"
        ].missing_count
        == 1
    )
    assert (
        report.raw_missing_values[
            "ArrDelayMinutes"
        ].missing_percentage
        == 25.0
    )

    assert report.reporting_airline_count == 1
    assert report.origin_airport_count == 1
    assert report.destination_airport_count == 1
    assert report.route_count == 1
    assert report.valid_start_date == "2022-01-15"
    assert report.valid_end_date == "2022-01-15"
    assert report.rows_in_exact_duplicate_groups == 0
    assert report.exact_duplicate_rows_beyond_first == 0


def test_reports_both_duplicate_definitions():
    frame = valid_raw_frame(row_count=3)

    frame["Flight_Number_Reporting_Airline"] = (
        pd.array(
            ["101", "101", "101"],
            dtype="string",
        )
    )

    processing_result = process_bts_frame(frame)
    report = build_bts_quality_report(
        frame,
        processing_result,
    )

    assert report.rows_in_exact_duplicate_groups == 3
    assert report.exact_duplicate_rows_beyond_first == 2


def test_counts_null_empty_and_whitespace_as_raw_missing():
    frame = valid_raw_frame(row_count=3)

    frame["Tail_Number"] = pd.array(
        [
            pd.NA,
            "",
            "   ",
        ],
        dtype="string",
    )

    processing_result = process_bts_frame(frame)
    report = build_bts_quality_report(
        frame,
        processing_result,
    )

    metric = report.raw_missing_values["Tail_Number"]

    assert metric.missing_count == 3
    assert metric.missing_percentage == 100.0


def test_reports_missing_processed_values():
    frame = valid_raw_frame()

    optional_columns = [
        "CRSDepTime",
        "CRSArrTime",
        "CRSElapsedTime",
        "Distance",
        "DistanceGroup",
    ]
    for column_name in optional_columns:
        frame.loc[0, column_name] = pd.NA

    processing_result = process_bts_frame(frame)
    report = build_bts_quality_report(
        frame,
        processing_result,
    )

    processed_columns = [
        "scheduled_departure_hour",
        "scheduled_arrival_hour",
        "scheduled_elapsed_minutes",
        "distance_miles",
        "distance_group",
    ]

    for column_name in processed_columns:
        metric = report.processed_missing_values[
            column_name
        ]

        assert metric.missing_count == 1
        assert metric.missing_percentage == 100.0


def test_handles_processing_result_with_no_valid_rows():
    frame = valid_raw_frame()
    frame.loc[0, "ArrDelayMinutes"] = pd.NA

    processing_result = process_bts_frame(frame)
    report = build_bts_quality_report(
        frame,
        processing_result,
    )

    assert report.valid_row_count == 0
    assert report.quarantined_row_count == 1
    assert report.valid_percentage == 0.0
    assert report.quarantined_percentage == 100.0
    assert report.target_class_counts == {}
    assert report.target_class_percentages == {}
    assert report.reporting_airline_count == 0
    assert report.origin_airport_count == 0
    assert report.destination_airport_count == 0
    assert report.route_count == 0
    assert report.valid_start_date is None
    assert report.valid_end_date is None


def test_report_is_json_serializable():
    frame = valid_raw_frame()
    processing_result = process_bts_frame(frame)

    report = build_bts_quality_report(
        frame,
        processing_result,
    )

    encoded = json.dumps(
        report.to_dict(),
        sort_keys=True,
    )

    assert '"dataset_id"' in encoded
    assert '"raw_missing_values"' in encoded


def test_does_not_modify_input_dataframes():
    frame = valid_raw_frame()
    processing_result = process_bts_frame(frame)

    raw_original = frame.copy(deep=True)
    valid_original = (
        processing_result.valid_rows.copy(deep=True)
    )
    quarantined_original = (
        processing_result.quarantined_rows.copy(
            deep=True
        )
    )

    build_bts_quality_report(
        frame,
        processing_result,
    )

    assert_frame_equal(frame, raw_original)
    assert_frame_equal(
        processing_result.valid_rows,
        valid_original,
    )
    assert_frame_equal(
        processing_result.quarantined_rows,
        quarantined_original,
    )


def test_rejects_inconsistent_processing_result():
    frame = valid_raw_frame()
    processing_result = process_bts_frame(frame)

    invalid_summary = replace(
        processing_result.summary,
        input_row_count=99,
    )
    invalid_result = replace(
        processing_result,
        summary=invalid_summary,
    )

    with pytest.raises(
        ValueError,
        match="input row count",
    ):
        build_bts_quality_report(
            frame,
            invalid_result,
        )