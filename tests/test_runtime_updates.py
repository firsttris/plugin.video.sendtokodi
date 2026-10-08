"""Runtimes are used without network access before playback and updated afterwards."""

import importlib
import sys
from types import SimpleNamespace

import pytest

from core import deno_manager, ytdlp_manager


def _explode(*_args, **_kwargs):
    raise AssertionError("must not run before playback")


@pytest.fixture
def actions(monkeypatch):
    calls = []
    settings = {
        "ytdlp_source": "stable",
        "ytdlp_autodownload": "true",
        "deno_autodownload": "true",
        "js_runtime_mode": "auto",
    }
    monkeypatch.setitem(
        sys.modules,
        "xbmc",
        SimpleNamespace(LOGINFO=1, LOGWARNING=2, LOGERROR=3, log=lambda *_a: None),
    )
    monkeypatch.setitem(
        sys.modules,
        "xbmcgui",
        SimpleNamespace(
            NOTIFICATION_WARNING=1,
            Dialog=lambda: SimpleNamespace(
                notification=lambda *_a: calls.append(("notification",)),
                yesno=lambda *_a: calls.append(("yesno",)) or False,
            ),
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "xbmcaddon",
        SimpleNamespace(
            Addon=lambda: SimpleNamespace(
                setSetting=lambda key, value: calls.append(("setSetting", key, value))
            )
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "xbmcplugin",
        SimpleNamespace(getSetting=lambda _handle, key: settings.get(key, "")),
    )
    sys.modules.pop("core.runtime.actions", None)
    module = importlib.import_module("core.runtime.actions")
    module.calls = calls
    module.settings = settings
    yield module
    sys.modules.pop("core.runtime.actions", None)


def _install_ytdlp(monkeypatch, version):
    path = "/addon/ytdlp/versions/{}".format(version)
    monkeypatch.setattr(ytdlp_manager, "_find_installed_runtime", lambda: (version, path))
    monkeypatch.setattr(
        ytdlp_manager,
        "_find_runtime_for_version",
        lambda v: path if v == version else None,
    )
    return path


def test_configure_uses_installed_ytdlp_without_network(actions, monkeypatch):
    path = _install_ytdlp(monkeypatch, "2026.08.19")
    monkeypatch.setattr(ytdlp_manager, "_resolve_latest_version", _explode)
    monkeypatch.setattr(ytdlp_manager, "_download_and_install", _explode)
    activated = []
    monkeypatch.setattr(ytdlp_manager, "activate_runtime", activated.append)

    actions.configure_managed_ytdlp(0, lambda *_a: None)

    assert activated == [path]
    assert ("setSetting", "ytdlp_installed_version_display", "2026.08.19") in actions.calls


def test_configure_installs_right_away_when_nothing_is_installed(actions, monkeypatch):
    monkeypatch.setattr(ytdlp_manager, "_find_installed_runtime", lambda: (None, None))
    monkeypatch.setattr(ytdlp_manager, "_resolve_latest_version", lambda **_k: "2026.08.19")
    installs = []
    monkeypatch.setattr(
        ytdlp_manager,
        "_download_and_install",
        lambda version, **kwargs: installs.append((version, kwargs)) or "/addon/ytdlp/versions/" + version,
    )
    monkeypatch.setattr(ytdlp_manager, "activate_runtime", lambda _path: None)

    actions.configure_managed_ytdlp(0, lambda *_a: None)

    assert [version for version, _kwargs in installs] == ["2026.08.19"]
    assert installs[0][1]["show_progress"] is True


def test_update_after_playback_installs_newer_ytdlp_silently(actions, monkeypatch):
    _install_ytdlp(monkeypatch, "2026.08.19")
    monkeypatch.setattr(ytdlp_manager, "_resolve_latest_version", lambda **_k: "2026.09.30")
    installs = []
    monkeypatch.setattr(
        ytdlp_manager,
        "_download_and_install",
        lambda version, **kwargs: installs.append((version, kwargs)) or "/addon/ytdlp/versions/" + version,
    )
    monkeypatch.setattr(deno_manager, "update_installed_runtime", lambda **_k: None)
    logs = []

    actions.update_runtimes_after_playback(0, lambda msg, *_a: logs.append(msg))

    assert installs == [("2026.09.30", {"source": "stable", "show_progress": False})]
    assert ("setSetting", "ytdlp_installed_version_display", "2026.09.30") in actions.calls
    assert any("used from the next playback" in msg for msg in logs)


def test_update_after_playback_respects_settings(actions, monkeypatch):
    actions.settings["ytdlp_autodownload"] = "false"
    actions.settings["js_runtime_mode"] = "quickjs"
    monkeypatch.setattr(ytdlp_manager, "ensure_ytdlp_ready", _explode)
    monkeypatch.setattr(deno_manager, "update_installed_runtime", _explode)

    actions.update_runtimes_after_playback(0, lambda *_a: None)

    actions.settings["ytdlp_autodownload"] = "true"
    actions.settings["ytdlp_source"] = "system"
    actions.settings["js_runtime_mode"] = "auto"
    actions.settings["deno_autodownload"] = "false"

    actions.update_runtimes_after_playback(0, lambda *_a: None)


def test_update_after_playback_updates_deno_and_survives_errors(actions, monkeypatch):
    def broken(**_kwargs):
        raise RuntimeError("GitHub unreachable")

    monkeypatch.setattr(ytdlp_manager, "ensure_ytdlp_ready", broken)
    monkeypatch.setattr(ytdlp_manager, "get_runtime_status", lambda *_a, **_k: {})
    monkeypatch.setattr(
        deno_manager, "update_installed_runtime", lambda **kwargs: kwargs["show_progress"] is False and "v2.8.0"
    )
    logs = []

    actions.update_runtimes_after_playback(0, lambda msg, *_a: logs.append(msg))

    assert any("Could not update yt-dlp: GitHub unreachable" in msg for msg in logs)
    assert ("setSetting", "deno_installed_version_display", "v2.8.0") in actions.calls


# --- Deno manager -----------------------------------------------------------


def test_deno_prefer_installed_skips_latest_lookup(monkeypatch):
    monkeypatch.setattr(deno_manager, "_find_installed_runtime", lambda: ("v2.7.5", "/addon/deno/v2.7.5/deno"))
    monkeypatch.setattr(deno_manager, "_resolve_latest_version", _explode)
    monkeypatch.setattr(deno_manager, "_download_deno", _explode)

    opts = deno_manager.get_ydl_opts(auto_download=True, prefer_installed=True)

    assert opts["js_runtimes"]["deno"]["path"] == "/addon/deno/v2.7.5/deno"


def test_deno_prefer_installed_uses_system_deno_without_lookup(monkeypatch):
    monkeypatch.setattr(deno_manager, "_find_installed_runtime", lambda: (None, None))
    monkeypatch.setattr(deno_manager, "_find_in_path", lambda: "/usr/bin/deno")
    monkeypatch.setattr(deno_manager, "_resolve_latest_version", _explode)

    opts = deno_manager.get_ydl_opts(auto_download=True, prefer_installed=True)

    assert opts["js_runtimes"]["deno"]["path"] == "/usr/bin/deno"


def test_deno_prefer_installed_still_downloads_when_nothing_is_available(monkeypatch):
    monkeypatch.setattr(deno_manager, "_find_installed_runtime", lambda: (None, None))
    monkeypatch.setattr(deno_manager, "_find_in_path", lambda: None)
    monkeypatch.setattr(deno_manager, "_resolve_latest_version", lambda **_k: "v2.7.5")
    monkeypatch.setattr(deno_manager, "_download_deno", lambda **_k: "/addon/deno/v2.7.5/deno")

    opts = deno_manager.get_ydl_opts(auto_download=True, prefer_installed=True)

    assert opts["js_runtimes"]["deno"]["path"] == "/addon/deno/v2.7.5/deno"


def test_deno_update_installed_runtime(monkeypatch, tmp_path):
    old_binary = tmp_path / "deno" / "versions" / "v2.7.5" / "deno"
    old_binary.parent.mkdir(parents=True)
    old_binary.write_bytes(b"")
    old_binary.chmod(0o755)
    deno_manager._set_installed_version("v2.7.5")
    monkeypatch.setattr(deno_manager, "_resolve_latest_version", lambda **_k: "v2.8.0")
    downloads = []

    def fake_download(show_progress, version):
        downloads.append((show_progress, version))
        deno_manager._set_installed_version(version)
        return "/addon/deno/{}/deno".format(version)

    monkeypatch.setattr(deno_manager, "_download_deno", fake_download)

    assert deno_manager.update_installed_runtime() == "v2.8.0"
    assert downloads == [(False, "v2.8.0")]


def test_deno_update_installed_runtime_ignores_system_or_missing_deno(monkeypatch):
    monkeypatch.setattr(deno_manager, "_find_in_path", lambda: "/usr/bin/deno")
    monkeypatch.setattr(deno_manager, "_resolve_latest_version", _explode)
    monkeypatch.setattr(deno_manager, "_download_deno", _explode)

    assert deno_manager.update_installed_runtime() is None
