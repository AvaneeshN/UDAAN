import json
from datetime import date
from pathlib import Path

import pytest

from ml.data_manifest import ManifestError, load_bts_manifest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
COMMITTED_MANIFEST_PATH = REPOSITORY_ROOT / "data" / "manifests" / "bts_baseline.json"


def committed_manifest_data() -> dict:
    return json.loads(COMMITTED_MANIFEST_PATH.read_text(encoding="utf-8"))

def planned_manifest_data() -> dict:
    data = committed_manifest_data()
    data["dataset_status"] = "planned"
    data["source"]["accessed_at_utc"] = None
    data["integrity"]["downloaded_files"] = []

    return data


def sample_download_record() -> dict:
    return {
        "filename": "sample.zip",
        "source_url": (
            "https://transtats.bts.gov/PREZIP/sample.zip"
        ),
        "retrieved_at_utc": "2026-09-01T13:21:40Z",
        "size_bytes": 100,
        "sha256": "a" * 64,
    }

def write_manifest(tmp_path: Path, data: object) -> Path:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(data),
        encoding="utf-8",
    )
    return manifest_path


def test_loads_committed_bts_manifest():
    manifest = load_bts_manifest()

    assert manifest.dataset_id == "bts_reporting_carrier_on_time_performance"
    assert manifest.scope.training.start_date == date(2022, 1, 1)
    assert manifest.scope.test.end_date == date(2025, 12, 31)
    assert "FlightDate" in manifest.required_columns
    assert "ArrDelayMinutes" in manifest.required_columns
    if manifest.dataset_status == "planned":
        assert manifest.source.accessed_at_utc is None
        assert manifest.integrity.downloaded_files == ()
    else:
        assert manifest.source.accessed_at_utc is not None
        assert manifest.integrity.downloaded_files

def test_committed_manifest_defines_unresolved_target_policy():
    manifest = load_bts_manifest()

    assert manifest.target.type == "binary"
    assert manifest.target.delay_threshold_minutes == 15
    assert manifest.target.unresolved_action == "quarantine"
    assert manifest.target.unresolved_when_any == (
        "Cancelled is missing or not in {0, 1}",
        "Diverted is missing or not in {0, 1}",
        (
            "Cancelled == 0 AND Diverted == 0 AND "
            "ArrDelayMinutes is missing"
        ),
    )


def test_rejects_target_without_unresolved_action(tmp_path):
    data = committed_manifest_data()
    del data["target"]["unresolved_action"]
    manifest_path = write_manifest(tmp_path, data)

    with pytest.raises(
        ManifestError,
        match="unresolved_action",
    ):
        load_bts_manifest(manifest_path)


def test_rejects_empty_unresolved_target_conditions(tmp_path):
    data = committed_manifest_data()
    data["target"]["unresolved_when_any"] = []
    manifest_path = write_manifest(tmp_path, data)

    with pytest.raises(
        ManifestError,
        match="unresolved_when_any",
    ):
        load_bts_manifest(manifest_path)

def test_accepts_planned_lifecycle_state(tmp_path):
    manifest_path = write_manifest(
        tmp_path,
        planned_manifest_data(),
    )

    manifest = load_bts_manifest(manifest_path)

    assert manifest.dataset_status == "planned"
    assert manifest.source.accessed_at_utc is None
    assert manifest.integrity.downloaded_files == ()


@pytest.mark.parametrize(
    "dataset_status",
    ["downloaded", "validated"],
)
def test_accepts_recorded_lifecycle_state(
    tmp_path,
    dataset_status,
):
    data = planned_manifest_data()
    record = sample_download_record()

    data["dataset_status"] = dataset_status
    data["source"]["accessed_at_utc"] = (
        record["retrieved_at_utc"]
    )
    data["integrity"]["downloaded_files"] = [record]

    manifest_path = write_manifest(tmp_path, data)
    manifest = load_bts_manifest(manifest_path)

    assert manifest.dataset_status == dataset_status
    assert manifest.source.accessed_at_utc is not None
    assert len(manifest.integrity.downloaded_files) == 1


def test_rejects_planned_state_with_access_time(
    tmp_path,
):
    data = planned_manifest_data()
    data["source"]["accessed_at_utc"] = (
        "2026-09-01T13:21:40Z"
    )
    manifest_path = write_manifest(tmp_path, data)

    with pytest.raises(
        ManifestError,
        match="planned dataset must not contain",
    ):
        load_bts_manifest(manifest_path)


