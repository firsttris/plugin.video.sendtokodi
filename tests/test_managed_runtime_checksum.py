import hashlib
import io
import urllib.error

import pytest

from core import managed_runtime


class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


def _serve(monkeypatch, body=None, status=None):
    def fake_urlopen(url, *_args, **_kwargs):
        if status is not None:
            raise urllib.error.HTTPError(url, status, "error", {}, None)
        return _FakeResponse(body)

    monkeypatch.setattr(managed_runtime.urllib.request, "urlopen", fake_urlopen)


def test_fetch_expected_sha256_picks_the_line_of_the_requested_file(monkeypatch):
    other, wanted = "a" * 64, "B" * 64
    _serve(monkeypatch, "{}  yt-dlp\n{}  yt-dlp.tar.gz\n".format(other, wanted).encode())

    assert managed_runtime.fetch_expected_sha256("https://x/SHA2-256SUMS", "yt-dlp.tar.gz") == "b" * 64


def test_fetch_expected_sha256_accepts_binary_mode_marker(monkeypatch):
    _serve(monkeypatch, "{} *deno.zip\n".format("c" * 64).encode())

    assert managed_runtime.fetch_expected_sha256("https://x/deno.zip.sha256sum", "deno.zip") == "c" * 64


def test_fetch_expected_sha256_returns_none_without_checksum_file(monkeypatch):
    _serve(monkeypatch, status=404)

    assert managed_runtime.fetch_expected_sha256("https://x/SHA2-256SUMS", "yt-dlp.tar.gz") is None


def test_fetch_expected_sha256_raises_on_other_http_errors(monkeypatch):
    _serve(monkeypatch, status=503)

    with pytest.raises(urllib.error.HTTPError):
        managed_runtime.fetch_expected_sha256("https://x/SHA2-256SUMS", "yt-dlp.tar.gz")


def test_fetch_expected_sha256_raises_when_the_file_is_not_listed(monkeypatch):
    _serve(monkeypatch, "{}  something-else\n".format("d" * 64).encode())

    with pytest.raises(managed_runtime.ChecksumMismatchError):
        managed_runtime.fetch_expected_sha256("https://x/SHA2-256SUMS", "yt-dlp.tar.gz")


def test_verify_download_accepts_a_matching_file(monkeypatch, tmp_path):
    archive = tmp_path / "yt-dlp.tar.gz"
    archive.write_bytes(b"payload")
    _serve(monkeypatch, "{}  yt-dlp.tar.gz\n".format(hashlib.sha256(b"payload").hexdigest()).encode())
    logs = []

    assert managed_runtime.verify_download(str(archive), "https://x/SUMS", "yt-dlp.tar.gz", logs.append, logs.append)
    assert any("Verified" in message for message in logs)


def test_verify_download_rejects_a_tampered_file(monkeypatch, tmp_path):
    archive = tmp_path / "yt-dlp.tar.gz"
    archive.write_bytes(b"tampered")
    _serve(monkeypatch, "{}  yt-dlp.tar.gz\n".format(hashlib.sha256(b"payload").hexdigest()).encode())

    with pytest.raises(managed_runtime.ChecksumMismatchError):
        managed_runtime.verify_download(str(archive), "https://x/SUMS", "yt-dlp.tar.gz", print, print)


def test_verify_download_warns_when_no_checksum_is_published(monkeypatch, tmp_path):
    archive = tmp_path / "yt-dlp.tar.gz"
    archive.write_bytes(b"payload")
    _serve(monkeypatch, status=404)
    warnings = []

    assert not managed_runtime.verify_download(str(archive), "https://x/SUMS", "yt-dlp.tar.gz", print, warnings.append)
    assert warnings
