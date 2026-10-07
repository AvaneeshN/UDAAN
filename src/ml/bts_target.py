import pandas as pd

from ml.data_manifest import BTSManifest, load_bts_manifest


TARGET_SOURCE_COLUMNS = (
    "Cancelled",
    "Diverted",
    "ArrDelayMinutes",
)

QUARANTINE_REASON_COLUMN = "quarantine_reason"

INVALID_CANCELLED_INDICATOR = "invalid_cancelled_indicator"
INVALID_DIVERTED_INDICATOR = "invalid_diverted_indicator"
MISSING_COMPLETED_ARRIVAL_DELAY = (
    "missing_arrival_delay_for_completed_flight"
)
INVALID_COMPLETED_ARRIVAL_DELAY = (
    "invalid_arrival_delay_for_completed_flight"
)


def _find_missing_text_values(series: pd.Series) -> pd.Series:
    """Identify missing, empty, or whitespace-only raw values."""
    text_values = series.astype("string")

    return (
        text_values.isna()
        | text_values.str.strip().eq("").fillna(False)
    )


def _require_target_source_columns(frame: pd.DataFrame) -> None:
    """Fail clearly if target-generation inputs are unavailable."""
    missing_columns = [
        column_name
        for column_name in TARGET_SOURCE_COLUMNS
        if column_name not in frame.columns
    ]

    if missing_columns:
        missing_list = ", ".join(missing_columns)
        raise ValueError(
            "BTS target inputs are missing required columns: "
            f"{missing_list}"
        )


def derive_bts_target(
    frame: pd.DataFrame,
    manifest: BTSManifest | None = None,
) -> pd.DataFrame:
    """
    Return a copy of the BTS dataframe with its target and quarantine reason.

    A flight is a significant disruption when it was cancelled, diverted,
    or arrived at least the configured number of minutes late.

    Rows whose target cannot be determined remain in the returned dataframe.
    Their target is pd.NA and quarantine_reason explains the problem.
    """
    resolved_manifest = manifest or load_bts_manifest()
    target_definition = resolved_manifest.target
    target_column = target_definition.name

    _require_target_source_columns(frame)

    generated_columns = {
        target_column,
        QUARANTINE_REASON_COLUMN,
    }
    conflicting_columns = generated_columns.intersection(frame.columns)

    if conflicting_columns:
        conflict_list = ", ".join(sorted(conflicting_columns))
        raise ValueError(
            "BTS target output columns already exist: "
            f"{conflict_list}"
        )

    cancelled = pd.to_numeric(
        frame["Cancelled"],
        errors="coerce",
    )
    diverted = pd.to_numeric(
        frame["Diverted"],
        errors="coerce",
    )
    arrival_delay = pd.to_numeric(
        frame["ArrDelayMinutes"],
        errors="coerce",
    )

    cancelled_is_valid = cancelled.isin([0, 1])
    diverted_is_valid = diverted.isin([0, 1])

    invalid_cancelled = ~cancelled_is_valid
    invalid_diverted = cancelled_is_valid & ~diverted_is_valid

    indicators_are_valid = (
        cancelled_is_valid
        & diverted_is_valid
    )

    cancelled_or_diverted = indicators_are_valid & (
        cancelled.eq(1).fillna(False)
        | diverted.eq(1).fillna(False)
    )

    completed_flight = indicators_are_valid & (
        cancelled.eq(0).fillna(False)
        & diverted.eq(0).fillna(False)
    )

    arrival_delay_is_missing = _find_missing_text_values(
        frame["ArrDelayMinutes"]
    )

    arrival_delay_is_finite = (
        arrival_delay.notna()
        & arrival_delay.abs().ne(float("inf")).fillna(False)
    )
    arrival_delay_is_nonnegative = (
        arrival_delay.ge(0).fillna(False)
    )
    arrival_delay_is_valid = (
        arrival_delay_is_finite
        & arrival_delay_is_nonnegative
    )

    missing_completed_arrival_delay = (
        completed_flight
        & arrival_delay_is_missing
    )
    invalid_completed_arrival_delay = (
        completed_flight
        & ~arrival_delay_is_missing
        & ~arrival_delay_is_valid
    )
    resolved_completed_flight = (
        completed_flight
        & arrival_delay_is_valid
    )

    labels = pd.Series(
        pd.NA,
        index=frame.index,
        dtype="Int8",
        name=target_column,
    )
    quarantine_reasons = pd.Series(
        pd.NA,
        index=frame.index,
        dtype="string",
        name=QUARANTINE_REASON_COLUMN,
    )

    labels.loc[cancelled_or_diverted] = (
        target_definition.positive_class
    )

    delayed_completed_flight = (
        resolved_completed_flight
        & arrival_delay.ge(
            target_definition.delay_threshold_minutes
        ).fillna(False)
    )
    on_time_completed_flight = (
        resolved_completed_flight
        & arrival_delay.lt(
            target_definition.delay_threshold_minutes
        ).fillna(False)
    )

    labels.loc[delayed_completed_flight] = (
        target_definition.positive_class
    )
    labels.loc[on_time_completed_flight] = (
        target_definition.negative_class
    )

    quarantine_reasons.loc[invalid_cancelled] = (
        INVALID_CANCELLED_INDICATOR
    )
    quarantine_reasons.loc[invalid_diverted] = (
        INVALID_DIVERTED_INDICATOR
    )
    quarantine_reasons.loc[
        missing_completed_arrival_delay
    ] = MISSING_COMPLETED_ARRIVAL_DELAY
    quarantine_reasons.loc[
        invalid_completed_arrival_delay
    ] = INVALID_COMPLETED_ARRIVAL_DELAY

    labelled_frame = frame.copy(deep=True)
    labelled_frame[target_column] = labels
    labelled_frame[QUARANTINE_REASON_COLUMN] = (
        quarantine_reasons
    )

    return labelled_frame