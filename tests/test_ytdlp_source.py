import json
import urllib.error

import pytest

from core import managed_runtime, ytdlp_manager


def _fake_urlopen(body):
    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def read(self):
            return self._payload

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    return lambda *_args, **_kwargs: FakeResponse(body)


# --- source resolution -------------------------------------------------------


def test_normalize_source_defaults_to_stable_for_unknown_values():
    assert ytdlp_manager.normalize_source(None) == "stable"
    assert ytdlp_manager.normalize_source("") == "stable"
    assert ytdlp_manager.normalize_source("garbage") == "stable"


def test_normalize_source_accepts_known_sources_case_insensitively():
    assert ytdlp_manager.normalize_source("nightly") == "nightly"
    assert ytdlp_manager.normalize_source("  NIGHTLY ") == "nightly"
    assert ytdlp_manager.normalize_source("stable") == "stable"


def test_source_endpoints_point_at_the_right_repositories():
    assert (
        ytdlp_manager._latest_release_api("stable")
        == "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
    )
    assert (
        ytdlp_manager._latest_release_api("nightly")
        == "https://api.github.com/repos/yt-dlp/yt-dlp-nightly-builds/releases/latest"
    )
    assert ytdlp_manager._releases_api("nightly").startswith(
        "https://api.github.com/repos/yt-dlp/yt-dlp-nightly-builds/releases?"
    )


def test_tarball_url_uses_release_asset_for_both_channels():
    # The release asset ships lazy_extractors.py; the nightly *repository*
    # archive is a README stub.
    assert ytdlp_manager._tarball_url("stable", "2026.08.19") == (
        "https://github.com/yt-dlp/yt-dlp/releases/download/2026.08.19/yt-dlp.tar.gz"
    )
    assert ytdlp_manager._fallback_tarball_url("stable", "2026.08.19") == (
        "https://github.com/yt-dlp/yt-dlp/archive/refs/tags/2026.08.19.tar.gz"
    )
    assert ytdlp_manager._fallback_tarball_url("nightly", "2026.09.27.232945") is None
    assert ytdlp_manager._tarball_url("nightly", "2026.09.27.232945") == (
        "https://github.com/yt-dlp/yt-dlp-nightly-builds/releases/download/"
        "2026.09.27.232945/yt-dlp.tar.gz"
    )


# --- nightly tag parsing -----------------------------------------------------


def test_nightly_tags_sort_above_and_below_stable_tags_numerically():
    versions = [
        "2026.08.19",
        "2026.09.27.232945",
        "2026.09.16.232951",
        "2026.08.30.232658",
    ]

    ordered = managed_runtime.sort_versions_descending(versions)

    assert ordered == [
        "2026.09.27.232945",
        "2026.09.16.232951",
        "2026.08.30.232658",
        "2026.08.19",
    ]


def test_nightly_tags_sort_numerically_not_lexically():
    # Lexical sorting would put "....232945" before "....003630".
    ordered = managed_runtime.sort_versions_descending(
        ["2026.09.27.003630", "2026.09.27.232945"]
    )

    assert ordered == ["2026.09.27.232945", "2026.09.27.003630"]


def test_list_available_versions_returns_nightly_tags(monkeypatch):
    payload = [
        {"tag_name": "2026.09.27.232945"},
        {"tag_name": "2026.09.16.232951"},
    ]
    monkeypatch.setattr(
        managed_runtime.urllib.request, "urlopen", _fake_urlopen(json.dumps(payload).encode())
    )

    versions = ytdlp_manager.list_available_versions(limit=10, source="nightly")

    assert versions == ["2026.09.27.232945", "2026.09.16.232951"]


