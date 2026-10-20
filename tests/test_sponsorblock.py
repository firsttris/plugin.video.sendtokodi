import hashlib
import importlib.util
import io
import json
import sys
import urllib.error
import urllib.parse
from pathlib import Path
from types import SimpleNamespace

import pytest

from core import sponsorblock


def _settings(values):
    return lambda key: values.get(key, '')


def test_settings_are_disabled_by_default():
    settings = sponsorblock.resolve_sponsorblock_settings(_settings({}))

    assert settings['enabled'] is False
    assert settings['categories'] == ['sponsor', 'selfpromo', 'interaction']
    assert settings['notify'] is True
    assert settings['api_url'] == sponsorblock.DEFAULT_API_URL


def test_settings_follow_the_category_toggles():
    settings = sponsorblock.resolve_sponsorblock_settings(_settings({
        'sponsorblock_enabled': 'true',
        'sponsorblock_category_sponsor': 'false',
        'sponsorblock_category_intro': 'true',
        'sponsorblock_notify': 'false',
        'sponsorblock_api_url': 'sponsor.example.org/',
    }))

    assert settings['enabled'] is True
    assert settings['categories'] == ['selfpromo', 'interaction', 'intro']
    assert settings['notify'] is False
    assert settings['api_url'] == 'https://sponsor.example.org'


def test_settings_without_categories_are_disabled():
    values = {'sponsorblock_enabled': 'true'}
    values.update({sponsorblock.category_setting_id(category): 'false' for category, _ in sponsorblock.CATEGORIES})

    assert sponsorblock.resolve_sponsorblock_settings(_settings(values))['enabled'] is False


def test_youtube_video_id_only_for_youtube():
    assert sponsorblock.resolve_youtube_video_id({'extractor_key': 'Youtube', 'id': 'abc'}) == 'abc'
    assert sponsorblock.resolve_youtube_video_id({'extractor_key': 'Vimeo', 'id': '123'}) is None
    assert sponsorblock.resolve_youtube_video_id({'extractor_key': 'Youtube'}) is None


def test_playing_video_id_prefers_the_item_property():
    published = sponsorblock.encode_playback('https://other', 'other')

    assert sponsorblock.resolve_playing_video_id('abc', 'https://stream', published) == 'abc'


def test_playing_video_id_matches_the_published_path_without_headers():
    published = sponsorblock.encode_playback('https://stream/video|User-Agent=x', 'abc')

    assert sponsorblock.resolve_playing_video_id('', 'https://stream/video|User-Agent=x', published) == 'abc'
    assert sponsorblock.resolve_playing_video_id('', 'https://stream/video', published) == 'abc'


@pytest.mark.parametrize('published', ['', 'not json', '[]', json.dumps({'path': 'https://stream'})])
def test_playing_video_id_ignores_missing_or_broken_publications(published):
    assert sponsorblock.resolve_playing_video_id('', 'https://stream', published) is None


def test_playing_video_id_ignores_other_playbacks():
    published = sponsorblock.encode_playback('https://stream/a', 'abc')

    assert sponsorblock.resolve_playing_video_id('', 'https://stream/b', published) is None


def test_segments_url_sends_only_a_hash_prefix():
    url = sponsorblock.build_segments_url('dQw4w9WgXcQ', ['sponsor', 'intro'])
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)

    prefix = hashlib.sha256(b'dQw4w9WgXcQ').hexdigest()[:4]
    assert parsed.path == '/api/skipSegments/' + prefix
    assert 'dQw4w9WgXcQ' not in url
    assert json.loads(query['categories'][0]) == ['sponsor', 'intro']
    assert json.loads(query['actionTypes'][0]) == ['skip']


