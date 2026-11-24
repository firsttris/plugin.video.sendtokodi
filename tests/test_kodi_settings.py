import importlib
import sys
import types


def _load_module(monkeypatch, plugin_values, addon_values, addon_has_get_setting=True):
    plugin = types.ModuleType("xbmcplugin")
    plugin.getSetting = lambda _handle, setting_id: plugin_values.get(setting_id, "")

    addon = types.ModuleType("xbmcaddon")
    settings = types.SimpleNamespace()
    if addon_has_get_setting:
        settings.getSetting = lambda setting_id: addon_values.get(setting_id, "")
    addon.Addon = lambda *_args, **_kwargs: settings

    monkeypatch.setitem(sys.modules, "xbmcplugin", plugin)
    monkeypatch.setitem(sys.modules, "xbmcaddon", addon)
    sys.modules.pop("core.kodi_settings", None)
    return importlib.import_module("core.kodi_settings")


def test_get_setting_uses_the_handle_value_when_it_has_one(monkeypatch):
    module = _load_module(monkeypatch, {"maxresolution": "1920"}, {"maxresolution": "3840"})

    assert module.get_setting("handle", "maxresolution") == "1920"


def test_get_setting_falls_back_to_the_addon_without_a_plugin_directory(monkeypatch):
    module = _load_module(monkeypatch, {}, {"ytdlp_source": "system"})

    assert module.get_setting("handle", "ytdlp_source") == "system"


def test_get_setting_returns_the_empty_value_when_the_addon_cannot_be_read(monkeypatch):
    module = _load_module(monkeypatch, {}, {}, addon_has_get_setting=False)

    assert module.get_setting("handle", "ytdlp_source") == ""
