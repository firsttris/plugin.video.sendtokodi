import io
import os
import sys
import tarfile
import json

from core import ytdlp_manager


def _build_tarball_with_package(root_name="yt-dlp-test"):
    buff = io.BytesIO()
    with tarfile.open(fileobj=buff, mode="w:gz") as tf:
        init_data = b"__version__ = 'test'\n"
        info = tarfile.TarInfo(name=root_name + "/yt_dlp/__init__.py")
        info.size = len(init_data)
        tf.addfile(info, io.BytesIO(init_data))

        module_data = b"def value():\n    return 1\n"
        info2 = tarfile.TarInfo(name=root_name + "/yt_dlp/version.py")
        info2.size = len(module_data)
        tf.addfile(info2, io.BytesIO(module_data))
    return buff.getvalue()


def test_normalize_requested_version_defaults_to_latest():
    assert ytdlp_manager._normalize_requested_version("") == ytdlp_manager.YTDLP_LATEST_SENTINEL
    assert ytdlp_manager._normalize_requested_version("latest") == ytdlp_manager.YTDLP_LATEST_SENTINEL


def test_write_and_read_installed_version(monkeypatch, tmp_path):
    version_file = tmp_path / "ytdlp_version.txt"
    monkeypatch.setattr(ytdlp_manager, "_installed_version_file", lambda: str(version_file))
    monkeypatch.setattr(ytdlp_manager, "_addon_data_dir", lambda: str(tmp_path))

    ytdlp_manager._write_installed_version("2026.03.26")

    assert ytdlp_manager._read_installed_version() == "2026.03.26"


def test_find_installed_runtime_from_version_file(monkeypatch, tmp_path):
    runtime_path = tmp_path / "versions" / "2026.03.26"
    package_path = runtime_path / "yt_dlp"
    package_path.mkdir(parents=True)
    (package_path / "__init__.py").write_text("__version__ = 'x'\n")

    monkeypatch.setattr(ytdlp_manager, "_read_installed_version", lambda: "2026.03.26")
    monkeypatch.setattr(ytdlp_manager, "_runtime_path_for_version", lambda _v: str(runtime_path))

    version, runtime = ytdlp_manager._find_installed_runtime()

    assert version == "2026.03.26"
    assert runtime == str(runtime_path)


def test_extract_yt_dlp_from_tarball(monkeypatch, tmp_path):
    tarball = _build_tarball_with_package("yt-dlp-2026.03.26")
    destination = tmp_path / "versions" / "2026.03.26"

    ytdlp_manager._extract_yt_dlp_from_tarball(tarball, str(destination))

    assert os.path.isfile(destination / "yt_dlp" / "__init__.py")
    assert os.path.isfile(destination / "yt_dlp" / "version.py")


def test_ensure_ready_returns_missing_when_no_install_and_autodownload_off(monkeypatch):
    monkeypatch.setattr(ytdlp_manager, "_find_installed_runtime", lambda: (None, None))

    result = ytdlp_manager.ensure_ytdlp_ready(allow_install=False, requested_version="latest")

    assert result["ready"] is False
    assert result["reason"] == "missing"


def test_ensure_ready_downloads_when_missing(monkeypatch):
    monkeypatch.setattr(ytdlp_manager, "_find_installed_runtime", lambda: (None, None))
    monkeypatch.setattr(ytdlp_manager, "_resolve_latest_version", lambda: "2026.03.26")
    monkeypatch.setattr(
        ytdlp_manager,
        "_download_and_install",
        lambda version: "/addon/ytdlp/versions/{}".format(version),
    )

    result = ytdlp_manager.ensure_ytdlp_ready(allow_install=True, requested_version="latest")

    assert result["ready"] is True
    assert result["version"] == "2026.03.26"
    assert result["runtime_path"] == "/addon/ytdlp/versions/2026.03.26"


def test_ensure_ready_reports_mismatch_without_autodownload(monkeypatch):
    monkeypatch.setattr(
        ytdlp_manager,
        "_find_installed_runtime",
        lambda: ("2026.03.10", "/addon/ytdlp/versions/2026.03.10"),
    )

    result = ytdlp_manager.ensure_ytdlp_ready(allow_install=False, requested_version="2026.03.26")

    assert result["ready"] is False
    assert result["reason"] == "version_mismatch"
    assert result["installed_version"] == "2026.03.10"