def test_list_available_versions_queries_the_nightly_repository(monkeypatch):
    seen = {}

    class FakeResponse:
        def read(self):
            return b"[]"

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(url, *_args, **_kwargs):
        seen["url"] = url
        return FakeResponse()

    monkeypatch.setattr(managed_runtime.urllib.request, "urlopen", fake_urlopen)

    ytdlp_manager.list_available_versions(limit=5, source="nightly")

    assert "yt-dlp-nightly-builds" in seen["url"]


# --- channel switch ----------------------------------------------------------


def _fresh_state(version):
    return {
        "last_checked_at": 1000,
        "next_check_at": 9999,
        "latest_known_version": version,
        "etag": "etag-{}".format(version),
        "cooldown_until": 0,
        "consecutive_failures": 0,
        "last_error": None,
    }


def test_update_state_file_is_separate_per_source(monkeypatch, tmp_path):
    monkeypatch.setattr(ytdlp_manager, "_addon_data_dir", lambda: str(tmp_path))

    # Stable keeps the file name used before sources existed.
    assert ytdlp_manager._update_state_file("stable") == str(tmp_path / "ytdlp_update_state.json")
    assert ytdlp_manager._update_state_file("nightly") == str(
        tmp_path / "ytdlp_update_state_nightly.json"
    )


def test_switching_source_does_not_reuse_the_other_sources_cached_latest(monkeypatch, tmp_path):
    # Cache is populated by the *stable* channel and still "fresh".
    (tmp_path / "ytdlp_update_state.json").write_text(json.dumps(_fresh_state("2026.08.19")))
    monkeypatch.setattr(ytdlp_manager, "_addon_data_dir", lambda: str(tmp_path))
    monkeypatch.setattr(managed_runtime.time, "time", lambda: 1500)

    seen_urls = []

    def fake_urlopen(request, *_args, **_kwargs):
        seen_urls.append(request.full_url if hasattr(request, "full_url") else str(request))
        raise AssertionError("expected a fresh lookup for the new source")

    monkeypatch.setattr(managed_runtime.urllib.request, "urlopen", fake_urlopen)

    # Asking for nightly must not serve the cached stable version.
    with pytest.raises(AssertionError):
        ytdlp_manager._resolve_latest_version(source="nightly")

    assert seen_urls and "yt-dlp-nightly-builds" in seen_urls[0]


def test_each_source_uses_its_own_cached_latest_version(monkeypatch, tmp_path):
    (tmp_path / "ytdlp_update_state.json").write_text(json.dumps(_fresh_state("2026.08.19")))
    (tmp_path / "ytdlp_update_state_nightly.json").write_text(
        json.dumps(_fresh_state("2026.09.27.232945"))
    )
    monkeypatch.setattr(ytdlp_manager, "_addon_data_dir", lambda: str(tmp_path))
    monkeypatch.setattr(managed_runtime.time, "time", lambda: 1500)
    monkeypatch.setattr(
        managed_runtime.urllib.request,
        "urlopen",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("network should not run")),
    )

    assert ytdlp_manager._resolve_latest_version(source="stable") == "2026.08.19"
    assert ytdlp_manager._resolve_latest_version(source="nightly") == "2026.09.27.232945"
    assert ytdlp_manager._resolve_latest_version(source="stable") == "2026.08.19"


def test_resolve_latest_version_writes_the_sources_state_file(monkeypatch, tmp_path):
    monkeypatch.setattr(ytdlp_manager, "_addon_data_dir", lambda: str(tmp_path))
    monkeypatch.setattr(managed_runtime.time, "time", lambda: 1000)

    class FakeResponse:
        headers = {"ETag": "etag-nightly"}

        def read(self):
            return json.dumps({"tag_name": "2026.09.27.232945"}).encode()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        managed_runtime.urllib.request, "urlopen", lambda *_a, **_k: FakeResponse()
    )

    assert ytdlp_manager._resolve_latest_version(source="nightly") == "2026.09.27.232945"

    state = json.loads((tmp_path / "ytdlp_update_state_nightly.json").read_text())
    assert state["latest_known_version"] == "2026.09.27.232945"
    assert not (tmp_path / "ytdlp_update_state.json").exists()


