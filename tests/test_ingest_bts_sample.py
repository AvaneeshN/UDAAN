import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ml import ingest_bts_sample as cli
from ml.bts_ingestion import (
    BTSIngestionError,
    IngestedBTSArchive,
)
from ml.bts_provenance import BTSProvenanceError
from ml.data_manifest import load_bts_manifest


MANIFEST = load_bts_manifest()

FIXED_TIME = datetime(
    2026,
    8,
    30,
    15,
    0,
    tzinfo=UTC,
)

INGESTED = IngestedBTSArchive(
    destination_path=Path(
        "data/raw/bts/sample.zip"
    ),
    source_url=str(
        MANIFEST.source.development_sample_url
    ),
    retrieved_at_utc=FIXED_TIME,
    size_bytes=1234,
    sha256="a" * 64,
    csv_member_name="bts_sample.csv",
    csv_size_bytes=5678,
    columns=MANIFEST.required_columns,
)


def test_default_mode_is_safe_dry_run(
    monkeypatch,
    capsys,
):
    def unexpected_ingestion(**kwargs):
        raise AssertionError(
            "dry-run must not start ingestion"
        )

    monkeypatch.setattr(
        cli,
        "ingest_bts_development_sample",
        unexpected_ingestion,
    )

    exit_code = cli.main([])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == cli.EXIT_SUCCESS
    assert captured.err == ""
    assert payload["status"] == "dry-run"
    assert payload["network_access"] is False
    assert payload["source_url"] == str(
        MANIFEST.source.development_sample_url
    )
    assert "--execute" in payload["execute_command"]


def test_execute_runs_ingestion_and_provenance(
    tmp_path,
    monkeypatch,
    capsys,
):
    calls = {}

    def fake_ingestion(**kwargs):
        calls["ingestion"] = kwargs
        return INGESTED

    def fake_provenance(
        ingested,
        *,
        manifest_path,
        repository_root,
    ):
        calls["provenance"] = {
            "ingested": ingested,
            "manifest_path": manifest_path,
            "repository_root": repository_root,
        }

        return MANIFEST.model_copy(
            update={
                "dataset_status": "downloaded"
            }
        )

    monkeypatch.setattr(
        cli,
        "ingest_bts_development_sample",
        fake_ingestion,
    )
    monkeypatch.setattr(
        cli,
        "record_bts_ingestion",
        fake_provenance,
    )

    exit_code = cli.main(
        [
            "--execute",
            "--repository-root",
            str(tmp_path),
            "--max-download-bytes",
            "5000",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == cli.EXIT_SUCCESS
    assert captured.err == ""
    assert payload["status"] == "success"
    assert payload["dataset_status"] == "downloaded"
    assert payload["sha256"] == INGESTED.sha256
    assert payload["column_count"] == len(
        MANIFEST.required_columns
    )
    assert calls["ingestion"][
        "max_download_bytes"
    ] == 5000
    assert calls["provenance"][
        "ingested"
    ] is INGESTED


def test_ingestion_failure_returns_error(
    monkeypatch,
    capsys,
):
    provenance_was_called = False

    def failing_ingestion(**kwargs):
        raise BTSIngestionError(
            "simulated download failure"
        )

    def unexpected_provenance(*args, **kwargs):
        nonlocal provenance_was_called
        provenance_was_called = True

    monkeypatch.setattr(
        cli,
        "ingest_bts_development_sample",
        failing_ingestion,
    )
    monkeypatch.setattr(
        cli,
        "record_bts_ingestion",
        unexpected_provenance,
    )

    exit_code = cli.main(["--execute"])

    captured = capsys.readouterr()
    payload = json.loads(captured.err)

    assert exit_code == cli.EXIT_OPERATIONAL_ERROR
    assert captured.out == ""
    assert payload["status"] == "error"
    assert payload["stage"] == "ingestion"
    assert payload["archive_retained"] is False
    assert provenance_was_called is False


def test_provenance_failure_returns_recovery_data(
    monkeypatch,
    capsys,
):
    def fake_ingestion(**kwargs):
        return INGESTED

    def failing_provenance(*args, **kwargs):
        raise BTSProvenanceError(
            "simulated manifest failure"
        )

    monkeypatch.setattr(
        cli,
        "ingest_bts_development_sample",
        fake_ingestion,
    )
    monkeypatch.setattr(
        cli,
        "record_bts_ingestion",
        failing_provenance,
    )

    exit_code = cli.main(["--execute"])

    captured = capsys.readouterr()
    payload = json.loads(captured.err)

    assert exit_code == cli.EXIT_PROVENANCE_ERROR
    assert captured.out == ""
    assert payload["stage"] == "provenance"
    assert payload["archive_retained"] is True
    assert payload["recovery"]["sha256"] == (
        INGESTED.sha256
    )
    assert payload["recovery"]["filename"] == (
        INGESTED.destination_path.name
    )


def test_missing_manifest_returns_error(
    tmp_path,
    capsys,
):
    exit_code = cli.main(
        [
            "--manifest",
            str(tmp_path / "missing.json"),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.err)

    assert exit_code == cli.EXIT_OPERATIONAL_ERROR
    assert captured.out == ""
    assert payload["stage"] == "manifest"


def test_invalid_download_limit_is_rejected(
    capsys,
):
    with pytest.raises(SystemExit) as exc_info:
        cli.main(
            [
                "--max-download-bytes",
                "0",
            ]
        )

    captured = capsys.readouterr()

    assert exc_info.value.code == 2
    assert captured.out == ""
    assert "positive integer" in captured.err


def test_unexpected_error_is_hidden_by_default(
    monkeypatch,
    capsys,
):
    def broken_manifest(path):
        raise RuntimeError(
            "sensitive internal debugging details"
        )

    monkeypatch.setattr(
        cli,
        "load_bts_manifest",
        broken_manifest,
    )

    exit_code = cli.main([])

    captured = capsys.readouterr()
    payload = json.loads(captured.err)

    assert exit_code == cli.EXIT_INTERNAL_ERROR
    assert captured.out == ""
    assert payload["stage"] == "internal"
    assert "sensitive internal" not in captured.err
    assert "Traceback" not in captured.err


def test_debug_mode_reraises_unexpected_error(
    monkeypatch,
):
    def broken_manifest(path):
        raise RuntimeError("debugging details")

    monkeypatch.setattr(
        cli,
        "load_bts_manifest",
        broken_manifest,
    )

    with pytest.raises(
        RuntimeError,
        match="debugging details",
    ):
        cli.main(["--debug"])

def test_keyboard_interrupt_is_reported_cleanly(
    monkeypatch,
    capsys,
):
    def interrupted_ingestion(**kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(
        cli,
        "ingest_bts_development_sample",
        interrupted_ingestion,
    )

    exit_code = cli.main(["--execute"])

    captured = capsys.readouterr()
    payload = json.loads(captured.err)

    assert exit_code == cli.EXIT_INTERRUPTED
    assert captured.out == ""
    assert payload["status"] == "cancelled"
    assert payload["stage"] == "ingestion"
    assert payload["archive_retained"] is False
    assert "Traceback" not in captured.err