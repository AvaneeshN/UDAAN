import pandas as pd
import pandera.pandas as pa

from ml.bts_cleaning import (
    MODEL_FEATURE_COLUMNS,
    PROCESSED_METADATA_COLUMNS,
)
from ml.data_manifest import BTSManifest, load_bts_manifest


PROCESSED_BTS_SCHEMA_NAME = "processed_bts_model_data"


def processed_bts_columns(
    manifest: BTSManifest | None = None,
) -> tuple[str, ...]:
    """Return the required processed column order."""
    resolved_manifest = manifest or load_bts_manifest()

    return (
        *PROCESSED_METADATA_COLUMNS,
        *MODEL_FEATURE_COLUMNS,
        resolved_manifest.target.name,
    )


def _positive_integer_check(
    description: str,
) -> pa.Check:
    return pa.Check(
        lambda series: series.gt(0).fillna(False),
        error=description,
    )


def _required_code_check(
    pattern: str,
    description: str,
) -> pa.Check:
    return pa.Check(
        lambda series: series.str.fullmatch(
            pattern,
            na=False,
        ),
        error=description,
    )


def _optional_range_check(
    minimum: int,
    maximum: int,
    description: str,
) -> pa.Check:
    return pa.Check(
        lambda series: (
            series.isna()
            | series.between(minimum, maximum)
        ),
        error=description,
    )


def _optional_positive_check(
    description: str,
) -> pa.Check:
    return pa.Check(
        lambda series: (
            series.isna()
            | series.gt(0)
        ),
        error=description,
    )


def _route_matches_airports(
    frame: pd.DataFrame,
) -> pd.Series:
    expected_route = frame[
        "origin_airport"
    ].str.cat(
        frame["destination_airport"],
        sep="-",
    )

    return frame["route"].eq(
        expected_route
    ).fillna(False)


def _month_matches_flight_date(
    frame: pd.DataFrame,
) -> pd.Series:
    expected_month = frame[
        "flight_date"
    ].dt.month

    return frame["month"].eq(
        expected_month
    ).fillna(False)


def _weekday_matches_flight_date(
    frame: pd.DataFrame,
) -> pd.Series:
    expected_weekday = (
        frame["flight_date"]
        .dt.dayofweek
        .add(1)
    )

    return frame["day_of_week"].eq(
        expected_weekday
    ).fillna(False)