def test_parse_segments_keeps_the_video_and_categories_and_merges():
    payload = [
        {'videoID': 'other', 'segments': [{'segment': [1, 5], 'category': 'sponsor', 'actionType': 'skip'}]},
        {'videoID': 'abc', 'segments': [
            {'segment': [100, 120], 'category': 'sponsor', 'actionType': 'skip'},
            {'segment': [10, 20], 'category': 'sponsor', 'actionType': 'skip'},
            {'segment': [20.5, 30], 'category': 'selfpromo', 'actionType': 'skip'},
            {'segment': [40, 50], 'category': 'intro', 'actionType': 'skip'},
            {'segment': [60, 70], 'category': 'sponsor', 'actionType': 'mute'},
            {'segment': [80, 80], 'category': 'sponsor', 'actionType': 'skip'},
            {'segment': None, 'category': 'sponsor', 'actionType': 'skip'},
        ]},
    ]

    segments = sponsorblock.parse_segments(payload, 'abc', ['sponsor', 'selfpromo'])

    assert segments == [(10.0, 30.0), (100.0, 120.0)]


def test_parse_segments_ignores_unexpected_payloads():
    assert sponsorblock.parse_segments({'error': 'x'}, 'abc', ['sponsor']) == []


def test_fetch_skip_segments_reads_the_api_response():
    payload = [{'videoID': 'abc', 'segments': [{'segment': [1, 9], 'category': 'sponsor', 'actionType': 'skip'}]}]
    requests = []

    def urlopen(request, timeout):
        requests.append((request.full_url, timeout))
        return io.BytesIO(json.dumps(payload).encode('utf-8'))

    segments = sponsorblock.fetch_skip_segments('abc', ['sponsor'], 'https://sb.example', urlopen=urlopen)

    assert segments == [(1.0, 9.0)]
    assert requests[0][0].startswith('https://sb.example/api/skipSegments/')
    assert requests[0][1] == sponsorblock.REQUEST_TIMEOUT_SECONDS


def test_fetch_skip_segments_treats_404_as_no_segments():
    def urlopen(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 404, 'Not Found', {}, None)

    assert sponsorblock.fetch_skip_segments('abc', ['sponsor'], urlopen=urlopen) == []


def test_fetch_skip_segments_raises_other_errors():
    def urlopen(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 500, 'Server Error', {}, None)

    with pytest.raises(urllib.error.HTTPError):
        sponsorblock.fetch_skip_segments('abc', ['sponsor'], urlopen=urlopen)


def test_skipper_skips_each_segment_once():
    skipper = sponsorblock.SegmentSkipper([(10.0, 30.0), (100.0, 120.0)])

    assert skipper.seek_target(5) is None
    assert skipper.seek_target(10.2) == 30.0
    # Seeking back into a skipped segment plays it.
    assert skipper.seek_target(15) is None
    assert skipper.seek_target(119.8) is None
    assert skipper.seek_target(101) == 120.0


# --- sponsorblock_service.py against fake Kodi modules ---

SERVICE_PATH = Path(__file__).resolve().parents[1] / 'sponsorblock_service.py'


class FakePlayer:
    def __init__(self):
        self.playing_video = True
        self.playing_file = 'https://stream/video'
        self.item_video_id = ''
        self.time = 0.0
        self.seeks = []

    def isPlayingVideo(self):
        return self.playing_video

    def getPlayingFile(self):
        return self.playing_file

    def getPlayingItem(self):
        return SimpleNamespace(getProperty=lambda _key: self.item_video_id)

    def getTime(self):
        return self.time

    def seekTime(self, target):
        self.seeks.append(target)


