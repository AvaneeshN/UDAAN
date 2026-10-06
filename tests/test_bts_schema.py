import pandas as pd
import pandera.pandas as pa
import pytest
from pandas.testing import assert_frame_equal

from ml.bts_schema import (
    RAW_BTS_SCHEMA_NAME,
    build_raw_bts_schema,
    validate_raw_bts_frame,
)
from ml.data_manifest import load_bts_manifest


def valid_raw_bts_frame() -> pd.DataFrame:
    manifest = load_bts_manifest()

    frame = pd.DataFrame({
        column_name: pd.Series([""], dtype="string")
        for column_name in manifest.required_columns
    })

    frame.loc[0, "FlightDate"] = "2022-01-01"
    frame.loc[0, "Reporting_Airline"] = "AA"
    frame.loc[0, "Origin"] = "JFK"
    frame.loc[0, "Dest"] = "LAX"
    frame.loc[0, "Year"] = "2022"
    frame.loc[0, "Month"] = "1"
    frame.loc[0, "Cancelled"] = "0.00"
    frame.loc[0, "Diverted"] = "0.00"

    return frame


def test_raw_schema_uses_manifest_column_contract():
    manifest = load_bts_manifest()
    schema = build_raw_bts_schema(manifest)

    assert schema.name == RAW_BTS_SCHEMA_NAME
    assert tuple(schema.columns) == manifest.required_columns
    assert schema.metadata["dataset_id"] == manifest.dataset_id
    assert (
        schema.metadata["manifest_schema_version"]
        == manifest.manifest_schema_version
    )


def test_accepts_valid_raw_string_dataframe():
    frame = valid_raw_bts_frame()
    original = frame.copy(deep=True)

    validated = validate_raw_bts_frame(frame)

    assert_frame_equal(validated, original)


def test_preserves_missing_raw_values():
    frame = valid_raw_bts_frame()
    frame.loc[0, "Tail_Number"] = pd.NA

    validated = validate_raw_bts_frame(frame)

    assert pd.isna(validated.loc[0, "Tail_Number"])


def test_rejects_missing_required_column():
    frame = valid_raw_bts_frame().drop(
        columns=["FlightDate"],
    )

    with pytest.raises(
        pa.errors.SchemaErrors,
        match="FlightDate",
    ):
        validate_raw_bts_frame(frame)


def test_rejects_unexpected_column():
    frame = valid_raw_bts_frame()
    frame["UnexpectedColumn"] = pd.Series(
        ["unexpected"],
        dtype="string",
    )

    with pytest.raises(
        pa.errors.SchemaErrors,
        match="UnexpectedColumn",
    ):
        validate_raw_bts_frame(frame)


def test_rejects_incorrect_raw_dtype():
    frame = valid_raw_bts_frame()
    frame["Year"] = pd.Series(
        [2022],
        dtype="int64",
    )

    with pytest.raises(
        pa.errors.SchemaErrors,
        match="Year",
    ):
        validate_raw_bts_frame(frame)


def test_rejects_incorrect_column_order():
    frame = valid_raw_bts_frame()
    reordered_columns = list(frame.columns)

    reordered_columns[0], reordered_columns[1] = (
        reordered_columns[1],
        reordered_columns[0],
    )

    frame = frame[reordered_columns]

    with pytest.raises(pa.errors.SchemaErrors):
        validate_raw_bts_frame(frame)


def test_rejects_empty_batch():
    frame = valid_raw_bts_frame().iloc[0:0]

    with pytest.raises(
        pa.errors.SchemaErrors,
        match="at least one row",
    ):
        validate_raw_bts_frame(frame)