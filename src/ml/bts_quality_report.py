from dataclasses import asdict, dataclass

import pandas as pd

from ml.bts_processing import BTSProcessingResult
from ml.data_manifest import BTSManifest, load_bts_manifest


@dataclass(frozen=True)
class MissingValueMetric:
    """Missing-value statistics for one column."""

    missing_count: int
    missing_percentage: float


@dataclass(frozen=True)
class BTSDataQualityReport:
    """Deterministic quality report for one BTS processing run."""

    dataset_id: str
    manifest_schema_version: int
    input_row_count: int
    valid_row_count: int
    quarantined_row_count: int
    valid_percentage: float
    quarantined_percentage: float
    target_class_counts: dict[int, int]
    target_class_percentages: dict[int, float]
    target_quarantine_reason_counts: dict[str, int]
    cleaning_quarantine_reason_counts: dict[str, int]
    raw_missing_values: dict[str, MissingValueMetric]
    processed_missing_values: dict[str, MissingValueMetric]
    rows_in_exact_duplicate_groups: int
    exact_duplicate_rows_beyond_first: int
    reporting_airline_count: int
    origin_airport_count: int
    destination_airport_count: int
    route_count: int
    valid_start_date: str | None
    valid_end_date: str | None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-ready dictionary representation."""
        return asdict(self)


def _percentage(
    numerator: int,
    denominator: int,
) -> float:
    if denominator == 0:
        return 0.0

    return round(
        numerator / denominator * 100,
        6,
    )


def _raw_missing_mask(
    series: pd.Series,
) -> pd.Series:
    """
    Treat null, empty and whitespace-only raw values as missing.
    """
    text_values = series.astype("string")

    return (
        text_values.isna()
        | text_values.str.strip().eq("").fillna(False)
    )


def _raw_missing_summary(
    frame: pd.DataFrame,
) -> dict[str, MissingValueMetric]:
    result = {}

    for column_name in frame.columns:
        missing_count = int(
            _raw_missing_mask(
                frame[column_name]
            ).sum()
        )

        result[column_name] = MissingValueMetric(
            missing_count=missing_count,
            missing_percentage=_percentage(
                missing_count,
                len(frame),
            ),
        )

    return result


def _processed_missing_summary(
    frame: pd.DataFrame,
) -> dict[str, MissingValueMetric]:
    result = {}

    for column_name in frame.columns:
        missing_count = int(
            frame[column_name].isna().sum()
        )

        result[column_name] = MissingValueMetric(
            missing_count=missing_count,
            missing_percentage=_percentage(
                missing_count,
                len(frame),
            ),
        )

    return result


def _target_class_percentages(
    target_class_counts: dict[int, int],
    valid_row_count: int,
) -> dict[int, float]:
    return {
        target_class: _percentage(
            count,
            valid_row_count,
        )
        for target_class, count
        in target_class_counts.items()
    }


def _valid_date_range(
    valid_rows: pd.DataFrame,
) -> tuple[str | None, str | None]:
    if valid_rows.empty:
        return None, None

    start_date = (
        valid_rows["flight_date"]
        .min()
        .date()
        .isoformat()
    )
    end_date = (
        valid_rows["flight_date"]
        .max()
        .date()
        .isoformat()
    )

    return start_date, end_date


def _validate_processing_result(
    raw_frame: pd.DataFrame,
    processing_result: BTSProcessingResult,
    manifest: BTSManifest,
) -> None:
    summary = processing_result.summary

    if summary.dataset_id != manifest.dataset_id:
        raise ValueError(
            "Processing result dataset_id does not match "
            "the manifest"
        )

    if (
        summary.manifest_schema_version
        != manifest.manifest_schema_version
    ):
        raise ValueError(
            "Processing result manifest schema version "
            "does not match the manifest"
        )

    if summary.input_row_count != len(raw_frame):
        raise ValueError(
            "Processing result input row count does not "
            "match the raw dataframe"
        )

    if summary.valid_row_count != len(
        processing_result.valid_rows
    ):
        raise ValueError(
            "Processing result valid row count is inconsistent"
        )

    if summary.quarantined_row_count != len(
        processing_result.quarantined_rows
    ):
        raise ValueError(
            "Processing result quarantined row count "
            "is inconsistent"
        )

    if (
        summary.valid_row_count
        + summary.quarantined_row_count
        != summary.input_row_count
    ):
        raise ValueError(
            "Processing result violates row-count conservation"
        )


def build_bts_quality_report(
    raw_frame: pd.DataFrame,
    processing_result: BTSProcessingResult,
    manifest: BTSManifest | None = None,
) -> BTSDataQualityReport:
    """
    Build a deterministic report without modifying or saving data.
    """
    resolved_manifest = manifest or load_bts_manifest()

    _validate_processing_result(
        raw_frame,
        processing_result,
        resolved_manifest,
    )

    summary = processing_result.summary
    valid_rows = processing_result.valid_rows

    duplicate_group_rows = int(
        raw_frame.duplicated(
            keep=False
        ).sum()
    )
    duplicate_rows_beyond_first = int(
        raw_frame.duplicated(
            keep="first"
        ).sum()
    )

    valid_start_date, valid_end_date = (
        _valid_date_range(valid_rows)
    )

    return BTSDataQualityReport(
        dataset_id=summary.dataset_id,
        manifest_schema_version=(
            summary.manifest_schema_version
        ),
        input_row_count=summary.input_row_count,
        valid_row_count=summary.valid_row_count,
        quarantined_row_count=(
            summary.quarantined_row_count
        ),
        valid_percentage=_percentage(
            summary.valid_row_count,
            summary.input_row_count,
        ),
        quarantined_percentage=_percentage(
            summary.quarantined_row_count,
            summary.input_row_count,
        ),
        target_class_counts=dict(
            summary.target_class_counts
        ),
        target_class_percentages=(
            _target_class_percentages(
                summary.target_class_counts,
                summary.valid_row_count,
            )
        ),
        target_quarantine_reason_counts=dict(
            summary.target_quarantine_reason_counts
        ),
        cleaning_quarantine_reason_counts=dict(
            summary.cleaning_quarantine_reason_counts
        ),
        raw_missing_values=_raw_missing_summary(
            raw_frame
        ),
        processed_missing_values=(
            _processed_missing_summary(valid_rows)
        ),
        rows_in_exact_duplicate_groups=(
            duplicate_group_rows
        ),
        exact_duplicate_rows_beyond_first=(
            duplicate_rows_beyond_first
        ),
        reporting_airline_count=int(
            valid_rows["reporting_airline"].nunique(
                dropna=True
            )
        ),
        origin_airport_count=int(
            valid_rows["origin_airport"].nunique(
                dropna=True
            )
        ),
        destination_airport_count=int(
            valid_rows[
                "destination_airport"
            ].nunique(
                dropna=True
            )
        ),
        route_count=int(
            valid_rows["route"].nunique(
                dropna=True
            )
        ),
        valid_start_date=valid_start_date,
        valid_end_date=valid_end_date,
    )