import stat
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import pytest

from ml.bts_archive import (
    BTSArchiveError,
    validate_bts_archive,
)
from ml.data_manifest import load_bts_manifest


REQUIRED_COLUMNS = load_bts_manifest().required_columns

EXPECTED_CSV_MEMBER = (
    "On_Time_Reporting_Carrier_"
    "On_Time_Performance_"
    "(1987_present)_2022_1.csv"
)

VALID_CSV = (
    ",".join(REQUIRED_COLUMNS)
    + "\n"
    + ",".join("0" for _ in REQUIRED_COLUMNS)
    + "\n"
).encode("utf-8")


def write_archive(
    path,
    members: dict[str, bytes],
) -> None:
    with ZipFile(
        path,
        mode="w",
        compression=ZIP_DEFLATED,
    ) as archive:
        for name, contents in members.items():
            archive.writestr(name, contents)


def test_validates_expected_bts_archive(tmp_path):
    archive_path = tmp_path / "sample.zip"
    write_archive(
        archive_path,
        {EXPECTED_CSV_MEMBER: VALID_CSV},
    )

    result = validate_bts_archive(archive_path)

    assert result.archive_path == archive_path
    assert result.csv_member_name == EXPECTED_CSV_MEMBER
    assert result.csv_size_bytes == len(VALID_CSV)
    assert result.columns == REQUIRED_COLUMNS
    assert (
        result.archive_size_bytes
        == archive_path.stat().st_size
    )


def test_rejects_corrupt_zip(tmp_path):
    archive_path = tmp_path / "corrupt.zip"
    archive_path.write_bytes(b"not a zip file")

    with pytest.raises(
        BTSArchiveError,
        match="Unable to validate",
    ):
        validate_bts_archive(archive_path)


def test_rejects_path_traversal(tmp_path):
    archive_path = tmp_path / "traversal.zip"
    write_archive(
        archive_path,
        {"../escape.csv": VALID_CSV},
    )

    with pytest.raises(
        BTSArchiveError,
        match="unsafe ZIP member path",
    ):
        validate_bts_archive(archive_path)

    assert not (tmp_path / "escape.csv").exists()


def test_rejects_symbolic_link(tmp_path):
    archive_path = tmp_path / "symlink.zip"
    link_info = ZipInfo(EXPECTED_CSV_MEMBER)
    link_info.create_system = 3
    link_info.external_attr = (
        stat.S_IFLNK | 0o777
    ) << 16

    with ZipFile(archive_path, mode="w") as archive:
        archive.writestr(link_info, b"target.csv")

    with pytest.raises(
        BTSArchiveError,
        match="symbolic links are not allowed",
    ):
        validate_bts_archive(archive_path)


def test_rejects_multiple_files(tmp_path):
    archive_path = tmp_path / "multiple.zip"
    write_archive(
        archive_path,
        {
            "first.csv": VALID_CSV,
            "second.csv": VALID_CSV,
        },
    )

    with pytest.raises(
        BTSArchiveError,
        match="exactly one CSV",
    ):
        validate_bts_archive(archive_path)


def test_rejects_non_csv_file(tmp_path):
    archive_path = tmp_path / "wrong-type.zip"
    write_archive(
        archive_path,
        {"bts_sample.txt": VALID_CSV},
    )

    with pytest.raises(
        BTSArchiveError,
        match="exactly one CSV",
    ):
        validate_bts_archive(archive_path)


def test_rejects_missing_required_columns(tmp_path):
    archive_path = tmp_path / "missing-columns.zip"
    csv_contents = b"FlightDate\n2022-01-01\n"

    write_archive(
        archive_path,
        {EXPECTED_CSV_MEMBER: csv_contents},
    )

    with pytest.raises(
        BTSArchiveError,
        match="missing required columns",
    ):
        validate_bts_archive(archive_path)


def test_rejects_duplicate_columns(tmp_path):
    archive_path = tmp_path / "duplicates.zip"
    duplicate_header = (
        ",".join(
            REQUIRED_COLUMNS
            + (REQUIRED_COLUMNS[0],)
        )
        + "\n"
        + ",".join(
            "0"
            for _ in range(
                len(REQUIRED_COLUMNS) + 1
            )
        )
        + "\n"
    ).encode("utf-8")

    write_archive(
        archive_path,
        {EXPECTED_CSV_MEMBER: duplicate_header},
    )

    with pytest.raises(
        BTSArchiveError,
        match="duplicate column names",
    ):
        validate_bts_archive(archive_path)


