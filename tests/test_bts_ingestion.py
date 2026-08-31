from datetime import UTC, datetime
from hashlib import sha256
from io import BytesIO
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile

import httpx
import pytest

from ml.bts_ingestion import (
    BTSIngestionError,
    ingest_bts_development_sample,
)
from ml.data_manifest import load_bts_manifest


MANIFEST = load_bts_manifest()
REQUIRED_COLUMNS = MANIFEST.required_columns

FIXED_TIME = datetime(
    2026,
    8,
    29,
    12,
    0,
    tzinfo=UTC,
)


def create_valid_zip() -> bytes:
    csv_contents = (
        ",".join(REQUIRED_COLUMNS)
        + "\n"
        + ",".join("0" for _ in REQUIRED_COLUMNS)
        + "\n"
    ).encode("utf-8")

    buffer = BytesIO()

    with ZipFile(
        buffer,
        mode="w",
        compression=ZIP_DEFLATED,
    ) as archive:
        archive.writestr(
            "bts_sample.csv",
            csv_contents,
        )

    return buffer.getvalue()


VALID_ZIP = create_valid_zip()


def expected_destination(
    repository_root: Path,
) -> Path:
    filename = PurePosixPath(
        MANIFEST.source.development_sample_url.path
    ).name

    return (
        repository_root
        / "data"
        / "raw"
        / "bts"
        / filename
    )


def successful_transport(
    payload: bytes = VALID_ZIP,
) -> httpx.MockTransport:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            headers={
                "Content-Type": "application/zip",
                "Content-Length": str(len(payload)),
            },
            content=payload,
            request=request,
        )

    return httpx.MockTransport(handler)


def test_ingests_validated_archive(tmp_path):
    result = ingest_bts_development_sample(
        repository_root=tmp_path,
        transport=successful_transport(),
        clock=lambda: FIXED_TIME,
    )

    destination = expected_destination(tmp_path)

    assert result.destination_path == destination
    assert destination.exists()
    assert destination.read_bytes() == VALID_ZIP
    assert result.source_url == str(
        MANIFEST.source.development_sample_url
    )
    assert result.retrieved_at_utc == FIXED_TIME
    assert result.size_bytes == len(VALID_ZIP)
    assert result.sha256 == sha256(
        VALID_ZIP
    ).hexdigest()
    assert result.csv_member_name == "bts_sample.csv"
    assert result.columns == REQUIRED_COLUMNS
    assert list(
        destination.parent.glob("*.part")
    ) == []


def test_invalid_archive_is_not_promoted(tmp_path):
    invalid_payload = b"not a valid ZIP"

    with pytest.raises(
        BTSIngestionError,
        match="Unable to validate",
    ):
        ingest_bts_development_sample(
            repository_root=tmp_path,
            transport=successful_transport(
                invalid_payload
            ),
        )

    destination = expected_destination(tmp_path)

    assert not destination.exists()
    assert list(
        destination.parent.glob("*.part")
    ) == []


def test_existing_destination_stops_network_access(
    tmp_path,
):
    destination = expected_destination(tmp_path)
    destination.parent.mkdir(parents=True)

    existing_contents = b"existing dataset"
    destination.write_bytes(existing_contents)

    request_was_made = False

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        nonlocal request_was_made
        request_was_made = True

        return httpx.Response(
            status_code=200,
            content=VALID_ZIP,
            request=request,
        )

    with pytest.raises(
        BTSIngestionError,
        match="destination already exists",
    ):
        ingest_bts_development_sample(
            repository_root=tmp_path,
            transport=httpx.MockTransport(handler),
        )

    assert request_was_made is False
    assert destination.read_bytes() == existing_contents


def test_promotion_race_does_not_overwrite(
    tmp_path,
    monkeypatch,
):
    competing_contents = b"competing dataset"

    def competing_link(source, destination):
        Path(destination).write_bytes(
            competing_contents
        )
        raise FileExistsError

    monkeypatch.setattr(
        "ml.bts_ingestion.link",
        competing_link,
    )

    with pytest.raises(
        BTSIngestionError,
        match="refusing to overwrite",
    ):
        ingest_bts_development_sample(
            repository_root=tmp_path,
            transport=successful_transport(),
        )

    destination = expected_destination(tmp_path)

    assert destination.read_bytes() == competing_contents
    assert list(
        destination.parent.glob("*.part")
    ) == []


def test_naive_retrieval_time_is_rejected(
    tmp_path,
):
    naive_time = datetime(2026, 8, 29, 12, 0)

    with pytest.raises(
        BTSIngestionError,
        match="timezone-aware",
    ):
        ingest_bts_development_sample(
            repository_root=tmp_path,
            transport=successful_transport(),
            clock=lambda: naive_time,
        )

    assert not expected_destination(tmp_path).exists()


def test_tampered_staging_file_is_rejected(
    tmp_path,
    monkeypatch,
):
    from ml import bts_ingestion

    real_validator = (
        bts_ingestion.validate_bts_archive
    )

    def tampering_validator(*args, **kwargs):
        validated = real_validator(
            *args,
            **kwargs,
        )

        Path(args[0]).write_bytes(
            b"tampered after validation"
        )

        return validated

    monkeypatch.setattr(
        bts_ingestion,
        "validate_bts_archive",
        tampering_validator,
    )

    with pytest.raises(
        BTSIngestionError,
        match="size changed after download",
    ):
        ingest_bts_development_sample(
            repository_root=tmp_path,
            transport=successful_transport(),
        )

    assert not expected_destination(tmp_path).exists()


def test_download_error_is_wrapped_and_cleaned(
    tmp_path,
):
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            headers={
                "Content-Type": "text/html",
            },
            content=b"<html>Error</html>",
            request=request,
        )

    with pytest.raises(
        BTSIngestionError,
        match="unsupported content type",
    ):
        ingest_bts_development_sample(
            repository_root=tmp_path,
            transport=httpx.MockTransport(handler),
        )

    destination = expected_destination(tmp_path)

    assert not destination.exists()
    assert list(
        destination.parent.glob("*.part")
    ) == []