# -*- coding: utf-8 -*-
"""SponsorBlock support: fetch the skip segments of a YouTube video and decide when to skip.

Kodi plays the stream itself, so nothing can be cut out of it. Instead the plugin
remembers which YouTube video it resolved, and sponsorblock_service.py watches the
playback and seeks over the segments.
"""
import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request


DEFAULT_API_URL = 'https://sponsor.ajay.app'
# Window property that hands the resolved video from the plugin to the service.
PLAYBACK_PROPERTY = 'plugin.video.sendtokodi.sponsorblock'
# ListItem property with the YouTube video id of the resolved item.
VIDEO_ID_PROPERTY = 'sendtokodi.youtube_id'
SPONSORBLOCK_EXTRACTOR_KEY = 'Youtube'
REQUEST_TIMEOUT_SECONDS = 5
# Segments closer than this are skipped in one seek.
MERGE_GAP_SECONDS = 1.0
# Do not seek for the last moment of a segment, it would only cause a stutter.
MIN_REMAINING_SECONDS = 0.5

# https://wiki.sponsor.ajay.app/w/Types, with whether each is skipped by default.
CATEGORIES = (
    ('sponsor', True),
    ('selfpromo', True),
    ('interaction', True),
    ('intro', False),
    ('outro', False),
    ('preview', False),
    ('hook', False),
    ('filler', False),
    ('music_offtopic', False),
)


def category_setting_id(category):
    return 'sponsorblock_category_' + category


def resolve_sponsorblock_settings(get_setting):
    """Read the SponsorBlock settings; get_setting takes a setting id and returns its string value."""
    categories = [
        category
        for category, default in CATEGORIES
        if _is_enabled(get_setting(category_setting_id(category)), default)
    ]
    api_url = (get_setting('sponsorblock_api_url') or '').strip().rstrip('/') or DEFAULT_API_URL
    if '://' not in api_url:
        api_url = 'https://' + api_url
    return {
        'enabled': get_setting('sponsorblock_enabled') == 'true' and bool(categories),
        'categories': categories,
        'notify': _is_enabled(get_setting('sponsorblock_notify'), True),
        'api_url': api_url,
    }


def _is_enabled(value, default):
    if value in ('true', 'false'):
        return value == 'true'
    return default


def resolve_youtube_video_id(result):
    """Return the YouTube video id of a yt-dlp result, or None for other sites."""
    if result.get('extractor_key') != SPONSORBLOCK_EXTRACTOR_KEY:
        return None
    video_id = result.get('id')
    return str(video_id) if video_id else None


def normalize_playing_path(path):
    # Kodi keeps the "|header=value" suffix of a url as part of the path.
    return (path or '').split('|', 1)[0]


def encode_playback(path, video_id):
    return json.dumps({'path': normalize_playing_path(path), 'video_id': video_id})


def resolve_playing_video_id(item_video_id, playing_path, published_playback):
    """Return the video id of the current playback, or None when SendToKodi did not resolve it.

    item_video_id is the ListItem property of the playing item; published_playback the
    window property the plugin wrote, which only counts when its path is the playing one.
    """
    if item_video_id:
        return item_video_id
    try:
        published = json.loads(published_playback or '')
    except ValueError:
        return None
    if not isinstance(published, dict) or not published.get('video_id'):
        return None
    if published.get('path') != normalize_playing_path(playing_path):
        return None
    return published['video_id']


def build_segments_url(video_id, categories, api_url=DEFAULT_API_URL):
    # Only the first characters of the hash are sent, so the server does not learn which video plays.
    video_hash = hashlib.sha256(video_id.encode('utf-8')).hexdigest()
    query = urllib.parse.urlencode({
        'categories': json.dumps(list(categories)),
        'actionTypes': json.dumps(['skip']),
        'service': 'YouTube',
    })
    return '{}/api/skipSegments/{}?{}'.format(api_url, video_hash[:4], query)


def parse_segments(payload, video_id, categories):
    """Return the sorted, merged (start, end) skip segments of video_id from an API response."""
    segments = []
    for video in payload if isinstance(payload, list) else []:
        if not isinstance(video, dict) or video.get('videoID') != video_id:
            continue
        for segment in video.get('segments') or []:
            if segment.get('category') not in categories or segment.get('actionType', 'skip') != 'skip':
                continue
            try:
                start, end = (float(value) for value in segment['segment'])
            except (KeyError, TypeError, ValueError):
                continue
            if end > start:
                segments.append((start, end))
    return merge_segments(segments)


def merge_segments(segments):
    merged = []
    for start, end in sorted(segments):
        if merged and start <= merged[-1][1] + MERGE_GAP_SECONDS:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def fetch_skip_segments(video_id, categories, api_url=DEFAULT_API_URL, urlopen=urllib.request.urlopen):
    request = urllib.request.Request(
        build_segments_url(video_id, categories, api_url),
        headers={'User-Agent': 'plugin.video.sendtokodi'},
    )
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        # 404 means that no video with this hash prefix has segments.
        if exc.code == 404:
            return []
        raise
    return parse_segments(payload, video_id, categories)


class SegmentSkipper:
    """Decide where to seek; every segment is skipped once, so seeking back into one plays it."""

    def __init__(self, segments):
        self._segments = list(segments)
        self._skipped = set()

    def seek_target(self, current_time):
        for index, (start, end) in enumerate(self._segments):
            if index in self._skipped:
                continue
            if start <= current_time < end - MIN_REMAINING_SECONDS:
                self._skipped.add(index)
                return end
        return None
