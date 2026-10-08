"""Smoke tests for service.py, the add-on entry point, against fake Kodi modules."""

import datetime
import importlib
import runpy
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

SERVICE_PATH = str(Path(__file__).resolve().parents[1] / "service.py")
PLUGIN_URL = "plugin://plugin.video.sendtokodi/"


class FakeInfoTag:
    def setTitle(self, _title):
        pass

    def setPlot(self, _plot):
        pass


class FakeListItem:
    def __init__(self, label=None, path=None):
        self.label = label
        self.path = path

    def getVideoInfoTag(self):
        return FakeInfoTag()

    def getMusicInfoTag(self):
        return FakeInfoTag()

    def setArt(self, _art):
        pass

    def setProperty(self, _key, _value):
        pass

    def setPath(self, path):
        self.path = path

    def getPath(self):
        return self.path


class FakeProgress:
    def create(self, *_args):
        pass

    def update(self, *_args):
        pass

    def close(self):
        pass


@pytest.fixture
def kodi(monkeypatch):
    calls = []
    extract = {"result": None, "error": None}
    # service.py patches datetime.datetime for the whole process; undo it afterwards.
    monkeypatch.setattr(datetime, "datetime", datetime.datetime)

    def notification(_title, message, *_args):
        calls.append(("notification", message))

    fakes = {
        "xbmc": SimpleNamespace(
            LOGDEBUG=0,
            LOGINFO=1,
            LOGWARNING=2,
            LOGERROR=3,
            log=lambda *_args: None,
        ),
        "xbmcgui": SimpleNamespace(
            ListItem=FakeListItem,
            Dialog=lambda: SimpleNamespace(notification=notification),
            DialogProgress=FakeProgress,
            DialogProgressBG=FakeProgress,
            NOTIFICATION_INFO="info",
            NOTIFICATION_ERROR="error",
            NOTIFICATION_WARNING="warning",
        ),
        "xbmcplugin": SimpleNamespace(
            getSetting=lambda _handle, key: {"maxresolution": "1920"}.get(key, ""),
            setResolvedUrl=lambda _handle, ok, listitem: calls.append(("resolved", ok, listitem.getPath())),
        ),
        "xbmcaddon": SimpleNamespace(
            Addon=lambda: SimpleNamespace(
                openSettings=lambda: calls.append(("openSettings",)),
                setSetting=lambda *_args: None,
            )
        ),
        "xbmcvfs": SimpleNamespace(
            translatePath=lambda path: path,
            exists=lambda _path: False,
            mkdirs=lambda _path: True,
            copy=lambda *_args: True,
        ),
        # No InputStream Helper: only plain streams are playable.
        "inputstreamhelper": None,
    }
    for name, module in fakes.items():
        monkeypatch.setitem(sys.modules, name, module)

    class FakeYoutubeDL:
        def __init__(self, _opts):
            pass

        def add_default_info_extractors(self):
            pass

        def extract_info(self, url, download=False):
            calls.append(("extract", url))
            if extract["error"] is not None:
                raise extract["error"]
            return dict(extract["result"])

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

    yt_dlp = types.ModuleType("yt_dlp")
    yt_dlp.YoutubeDL = FakeYoutubeDL
    monkeypatch.setitem(sys.modules, "yt_dlp", yt_dlp)

    for name in ("core.runtime.actions", "core.runtime.playback"):
        sys.modules.pop(name, None)
    actions = importlib.import_module("core.runtime.actions")
    importlib.import_module("core.runtime.playback")
    monkeypatch.setattr(actions, "configure_managed_ytdlp", lambda _handle, _log: calls.append(("configure",)))
    monkeypatch.setattr(actions, "refresh_runtime_displays", lambda _handle, _log: None)
    monkeypatch.setattr(
        actions, "update_runtimes_after_playback", lambda _handle, _log: calls.append(("update",))
    )
    from core import deno_manager

    monkeypatch.setattr(deno_manager, "get_ydl_opts", lambda **_kwargs: {})

    def run(paramstring):
        monkeypatch.setattr(sys, "argv", [PLUGIN_URL, "1", paramstring])
        runpy.run_path(SERVICE_PATH, run_name="__main__")

    yield SimpleNamespace(calls=calls, extract=extract, run=run)

    for name in ("core.runtime.actions", "core.runtime.playback"):
        sys.modules.pop(name, None)


def test_without_parameters_opens_the_settings(kodi):
    kodi.run("")

    assert kodi.calls == [("openSettings",)]


def test_plays_a_direct_video_and_checks_updates_afterwards(kodi):
    video_url = "https://example.invalid/video.mp4"
    kodi.extract["result"] = {
        "title": "Video",
        "url": video_url,
        "formats": [{"url": video_url, "vcodec": "avc1", "acodec": "mp4a", "protocol": "https", "format": "18"}],
    }

    kodi.run("?https://example.invalid/watch")

    assert kodi.calls == [
        ("configure",),
        ("extract", "https://example.invalid/watch"),
        ("resolved", True, video_url),
        ("update",),
    ]


def test_failed_resolve_reports_and_still_checks_updates(kodi):
    kodi.extract["error"] = RuntimeError("unsupported url")

    kodi.run("?https://example.invalid/broken")

    assert kodi.calls == [
        ("configure",),
        ("extract", "https://example.invalid/broken"),
        ("notification", "Could not resolve the url, check the log for more info"),
        ("resolved", False, None),
        ("update",),
    ]
