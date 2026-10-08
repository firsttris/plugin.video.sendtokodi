"""Runtime actions on a device where Deno cannot run (Android)."""

import importlib
import sys
from types import SimpleNamespace

import pytest

from core import deno_manager


def _explode(*_args, **_kwargs):
    raise AssertionError("Deno must not be downloaded on Android")


@pytest.fixture
def actions(monkeypatch):
    calls = []
    monkeypatch.setitem(
        sys.modules,
        "xbmc",
        SimpleNamespace(LOGINFO=1, LOGWARNING=2, LOGERROR=3, log=lambda *_a: None),
    )
    monkeypatch.setitem(sys.modules, "xbmcgui", SimpleNamespace(Dialog=_explode))
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
        SimpleNamespace(getSetting=lambda _handle, key: {"deno_autodownload": "true"}.get(key, "")),
    )
    monkeypatch.setattr(deno_manager, "_is_android", lambda: True)
    monkeypatch.setattr(deno_manager, "_download_deno", _explode)
    monkeypatch.setattr(deno_manager, "list_available_versions", _explode)

    sys.modules.pop("core.runtime.actions", None)
    module = importlib.import_module("core.runtime.actions")
    module.calls = calls
    yield module
    sys.modules.pop("core.runtime.actions", None)


@pytest.mark.parametrize("action", ["deno_update_now", "deno_select_version"])
def test_deno_actions_report_android_instead_of_downloading(actions, action):
    errors = []

    handled = actions.handle_runtime_action(
        action,
        1,
        _explode,
        _explode,
        errors.append,
        lambda *_a: None,
    )

    assert handled is True
    assert errors == ["Deno has no Android build"]
    assert ("setSetting", "deno_installed_version_display", "not installed") in actions.calls
