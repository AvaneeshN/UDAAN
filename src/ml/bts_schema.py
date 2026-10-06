import pandas as pd
import pandera.pandas as pa

from ml.data_manifest import BTSManifest, load_bts_manifest


RAW_BTS_SCHEMA_NAME = "raw_bts_selected_columns"


def build_raw_bts_schema(
    manifest: BTSManifest | None = None,
) -> pa.DataFrameSchema:
    """Build the schema for selected columns read from a raw BTS CSV."""
    resolved_manifest = manifest or load_bts_manifest()

    columns = {
        column_name: pa.Column(
            pd.StringDtype(),
            nullable=True,
            required=True,
            coerce=False,
        )
        for column_name in resolved_manifest.required_columns
    }

    return pa.DataFrameSchema(
        columns=columns,
        checks=pa.Check(
            lambda frame: len(frame.index) > 0,
            error="BTS batch must contain at least one row",
        ),
        strict=True,
        ordered=True,
        unique_column_names=True,
        coerce=False,
        drop_invalid_rows=False,
        name=RAW_BTS_SCHEMA_NAME,
        metadata={
            "manifest_schema_version": (
                resolved_manifest.manifest_schema_version
            ),
            "dataset_id": resolved_manifest.dataset_id,
        },
    )


def validate_raw_bts_frame(
    frame: pd.DataFrame,
    manifest: BTSManifest | None = None,
) -> pd.DataFrame:
    """Validate a selected raw BTS dataframe without changing its values."""
    schema = build_raw_bts_schema(manifest)

    return schema.validate(
        frame,
        lazy=True,
    )