def build_processed_bts_schema(
    manifest: BTSManifest | None = None,
) -> pa.DataFrameSchema:
    """Build the strict schema for valid processed BTS rows."""
    resolved_manifest = manifest or load_bts_manifest()
    target_definition = resolved_manifest.target
    target_column = target_definition.name

    columns = {
        "flight_date": pa.Column(
            "datetime64[ns]",
            nullable=False,
            required=True,
            coerce=False,
        ),
        "dot_airline_id": pa.Column(
            pd.Int64Dtype(),
            checks=_positive_integer_check(
                "dot_airline_id must be positive"
            ),
            nullable=False,
            required=True,
            coerce=False,
        ),
        "flight_number": pa.Column(
            pd.Int64Dtype(),
            checks=_positive_integer_check(
                "flight_number must be positive"
            ),
            nullable=False,
            required=True,
            coerce=False,
        ),
        "origin_airport_id": pa.Column(
            pd.Int64Dtype(),
            checks=_positive_integer_check(
                "origin_airport_id must be positive"
            ),
            nullable=False,
            required=True,
            coerce=False,
        ),
        "destination_airport_id": pa.Column(
            pd.Int64Dtype(),
            checks=_positive_integer_check(
                "destination_airport_id must be positive"
            ),
            nullable=False,
            required=True,
            coerce=False,
        ),
        "reporting_airline": pa.Column(
            pd.StringDtype(),
            checks=_required_code_check(
                r"[A-Z0-9]{2}",
                "reporting_airline must contain "
                "two uppercase letters or digits",
            ),
            nullable=False,
            required=True,
            coerce=False,
        ),
        "origin_airport": pa.Column(
            pd.StringDtype(),
            checks=_required_code_check(
                r"[A-Z]{3}",
                "origin_airport must contain "
                "three uppercase letters",
            ),
            nullable=False,
            required=True,
            coerce=False,
        ),
        "destination_airport": pa.Column(
            pd.StringDtype(),
            checks=_required_code_check(
                r"[A-Z]{3}",
                "destination_airport must contain "
                "three uppercase letters",
            ),
            nullable=False,
            required=True,
            coerce=False,
        ),
        "route": pa.Column(
            pd.StringDtype(),
            checks=_required_code_check(
                r"[A-Z]{3}-[A-Z]{3}",
                "route must use ORIGIN-DESTINATION format",
            ),
            nullable=False,
            required=True,
            coerce=False,
        ),
        "month": pa.Column(
            pd.Int8Dtype(),
            checks=pa.Check(
                lambda series: series.between(1, 12),
                error="month must be between 1 and 12",
            ),
            nullable=False,
            required=True,
            coerce=False,
        ),
        "day_of_week": pa.Column(
            pd.Int8Dtype(),
            checks=pa.Check(
                lambda series: series.between(1, 7),
                error="day_of_week must be between 1 and 7",
            ),
            nullable=False,
            required=True,
            coerce=False,
        ),
        "scheduled_departure_hour": pa.Column(
            pd.Int8Dtype(),
            checks=_optional_range_check(
                0,
                23,
                "scheduled_departure_hour must be "
                "between 0 and 23",
            ),
            nullable=True,
            required=True,
            coerce=False,
        ),
        "scheduled_arrival_hour": pa.Column(
            pd.Int8Dtype(),
            checks=_optional_range_check(
                0,
                23,
                "scheduled_arrival_hour must be "
                "between 0 and 23",
            ),
            nullable=True,
            required=True,
            coerce=False,
        ),
        "scheduled_elapsed_minutes": pa.Column(
            pd.Float64Dtype(),
            checks=_optional_positive_check(
                "scheduled_elapsed_minutes must be positive"
            ),
            nullable=True,
            required=True,
            coerce=False,
        ),
        "distance_miles": pa.Column(
            pd.Float64Dtype(),
            checks=_optional_positive_check(
                "distance_miles must be positive"
            ),
            nullable=True,
            required=True,
            coerce=False,
        ),
        "distance_group": pa.Column(
            pd.Int8Dtype(),
            checks=_optional_range_check(
                1,
                11,
                "distance_group must be between 1 and 11",
            ),
            nullable=True,
            required=True,
            coerce=False,
        ),
        target_column: pa.Column(
            pd.Int8Dtype(),
            checks=pa.Check(
                lambda series: series.isin([
                    target_definition.negative_class,
                    target_definition.positive_class,
                ]),
                error=(
                    f"{target_column} must contain only "
                    "the configured binary classes"
                ),
            ),
            nullable=False,
            required=True,
            coerce=False,
        ),
    }

    return pa.DataFrameSchema(
        columns=columns,
        checks=[
            pa.Check(
                _route_matches_airports,
                error=(
                    "route must match origin_airport "
                    "and destination_airport"
                ),
            ),
            pa.Check(
                _month_matches_flight_date,
                error="month must match flight_date",
            ),
            pa.Check(
                _weekday_matches_flight_date,
                error="day_of_week must match flight_date",
            ),
        ],
        strict=True,
        ordered=True,
        unique_column_names=True,
        coerce=False,
        drop_invalid_rows=False,
        name=PROCESSED_BTS_SCHEMA_NAME,
        metadata={
            "manifest_schema_version": (
                resolved_manifest.manifest_schema_version
            ),
            "dataset_id": resolved_manifest.dataset_id,
            "target_column": target_column,
            "model_feature_columns": MODEL_FEATURE_COLUMNS,
        },
    )


def validate_processed_bts_frame(
    frame: pd.DataFrame,
    manifest: BTSManifest | None = None,
) -> pd.DataFrame:
    """Validate processed BTS rows without changing their values."""
    schema = build_processed_bts_schema(
        manifest
    )

    return schema.validate(
        frame,
        lazy=True,
    )