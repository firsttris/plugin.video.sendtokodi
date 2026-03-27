import pytest
import io
import os
import sys
import zipfile
from types import SimpleNamespace

from core import deno_manager


def test_detect_platform_supported(monkeypatch):
    monkeypatch.setattr(deno_manager.platform, "system", lambda: "Linux")
    monkeypatch.setattr(deno_manager.platform, "machine", lambda: "x86_64")

    assert deno_manager._detect_platform() == ("linux", "x86_64")


def test_detect_platform_unsupported(monkeypatch):
    monkeypatch.setattr(deno_manager.platform, "system", lambda: "Plan9")
    monkeypatch.setattr(deno_manager.platform, "machine", lambda: "mips")

    with pytest.raises(RuntimeError):
        deno_manager._detect_platform()


def test_deno_binary_name_windows(monkeypatch):
    monkeypatch.setattr(deno_manager.platform, "system", lambda: "Windows")
    assert deno_manager._deno_binary_name() == "deno.exe"


def test_deno_binary_name_posix(monkeypatch):
    monkeypatch.setattr(deno_manager.platform, "system", lambda: "Linux")
    assert deno_manager._deno_binary_name() == "deno"


def test_get_and_set_installed_version(monkeypatch, tmp_path):
    version_file = tmp_path / "deno_version.txt"
    monkeypatch.setattr(deno_manager, "_version_file", lambda: str(version_file))

    deno_manager._set_installed_version("v-test")

    assert deno_manager._get_installed_version() == "v-test"


def test_get_ydl_opts_prefers_existing_addon_binary(monkeypatch):
    monkeypatch.setattr(deno_manager, "_find_in_addon_data", lambda: "/addon/deno")
    monkeypatch.setattr(deno_manager, "_get_installed_version", lambda: deno_manager.DENO_VERSION)
    monkeypatch.setattr(deno_manager, "_find_in_path", lambda: None)
    monkeypatch.setattr(
        deno_manager,
        "_download_deno",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("download should not run")),
    )

    opts = deno_manager.get_ydl_opts(auto_download=True)

    assert opts["js_runtimes"]["deno"]["path"] == "/addon/deno"
    assert opts["remote_components"] == {"ejs:github"}


def test_get_ydl_opts_updates_on_version_mismatch(monkeypatch):
    monkeypatch.setattr(deno_manager, "_find_in_addon_data", lambda: "/addon/deno")
    monkeypatch.setattr(deno_manager, "_get_installed_version", lambda: "old-version")
    monkeypatch.setattr(deno_manager, "_addon_data_dir", lambda: "/addon")
    monkeypatch.setattr(deno_manager, "_download_deno", lambda *_args, **_kwargs: "/addon/deno-new")

    opts = deno_manager.get_ydl_opts(auto_download=True)

    assert opts["js_runtimes"]["deno"]["path"] == "/addon/deno-new"


def test_get_ydl_opts_uses_system_path_when_needed(monkeypatch):
    monkeypatch.setattr(deno_manager, "_find_in_addon_data", lambda: None)
    monkeypatch.setattr(deno_manager, "_find_in_path", lambda: "/usr/bin/deno")

    opts = deno_manager.get_ydl_opts(auto_download=True)

    assert opts["js_runtimes"]["deno"]["path"] == "/usr/bin/deno"


def test_get_ydl_opts_returns_empty_when_missing_and_download_disabled(monkeypatch):
    monkeypatch.setattr(deno_manager, "_find_in_addon_data", lambda: None)
    monkeypatch.setattr(deno_manager, "_find_in_path", lambda: None)

    opts = deno_manager.get_ydl_opts(auto_download=False)

    assert opts == {}


