from dataclasses import dataclass

import pandas as pd

from ml.bts_cleaning import (
    CLEANING_QUARANTINE_REASON_COLUMN,
    clean_bts_frame,
)
from ml.bts_processed_schema import (
    validate_processed_bts_frame,
)
from ml.bts_schema import validate_raw_bts_frame
from ml.bts_target import (
    QUARANTINE_REASON_COLUMN,
    derive_bts_target,
)
from ml.data_manifest import BTSManifest, load_bts_manifest


@dataclass(frozen=True)
class BTSProcessingSummary:
    """Auditable counts produced by one processing run."""

    dataset_id: str
    manifest_schema_version: int
    input_row_count: int
    valid_row_count: int
    quarantined_row_count: int
    target_class_counts: dict[int, int]
    target_quarantine_reason_counts: dict[str, int]
    cleaning_quarantine_reason_counts: dict[str, int]


@dataclass(frozen=True)
class BTSProcessingResult:
    """Validated data and summary produced by BTS processing."""

    valid_rows: pd.DataFrame
    quarantined_rows: pd.DataFrame
    summary: BTSProcessingSummary


def _reason_counts(
    frame: pd.DataFrame,
    column_name: str,
) -> dict[str, int]:
    if frame.empty or column_name not in frame.columns:
        return {}

    counts = (
        frame[column_name]
        .dropna()
        .value_counts()
        .sort_index()
    )

    return {
        str(reason): int(count)
        for reason, count in counts.items()
    }


def _target_class_counts(
    frame: pd.DataFrame,
    target_column: str,
) -> dict[int, int]:
    if frame.empty:
        return {}

    counts = (
        frame[target_column]
        .value_counts()
        .sort_index()
    )

    return {
        int(target_class): int(count)
        for target_class, count in counts.items()
    }


def process_bts_frame(
    raw_frame: pd.DataFrame,
    manifest: BTSManifest | None = None,
) -> BTSProcessingResult:
    """
    Run the complete in-memory BTS processing pipeline.

    Processing order:

    1. Validate the raw dataframe.
    2. Derive the disruption target.
    3. Clean and quarantine rows.
    4. Validate the processed valid rows.
    5. Produce deterministic audit counts.

    This function performs no file writes and no model training.
    """
    resolved_manifest = manifest or load_bts_manifest()
    target_column = resolved_manifest.target.name

    validated_raw = validate_raw_bts_frame(
        raw_frame,
        manifest=resolved_manifest,
    )

    labelled = derive_bts_target(
        validated_raw,
        manifest=resolved_manifest,
    )

    cleaned = clean_bts_frame(
        labelled,
        manifest=resolved_manifest,
    )

    validated_processed = validate_processed_bts_frame(
        cleaned.valid_rows,
        manifest=resolved_manifest,
    )

    valid_row_count = len(validated_processed)
    quarantined_row_count = len(
        cleaned.quarantined_rows
    )

    if (
        valid_row_count + quarantined_row_count
        != len(raw_frame)
    ):
        raise RuntimeError(
            "BTS processing violated row-count conservation"
        )

    summary = BTSProcessingSummary(
        dataset_id=resolved_manifest.dataset_id,
        manifest_schema_version=(
            resolved_manifest.manifest_schema_version
        ),
        input_row_count=len(raw_frame),
        valid_row_count=valid_row_count,
        quarantined_row_count=quarantined_row_count,
        target_class_counts=_target_class_counts(
            validated_processed,
            target_column,
        ),
        target_quarantine_reason_counts=_reason_counts(
            cleaned.quarantined_rows,
            QUARANTINE_REASON_COLUMN,
        ),
        cleaning_quarantine_reason_counts=_reason_counts(
            cleaned.quarantined_rows,
            CLEANING_QUARANTINE_REASON_COLUMN,
        ),
    )

    return BTSProcessingResult(
        valid_rows=validated_processed,
        quarantined_rows=cleaned.quarantined_rows,
        summary=summary,
    )