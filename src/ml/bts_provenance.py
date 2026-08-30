import json
from copy import deepcopy
from datetime import UTC, datetime
from hashlib import sha256
from json import JSONDecodeError
from os import chmod, fsync, replace
from pathlib import Path, PurePosixPath
from stat import S_IMODE
from tempfile import NamedTemporaryFile

from pydantic import ValidationError

from ml.bts_downloader import REPOSITORY_ROOT
from ml.bts_ingestion import IngestedBTSArchive
from ml.data_manifest import (
    DEFAULT_MANIFEST_PATH,
    BTSManifest,
    DownloadedFile,
    load_bts_manifest,
)


CHECKSUM_CHUNK_SIZE_BYTES = 1024 * 1024


class BTSProvenanceError(RuntimeError):
    """Raised when BTS provenance cannot be recorded safely."""


def _normalize_utc_timestamp(
    value: object,
) -> datetime:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise BTSProvenanceError(
            "retrieval time must be timezone-aware"
        )

    return value.astimezone(UTC)


def _utc_isoformat(value: datetime) -> str:
    return (
        value.astimezone(UTC)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _calculate_file_integrity(
    path: Path,
) -> tuple[int, str]:
    actual_size = 0
    digest = sha256()

    try:
        with path.open("rb") as archive_file:
            while True:
                chunk = archive_file.read(
                    CHECKSUM_CHUNK_SIZE_BYTES
                )

                if not chunk:
                    break

                actual_size += len(chunk)
                digest.update(chunk)

    except OSError as exc:
        raise BTSProvenanceError(
            "unable to read the stored BTS archive"
        ) from exc

    return actual_size, digest.hexdigest()


def _build_download_record(
    ingested: IngestedBTSArchive,
    manifest: BTSManifest,
    repository_root: Path,
) -> DownloadedFile:
    expected_source_url = str(
        manifest.source.development_sample_url
    )

    if ingested.source_url != expected_source_url:
        raise BTSProvenanceError(
            "ingestion source does not match the manifest"
        )

    expected_filename = PurePosixPath(
        manifest.source.development_sample_url.path
    ).name

    root = Path(repository_root).resolve()
    storage_directory = (
        root
        / Path(
            *PurePosixPath(
                manifest.storage.raw_directory
            ).parts
        )
    ).resolve()

    try:
        storage_directory.relative_to(root)
    except ValueError as exc:
        raise BTSProvenanceError(
            "manifest raw storage is outside the repository"
        ) from exc

    expected_destination = (
        storage_directory / expected_filename
    )

    destination = Path(
        ingested.destination_path
    ).absolute()

    if destination != expected_destination:
        raise BTSProvenanceError(
            "ingested archive is not in the expected raw "
            "storage location"
        )

    if destination.is_symlink():
        raise BTSProvenanceError(
            "stored BTS archive must not be a symbolic link"
        )

    if not destination.is_file():
        raise BTSProvenanceError(
            f"stored BTS archive does not exist: "
            f"{destination}"
        )

    missing_columns = [
        column
        for column in manifest.required_columns
        if column not in ingested.columns
    ]

    if missing_columns:
        missing = ", ".join(missing_columns)
        raise BTSProvenanceError(
            f"ingestion result is missing columns: {missing}"
        )

    actual_size, actual_sha256 = (
        _calculate_file_integrity(destination)
    )

    if actual_size != ingested.size_bytes:
        raise BTSProvenanceError(
            "stored BTS archive size does not match "
            "the ingestion result"
        )

    if actual_sha256 != ingested.sha256:
        raise BTSProvenanceError(
            "stored BTS archive checksum does not match "
            "the ingestion result"
        )

    retrieved_at_utc = _normalize_utc_timestamp(
        ingested.retrieved_at_utc
    )

    try:
        return DownloadedFile(
            filename=expected_filename,
            source_url=expected_source_url,
            retrieved_at_utc=retrieved_at_utc,
            size_bytes=actual_size,
            sha256=actual_sha256,
        )
    except ValidationError as exc:
        raise BTSProvenanceError(
            "download provenance is invalid"
        ) from exc


def _read_manifest_document(
    path: Path,
) -> dict:
    try:
        contents = path.read_text(encoding="utf-8")
        document = json.loads(contents)
    except OSError as exc:
        raise BTSProvenanceError(
            f"unable to read the manifest: {path}"
        ) from exc
    except JSONDecodeError as exc:
        raise BTSProvenanceError(
            f"manifest is not valid JSON: {path}"
        ) from exc

    if not isinstance(document, dict):
        raise BTSProvenanceError(
            "manifest root must be a JSON object"
        )

    return document


def _write_manifest_atomically(
    path: Path,
    document: dict,
) -> None:
    temporary_path: Path | None = None

    try:
        permissions = S_IMODE(path.stat().st_mode)

        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as temporary_file:
            temporary_path = Path(
                temporary_file.name
            )

            json.dump(
                document,
                temporary_file,
                indent=2,
                ensure_ascii=False,
            )
            temporary_file.write("\n")
            temporary_file.flush()
            fsync(temporary_file.fileno())

        chmod(temporary_path, permissions)
        replace(temporary_path, path)

    except OSError as exc:
        raise BTSProvenanceError(
            "unable to update the BTS manifest atomically"
        ) from exc
    finally:
        if (
            temporary_path is not None
            and temporary_path.exists()
        ):
            try:
                temporary_path.unlink()
            except OSError:
                pass


def record_bts_ingestion(
    ingested: IngestedBTSArchive,
    manifest_path: str | Path = DEFAULT_MANIFEST_PATH,
    *,
    repository_root: Path = REPOSITORY_ROOT,
) -> BTSManifest:
    """Record a completed BTS ingestion in the manifest."""

    path = Path(manifest_path)
    manifest = load_bts_manifest(path)

    new_record = _build_download_record(
        ingested,
        manifest,
        repository_root,
    )

    original_document = _read_manifest_document(
        path
    )
    updated_document = deepcopy(original_document)

    existing_records = list(
        manifest.integrity.downloaded_files
    )

    matching_records = [
        record
        for record in existing_records
        if record.filename == new_record.filename
    ]

    if len(matching_records) > 1:
        raise BTSProvenanceError(
            "manifest contains duplicate download records"
        )

    if (
        matching_records
        and matching_records[0] != new_record
    ):
        raise BTSProvenanceError(
            "manifest contains a conflicting record "
            f"for {new_record.filename}"
        )

    if not matching_records:
        updated_document["integrity"][
            "downloaded_files"
        ].append(
            new_record.model_dump(mode="json")
        )
        existing_records.append(new_record)

    for record in existing_records:
        _normalize_utc_timestamp(
            record.retrieved_at_utc
        )

    latest_retrieval_time = max(
        record.retrieved_at_utc
        for record in existing_records
    )

    updated_document["source"][
        "accessed_at_utc"
    ] = _utc_isoformat(latest_retrieval_time)

    if (
        updated_document["dataset_status"]
        == "planned"
    ):
        updated_document["dataset_status"] = (
            "downloaded"
        )

    try:
        updated_manifest = BTSManifest.model_validate(
            updated_document
        )
    except ValidationError as exc:
        raise BTSProvenanceError(
            "updated BTS manifest failed validation"
        ) from exc

    if updated_document == original_document:
        return manifest

    _write_manifest_atomically(
        path,
        updated_document,
    )

    return updated_manifest