def test_get_ydl_opts_returns_empty_on_internal_error(monkeypatch):
    monkeypatch.setattr(
        deno_manager,
        "_find_in_addon_data",
        lambda: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    opts = deno_manager.get_ydl_opts(auto_download=True)

    assert opts == {}


def test_log_uses_xbmc_when_available(monkeypatch):
    calls = []
    fake_xbmc = SimpleNamespace(LOGINFO=10, LOGWARNING=20, log=lambda msg, level: calls.append((msg, level)))
    monkeypatch.setitem(sys.modules, "xbmc", fake_xbmc)

    deno_manager._log("hello")

    assert calls == [("plugin.video.sendtokodi deno_manager: hello", 10)]


def test_warn_routes_through_log_when_xbmc_available(monkeypatch):
    calls = []
    fake_xbmc = SimpleNamespace(LOGINFO=10, LOGWARNING=20, log=lambda msg, level: calls.append((msg, level)))
    monkeypatch.setitem(sys.modules, "xbmc", fake_xbmc)

    deno_manager._warn("careful")

    assert calls == [("plugin.video.sendtokodi deno_manager: careful", 20)]


def test_addon_data_dir_uses_xbmcvfs_when_available(monkeypatch):
    fake_xbmcvfs = SimpleNamespace(translatePath=lambda _p: "/kodi/special/path")
    monkeypatch.setitem(sys.modules, "xbmcvfs", fake_xbmcvfs)

    assert deno_manager._addon_data_dir() == "/kodi/special/path"


def test_get_installed_version_returns_none_on_error(monkeypatch):
    monkeypatch.setattr(deno_manager, "_version_file", lambda: "/does/not/exist")
    assert deno_manager._get_installed_version() is None


def test_set_installed_version_warns_on_write_error(monkeypatch):
    warnings = []
    monkeypatch.setattr(deno_manager, "_version_file", lambda: "/")
    monkeypatch.setattr(deno_manager, "_warn", lambda msg: warnings.append(msg))

    deno_manager._set_installed_version("v-test")

    assert warnings


def test_find_in_addon_data_finds_executable(monkeypatch, tmp_path):
    deno_file = tmp_path / "deno"
    deno_file.write_bytes(b"#!/bin/sh\n")
    deno_file.chmod(0o755)

    monkeypatch.setattr(deno_manager, "_addon_data_dir", lambda: str(tmp_path))
    monkeypatch.setattr(deno_manager, "_deno_binary_name", lambda: "deno")

    assert deno_manager._find_in_addon_data() == str(deno_file)


def test_find_in_path_delegates_to_shutil(monkeypatch):
    monkeypatch.setattr(deno_manager.shutil, "which", lambda exe: "/usr/bin/deno" if exe == "deno" else None)
    assert deno_manager._find_in_path() == "/usr/bin/deno"


def test_download_deno_extracts_binary_and_sets_executable(monkeypatch, tmp_path):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("nested/deno", b"binary-content")
    zip_data = zip_buffer.getvalue()

    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload
            self._offset = 0
            self.headers = {"Content-Length": str(len(payload))}

        def read(self, size):
            if self._offset >= len(self._payload):
                return b""
            chunk = self._payload[self._offset:self._offset + size]
            self._offset += len(chunk)
            return chunk

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(deno_manager, "_detect_platform", lambda: ("linux", "x86_64"))
    monkeypatch.setattr(deno_manager.urllib.request, "urlopen", lambda *_args, **_kwargs: FakeResponse(zip_data))
    monkeypatch.setattr(deno_manager.platform, "system", lambda: "Linux")
    monkeypatch.setattr(deno_manager, "_deno_binary_name", lambda: "deno")

    logs = []
    monkeypatch.setattr(deno_manager, "_log", lambda msg, level=None: logs.append((msg, level)))
    set_version = []
    monkeypatch.setattr(deno_manager, "_set_installed_version", lambda version: set_version.append(version))

    dest = deno_manager._download_deno(str(tmp_path), show_progress=False)

    assert os.path.isfile(dest)
    assert open(dest, "rb").read() == b"binary-content"
    assert set_version == [deno_manager.DENO_VERSION]
    assert any("Downloading Deno" in msg for msg, _ in logs)


def test_download_deno_raises_if_binary_missing(monkeypatch, tmp_path):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("other-file", b"x")
    zip_data = zip_buffer.getvalue()

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload
            self.done = False
            self.headers = {"Content-Length": str(len(payload))}

        def read(self, _size):
            if self.done:
                return b""
            self.done = True
            return self.payload

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(deno_manager, "_detect_platform", lambda: ("linux", "x86_64"))
    monkeypatch.setattr(deno_manager.urllib.request, "urlopen", lambda *_args, **_kwargs: FakeResponse(zip_data))
    monkeypatch.setattr(deno_manager, "_deno_binary_name", lambda: "deno")

    with pytest.raises(RuntimeError):
        deno_manager._download_deno(str(tmp_path), show_progress=False)


def test_get_ydl_opts_downloads_when_missing(monkeypatch):
    monkeypatch.setattr(deno_manager, "_find_in_addon_data", lambda: None)
    monkeypatch.setattr(deno_manager, "_find_in_path", lambda: None)
    monkeypatch.setattr(deno_manager, "_addon_data_dir", lambda: "/addon")
    monkeypatch.setattr(deno_manager, "_download_deno", lambda *_args, **_kwargs: "/addon/deno")

    opts = deno_manager.get_ydl_opts(auto_download=True)

    assert opts["js_runtimes"]["deno"]["path"] == "/addon/deno"
