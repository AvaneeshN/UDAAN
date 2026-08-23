import json
from datetime import date
from pathlib import Path

import pytest

from ml.data_manifest import ManifestError, load_bts_manifest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
COMMITTED_MANIFEST_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "manifests"
    / "bts_baseline.json"
)


def committed_manifest_data() -> dict:
    return json.loads(
        COMMITTED_MANIFEST_PATH.read_text(encoding="utf-8")
    )


def write_manifest(tmp_path: Path, data: object) -> Path:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(data),
        encoding="utf-8",
    )
    return manifest_path


def test_loads_committed_bts_manifest():
    manifest = load_bts_manifest()

    assert (
        manifest.dataset_id
        == "bts_reporting_carrier_on_time_performance"
    )
    assert manifest.scope.training.start_date == date(2022, 1, 1)
    assert manifest.scope.test.end_date == date(2025, 12, 31)
    assert "FlightDate" in manifest.required_columns
    assert "ArrDelayMinutes" in manifest.required_columns
    assert manifest.integrity.downloaded_files == ()


def test_default_manifest_path_is_independent_of_working_directory(
    monkeypatch,
    tmp_path,
):
    monkeypatch.chdir(tmp_path)

    manifest = load_bts_manifest()

    assert manifest.manifest_schema_version == 1


def test_rejects_invalid_json(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("{", encoding="utf-8")

    with pytest.raises(
        ManifestError,
        match="not valid JSON",
    ):
        load_bts_manifest(manifest_path)


def test_rejects_unsupported_schema_version(tmp_path):
    data = committed_manifest_data()
    data["manifest_schema_version"] = 2
    manifest_path = write_manifest(tmp_path, data)

    with pytest.raises(
        ManifestError,
        match="unsupported manifest schema version",
    ):
        load_bts_manifest(manifest_path)


def test_rejects_overlapping_chronological_splits(tmp_path):
    data = committed_manifest_data()
    data["scope"]["validation"]["start_date"] = "2024-06-30"
    manifest_path = write_manifest(tmp_path, data)

    with pytest.raises(
        ManifestError,
        match="training period must end before validation period",
    ):
        load_bts_manifest(manifest_path)


def test_rejects_unsafe_storage_path(tmp_path):
    data = committed_manifest_data()
    data["storage"]["raw_directory"] = "../outside-repository"
    manifest_path = write_manifest(tmp_path, data)

    with pytest.raises(
        ManifestError,
        match="repository-relative POSIX path",
    ):
        load_bts_manifest(manifest_path)


def test_rejects_duplicate_raw_columns(tmp_path):
    data = committed_manifest_data()
    data["raw_columns"]["scheduled_information"].append(
        "FlightDate"
    )
    manifest_path = write_manifest(tmp_path, data)

    with pytest.raises(
        ManifestError,
        match="must not contain duplicate columns",
    ):
        load_bts_manifest(manifest_path)