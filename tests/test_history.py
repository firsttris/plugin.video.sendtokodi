"""Tests for the persistent playback history (core/history.py)."""

import importlib
import json
import sys
import types

import pytest


def _load_history_module(monkeypatch):
    xbmc = types.SimpleNamespace(LOGDEBUG=0, LOGINFO=1, LOGWARNING=2, LOGERROR=3, log=lambda *_args: None)
    xbmcvfs = types.SimpleNamespace(translatePath=lambda path: path)

    monkeypatch.setitem(sys.modules, 'xbmc', xbmc)
    monkeypatch.setitem(sys.modules, 'xbmcvfs', xbmcvfs)

    sys.modules.pop('core.history', None)
    return importlib.import_module('core.history')


@pytest.fixture
def history_setup(tmp_path, monkeypatch):
    """core.history loaded with fake Kodi modules and a history file in tmp_path."""
    history = _load_history_module(monkeypatch)
    addon_data = tmp_path / "addon_data"
    monkeypatch.setattr(history, "_history_path", lambda: str(addon_data / "history.json"))

    def write_file(content):
        addon_data.mkdir(parents=True, exist_ok=True)
        (addon_data / "history.json").write_text(content)

    def read_entries():
        return json.loads((addon_data / "history.json").read_text())["entries"]

    return types.SimpleNamespace(history=history, write_file=write_file, read_entries=read_entries)


def _metadata(url="https://example.invalid/watch", **overrides):
    metadata = {
        "webpage_url": url,
        "title": "Video",
        "thumbnail": "https://example.invalid/thumb.jpg",
        "extractor": "test",
        "duration": 61.5,
        "kind": "video",
    }
    metadata.update(overrides)
    return metadata


def test_missing_file_means_empty_history(history_setup):
    assert history_setup.history.list_entries() == []
    assert history_setup.history.get("whatever") is None


def test_invalid_json_means_empty_history(history_setup):
    history_setup.write_file("not json")

    assert history_setup.history.list_entries() == []


def test_record_adds_an_entry_with_the_documented_fields(history_setup):
    entry_id = history_setup.history.record(_metadata(), manifest_id="a" * 32, timestamp=1000)

    assert entry_id == history_setup.history._entry_id("https://example.invalid/watch")
    entries = history_setup.history.list_entries()
    assert len(entries) == 1
    assert entries[0] == {
        "id": entry_id,
        "url": "https://example.invalid/watch",
        "title": "Video",
        "thumbnail": "https://example.invalid/thumb.jpg",
        "extractor": "test",
        "duration": 61.5,
        "kind": "video",
        "played_at": 1000,
        "manifest_id": "a" * 32,
    }


def test_record_without_a_page_url_is_skipped(history_setup):
    assert history_setup.history.record({"title": "No url"}) is None
    assert history_setup.history.list_entries() == []


def test_record_prefers_webpage_url_over_url(history_setup):
    entry_id = history_setup.history.record({"url": "https://a", "webpage_url": "https://b"})
    assert history_setup.history.get(entry_id)["url"] == "https://b"


def test_record_without_a_title_falls_back_to_the_url(history_setup):
    history_setup.history.record(_metadata(title=None))
    assert history_setup.history.list_entries()[0]["title"] == "https://example.invalid/watch"


def test_record_defaults_to_kind_video(history_setup):
    history_setup.history.record(_metadata(kind=None))
    assert history_setup.history.list_entries()[0]["kind"] == "video"


def test_replaying_the_same_url_moves_the_entry_to_the_top(history_setup):
    history_setup.history.record(_metadata(url="https://a"), timestamp=1000)
    history_setup.history.record(_metadata(url="https://b", title="Second"), timestamp=2000)
    history_setup.history.record(_metadata(url="https://a", title="First again"), timestamp=3000)

    entries = history_setup.history.list_entries()
    assert [entry["url"] for entry in entries] == ["https://a", "https://b"]
    assert entries[0]["played_at"] == 3000
    assert entries[0]["title"] == "First again"


def test_replay_keeps_the_downloaded_marker(history_setup):
    entry_id = history_setup.history.record(_metadata(url="https://a"), timestamp=1000)
    history_setup.history.mark_downloaded(entry_id, timestamp=1500)

    history_setup.history.record(_metadata(url="https://a", title="Replayed"), timestamp=2500)

    entry = history_setup.history.list_entries()[0]
    assert entry["downloaded_at"] == 1500
    assert entry["title"] == "Replayed"


def test_get_returns_a_copy(history_setup):
    entry_id = history_setup.history.record(_metadata())
    entry = history_setup.history.get(entry_id)
    entry["title"] = "mutated"
    assert history_setup.history.get(entry_id)["title"] == "Video"


def test_mark_downloaded_sets_the_marker_and_moves_to_the_top(history_setup):
    history_setup.history.record(_metadata(url="https://a"), timestamp=1000)
    history_setup.history.record(_metadata(url="https://b"), timestamp=2000)
    first_id = history_setup.history._entry_id("https://a")

    assert history_setup.history.mark_downloaded(first_id, timestamp=2500) is True

    entries = history_setup.history.list_entries()
    assert [entry["url"] for entry in entries] == ["https://a", "https://b"]
    assert entries[0]["downloaded_at"] == 2500


def test_mark_downloaded_unknown_entry(history_setup):
    history_setup.history.record(_metadata())
    assert history_setup.history.mark_downloaded("unknown") is False


def test_write_failure_is_tolerated(history_setup, monkeypatch):
    history = history_setup.history

    def failing_replace(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(history.os, "replace", failing_replace)

    # The record call does not raise; playback keeps working.
    assert history.record(_metadata()) is not None


def test_malformed_entries_are_dropped(history_setup):
    history_setup.write_file(json.dumps({"version": 1, "entries": [
        {"id": "ok", "url": "https://a"},
        {"id": "bad"},
        "junk",
        42,
    ]}))

    entries = history_setup.history.list_entries()

    assert [entry["id"] for entry in entries] == ["ok"]
