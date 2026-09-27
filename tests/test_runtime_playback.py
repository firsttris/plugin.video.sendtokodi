import importlib
import sys
import types


class DummyInfoTag:
    def __init__(self):
        self.title = None
        self.plot = None

    def setTitle(self, title):
        self.title = title

    def setPlot(self, plot):
        self.plot = plot


class DummyListItem:
    def __init__(self, label=None, path=None):
        self.label = label
        self.path = path
        self.properties = {}
        self.mime_type = None
        self.art = None
        self.subtitles = None
        self.video_info = DummyInfoTag()
        self.music_info = DummyInfoTag()

    def getVideoInfoTag(self):
        return self.video_info

    def getMusicInfoTag(self):
        return self.music_info

    def setArt(self, art):
        self.art = art

    def setSubtitles(self, subtitles):
        self.subtitles = subtitles

    def setProperty(self, key, value):
        self.properties[key] = value

    def setPath(self, path):
        self.path = path

    def setMimeType(self, mime_type):
        self.mime_type = mime_type

    def getPath(self):
        return self.path


def _load_playback_module(monkeypatch):
    xbmc = types.SimpleNamespace(LOGWARNING=2)
    xbmcgui = types.SimpleNamespace(ListItem=DummyListItem, Dialog=lambda: None, DialogProgressBG=lambda: None)
    xbmcvfs = types.SimpleNamespace(exists=lambda _path: False, translatePath=lambda path: path)

    monkeypatch.setitem(sys.modules, 'xbmc', xbmc)
    monkeypatch.setitem(sys.modules, 'xbmcgui', xbmcgui)
    monkeypatch.setitem(sys.modules, 'xbmcvfs', xbmcvfs)

    sys.modules.pop('core.runtime.playback', None)
    return importlib.import_module('core.runtime.playback')


def test_create_list_item_from_video_appends_headers_for_native_live_hls_manifest(monkeypatch):
    playback = _load_playback_module(monkeypatch)
    monkeypatch.setattr(playback, '_resolve_subtitle_paths', lambda *_args, **_kwargs: [])

    result = {
        'title': 'live',
        'description': 'desc',
        'formats': [
            {
                'format': 'hls-live',
                'url': 'https://example.com/live-1080.m3u8',
                'manifest_url': 'https://example.com/master.m3u8',
                'protocol': 'm3u8_native',
                'vcodec': 'avc1',
                'acodec': 'aac',
                'width': 1920,
            }
        ],
        'is_live': True,
        'thumbnail': 'https://example.com/thumb.jpg',
        'http_headers': {'User-Agent': 'UA'},
    }

    list_item = playback.create_list_item_from_video(
        result=result,
        ydl_opts={},
        usemanifest=True,
        usedashbuilder=False,
        maxwidth=1920,
        strict_max_resolution=True,
        askstream=False,
        disable_opus_for_audio_only_hls_native=False,
        isa_supports=lambda stream: stream == 'hls',
        youtube_dl_cls=None,
        log=lambda *_args, **_kwargs: None,
        show_error_notification=lambda *_args, **_kwargs: None,
    )

    assert list_item.path == 'https://example.com/master.m3u8|User-Agent=UA'
    assert 'inputstream' not in list_item.properties
    assert list_item.mime_type is None


def test_create_list_item_from_video_sets_hls_manifest_type_for_isa(monkeypatch):
    playback = _load_playback_module(monkeypatch)
    monkeypatch.setattr(playback, '_resolve_subtitle_paths', lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        playback,
        'select_playback_source',
        lambda *_args, **_kwargs: {
            'url': 'https://example.com/master.m3u8',
            'isa': True,
            'headers': {'User-Agent': 'UA'},
            'source': 'format_manifest',
        },
    )

    result = {
        'title': 'hls',
        'description': 'desc',
        'formats': [],
        'http_headers': {'User-Agent': 'UA'},
    }

    list_item = playback.create_list_item_from_video(
        result=result,
        ydl_opts={},
        usemanifest=True,
        usedashbuilder=False,
        maxwidth=1920,
        strict_max_resolution=True,
        askstream=False,
        disable_opus_for_audio_only_hls_native=False,
        isa_supports=lambda stream: stream == 'hls',
        youtube_dl_cls=None,
        log=lambda *_args, **_kwargs: None,
        show_error_notification=lambda *_args, **_kwargs: None,
    )

    assert list_item.properties['inputstream'] == 'inputstream.adaptive'
    assert list_item.properties['inputstream.adaptive.manifest_type'] == 'hls'
    assert list_item.properties['inputstream.adaptive.manifest_headers'] == 'User-Agent=UA'
    assert list_item.properties['inputstream.adaptive.stream_headers'] == 'User-Agent=UA'
    assert list_item.mime_type == 'application/vnd.apple.mpegurl'


def test_create_list_item_from_video_sets_dash_manifest_type_for_isa(monkeypatch):
    playback = _load_playback_module(monkeypatch)
    monkeypatch.setattr(playback, '_resolve_subtitle_paths', lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        playback,
        'select_playback_source',
        lambda *_args, **_kwargs: {
            'url': 'http://127.0.0.1:12345/manifest/test.mpd',
            'isa': True,
            'headers': {'User-Agent': 'UA'},
            'source': 'dash_manifest',
            'events': [],
        },
    )

    result = {
        'title': 'dash',
        'description': 'desc',
        'formats': [],
        'http_headers': {'User-Agent': 'UA'},
    }

    list_item = playback.create_list_item_from_video(
        result=result,
        ydl_opts={},
        usemanifest=False,
        usedashbuilder=True,
        maxwidth=1920,
        strict_max_resolution=True,
        askstream=False,
        disable_opus_for_audio_only_hls_native=False,
        isa_supports=lambda stream: stream == 'mpd',
        youtube_dl_cls=None,
        log=lambda *_args, **_kwargs: None,
        show_error_notification=lambda *_args, **_kwargs: None,
    )

    assert list_item.properties['inputstream.adaptive.manifest_type'] == 'mpd'
    assert list_item.mime_type == 'application/dash+xml'