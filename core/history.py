# -*- coding: utf-8 -*-
"""Persistent playback history for SendToKodi.

Entries live in history.json inside the add-on's profile data, newest first,
deduplicated by page url. The file is rewritten atomically on every change; a
missing or invalid file simply means an empty history. Only successfully
resolved items are recorded; a failed write leaves the playback unaffected.
"""
import hashlib
import json
import os
import threading
import time
from tempfile import NamedTemporaryFile

import xbmc
import xbmcvfs

HISTORY_FILE = 'special://profile/addon_data/plugin.video.sendtokodi/history.json'
HISTORY_VERSION = 1

_LOCK = threading.Lock()


def _log(message, level=xbmc.LOGWARNING):
    xbmc.log('plugin.video.sendtokodi: history: {}'.format(message), level)


def _history_path():
    return xbmcvfs.translatePath(HISTORY_FILE)


def _entry_id(url):
    # Stable entry id derived from the page url.
    return hashlib.sha256(url.encode('utf-8')).hexdigest()[:16]


def _empty():
    return {'version': HISTORY_VERSION, 'entries': []}


def _load_unlocked():
    path = _history_path()
    try:
        with open(path, 'r', encoding='utf-8') as history_file:
            document = json.load(history_file)
    except FileNotFoundError:
        return _empty()
    except Exception as exc:
        _log("Could not read {}: {}".format(path, exc))
        return _empty()

    entries = document.get('entries') if isinstance(document, dict) else None
    if not isinstance(entries, list):
        _log("Ignoring malformed history file {}".format(path))
        return _empty()
    valid = [entry for entry in entries if isinstance(entry, dict) and entry.get('url')]
    if len(valid) != len(entries):
        _log("Dropped {} malformed history entries".format(len(entries) - len(valid)))
    return {'version': document.get('version', HISTORY_VERSION), 'entries': valid}


def _write_unlocked(document):
    path = _history_path()
    tmp_path = None
    try:
        directory = os.path.dirname(path)
        if directory and not os.path.isdir(directory):
            os.makedirs(directory, exist_ok=True)
        # Write next to the target, then replace atomically so a crash never
        # leaves a half-written history behind.
        with NamedTemporaryFile('w', encoding='utf-8', dir=directory or '.', delete=False, suffix='.tmp') as tmp:
            json.dump(document, tmp, ensure_ascii=False, indent=1)
            tmp_path = tmp.name
        os.replace(tmp_path, path)
    except Exception as exc:
        _log("Could not write {}: {}".format(path, exc))
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def list_entries():
    """All history entries, most recent first."""
    with _LOCK:
        return list(_load_unlocked()['entries'])


def get(history_id):
    """The entry with the given id, or None."""
    with _LOCK:
        for entry in _load_unlocked()['entries']:
            if entry.get('id') == history_id:
                return dict(entry)
    return None


def record(metadata, manifest_id=None, timestamp=None):
    """Record a successful playback; returns the entry id, or None when skipped.

    *metadata* carries at least webpage_url (the page url used for a later full
    re-resolution) plus the display fields; see playback._collect_playback_metadata.
    An existing entry for the same url is moved to the top and refreshed, keeping
    its downloaded_at marker.
    """
    metadata = metadata or {}
    url = metadata.get('webpage_url') or metadata.get('url')
    if not url:
        return None
    timestamp = time.time() if timestamp is None else timestamp
    entry_id = _entry_id(url)
    entry = {
        'id': entry_id,
        'url': url,
        'title': metadata.get('title') or url,
        'thumbnail': metadata.get('thumbnail'),
        'extractor': metadata.get('extractor'),
        'duration': metadata.get('duration'),
        'kind': metadata.get('kind') or 'video',
        'played_at': timestamp,
        'manifest_id': manifest_id,
    }
    with _LOCK:
        document = _load_unlocked()
        previous = None
        remaining = []
        for existing in document['entries']:
            if existing.get('id') == entry_id:
                previous = existing
            else:
                remaining.append(existing)
        if previous is not None and previous.get('downloaded_at') is not None:
            entry['downloaded_at'] = previous['downloaded_at']
        document['entries'] = [entry] + remaining
        _write_unlocked(document)
    return entry_id


def mark_downloaded(history_id, timestamp=None):
    """Mark an entry as downloaded and move it to the top; True on success."""
    timestamp = time.time() if timestamp is None else timestamp
    with _LOCK:
        document = _load_unlocked()
        kept = []
        target = None
        for entry in document['entries']:
            if entry.get('id') == history_id:
                target = entry
            else:
                kept.append(entry)
        if target is None:
            return False
        target['downloaded_at'] = timestamp
        document['entries'] = [target] + kept
        _write_unlocked(document)
        return True
