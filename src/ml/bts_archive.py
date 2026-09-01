import csv
import math
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from zipfile import (
    BadZipFile,
    ZIP_DEFLATED,
    ZIP_STORED,
    ZipFile,
    ZipInfo,
)

from ml.data_manifest import (
    DEFAULT_MANIFEST_PATH,
    load_bts_manifest,
)


DEFAULT_MAX_ARCHIVE_MEMBERS = 10
DEFAULT_MAX_UNCOMPRESSED_BYTES = 1024 * 1024 * 1024
DEFAULT_MAX_COMPRESSION_RATIO = 200.0
DEFAULT_MAX_HEADER_BYTES = 128 * 1024
VALIDATION_CHUNK_SIZE_BYTES = 1024 * 1024

ALLOWED_COMPRESSION_METHODS = frozenset(
    {
        ZIP_STORED,
        ZIP_DEFLATED,
    }
)

ALLOWED_METADATA_MEMBER_NAMES = frozenset(
    {
        "readme.html",
    }
)


class BTSArchiveError(RuntimeError):
    """Raised when a staged BTS archive is unsafe or invalid."""


@dataclass(frozen=True)
class ValidatedBTSArchive:
    archive_path: Path
    csv_member_name: str
    archive_size_bytes: int
    csv_size_bytes: int
    columns: tuple[str, ...]


def _validate_positive_integer(
    value: object,
    name: str,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= 0
    ):
        raise BTSArchiveError(
            f"{name} must be a positive integer"
        )

    return value


def _validate_positive_number(
    value: object,
    name: str,
) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or value <= 0
    ):
        raise BTSArchiveError(
            f"{name} must be a positive finite number"
        )

    return float(value)


def _validate_member_path(info: ZipInfo) -> None:
    raw_name = info.filename
    candidate = (
        raw_name[:-1]
        if info.is_dir()
        else raw_name
    )
    segments = candidate.split("/")

    unsafe = (
        not candidate
        or "\x00" in raw_name
        or "\\" in raw_name
        or raw_name.startswith("/")
        or any(
            segment in {"", ".", ".."}
            for segment in segments
        )
        or ":" in segments[0]
    )

    if unsafe:
        raise BTSArchiveError(
            f"unsafe ZIP member path: {raw_name}"
        )

    unix_mode = info.external_attr >> 16

    if stat.S_ISLNK(unix_mode):
        raise BTSArchiveError(
            f"symbolic links are not allowed: {raw_name}"
        )


def _inspect_members(
    archive: ZipFile,
    *,
    expected_csv_member_name: str,
    max_members: int,
    max_uncompressed_bytes: int,
    max_compression_ratio: float,
) -> ZipInfo:
    members = archive.infolist()

    if not members:
        raise BTSArchiveError("BTS ZIP archive is empty")

    if len(members) > max_members:
        raise BTSArchiveError(
            "BTS ZIP archive contains too many members"
        )

    files: list[ZipInfo] = []
    total_uncompressed_bytes = 0

    for info in members:
        _validate_member_path(info)

        if info.flag_bits & 0x1:
            raise BTSArchiveError(
                f"encrypted ZIP members are not allowed: "
                f"{info.filename}"
            )

        if info.compress_type not in ALLOWED_COMPRESSION_METHODS:
            raise BTSArchiveError(
                f"unsupported ZIP compression method: "
                f"{info.filename}"
            )

        if info.is_dir():
            continue

        files.append(info)
        total_uncompressed_bytes += info.file_size

        if total_uncompressed_bytes > max_uncompressed_bytes:
            raise BTSArchiveError(
                "BTS ZIP uncompressed size exceeds the limit"
            )

        if info.file_size > 0:
            if info.compress_size <= 0:
                raise BTSArchiveError(
                    f"invalid compressed size: {info.filename}"
                )

            compression_ratio = (
                info.file_size / info.compress_size
            )

            if compression_ratio > max_compression_ratio:
                raise BTSArchiveError(
                    "BTS ZIP compression ratio exceeds the limit"
                )

    csv_files = [
        info
        for info in files
        if PurePosixPath(
            info.filename
        ).suffix.lower() == ".csv"
    ]

    if len(csv_files) != 1:
        raise BTSArchiveError(
            "BTS ZIP must contain exactly one CSV file"
        )

    csv_info = csv_files[0]

    if csv_info.filename != expected_csv_member_name:
        raise BTSArchiveError(
            "BTS ZIP contains an unexpected CSV member: "
            f"{csv_info.filename}"
        )

    permitted_names = (
        ALLOWED_METADATA_MEMBER_NAMES
        | {expected_csv_member_name}
    )

    unexpected_members = sorted(
        info.filename
        for info in files
        if info.filename not in permitted_names
    )

    if unexpected_members:
        unexpected = ", ".join(
            unexpected_members
        )
        raise BTSArchiveError(
            f"BTS ZIP contains unexpected members: "
            f"{unexpected}"
        )

    return csv_info


