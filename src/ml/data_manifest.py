import json
from datetime import date, datetime
from json import JSONDecodeError
from pathlib import Path, PurePosixPath
from typing import Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)


SUPPORTED_MANIFEST_SCHEMA_VERSION = 1
DEFAULT_MANIFEST_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "manifests"
    / "bts_baseline.json"
)


class ManifestError(ValueError):
    """Raised when a dataset manifest cannot be loaded safely."""


class StrictManifestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DateRange(StrictManifestModel):
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_date_order(self) -> Self:
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be earlier than start_date")
        return self


class ManifestSource(StrictManifestModel):
    publisher: str = Field(min_length=1)
    table_name: str = Field(min_length=1)
    landing_page: HttpUrl
    download_page: HttpUrl
    field_documentation: HttpUrl
    delay_cause_documentation: HttpUrl
    accessed_at_utc: datetime | None


class UsageReview(StrictManifestModel):
    publicly_accessible: bool
    legal_review_status: Literal["pending", "approved", "rejected"]
    commercial_model_training_reviewed: bool
    raw_data_redistribution_reviewed: bool


class StoragePaths(StrictManifestModel):
    raw_directory: str
    interim_directory: str
    processed_directory: str
    raw_and_generated_data_tracked_by_git: Literal[False]

    @field_validator(
        "raw_directory",
        "interim_directory",
        "processed_directory",
    )
    @classmethod
    def validate_storage_path(
        cls,
        value: str,
        info: ValidationInfo,
    ) -> str:
        expected_prefixes = {
            "raw_directory": ("data", "raw"),
            "interim_directory": ("data", "interim"),
            "processed_directory": ("data", "processed"),
        }

        path = PurePosixPath(value)
        parts = path.parts

        unsafe = (
            "\\" in value
            or path.is_absolute()
            or not parts
            or parts[0].endswith(":")
            or ".." in parts
        )
        if unsafe:
            raise ValueError(
                f"{info.field_name} must be a repository-relative POSIX path"
            )

        expected_prefix = expected_prefixes[info.field_name]
        if tuple(parts[:2]) != expected_prefix:
            expected = "/".join(expected_prefix)
            raise ValueError(
                f"{info.field_name} must be located under {expected}/"
            )

        return value


class DatasetScope(StrictManifestModel):
    row_unit: str = Field(min_length=1)
    development_sample: DateRange
    training: DateRange
    validation: DateRange
    test: DateRange

    @model_validator(mode="after")
    def validate_chronological_splits(self) -> Self:
        if (
            self.development_sample.start_date
            < self.training.start_date
            or self.development_sample.end_date
            > self.training.end_date
        ):
            raise ValueError(
                "development sample must be contained in training period"
            )

        if self.training.end_date >= self.validation.start_date:
            raise ValueError(
                "training period must end before validation period"
            )

        if self.validation.end_date >= self.test.start_date:
            raise ValueError(
                "validation period must end before test period"
            )

        return self


class RawColumns(StrictManifestModel):
    flight_identity: tuple[str, ...] = Field(min_length=1)
    scheduled_information: tuple[str, ...] = Field(min_length=1)
    outcome_information: tuple[str, ...] = Field(min_length=1)

    @property
    def all_columns(self) -> tuple[str, ...]:
        return (
            self.flight_identity
            + self.scheduled_information
            + self.outcome_information
        )

    @model_validator(mode="after")
    def validate_unique_columns(self) -> Self:
        columns = self.all_columns
        if len(columns) != len(set(columns)):
            raise ValueError(
                "raw column groups must not contain duplicate columns"
            )
        return self


class TargetDefinition(StrictManifestModel):
    name: str = Field(min_length=1)
    type: Literal["binary"]
    positive_class: Literal[1]
    negative_class: Literal[0]
    delay_threshold_minutes: int = Field(gt=0)
    positive_when_any: tuple[str, ...] = Field(min_length=1)


class DownloadedFile(StrictManifestModel):
    filename: str = Field(min_length=1)
    source_url: HttpUrl
    retrieved_at_utc: datetime
    size_bytes: int = Field(gt=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class IntegrityDefinition(StrictManifestModel):
    checksum_algorithm: Literal["sha256"]
    downloaded_files: tuple[DownloadedFile, ...]


class BTSManifest(StrictManifestModel):
    manifest_schema_version: int
    dataset_id: str = Field(min_length=1)
    dataset_status: Literal["planned", "downloaded", "validated"]
    description: str = Field(min_length=1)
    source: ManifestSource
    usage_review: UsageReview
    storage: StoragePaths
    scope: DatasetScope
    raw_columns: RawColumns
    target: TargetDefinition
    integrity: IntegrityDefinition
    limitations: tuple[str, ...] = Field(min_length=1)

    @field_validator("manifest_schema_version")
    @classmethod
    def validate_schema_version(cls, value: int) -> int:
        if value != SUPPORTED_MANIFEST_SCHEMA_VERSION:
            raise ValueError(
                "unsupported manifest schema version: "
                f"{value}; expected {SUPPORTED_MANIFEST_SCHEMA_VERSION}"
            )
        return value

    @property
    def required_columns(self) -> tuple[str, ...]:
        return self.raw_columns.all_columns


def load_bts_manifest(
    path: str | Path = DEFAULT_MANIFEST_PATH,
) -> BTSManifest:
    """Load and validate the BTS dataset manifest."""

    manifest_path = Path(path)

    try:
        contents = manifest_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ManifestError(
            f"Unable to read BTS manifest: {manifest_path}"
        ) from exc

    try:
        raw_manifest = json.loads(contents)
    except JSONDecodeError as exc:
        raise ManifestError(
            f"BTS manifest is not valid JSON: {manifest_path}"
        ) from exc

    try:
        return BTSManifest.model_validate(raw_manifest)
    except ValidationError as exc:
        raise ManifestError(
            f"BTS manifest failed validation: {exc}"
        ) from exc