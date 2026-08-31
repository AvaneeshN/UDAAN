import argparse
import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import TextIO

from ml.bts_downloader import (
    DEFAULT_MAX_DOWNLOAD_BYTES,
    REPOSITORY_ROOT,
)
from ml.bts_ingestion import (
    BTSIngestionError,
    IngestedBTSArchive,
    ingest_bts_development_sample,
)
from ml.bts_provenance import (
    BTSProvenanceError,
    record_bts_ingestion,
)
from ml.data_manifest import (
    DEFAULT_MANIFEST_PATH,
    ManifestError,
    load_bts_manifest,
)


EXIT_SUCCESS = 0
EXIT_OPERATIONAL_ERROR = 1
EXIT_PROVENANCE_ERROR = 3
EXIT_INTERNAL_ERROR = 70
EXIT_INTERRUPTED = 130

def _positive_integer(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "value must be a positive integer"
        ) from exc

    if parsed <= 0:
        raise argparse.ArgumentTypeError(
            "value must be a positive integer"
        )

    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ml.ingest_bts_sample",
        description=(
            "Safely download and record the BTS "
            "development sample."
        ),
        allow_abbrev=False,
    )

    parser.add_argument(
        "--execute",
        action="store_true",
        help=(
            "Perform the network download. Without this "
            "flag, only the ingestion plan is displayed."
        ),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST_PATH,
        help="Path to the BTS dataset manifest.",
    )
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=REPOSITORY_ROOT,
        help="Repository root used for raw-data storage.",
    )
    parser.add_argument(
        "--max-download-bytes",
        type=_positive_integer,
        default=DEFAULT_MAX_DOWNLOAD_BYTES,
        help="Maximum permitted compressed download size.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help=(
            "Allow unexpected exceptions to display a "
            "traceback for development debugging."
        ),
    )

    return parser


def _write_json(
    payload: dict[str, object],
    stream: TextIO,
) -> None:
    print(
        json.dumps(
            payload,
            sort_keys=True,
        ),
        file=stream,
    )


def _utc_text(value: datetime) -> str:
    return (
        value.astimezone(UTC)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _ingestion_details(
    ingested: IngestedBTSArchive,
) -> dict[str, object]:
    return {
        "filename": ingested.destination_path.name,
        "source_url": ingested.source_url,
        "retrieved_at_utc": _utc_text(
            ingested.retrieved_at_utc
        ),
        "size_bytes": ingested.size_bytes,
        "sha256": ingested.sha256,
        "csv_member_name": ingested.csv_member_name,
        "csv_size_bytes": ingested.csv_size_bytes,
        "column_count": len(ingested.columns),
    }


def _run_command(
    args: argparse.Namespace,
) -> int:
    try:
        manifest = load_bts_manifest(
            args.manifest
        )
    except ManifestError as exc:
        _write_json(
            {
                "status": "error",
                "stage": "manifest",
                "message": str(exc),
            },
            sys.stderr,
        )
        return EXIT_OPERATIONAL_ERROR

    filename = PurePosixPath(
        manifest.source.development_sample_url.path
    ).name

    if not args.execute:
        _write_json(
            {
                "status": "dry-run",
                "network_access": False,
                "dataset_id": manifest.dataset_id,
                "dataset_status": (
                    manifest.dataset_status
                ),
                "source_url": str(
                    manifest.source
                    .development_sample_url
                ),
                "filename": filename,
                "raw_directory": (
                    manifest.storage.raw_directory
                ),
                "max_download_bytes": (
                    args.max_download_bytes
                ),
                "execute_command": (
                    "python -m ml.ingest_bts_sample "
                    "--execute"
                ),
            },
            sys.stdout,
        )
        return EXIT_SUCCESS

    try:
        ingested = ingest_bts_development_sample(
            manifest_path=args.manifest,
            repository_root=args.repository_root,
            max_download_bytes=(
                args.max_download_bytes
            ),
        )
    except KeyboardInterrupt:
        _write_json(
            {
                "status": "cancelled",
                "stage": "ingestion",
                "message": (
                    "BTS ingestion was interrupted by the user"
                ),
                "archive_retained": False,
            },
            sys.stderr,
        )
        return EXIT_INTERRUPTED
    except (BTSIngestionError, ManifestError) as exc:
        _write_json(
            {
                "status": "error",
                "stage": "ingestion",
                "message": str(exc),
                "archive_retained": False,
            },
            sys.stderr,
        )
        return EXIT_OPERATIONAL_ERROR

    try:
        updated_manifest = record_bts_ingestion(
            ingested,
            manifest_path=args.manifest,
            repository_root=args.repository_root,
        )
    except (
        BTSProvenanceError,
        ManifestError,
    ) as exc:
        _write_json(
            {
                "status": "error",
                "stage": "provenance",
                "message": str(exc),
                "archive_retained": True,
                "recovery": _ingestion_details(
                    ingested
                ),
            },
            sys.stderr,
        )
        return EXIT_PROVENANCE_ERROR

    success = _ingestion_details(ingested)
    success.update(
        {
            "status": "success",
            "dataset_id": (
                updated_manifest.dataset_id
            ),
            "dataset_status": (
                updated_manifest.dataset_status
            ),
        }
    )

    _write_json(success, sys.stdout)
    return EXIT_SUCCESS


def main(
    argv: Sequence[str] | None = None,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return _run_command(args)
    except Exception:
        if args.debug:
            raise

        _write_json(
            {
                "status": "error",
                "stage": "internal",
                "message": (
                    "an unexpected internal error occurred"
                ),
            },
            sys.stderr,
        )
        return EXIT_INTERNAL_ERROR


if __name__ == "__main__":
    raise SystemExit(main())