@pytest.fixture
def service(monkeypatch):
    state = {
        'settings': {'sponsorblock_enabled': 'true'},
        'window': {},
        'notifications': [],
        'aborts': [],
    }

    class FakeMonitor:
        def waitForAbort(self, _seconds):
            return state['aborts'].pop(0) if state['aborts'] else True

    fakes = {
        'xbmc': SimpleNamespace(
            LOGINFO=1,
            LOGWARNING=2,
            log=lambda *_args: None,
            Player=FakePlayer,
            Monitor=FakeMonitor,
        ),
        'xbmcaddon': SimpleNamespace(
            Addon=lambda _id=None: SimpleNamespace(
                getSetting=lambda key: state['settings'].get(key, ''),
                getLocalizedString=lambda _id: 'Skipped',
            )
        ),
        'xbmcgui': SimpleNamespace(
            Window=lambda _id: SimpleNamespace(getProperty=lambda key: state['window'].get(key, '')),
            Dialog=lambda: SimpleNamespace(notification=lambda *args: state['notifications'].append(args)),
            NOTIFICATION_INFO='info',
        ),
    }
    for name, module in fakes.items():
        monkeypatch.setitem(sys.modules, name, module)

    spec = importlib.util.spec_from_file_location('sponsorblock_service', SERVICE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    fetches = []

    def fetch(video_id, categories, api_url):
        fetches.append((video_id, categories, api_url))
        return state.get('segments', [(10.0, 20.0)])

    monkeypatch.setattr(sponsorblock, 'fetch_skip_segments', fetch)
    return SimpleNamespace(module=module, state=state, fetches=fetches)


def test_service_skips_a_segment_of_a_published_video(service):
    service.state['window'][sponsorblock.PLAYBACK_PROPERTY] = sponsorblock.encode_playback('https://stream/video', 'abc')
    player = service.module.SponsorBlockPlayer()
    player.onAVStarted()

    player.skipper = service.module.load_skipper(player)
    player.time = 12.0
    service.module.skip_if_needed(player)

    assert service.fetches == [('abc', ['sponsor', 'selfpromo', 'interaction'], sponsorblock.DEFAULT_API_URL)]
    assert player.seeks == [20.0]
    assert len(service.state['notifications']) == 1


def test_service_skips_silently_without_notifications(service):
    service.state['settings']['sponsorblock_notify'] = 'false'
    player = service.module.SponsorBlockPlayer()
    player.item_video_id = 'abc'

    player.skipper = service.module.load_skipper(player)
    player.time = 10.0
    service.module.skip_if_needed(player)

    assert player.seeks == [20.0]
    assert service.state['notifications'] == []


def test_service_does_nothing_when_disabled(service):
    service.state['settings']['sponsorblock_enabled'] = 'false'
    player = service.module.SponsorBlockPlayer()
    player.item_video_id = 'abc'

    assert service.module.load_skipper(player) is None
    assert service.fetches == []


def test_service_ignores_videos_it_did_not_resolve(service):
    service.state['window'][sponsorblock.PLAYBACK_PROPERTY] = sponsorblock.encode_playback('https://other', 'abc')
    player = service.module.SponsorBlockPlayer()

    assert service.module.load_skipper(player) is None
    assert service.fetches == []


def test_service_keeps_playing_when_the_api_fails(service, monkeypatch):
    def failing_fetch(*_args):
        raise OSError('offline')

    monkeypatch.setattr(sponsorblock, 'fetch_skip_segments', failing_fetch)
    player = service.module.SponsorBlockPlayer()
    player.item_video_id = 'abc'

    assert service.module.load_skipper(player) is None


def test_service_without_segments_has_no_skipper(service):
    service.state['segments'] = []
    player = service.module.SponsorBlockPlayer()
    player.item_video_id = 'abc'

    assert service.module.load_skipper(player) is None


def test_service_ignores_a_playback_that_ended_before_the_check(service):
    player = service.module.SponsorBlockPlayer()
    player.skipper = sponsorblock.SegmentSkipper([(0.0, 20.0)])

    def ended():
        raise RuntimeError('Kodi is not playing any media file')

    player.getTime = ended
    service.module.skip_if_needed(player)

    assert player.seeks == []


def test_service_loop_loads_segments_after_playback_started(service, monkeypatch):
    players = []
    original_player = service.module.SponsorBlockPlayer

    def make_player():
        player = original_player()
        player.item_video_id = 'abc'
        player.time = 15.0
        player.onAVStarted()
        players.append(player)
        return player

    monkeypatch.setattr(service.module, 'SponsorBlockPlayer', make_player)
    service.state['aborts'] = [False]

    service.module.run()

    assert players[0].seeks == [20.0]
    assert players[0].started is False


def test_service_player_resets_when_playback_stops(service):
    player = service.module.SponsorBlockPlayer()
    player.onAVStarted()
    player.skipper = sponsorblock.SegmentSkipper([])

    player.onPlayBackEnded()

    assert player.started is False
    assert player.skipper is None
