"""Tests for the system source fallback in configure_managed_ytdlp.

When ytdlp_source is 'system' but no yt_dlp is importable, the addon
reverts to 'stable' and notifies the user.
"""

import sys
import types
from types import SimpleNamespace

import pytest


@pytest.fixture
def kodi_mocks(monkeypatch):
    """Provide minimal Kodi module mocks."""
    calls = []

    xbmc = SimpleNamespace(
        LOGINFO=10,
        LOGWARNING=20,
        LOGERROR=40,
        log=lambda msg, level: calls.append(("log", msg, level)),
    )
    xbmcgui = SimpleNamespace(
        NOTIFICATION_WARNING=1,
        NOTIFICATION_ERROR=2,
        Dialog=lambda: SimpleNamespace(
            notification=lambda title, msg, icon: calls.append(("notification", title, msg, icon))
        ),
    )
    xbmcaddon = SimpleNamespace(
        Addon=lambda: SimpleNamespace(
            setSetting=lambda key, value: calls.append(("setSetting", key, value))
        )
    )
    xbmcplugin = SimpleNamespace(
        getSetting=lambda handle, key: {"ytdlp_source": "system"}.get(key, "")
    )

    monkeypatch.setitem(sys.modules, "xbmc", xbmc)
    monkeypatch.setitem(sys.modules, "xbmcgui", xbmcgui)
    monkeypatch.setitem(sys.modules, "xbmcaddon", xbmcaddon)
    monkeypatch.setitem(sys.modules, "xbmcplugin", xbmcplugin)

    return calls


def test_system_source_fallback_reverts_to_stable(kodi_mocks, monkeypatch):
    """When system has no importable yt_dlp, revert to stable and notify."""
    from core.runtime import actions

    # Mock ensure_ytdlp_ready to return "missing" for system
    def fake_ensure(allow_install, requested_version, source):
        if source == "system":
            return {"ready": False, "reason": "missing", "version": None, "runtime_path": None}
        return {"ready": True, "reason": None, "version": "2026.08.19", "runtime_path": "/fake/path"}

    monkeypatch.setattr(
        sys.modules["core.ytdlp_manager"],
        "ensure_ytdlp_ready",
        fake_ensure,
    )
    monkeypatch.setattr(
        sys.modules["core.ytdlp_manager"],
        "is_managed_source",
        lambda s: s != "system",
    )
    monkeypatch.setattr(
        sys.modules["core.ytdlp_manager"],
        "activate_installed_version",
        lambda v: "/fake/path",
    )

    log_calls = []
    actions.configure_managed_ytdlp(0, lambda msg, level: log_calls.append((msg, level)))

    # Check setSetting was called for ytdlp_source
    source_calls = [c for c in kodi_mocks if c[0] == "setSetting" and c[1] == "ytdlp_source"]
    assert len(source_calls) == 1
    assert source_calls[0][2] == "stable"

    # Check notification was shown
    notif_calls = [c for c in kodi_mocks if c[0] == "notification"]
    assert len(notif_calls) == 1
    assert "reverting to stable" in notif_calls[0][2]

    # Check log was emitted
    assert any("reverting to stable" in msg for msg, level in log_calls)


def test_system_source_no_fallback_when_importable(kodi_mocks, monkeypatch):
    """When system has importable yt_dlp, no fallback occurs."""
    from core.runtime import actions

    def fake_ensure(allow_install, requested_version, source):
        return {"ready": True, "reason": None, "version": "2099.01.02", "runtime_path": None}

    monkeypatch.setattr(
        sys.modules["core.ytdlp_manager"],
        "ensure_ytdlp_ready",
        fake_ensure,
    )
    monkeypatch.setattr(
        sys.modules["core.ytdlp_manager"],
        "is_managed_source",
        lambda s: s != "system",
    )

    actions.configure_managed_ytdlp(0, lambda msg, level: None)

    # No setSetting, no notification
    set_calls = [c for c in kodi_mocks if c[0] == "setSetting"]
    notif_calls = [c for c in kodi_mocks if c[0] == "notification"]
    assert len(set_calls) == 0
    assert len(notif_calls) == 0
