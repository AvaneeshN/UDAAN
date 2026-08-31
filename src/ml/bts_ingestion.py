from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from os import link
from pathlib import Path

import httpx

from ml.bts_archive import (
    BTSArchiveError,
    ValidatedBTSArchive,
    validate_bts_archive,
)
from ml.bts_downloader import (
    DEFAULT_MAX_DOWNLOAD_BYTES,
    REPOSITORY_ROOT,
    BTSDownloadError,
    StagedDownload,
    stage_bts_development_sample,
)
from ml.data_manifest import DEFAULT_MANIFEST_PATH


INTEGRITY_CHUNK_SIZE_BYTES = 1024 * 1024


class BTSIngestionError(RuntimeError):
    """Raised when BTS ingestion cannot complete safely."""


@dataclass(frozen=True)
class IngestedBTSArchive:
    destination_path: Path
    source_url: str
    retrieved_at_utc: datetime
    size_bytes: int
    sha256: str
    csv_member_name: str
    csv_size_bytes: int
    columns: tuple[str, ...]


def utc_now() -> datetime:
    return datetime.now(UTC)


def _normalize_retrieval_time(
    value: object,
) -> datetime:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise BTSIngestionError(
            "retrieval time must be timezone-aware"
        )

    return value.astimezone(UTC)


def _verify_staged_integrity(
    staged: StagedDownload,
    validated: ValidatedBTSArchive,
) -> None:
    if validated.archive_path != staged.temporary_path:
        raise BTSIngestionError(
            "validator inspected a different archive"
        )

    digest = sha256()
    actual_size = 0

    try:
        with staged.temporary_path.open("rb") as archive_file:
            while True:
                chunk = archive_file.read(
                    INTEGRITY_CHUNK_SIZE_BYTES
                )

                if not chunk:
                    break

                actual_size += len(chunk)
                digest.update(chunk)

    except OSError as exc:
        raise BTSIngestionError(
            "unable to verify the staged BTS archive"
        ) from exc

    if (
        actual_size != staged.size_bytes
        or actual_size != validated.archive_size_bytes
    ):
        raise BTSIngestionError(
            "staged BTS archive size changed after download"
        )

    if digest.hexdigest() != staged.sha256:
        raise BTSIngestionError(
            "staged BTS archive checksum changed after download"
        )


def _promote_without_overwrite(
    staged: StagedDownload,
) -> None:
    try:
        link(
            staged.temporary_path,
            staged.destination_path,
        )
    except FileExistsError as exc:
        raise BTSIngestionError(
            "refusing to overwrite an existing BTS archive: "
            f"{staged.destination_path}"
        ) from exc
    except OSError as exc:
        raise BTSIngestionError(
            "unable to promote the validated BTS archive"
        ) from exc


def ingest_bts_development_sample(
    manifest_path: str | Path = DEFAULT_MANIFEST_PATH,
    *,
    repository_root: Path = REPOSITORY_ROOT,
    transport: httpx.BaseTransport | None = None,
    max_download_bytes: int = DEFAULT_MAX_DOWNLOAD_BYTES,
    clock: Callable[[], datetime] = utc_now,
) -> IngestedBTSArchive:
    """Download, validate, and safely promote the BTS sample."""

    try:
        with stage_bts_development_sample(
            manifest_path=manifest_path,
            repository_root=repository_root,
            transport=transport,
            max_download_bytes=max_download_bytes,
        ) as staged:
            validated = validate_bts_archive(
                staged.temporary_path,
                manifest_path=manifest_path,
            )

            _verify_staged_integrity(
                staged,
                validated,
            )

            retrieved_at_utc = (
                _normalize_retrieval_time(clock())
            )

            result = IngestedBTSArchive(
                destination_path=staged.destination_path,
                source_url=staged.source_url,
                retrieved_at_utc=retrieved_at_utc,
                size_bytes=staged.size_bytes,
                sha256=staged.sha256,
                csv_member_name=(
                    validated.csv_member_name
                ),
                csv_size_bytes=(
                    validated.csv_size_bytes
                ),
                columns=validated.columns,
            )

            _promote_without_overwrite(staged)

            return result

    except (BTSDownloadError, BTSArchiveError) as exc:
        raise BTSIngestionError(
            f"BTS ingestion failed: {exc}"
        ) from exc