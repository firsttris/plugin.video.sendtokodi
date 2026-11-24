"""Smoke tests for service.py, the add-on entry point, against fake Kodi modules."""

import datetime
import importlib
import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

SERVICE_PATH = str(Path(__file__).resolve().parents[1] / "service.py")
PLUGIN_URL = "plugin://plugin.video.sendtokodi/"


class FakeInfoTag:
    def __init__(self):
        self.title = None
        self.plot = None
        self.duration = None

    def setTitle(self, _title):
        pass

    def setPlot(self, _plot):
        pass

    def setDuration(self, _duration):
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

    def setMimeType(self, _mime_type):
        pass

    def setSubtitles(self, _subtitles):
        pass

    def addContextMenuItems(self, _items):
        pass


class FakeProgress:
    def create(self, *_args):
        pass

    def update(self, *_args):
        pass

    def close(self):
        pass


@pytest.fixture
def kodi(monkeypatch, tmp_path):
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
            SORT_METHOD_NONE="none",
            addSortMethod=lambda *_args: None,
            addDirectoryItem=lambda _handle, path, listitem, **_kwargs: calls.append(
                ("addDirectoryItem", path, listitem.label)
            ),
            endOfDirectory=lambda _handle, **_kwargs: calls.append(("endOfDirectory",)),
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
    sys.modules.pop("core.history", None)
    history = importlib.import_module("core.history")
    # Every playback is recorded into a per-test history file, so the tests stay
    # isolated from each other and from the machine's real add-on data.
    history_path = str(tmp_path / "history.json")
    monkeypatch.setattr(history, "_history_path", lambda: history_path)
    from core import deno_manager

    monkeypatch.setattr(deno_manager, "get_ydl_opts", lambda **_kwargs: {})

    def run(paramstring):
        monkeypatch.setattr(sys, "argv", [PLUGIN_URL, "1", paramstring])
        # exec keeps sys.argv untouched; runpy would replace sys.argv[0] with
        # the script path, while Kodi passes the plugin:// url there.
        with open(SERVICE_PATH, encoding="utf-8") as service_file:
            service_source = service_file.read()
        exec(
            compile(service_source, SERVICE_PATH, "exec"),
            {"__name__": "__main__", "__file__": SERVICE_PATH},
        )

    yield SimpleNamespace(calls=calls, extract=extract, run=run, history_path=history_path)

    for name in ("core.runtime.actions", "core.runtime.playback"):
        sys.modules.pop(name, None)


def _history_file(tmp_path):
    return tmp_path / "history.json"


def _write_history(tmp_path, entries):
    _history_file(tmp_path).write_text(json.dumps({"version": 1, "entries": entries}))


def _history_entry(entry_id, **overrides):
    entry = {
        "id": entry_id,
        "url": "https://example.invalid/watch",
        "title": "Video",
        "thumbnail": None,
        "extractor": "test",
        "duration": 12.0,
        "kind": "video",
        "played_at": 1,
    }
    entry.update(overrides)
    return entry


def _single_video_result(**overrides):
    video_url = "https://example.invalid/video.mp4"
    result = {
        "title": "Video",
        "url": video_url,
        "webpage_url": "https://example.invalid/watch",
        "formats": [{"url": video_url, "vcodec": "avc1", "acodec": "mp4a", "protocol": "https", "format": "18"}],
    }
    result.update(overrides)
    return result


def test_without_parameters_shows_the_history_list(kodi):
    kodi.run("")

    assert kodi.calls == [
        ("addDirectoryItem", PLUGIN_URL + "?action=noop", "No recent playback"),
        ("addDirectoryItem", PLUGIN_URL + "?action=settings", "Settings"),
        ("endOfDirectory",),
    ]


def test_history_entries_are_listed_in_file_order(kodi, tmp_path):
    _write_history(tmp_path, [_history_entry("second"), _history_entry("first")])

    kodi.run("")

    assert kodi.calls == [
        ("addDirectoryItem", PLUGIN_URL + "?action=replay&id=second", "Video"),
        ("addDirectoryItem", PLUGIN_URL + "?action=replay&id=first", "Video"),
        ("addDirectoryItem", PLUGIN_URL + "?action=settings", "Settings"),
        ("endOfDirectory",),
    ]


def test_settings_action_opens_settings_and_rerenders_the_list(kodi):
    kodi.run("?action=settings")

    assert kodi.calls == [
        ("openSettings",),
        ("addDirectoryItem", PLUGIN_URL + "?action=noop", "No recent playback"),
        ("addDirectoryItem", PLUGIN_URL + "?action=settings", "Settings"),
        ("endOfDirectory",),
    ]


def test_replay_resolves_the_stored_page_url_through_the_normal_path(kodi, tmp_path):
    _write_history(tmp_path, [_history_entry("abc")])
    kodi.extract["result"] = _single_video_result()

    kodi.run("?action=replay&id=abc")

    assert kodi.calls == [
        ("configure",),
        ("extract", "https://example.invalid/watch"),
        ("resolved", True, "https://example.invalid/video.mp4"),
        ("update",),
    ]


def test_replay_without_an_id_reports_an_error(kodi):
    kodi.run("?action=replay")

    assert ("notification", "Missing history entry id") in kodi.calls
    # The playable item is resolved as failed so Kodi does not wait for it.
    assert [call for call in kodi.calls if call[0] == "resolved"] == [("resolved", False, None)]


def test_replay_of_an_unknown_entry_reports_an_error(kodi, tmp_path):
    _write_history(tmp_path, [_history_entry("abc")])

    kodi.run("?action=replay&id=unknown")

    assert ("notification", "Unknown history entry") in kodi.calls
    assert [call for call in kodi.calls if call[0] == "resolved"] == [("resolved", False, None)]
    assert not [call for call in kodi.calls if call[0] == "extract"]
    assert ("update",) in kodi.calls


def test_a_successful_play_is_recorded_in_the_history(kodi, tmp_path):
    kodi.extract["result"] = _single_video_result(title="Recorded", extractor="test", duration=33.0)

    kodi.run("?https://example.invalid/watch")

    entries = json.loads(_history_file(tmp_path).read_text())["entries"]
    assert len(entries) == 1
    assert entries[0]["url"] == "https://example.invalid/watch"
    assert entries[0]["title"] == "Recorded"
    assert entries[0]["extractor"] == "test"
    assert entries[0]["duration"] == 33.0
    assert set(entries[0]) == {"id", "url", "title", "thumbnail", "extractor", "duration", "kind", "played_at"}


def test_a_failed_play_records_nothing(kodi, tmp_path):
    kodi.extract["error"] = RuntimeError("unsupported url")

    kodi.run("?https://example.invalid/broken")

    assert ("notification", "Could not resolve the url, check the log for more info") in kodi.calls
    assert not _history_file(tmp_path).exists()


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