def test_activate_runtime_prepends_to_sys_path():
    test_path = "/tmp/sendtokodi-ytdlp"
    original = list(sys.path)
    try:
        if test_path in sys.path:
            sys.path.remove(test_path)

        ytdlp_manager.activate_runtime(test_path)

        assert sys.path[0] == test_path
    finally:
        sys.path[:] = original


def test_get_runtime_status_reports_versions(monkeypatch):
    monkeypatch.setattr(
        ytdlp_manager,
        "_find_installed_runtime",
        lambda: ("2026.03.10", "/addon/ytdlp/versions/2026.03.10"),
    )
    monkeypatch.setattr(ytdlp_manager, "_resolve_latest_version", lambda: "2026.03.26")
    monkeypatch.setattr(
        ytdlp_manager,
        "list_installed_versions",
        lambda: ["2026.03.10", "2026.03.01"],
    )

    status = ytdlp_manager.get_runtime_status("latest")

    assert status["requested_version"] == "latest"
    assert status["installed_version"] == "2026.03.10"
    assert status["installed_versions"] == ["2026.03.10", "2026.03.01"]
    assert status["latest_version"] == "2026.03.26"
    assert status["is_latest_installed"] is False


def test_ensure_ready_switches_to_existing_requested_version_without_download(monkeypatch):
    monkeypatch.setattr(
        ytdlp_manager,
        "_find_installed_runtime",
        lambda: ("2026.03.10", "/addon/ytdlp/versions/2026.03.10"),
    )
    monkeypatch.setattr(ytdlp_manager, "_resolve_latest_version", lambda: "2026.03.26")
    monkeypatch.setattr(
        ytdlp_manager,
        "_find_runtime_for_version",
        lambda version: "/addon/ytdlp/versions/{}".format(version)
        if version == "2026.03.26"
        else None,
    )

    writes = []
    monkeypatch.setattr(ytdlp_manager, "_write_installed_version", lambda version: writes.append(version))
    monkeypatch.setattr(
        ytdlp_manager,
        "_download_and_install",
        lambda _version: (_ for _ in ()).throw(AssertionError("download should not run")),
    )

    result = ytdlp_manager.ensure_ytdlp_ready(allow_install=True, requested_version="2026.03.26")

    assert result["ready"] is True
    assert result["version"] == "2026.03.26"
    assert result["runtime_path"] == "/addon/ytdlp/versions/2026.03.26"
    assert writes == ["2026.03.26"]


def test_get_runtime_status_handles_latest_lookup_error(monkeypatch):
    monkeypatch.setattr(ytdlp_manager, "_find_installed_runtime", lambda: (None, None))
    monkeypatch.setattr(
        ytdlp_manager,
        "_resolve_latest_version",
        lambda: (_ for _ in ()).throw(RuntimeError("network error")),
    )

    status = ytdlp_manager.get_runtime_status("2026.03.01")

    assert status["requested_version"] == "2026.03.01"
    assert status["latest_version"] is None
    assert status["latest_error"] == "network error"


def test_ensure_ready_falls_back_to_installed_runtime_on_error(monkeypatch):
    calls = [
        ("2026.03.10", "/addon/ytdlp/versions/2026.03.10"),
        ("2026.03.10", "/addon/ytdlp/versions/2026.03.10"),
    ]
    monkeypatch.setattr(ytdlp_manager, "_find_installed_runtime", lambda: calls.pop(0))
    monkeypatch.setattr(
        ytdlp_manager,
        "_resolve_latest_version",
        lambda: (_ for _ in ()).throw(RuntimeError("rate limit exceeded")),
    )

    result = ytdlp_manager.ensure_ytdlp_ready(allow_install=True, requested_version="latest")

    assert result["ready"] is True
    assert result["version"] == "2026.03.10"
    assert result["runtime_path"] == "/addon/ytdlp/versions/2026.03.10"
    assert result["error"] == "rate limit exceeded"


def test_list_available_versions(monkeypatch):
    payload = [
        {"tag_name": "2026.03.26"},
        {"tag_name": "2026.03.20"},
    ]

    class FakeResponse:
        def __init__(self, body):
            self._body = body

        def read(self):
            return self._body

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    body = json.dumps(payload).encode("utf-8")
    monkeypatch.setattr(
        ytdlp_manager.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: FakeResponse(body),
    )

    versions = ytdlp_manager.list_available_versions(limit=10)

    assert versions == ["2026.03.26", "2026.03.20"]
