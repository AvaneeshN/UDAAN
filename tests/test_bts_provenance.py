import json
from dataclasses import replace as dataclass_replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path, PurePosixPath

import pytest

from ml.bts_ingestion import IngestedBTSArchive
from ml.bts_provenance import (
    BTSProvenanceError,
    record_bts_ingestion,
)
from ml.data_manifest import (
    DEFAULT_MANIFEST_PATH,
    load_bts_manifest,
)


FIXED_TIME = datetime(
    2026,
    8,
    30,
    12,
    0,
    tzinfo=UTC,
)

ARCHIVE_CONTENTS = b"validated BTS archive"


def prepare_environment(
    tmp_path,
) -> tuple[Path, IngestedBTSArchive]:
    manifest_directory = (
        tmp_path / "data" / "manifests"
    )
    manifest_directory.mkdir(parents=True)

    manifest_path = (
        manifest_directory / "bts_baseline.json"
    )
    manifest_document = json.loads(
        DEFAULT_MANIFEST_PATH.read_text(
            encoding="utf-8"
        )
    )

    manifest_document["dataset_status"] = "planned"
    manifest_document["source"][
        "accessed_at_utc"
    ] = None
    manifest_document["integrity"][
        "downloaded_files"
    ] = []

    manifest_path.write_text(
        json.dumps(
            manifest_document,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    manifest = load_bts_manifest(manifest_path)

    filename = PurePosixPath(
        manifest.source.development_sample_url.path
    ).name

    destination = (
        tmp_path
        / "data"
        / "raw"
        / "bts"
        / filename
    )
    destination.parent.mkdir(parents=True)
    destination.write_bytes(ARCHIVE_CONTENTS)

    ingested = IngestedBTSArchive(
        destination_path=destination,
        source_url=str(
            manifest.source.development_sample_url
        ),
        retrieved_at_utc=FIXED_TIME,
        size_bytes=len(ARCHIVE_CONTENTS),
        sha256=sha256(
            ARCHIVE_CONTENTS
        ).hexdigest(),
        csv_member_name=(
        "On_Time_Reporting_Carrier_"
        "On_Time_Performance_"
        "(1987_present)_2022_1.csv"
    ),
        csv_size_bytes=100,
        columns=manifest.required_columns,
    )

    return manifest_path, ingested


def test_records_ingestion_in_manifest(tmp_path):
    manifest_path, ingested = (
        prepare_environment(tmp_path)
    )

    updated = record_bts_ingestion(
        ingested,
        manifest_path,
        repository_root=tmp_path,
    )

    assert updated.dataset_status == "downloaded"
    assert updated.source.accessed_at_utc == FIXED_TIME
    assert len(
        updated.integrity.downloaded_files
    ) == 1

    record = updated.integrity.downloaded_files[0]

    assert record.filename == (
        ingested.destination_path.name
    )
    assert str(record.source_url) == (
        ingested.source_url
    )
    assert record.retrieved_at_utc == FIXED_TIME
    assert record.size_bytes == (
        len(ARCHIVE_CONTENTS)
    )
    assert record.sha256 == ingested.sha256

    assert load_bts_manifest(
        manifest_path
    ) == updated


def test_rejects_wrong_source_url(tmp_path):
    manifest_path, ingested = (
        prepare_environment(tmp_path)
    )
    original = manifest_path.read_bytes()

    invalid = dataclass_replace(
        ingested,
        source_url="https://example.com/data.zip",
    )

    with pytest.raises(
        BTSProvenanceError,
        match="source does not match",
    ):
        record_bts_ingestion(
            invalid,
            manifest_path,
            repository_root=tmp_path,
        )

    assert manifest_path.read_bytes() == original


def test_rejects_wrong_storage_location(
    tmp_path,
):
    manifest_path, ingested = (
        prepare_environment(tmp_path)
    )

    other_path = tmp_path / "other.zip"
    other_path.write_bytes(ARCHIVE_CONTENTS)

    invalid = dataclass_replace(
        ingested,
        destination_path=other_path,
    )

    with pytest.raises(
        BTSProvenanceError,
        match="not in the expected raw",
    ):
        record_bts_ingestion(
            invalid,
            manifest_path,
            repository_root=tmp_path,
        )


def test_rejects_modified_archive(tmp_path):
    manifest_path, ingested = (
        prepare_environment(tmp_path)
    )
    original = manifest_path.read_bytes()

    ingested.destination_path.write_bytes(
        b"archive changed after ingestion"
    )

    with pytest.raises(
        BTSProvenanceError,
        match="size does not match",
    ):
        record_bts_ingestion(
            ingested,
            manifest_path,
            repository_root=tmp_path,
        )

    assert manifest_path.read_bytes() == original


def test_rejects_missing_required_columns(
    tmp_path,
):
    manifest_path, ingested = (
        prepare_environment(tmp_path)
    )

    invalid = dataclass_replace(
        ingested,
        columns=ingested.columns[:-1],
    )

    with pytest.raises(
        BTSProvenanceError,
        match="missing columns",
    ):
        record_bts_ingestion(
            invalid,
            manifest_path,
            repository_root=tmp_path,
        )


def test_rejects_naive_retrieval_time(
    tmp_path,
):
    manifest_path, ingested = (
        prepare_environment(tmp_path)
    )

    invalid = dataclass_replace(
        ingested,
        retrieved_at_utc=datetime(
            2026,
            8,
            30,
            12,
            0,
        ),
    )

    with pytest.raises(
        BTSProvenanceError,
        match="timezone-aware",
    ):
        record_bts_ingestion(
            invalid,
            manifest_path,
            repository_root=tmp_path,
        )


def test_recording_same_ingestion_is_idempotent(
    tmp_path,
):
    manifest_path, ingested = (
        prepare_environment(tmp_path)
    )

    record_bts_ingestion(
        ingested,
        manifest_path,
        repository_root=tmp_path,
    )
    first_contents = manifest_path.read_bytes()

    record_bts_ingestion(
        ingested,
        manifest_path,
        repository_root=tmp_path,
    )

    assert manifest_path.read_bytes() == first_contents

    manifest = load_bts_manifest(manifest_path)

    assert len(
        manifest.integrity.downloaded_files
    ) == 1


def test_rejects_conflicting_existing_record(
    tmp_path,
):
    manifest_path, ingested = (
        prepare_environment(tmp_path)
    )

    record_bts_ingestion(
        ingested,
        manifest_path,
        repository_root=tmp_path,
    )
    original = manifest_path.read_bytes()

    conflict = dataclass_replace(
        ingested,
        retrieved_at_utc=(
            FIXED_TIME + timedelta(seconds=1)
        ),
    )

    with pytest.raises(
        BTSProvenanceError,
        match="conflicting record",
    ):
        record_bts_ingestion(
            conflict,
            manifest_path,
            repository_root=tmp_path,
        )

    assert manifest_path.read_bytes() == original


def test_atomic_write_failure_preserves_manifest(
    tmp_path,
    monkeypatch,
):
    manifest_path, ingested = (
        prepare_environment(tmp_path)
    )
    original = manifest_path.read_bytes()

    def failing_replace(source, destination):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(
        "ml.bts_provenance.replace",
        failing_replace,
    )

    with pytest.raises(
        BTSProvenanceError,
        match="atomically",
    ):
        record_bts_ingestion(
            ingested,
            manifest_path,
            repository_root=tmp_path,
        )

    assert manifest_path.read_bytes() == original
    assert list(
        manifest_path.parent.glob(
            f".{manifest_path.name}.*.tmp"
        )
    ) == []


def test_does_not_downgrade_validated_status(
    tmp_path,
):
    manifest_path, ingested = (
        prepare_environment(tmp_path)
    )

    record_bts_ingestion(
        ingested,
        manifest_path,
        repository_root=tmp_path,
    )

    document = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )
    document["dataset_status"] = "validated"

    manifest_path.write_text(
        json.dumps(
            document,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    updated = record_bts_ingestion(
        ingested,
        manifest_path,
        repository_root=tmp_path,
    )

    assert updated.dataset_status == "validated"