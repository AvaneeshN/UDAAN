from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
from os import fsync
from pathlib import Path, PurePosixPath
from tempfile import NamedTemporaryFile

import httpx

from ml.data_manifest import (
    DEFAULT_MANIFEST_PATH,
    load_bts_manifest,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024
DOWNLOAD_CHUNK_SIZE_BYTES = 64 * 1024

ALLOWED_CONTENT_TYPES = frozenset(
    {
        "application/zip",
        "application/x-zip-compressed",
        "application/octet-stream",
    }
)


class BTSDownloadError(RuntimeError):
    """Raised when the BTS sample cannot be staged safely."""


@dataclass(frozen=True)
class StagedDownload:
    source_url: str
    temporary_path: Path
    destination_path: Path
    size_bytes: int
    sha256: str


def validate_response_headers(
    response: httpx.Response,
    max_download_bytes: int,
) -> None:
    content_type = response.headers.get("Content-Type")

    if content_type:
        normalized_content_type = (
            content_type.split(";", maxsplit=1)[0]
            .strip()
            .lower()
        )

        if normalized_content_type not in ALLOWED_CONTENT_TYPES:
            raise BTSDownloadError(
                "BTS response has an unsupported content type: "
                f"{normalized_content_type}"
            )

    content_length = response.headers.get("Content-Length")

    if content_length is None:
        return

    try:
        declared_size = int(content_length)
    except ValueError as exc:
        raise BTSDownloadError(
            "BTS response has an invalid Content-Length"
        ) from exc

    if declared_size < 0:
        raise BTSDownloadError(
            "BTS response has a negative Content-Length"
        )

    if declared_size > max_download_bytes:
        raise BTSDownloadError(
            "BTS response Content-Length exceeds the download limit"
        )


@contextmanager
def stage_bts_development_sample(
    manifest_path: str | Path = DEFAULT_MANIFEST_PATH,
    *,
    repository_root: Path = REPOSITORY_ROOT,
    transport: httpx.BaseTransport | None = None,
    max_download_bytes: int = DEFAULT_MAX_DOWNLOAD_BYTES,
) -> Iterator[StagedDownload]:
    if (
        isinstance(max_download_bytes, bool)
        or not isinstance(max_download_bytes, int)
        or max_download_bytes <= 0
    ):
        raise BTSDownloadError(
            "max_download_bytes must be a positive integer"
        )

    # The manifest must pass validation before any network access.
    manifest = load_bts_manifest(manifest_path)

    source_url = str(
        manifest.source.development_sample_url
    )
    filename = PurePosixPath(
        manifest.source.development_sample_url.path
    ).name

    root = Path(repository_root).resolve()
    storage_path = Path(
        *PurePosixPath(
            manifest.storage.raw_directory
        ).parts
    )
    destination_directory = (root / storage_path).resolve()

    try:
        destination_directory.relative_to(root)
    except ValueError as exc:
        raise BTSDownloadError(
            "BTS destination must remain inside the repository root"
        ) from exc

    destination_directory.mkdir(
        parents=True,
        exist_ok=True,
    )
    destination_path = destination_directory / filename

    if destination_path.exists():
        raise BTSDownloadError(
            f"BTS destination already exists: {destination_path}"
        )

    temporary_path: Path | None = None

    try:
        with NamedTemporaryFile(
            mode="w+b",
            prefix=f".{filename}.",
            suffix=".part",
            dir=destination_directory,
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            digest = sha256()
            downloaded_size = 0

            timeout = httpx.Timeout(
                connect=10.0,
                read=60.0,
                write=10.0,
                pool=10.0,
            )

            headers = {
                "User-Agent": "UDAAN-BTS-Downloader/1.0",
                "Accept": (
                    "application/zip, "
                    "application/x-zip-compressed, "
                    "application/octet-stream"
                ),
                "Accept-Encoding": "identity",
            }

            with httpx.Client(
                transport=transport,
                timeout=timeout,
                follow_redirects=False,
                trust_env=False,
                headers=headers,
            ) as client:
                with client.stream(
                    "GET",
                    source_url,
                ) as response:
                    response.raise_for_status()
                    validate_response_headers(
                        response,
                        max_download_bytes,
                    )

                    for chunk in response.iter_bytes(
                        chunk_size=DOWNLOAD_CHUNK_SIZE_BYTES
                    ):
                        if not chunk:
                            continue

                        downloaded_size += len(chunk)

                        if downloaded_size > max_download_bytes:
                            raise BTSDownloadError(
                                "BTS response exceeded the "
                                "download limit while streaming"
                            )

                        temporary_file.write(chunk)
                        digest.update(chunk)

            if downloaded_size == 0:
                raise BTSDownloadError(
                    "BTS response contained no data"
                )

            temporary_file.flush()
            fsync(temporary_file.fileno())

        staged_download = StagedDownload(
            source_url=source_url,
            temporary_path=temporary_path,
            destination_path=destination_path,
            size_bytes=downloaded_size,
            sha256=digest.hexdigest(),
        )

        yield staged_download

    except BTSDownloadError:
        raise
    except httpx.HTTPError as exc:
        raise BTSDownloadError(
            f"BTS download request failed: {exc}"
        ) from exc
    except OSError as exc:
        raise BTSDownloadError(
            f"Unable to stage the BTS download: {exc}"
        ) from exc
    finally:
        if (
            temporary_path is not None
            and temporary_path.exists()
        ):
            temporary_path.unlink()