def test_install_uses_the_tarball_of_the_requested_source(monkeypatch, tmp_path):
    downloaded = []

    monkeypatch.setattr(ytdlp_manager, "_addon_data_dir", lambda: str(tmp_path))
    monkeypatch.setattr(
        managed_runtime,
        "download_with_progress",
        lambda url, *_a, **_k: downloaded.append(url) or b"",
    )
    monkeypatch.setattr(
        ytdlp_manager, "_extract_yt_dlp_from_tarball", lambda data, destination: None
    )

    ytdlp_manager._download_and_install("2026.09.27.232945", source="nightly")

    assert downloaded == [
        "https://github.com/yt-dlp/yt-dlp-nightly-builds/releases/download/"
        "2026.09.27.232945/yt-dlp.tar.gz"
    ]


def test_ensure_ready_passes_source_to_download(monkeypatch):
    calls = []

    monkeypatch.setattr(ytdlp_manager, "_find_installed_runtime", lambda: (None, None))
    monkeypatch.setattr(
        ytdlp_manager, "_resolve_latest_version", lambda **kwargs: "2026.09.27.232945"
    )
    monkeypatch.setattr(
        ytdlp_manager,
        "_download_and_install",
        lambda version, source=None: calls.append((version, source))
        or "/addon/ytdlp/versions/{}".format(version),
    )

    result = ytdlp_manager.ensure_ytdlp_ready(
        allow_install=True, requested_version="latest", source="nightly"
    )

    assert result["ready"] is True
    assert calls == [("2026.09.27.232945", "nightly")]


def test_get_runtime_status_reports_the_active_source(monkeypatch):
    monkeypatch.setattr(ytdlp_manager, "_find_installed_runtime", lambda: (None, None))
    monkeypatch.setattr(
        ytdlp_manager, "_resolve_latest_version", lambda **kwargs: "2026.09.27.232945"
    )

    status = ytdlp_manager.get_runtime_status("latest", source="nightly")

    assert status["source"] == "nightly"
    assert status["latest_version"] == "2026.09.27.232945"


def _http_error(url, code):
    return urllib.error.HTTPError(url, code, "error", {}, None)


def test_install_falls_back_to_tag_archive_when_asset_is_missing(monkeypatch, tmp_path):
    downloaded = []

    def fake_download(url, *_a, **_k):
        downloaded.append(url)
        if url.endswith("/yt-dlp.tar.gz"):
            raise _http_error(url, 404)
        return b""

    monkeypatch.setattr(ytdlp_manager, "_addon_data_dir", lambda: str(tmp_path))
    monkeypatch.setattr(managed_runtime, "download_with_progress", fake_download)
    monkeypatch.setattr(
        ytdlp_manager, "_extract_yt_dlp_from_tarball", lambda data, destination: None
    )

    ytdlp_manager._download_and_install("2021.01.08", source="stable")

    assert downloaded == [
        "https://github.com/yt-dlp/yt-dlp/releases/download/2021.01.08/yt-dlp.tar.gz",
        "https://github.com/yt-dlp/yt-dlp/archive/refs/tags/2021.01.08.tar.gz",
    ]


def test_install_does_not_fall_back_for_nightly_or_other_errors(monkeypatch, tmp_path):
    monkeypatch.setattr(ytdlp_manager, "_addon_data_dir", lambda: str(tmp_path))

    def fail(url, *_a, **_k):
        raise _http_error(url, 404 if "nightly" in url else 503)

    monkeypatch.setattr(managed_runtime, "download_with_progress", fail)

    with pytest.raises(urllib.error.HTTPError):
        ytdlp_manager._download_and_install("2026.09.27.232945", source="nightly")
    with pytest.raises(urllib.error.HTTPError):
        ytdlp_manager._download_and_install("2026.08.19", source="stable")
