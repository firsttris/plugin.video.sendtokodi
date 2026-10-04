"""Tests for the system yt-dlp source in the runtime actions.

The system source never downloads anything and never rewrites the setting:
an importable yt_dlp is used as-is, a missing one is only reported.
"""

import importlib
import sys
import types
from types import SimpleNamespace

import pytest

from core import ytdlp_manager


def _fake_yt_dlp(version="2099.01.02"):
    module = types.ModuleType("yt_dlp")
    module.version = SimpleNamespace(__version__=version)
    return module


def _explode(*_args, **_kwargs):
    raise AssertionError("the system source must not download anything")


@pytest.fixture
def actions(monkeypatch):
    """Import core.runtime.actions fresh against minimal Kodi mocks."""
    calls = []

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
            NOTIFICATION_ERROR=2,
            Dialog=lambda: SimpleNamespace(
                notification=lambda _title, msg, _icon: calls.append(("notification", msg)),
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
        SimpleNamespace(
            getSetting=lambda _handle, key: {
                "ytdlp_source": "system",
                "ytdlp_autodownload": "true",
            }.get(key, "")
        ),
    )
    monkeypatch.setattr(ytdlp_manager, "_download_and_install", _explode)
    monkeypatch.setattr(ytdlp_manager, "_resolve_latest_version", _explode)
    monkeypatch.setattr(ytdlp_manager, "list_available_versions", _explode)

    sys.modules.pop("core.runtime.actions", None)
    module = importlib.import_module("core.runtime.actions")
    module.calls = calls
    yield module
    sys.modules.pop("core.runtime.actions", None)


def _source_setting_writes(calls):
    return [c for c in calls if c[0] == "setSetting" and c[1] == "ytdlp_source"]


def test_system_source_uses_importable_yt_dlp(actions, monkeypatch):
    monkeypatch.setitem(sys.modules, "yt_dlp", _fake_yt_dlp("2099.01.02"))
    log_calls = []

    actions.configure_managed_ytdlp(0, lambda msg, level: log_calls.append(msg))

    assert _source_setting_writes(actions.calls) == []
    assert not [c for c in actions.calls if c[0] in ("notification", "yesno")]
    assert ("setSetting", "ytdlp_installed_version_display", "2099.01.02") in actions.calls
    assert any("Using system yt-dlp 2099.01.02" in msg for msg in log_calls)


def test_system_source_without_library_only_reports(actions, monkeypatch):
    monkeypatch.setitem(sys.modules, "yt_dlp", None)
    log_calls = []

    actions.configure_managed_ytdlp(0, lambda msg, level: log_calls.append(msg))

    # No setting rewrite, no download prompt, just a notification.
    assert _source_setting_writes(actions.calls) == []
    assert ("yesno",) not in actions.calls
    assert [c for c in actions.calls if c[0] == "notification"] == [
        ("notification", "System yt-dlp not found (yt-dlp source: system)")
    ]
    assert any("no yt_dlp package is importable" in msg for msg in log_calls)


def test_select_version_with_system_source_shows_system_version(actions, monkeypatch):
    monkeypatch.setitem(sys.modules, "yt_dlp", _fake_yt_dlp("2099.01.02"))
    infos, errors = [], []

    actions.handle_runtime_action(
        "ytdlp_select_version", 0, _explode, infos.append, errors.append, lambda *_a: None
    )

    assert infos == ["yt-dlp 2099.01.02 is provided by the system"]
    assert errors == []


def test_update_now_with_system_source_does_not_install(actions, monkeypatch):
    monkeypatch.setitem(sys.modules, "yt_dlp", None)
    infos, errors = [], []

    actions.handle_runtime_action(
        "ytdlp_update_now", 0, _explode, infos.append, errors.append, lambda *_a: None
    )

    assert infos == []
    assert errors == ["System yt-dlp not found"]


def test_version_dialog_title_shows_the_release_channel(actions, monkeypatch):
    titles = []
    monkeypatch.setattr(
        actions.xbmcgui,
        "Dialog",
        lambda: SimpleNamespace(select=lambda title, _entries: titles.append(title) or -1),
    )

    actions._choose_runtime_version(
        "ytdlp",
        {"source": "nightly", "installed_version": "2026.08.19", "installed_versions": ["2026.08.19"]},
        lambda: ["2026.09.27.232945"],
        lambda _title, _msg, func: func(),
        lambda _msg: None,
        lambda _msg: None,
        lambda *_a: None,
    )

    assert titles == ["SendToKodi - manage yt-dlp (nightly) version"]