def test_rejects_planned_state_with_download_record(
    tmp_path,
):
    data = planned_manifest_data()
    data["integrity"]["downloaded_files"] = [
        sample_download_record()
    ]
    manifest_path = write_manifest(tmp_path, data)

    with pytest.raises(
        ManifestError,
        match="planned dataset must not contain",
    ):
        load_bts_manifest(manifest_path)


@pytest.mark.parametrize(
    "dataset_status",
    ["downloaded", "validated"],
)
def test_rejects_recorded_state_without_file(
    tmp_path,
    dataset_status,
):
    data = planned_manifest_data()
    data["dataset_status"] = dataset_status
    data["source"]["accessed_at_utc"] = (
        "2026-09-01T13:21:40Z"
    )
    manifest_path = write_manifest(tmp_path, data)

    with pytest.raises(
        ManifestError,
        match="must contain at least one downloaded file",
    ):
        load_bts_manifest(manifest_path)


@pytest.mark.parametrize(
    "dataset_status",
    ["downloaded", "validated"],
)
def test_rejects_recorded_state_without_access_time(
    tmp_path,
    dataset_status,
):
    data = planned_manifest_data()
    data["dataset_status"] = dataset_status
    data["integrity"]["downloaded_files"] = [
        sample_download_record()
    ]
    manifest_path = write_manifest(tmp_path, data)

    with pytest.raises(
        ManifestError,
        match="must include accessed_at_utc",
    ):
        load_bts_manifest(manifest_path)

def test_default_manifest_path_is_independent_of_working_directory(
    monkeypatch,
    tmp_path,
):
    monkeypatch.chdir(tmp_path)

    manifest = load_bts_manifest()

    assert manifest.manifest_schema_version == 2


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
    data["manifest_schema_version"] = 3
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
    data["raw_columns"]["scheduled_information"].append("FlightDate")
    manifest_path = write_manifest(tmp_path, data)

    with pytest.raises(
        ManifestError,
        match="must not contain duplicate columns",
    ):
        load_bts_manifest(manifest_path)


def test_development_sample_uses_approved_bts_zip():
    manifest = load_bts_manifest()

    assert (
        str(manifest.source.development_sample_url)
        == "https://transtats.bts.gov/PREZIP/"
        "On_Time_Reporting_Carrier_On_Time_Performance_"
        "1987_present_2022_1.zip"
    )


def test_rejects_insecure_development_sample_url(tmp_path):
    data = committed_manifest_data()
    data["source"]["development_sample_url"] = (
        "http://transtats.bts.gov/PREZIP/sample.zip"
    )
    manifest_path = write_manifest(tmp_path, data)

    with pytest.raises(
        ManifestError,
        match="must use HTTPS",
    ):
        load_bts_manifest(manifest_path)


def test_rejects_unapproved_download_host(tmp_path):
    data = committed_manifest_data()
    data["source"]["development_sample_url"] = "https://example.com/PREZIP/sample.zip"
    manifest_path = write_manifest(tmp_path, data)

    with pytest.raises(
        ManifestError,
        match="approved BTS host",
    ):
        load_bts_manifest(manifest_path)


def test_rejects_download_url_for_wrong_month(tmp_path):
    data = committed_manifest_data()
    data["source"]["development_sample_url"] = (
        "https://transtats.bts.gov/PREZIP/"
        "On_Time_Reporting_Carrier_On_Time_Performance_"
        "1987_present_2022_2.zip"
    )
    manifest_path = write_manifest(tmp_path, data)

    with pytest.raises(
        ManifestError,
        match="reporting-carrier development sample month",
    ):
        load_bts_manifest(manifest_path)


def test_rejects_different_bts_dataset(tmp_path):
    data = committed_manifest_data()
    data["source"]["development_sample_url"] = (
        "https://transtats.bts.gov/PREZIP/"
        "On_Time_Marketing_Carrier_On_Time_Performance_"
        "Beginning_January_2018_2022_1.zip"
    )
    manifest_path = write_manifest(tmp_path, data)

    with pytest.raises(
        ManifestError,
        match="reporting-carrier development sample month",
    ):
        load_bts_manifest(manifest_path)