def _read_and_validate_csv(
    archive: ZipFile,
    csv_info: ZipInfo,
    *,
    required_columns: tuple[str, ...],
    max_uncompressed_bytes: int,
    max_header_bytes: int,
) -> tuple[tuple[str, ...], int]:
    with archive.open(csv_info, mode="r") as csv_stream:
        header_bytes = csv_stream.readline(
            max_header_bytes + 1
        )

        if not header_bytes:
            raise BTSArchiveError("BTS CSV file is empty")

        if len(header_bytes) > max_header_bytes:
            raise BTSArchiveError(
                "BTS CSV header exceeds the size limit"
            )

        try:
            header_text = header_bytes.decode("utf-8-sig")
            columns = tuple(
                next(
                    csv.reader(
                        [header_text],
                        strict=True,
                    )
                )
            )
        except (UnicodeDecodeError, csv.Error, StopIteration) as exc:
            raise BTSArchiveError(
                "BTS CSV header is invalid"
            ) from exc

        # BTS PREZIP CSV files contain one trailing
        # delimiter after the 109 documented fields.
        if columns and columns[-1] == "":
            columns = columns[:-1]

        if not columns or any(
            not column
            for column in columns
        ):
            raise BTSArchiveError(
                "BTS CSV contains an empty column name"
            )

        if len(columns) != len(set(columns)):
            raise BTSArchiveError(
                "BTS CSV contains duplicate column names"
            )

        available_columns = set(columns)
        missing_columns = [
            column
            for column in required_columns
            if column not in available_columns
        ]

        if missing_columns:
            missing = ", ".join(missing_columns)
            raise BTSArchiveError(
                f"BTS CSV is missing required columns: {missing}"
            )

        actual_size = len(header_bytes)

        while True:
            chunk = csv_stream.read(
                VALIDATION_CHUNK_SIZE_BYTES
            )

            if not chunk:
                break

            actual_size += len(chunk)

            if actual_size > max_uncompressed_bytes:
                raise BTSArchiveError(
                    "BTS CSV exceeded the uncompressed size limit"
                )

        if actual_size == len(header_bytes):
            raise BTSArchiveError(
                "BTS CSV contains no data rows"
            )

        if actual_size != csv_info.file_size:
            raise BTSArchiveError(
                "BTS CSV size does not match ZIP metadata"
            )

        return columns, actual_size


def validate_bts_archive(
    archive_path: str | Path,
    manifest_path: str | Path = DEFAULT_MANIFEST_PATH,
    *,
    max_members: int = DEFAULT_MAX_ARCHIVE_MEMBERS,
    max_uncompressed_bytes: int = (
        DEFAULT_MAX_UNCOMPRESSED_BYTES
    ),
    max_compression_ratio: float = (
        DEFAULT_MAX_COMPRESSION_RATIO
    ),
    max_header_bytes: int = DEFAULT_MAX_HEADER_BYTES,
) -> ValidatedBTSArchive:
    """Validate a staged BTS ZIP without extracting it."""

    max_members = _validate_positive_integer(
        max_members,
        "max_members",
    )
    max_uncompressed_bytes = _validate_positive_integer(
        max_uncompressed_bytes,
        "max_uncompressed_bytes",
    )
    max_header_bytes = _validate_positive_integer(
        max_header_bytes,
        "max_header_bytes",
    )
    max_compression_ratio = _validate_positive_number(
        max_compression_ratio,
        "max_compression_ratio",
    )

    manifest = load_bts_manifest(manifest_path)
    path = Path(archive_path)

    sample = manifest.scope.development_sample

    expected_csv_member_name = (
        "On_Time_Reporting_Carrier_"
        "On_Time_Performance_"
        "(1987_present)_"
        f"{sample.start_date.year}_"
        f"{sample.start_date.month}.csv"
    )

    if not path.is_file():
        raise BTSArchiveError(
            f"BTS archive does not exist: {path}"
        )

    try:
        archive_size_bytes = path.stat().st_size

        with ZipFile(path, mode="r") as archive:
            csv_info = _inspect_members(
                archive,
                expected_csv_member_name=(
                    expected_csv_member_name
                ),
                max_members=max_members,
                max_uncompressed_bytes=(
                    max_uncompressed_bytes
                ),
                max_compression_ratio=(
                    max_compression_ratio
                ),
            )

            columns, csv_size_bytes = (
                _read_and_validate_csv(
                    archive,
                    csv_info,
                    required_columns=(
                        manifest.required_columns
                    ),
                    max_uncompressed_bytes=(
                        max_uncompressed_bytes
                    ),
                    max_header_bytes=max_header_bytes,
                )
            )

    except BTSArchiveError:
        raise
    except (
        BadZipFile,
        EOFError,
        NotImplementedError,
        OSError,
        RuntimeError,
    ) as exc:
        raise BTSArchiveError(
            f"Unable to validate BTS ZIP archive: {exc}"
        ) from exc

    return ValidatedBTSArchive(
        archive_path=path,
        csv_member_name=csv_info.filename,
        archive_size_bytes=archive_size_bytes,
        csv_size_bytes=csv_size_bytes,
        columns=columns,
    )