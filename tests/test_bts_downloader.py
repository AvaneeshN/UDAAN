from hashlib import sha256

import httpx
import pytest

from ml.bts_downloader import (
    BTSDownloadError,
    stage_bts_development_sample,
)
from ml.data_manifest import ManifestError


PAYLOAD = b"temporary BTS ZIP content"


def successful_transport(
    payload: bytes = PAYLOAD,
) -> httpx.MockTransport:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.host == "transtats.bts.gov"
        assert (
            request.headers["Accept-Encoding"]
            == "identity"
        )

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


def test_stages_download_and_cleans_temporary_file(
    tmp_path,
):
    with stage_bts_development_sample(
        repository_root=tmp_path,
        transport=successful_transport(),
    ) as staged:
        temporary_path = staged.temporary_path

        assert temporary_path.exists()
        assert temporary_path.read_bytes() == PAYLOAD
        assert staged.size_bytes == len(PAYLOAD)
        assert staged.sha256 == sha256(PAYLOAD).hexdigest()
        assert staged.destination_path.name.endswith(
            "2022_1.zip"
        )
        assert not staged.destination_path.exists()

    assert not temporary_path.exists()


def test_rejects_declared_oversized_response(tmp_path):
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            headers={
                "Content-Type": "application/zip",
                "Content-Length": "11",
            },
            content=b"",
            request=request,
        )

    with pytest.raises(
        BTSDownloadError,
        match="Content-Length exceeds",
    ):
        with stage_bts_development_sample(
            repository_root=tmp_path,
            transport=httpx.MockTransport(handler),
            max_download_bytes=10,
        ):
            pass


def test_rejects_oversized_stream_when_length_is_wrong(
    tmp_path,
):
    payload = b"01234567890"

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            headers={
                "Content-Type": "application/zip",
                "Content-Length": "1",
            },
            content=payload,
            request=request,
        )

    with pytest.raises(
        BTSDownloadError,
        match="exceeded the download limit while streaming",
    ):
        with stage_bts_development_sample(
            repository_root=tmp_path,
            transport=httpx.MockTransport(handler),
            max_download_bytes=10,
        ):
            pass

    staging_directory = (
        tmp_path / "data" / "raw" / "bts"
    )

    assert list(
        staging_directory.glob("*.part")
    ) == []


def test_rejects_unexpected_content_type(tmp_path):
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
        BTSDownloadError,
        match="unsupported content type",
    ):
        with stage_bts_development_sample(
            repository_root=tmp_path,
            transport=httpx.MockTransport(handler),
        ):
            pass


def test_rejects_redirect_response(tmp_path):
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=302,
            headers={
                "Location": "https://example.com/file.zip",
            },
            request=request,
        )

    with pytest.raises(
        BTSDownloadError,
        match="download request failed",
    ):
        with stage_bts_development_sample(
            repository_root=tmp_path,
            transport=httpx.MockTransport(handler),
        ):
            pass


def test_invalid_manifest_fails_before_network_access(
    tmp_path,
):
    manifest_path = tmp_path / "invalid.json"
    manifest_path.write_text("{", encoding="utf-8")
    request_was_made = False

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        nonlocal request_was_made
        request_was_made = True

        return httpx.Response(
            status_code=200,
            content=PAYLOAD,
            request=request,
        )

    with pytest.raises(
        ManifestError,
        match="not valid JSON",
    ):
        with stage_bts_development_sample(
            manifest_path=manifest_path,
            repository_root=tmp_path,
            transport=httpx.MockTransport(handler),
        ):
            pass

    assert request_was_made is False


@pytest.mark.parametrize(
    "invalid_limit",
    [0, -1, True, 1.5, "10"],
)
def test_rejects_invalid_download_limit(
    tmp_path,
    invalid_limit,
):
    with pytest.raises(
        BTSDownloadError,
        match="must be a positive integer",
    ):
        with stage_bts_development_sample(
            repository_root=tmp_path,
            transport=successful_transport(),
            max_download_bytes=invalid_limit,
        ):
            pass


def test_existing_destination_stops_before_network_access(
    tmp_path,
):
    destination_directory = (
        tmp_path / "data" / "raw" / "bts"
    )
    destination_directory.mkdir(parents=True)

    destination_path = destination_directory / (
        "On_Time_Reporting_Carrier_On_Time_Performance_"
        "1987_present_2022_1.zip"
    )
    original_content = b"existing verified data"
    destination_path.write_bytes(original_content)

    request_was_made = False

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        nonlocal request_was_made
        request_was_made = True

        return httpx.Response(
            status_code=200,
            content=PAYLOAD,
            request=request,
        )

    with pytest.raises(
        BTSDownloadError,
        match="destination already exists",
    ):
        with stage_bts_development_sample(
            repository_root=tmp_path,
            transport=httpx.MockTransport(handler),
        ):
            pass

    assert request_was_made is False
    assert destination_path.read_bytes() == original_content