def test_rejects_uncompressed_size_over_limit(
    tmp_path,
):
    archive_path = tmp_path / "oversized.zip"
    write_archive(
        archive_path,
        {EXPECTED_CSV_MEMBER: VALID_CSV},
    )

    with pytest.raises(
        BTSArchiveError,
        match="uncompressed size exceeds",
    ):
        validate_bts_archive(
            archive_path,
            max_uncompressed_bytes=(
                len(VALID_CSV) - 1
            ),
        )


def test_rejects_excessive_compression_ratio(
    tmp_path,
):
    archive_path = tmp_path / "ratio.zip"
    compressible_contents = (
        VALID_CSV + b"0," * 50_000
    )

    write_archive(
        archive_path,
        {EXPECTED_CSV_MEMBER: compressible_contents},
    )

    with pytest.raises(
        BTSArchiveError,
        match="compression ratio exceeds",
    ):
        validate_bts_archive(
            archive_path,
            max_compression_ratio=2.0,
        )


def test_rejects_header_over_limit(tmp_path):
    archive_path = tmp_path / "header.zip"
    write_archive(
        archive_path,
        {EXPECTED_CSV_MEMBER: VALID_CSV},
    )

    with pytest.raises(
        BTSArchiveError,
        match="header exceeds",
    ):
        validate_bts_archive(
            archive_path,
            max_header_bytes=10,
        )


def test_rejects_too_many_archive_members(
    tmp_path,
):
    archive_path = tmp_path / "members.zip"
    write_archive(
        archive_path,
        {
            "folder/": b"",
            EXPECTED_CSV_MEMBER: VALID_CSV,
        },
    )

    with pytest.raises(
        BTSArchiveError,
        match="too many members",
    ):
        validate_bts_archive(
            archive_path,
            max_members=1,
        )


def test_allows_known_bts_readme(tmp_path):
    archive_path = tmp_path / "with-readme.zip"

    write_archive(
        archive_path,
        {
            EXPECTED_CSV_MEMBER: VALID_CSV,
            "readme.html": b"<html>BTS documentation</html>",
        },
    )

    result = validate_bts_archive(archive_path)

    assert (
        result.csv_member_name
        == EXPECTED_CSV_MEMBER
    )


def test_rejects_unexpected_additional_file(
    tmp_path,
):
    archive_path = tmp_path / "unexpected.zip"

    write_archive(
        archive_path,
        {
            EXPECTED_CSV_MEMBER: VALID_CSV,
            "notes.txt": b"unexpected content",
        },
    )

    with pytest.raises(
        BTSArchiveError,
        match="unexpected members",
    ):
        validate_bts_archive(archive_path)


def test_rejects_unexpected_csv_member_name(
    tmp_path,
):
    archive_path = tmp_path / "wrong-name.zip"

    write_archive(
        archive_path,
        {"different.csv": VALID_CSV},
    )

    with pytest.raises(
        BTSArchiveError,
        match="unexpected CSV member",
    ):
        validate_bts_archive(archive_path)


def test_normalizes_one_trailing_blank_column(
    tmp_path,
):
    archive_path = tmp_path / "trailing-column.zip"

    csv_contents = (
        ",".join(REQUIRED_COLUMNS)
        + ",\n"
        + ",".join(
            "0"
            for _ in REQUIRED_COLUMNS
        )
        + ",\n"
    ).encode("utf-8")

    write_archive(
        archive_path,
        {
            EXPECTED_CSV_MEMBER: csv_contents,
            "readme.html": b"<html>README</html>",
        },
    )

    result = validate_bts_archive(archive_path)

    assert result.columns == REQUIRED_COLUMNS
    assert "" not in result.columns


def test_rejects_blank_column_inside_header(
    tmp_path,
):
    archive_path = tmp_path / "interior-blank.zip"

    columns = list(REQUIRED_COLUMNS)
    columns.insert(1, "")

    csv_contents = (
        ",".join(columns)
        + "\n"
        + ",".join(
            "0"
            for _ in columns
        )
        + "\n"
    ).encode("utf-8")

    write_archive(
        archive_path,
        {EXPECTED_CSV_MEMBER: csv_contents},
    )

    with pytest.raises(
        BTSArchiveError,
        match="empty column name",
    ):
        validate_bts_archive(archive_path)