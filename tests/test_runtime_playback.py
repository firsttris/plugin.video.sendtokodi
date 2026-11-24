import importlib
import sys
import types

import pytest


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
        self.content_lookup = None
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

    def setContentLookup(self, enabled):
        self.content_lookup = enabled

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
            'manifest_type': 'hls',
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
    assert list_item.content_lookup is False


def test_create_list_item_from_video_uses_selected_manifest_type_instead_of_url(monkeypatch):
    playback = _load_playback_module(monkeypatch)
    monkeypatch.setattr(playback, '_resolve_subtitle_paths', lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        playback,
        'select_playback_source',
        lambda *_args, **_kwargs: {
            'url': 'https://x.streaming.media.azure.net/a/b.ism/manifest(format=m3u8-aapl)',
            'isa': True,
            'headers': None,
            'manifest_type': 'hls',
            'source': 'raw_format',
        },
    )

    list_item = playback.create_list_item_from_video(
        result={'title': 'azure', 'formats': []},
        ydl_opts={},
        usemanifest=False,
        usedashbuilder=False,
        maxwidth=1920,
        strict_max_resolution=True,
        askstream=False,
        disable_opus_for_audio_only_hls_native=False,
        isa_supports=lambda _stream: True,
        youtube_dl_cls=None,
        log=lambda *_args, **_kwargs: None,
        show_error_notification=lambda *_args, **_kwargs: None,
    )

    assert list_item.properties['inputstream.adaptive.manifest_type'] == 'hls'
    assert list_item.mime_type == 'application/vnd.apple.mpegurl'
    assert list_item.content_lookup is False


def test_create_list_item_from_video_skips_manifest_type_unknown_to_isa(monkeypatch):
    playback = _load_playback_module(monkeypatch)
    monkeypatch.setattr(playback, '_resolve_subtitle_paths', lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        playback,
        'select_playback_source',
        lambda *_args, **_kwargs: {
            'url': 'rtmp://example.com/live/stream',
            'isa': True,
            'headers': None,
            'manifest_type': 'rtmp',
            'source': 'raw_format',
        },
    )

    list_item = playback.create_list_item_from_video(
        result={'title': 'rtmp', 'formats': []},
        ydl_opts={},
        usemanifest=False,
        usedashbuilder=False,
        maxwidth=1920,
        strict_max_resolution=True,
        askstream=False,
        disable_opus_for_audio_only_hls_native=False,
        isa_supports=lambda _stream: True,
        youtube_dl_cls=None,
        log=lambda *_args, **_kwargs: None,
        show_error_notification=lambda *_args, **_kwargs: None,
    )

    assert list_item.properties['inputstream'] == 'inputstream.adaptive'
    assert 'inputstream.adaptive.manifest_type' not in list_item.properties
    assert list_item.mime_type is None


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
            'manifest_type': 'mpd',
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
    assert list_item.content_lookup is False

def test_resolve_subtitle_paths_downloads_in_parallel_and_keeps_order(monkeypatch, tmp_path):
    import threading

    playback = _load_playback_module(monkeypatch)
    monkeypatch.setattr(playback, '_subtitle_download_dir', lambda: str(tmp_path))

    started = []
    all_started = threading.Event()

    def fake_download(url, destination_path, _headers):
        started.append(url)
        if len(started) == 3:
            all_started.set()
        # Only returns when all three downloads run at the same time.
        assert all_started.wait(timeout=5), "downloads ran one after another"
        if url.endswith('/fr.vtt'):
            raise OSError('404')
        with open(destination_path, 'w') as subtitle_file:
            subtitle_file.write(url)

    monkeypatch.setattr(playback, '_download_subtitle_file', fake_download)
    subtitles = {
        'de': [{'url': 'https://example.invalid/de.vtt', 'ext': 'vtt'}],
        'en': [{'url': 'https://example.invalid/en.vtt', 'ext': 'vtt'}],
        'local': [{'url': '/storage/local.srt', 'ext': 'srt'}],
        'fr': [{'url': 'https://example.invalid/fr.vtt', 'ext': 'vtt'}],
    }
    logs = []

    paths = playback._resolve_subtitle_paths(subtitles, {}, lambda msg, *_a: logs.append(msg))

    assert paths == [
        str(tmp_path / 'de.vtt'),
        str(tmp_path / 'en.vtt'),
        '/storage/local.srt',
        'https://example.invalid/fr.vtt',
    ]
    assert any('Failed to download subtitle https://example.invalid/fr.vtt' in msg for msg in logs)


def test_resolve_subtitle_paths_clears_files_from_the_previous_playback(monkeypatch, tmp_path):
    playback = _load_playback_module(monkeypatch)
    monkeypatch.setattr(playback, '_subtitle_download_dir', lambda: str(tmp_path))
    stale_file = tmp_path / 'English - en.srt'
    stale_file.write_text('subtitles of the previous video', encoding='utf-8')
    monkeypatch.setattr(playback, '_download_subtitle_file', lambda *_args: None)

    subtitles = {'en': [{'url': 'https://example.invalid/en.vtt', 'ext': 'vtt', 'name': 'English'}]}

    playback._resolve_subtitle_paths(subtitles, {}, lambda *_args: None)

    assert not stale_file.exists()


def test_resolve_subtitle_paths_ignores_files_that_cannot_be_removed(monkeypatch, tmp_path):
    playback = _load_playback_module(monkeypatch)
    monkeypatch.setattr(playback, '_subtitle_download_dir', lambda: str(tmp_path))
    (tmp_path / 'stale.srt').write_text('x', encoding='utf-8')

    def refuse(_path):
        raise OSError('busy')

    monkeypatch.setattr(playback.os, 'remove', refuse)
    monkeypatch.setattr(playback, '_download_subtitle_file', lambda *_args: None)

    subtitles = {'en': [{'url': 'https://example.invalid/en.vtt', 'ext': 'vtt'}]}

    paths = playback._resolve_subtitle_paths(subtitles, {}, lambda *_args: None)

    assert paths == [str(tmp_path / 'en.vtt')]


def test_resolve_subtitle_paths_logs_when_the_directory_cannot_be_listed(monkeypatch, tmp_path):
    playback = _load_playback_module(monkeypatch)
    monkeypatch.setattr(playback, '_subtitle_download_dir', lambda: str(tmp_path))

    def refuse(_path):
        raise OSError('denied')

    monkeypatch.setattr(playback.os, 'listdir', refuse)
    monkeypatch.setattr(playback, '_download_subtitle_file', lambda *_args: None)
    logs = []

    paths = playback._resolve_subtitle_paths(
        {'en': [{'url': 'https://example.invalid/en.vtt', 'ext': 'vtt'}]},
        {},
        lambda message, *_args: logs.append(message),
    )

    assert any('Failed to clear subtitle directory' in message for message in logs)
    assert paths == [str(tmp_path / 'en.vtt')]


class _FakePlaylist:
    def __init__(self):
        self.items = []

    def clear(self):
        self.items = []

    def add(self, path, _item, index=None):
        if index is None:
            self.items.append(path)
        else:
            self.items.insert(index, path)


class _FakeProgress:
    def __init__(self, events):
        self.events = events

    def create(self, heading, *_args):
        self.events.append(('progress', heading))

    def close(self):
        pass


@pytest.mark.parametrize('media_download_enabled', [False, True])
def test_play_playlist_resolves_starting_entry_with_progress(monkeypatch, media_download_enabled):
    playback = _load_playback_module(monkeypatch)
    events = []
    playlist = _FakePlaylist()
    monkeypatch.setattr(playback.xbmc, 'PlayList', lambda _kind: playlist, raising=False)
    monkeypatch.setattr(playback.xbmc, 'executebuiltin', lambda command: events.append(('builtin', command)), raising=False)
    monkeypatch.setattr(playback.xbmcgui, 'DialogProgressBG', lambda: _FakeProgress(events))
    monkeypatch.setattr(
        playback,
        'create_list_item_from_video',
        lambda result, *_args, **_kwargs: DummyListItem(path='resolved:' + result['url']),
    )

    class FakeYdl:
        def extract_info(self, url, download=False):
            events.append(('extract', url, download))
            return {'url': url, 'title': 'Second'}

        def process_ie_result(self, result, download=False):
            events.append(('download', result['url'], download))
            return dict(result, downloaded=True)

    result = {
        'entries': [
            {'id': 'a', 'url': 'https://example.invalid/a', 'title': 'First'},
            {'id': 'b', 'url': 'https://example.invalid/b', 'title': 'Second'},
        ]
    }

    playback.play_playlist_result(
        result,
        'https://example.invalid/list?v=b',
        FakeYdl(),
        'plugin://plugin.video.sendtokodi/',
        '?https://example.invalid/list?v=b',
        media_download_enabled,
        {},
        True,
        True,
        1920,
        True,
        False,
        True,
        lambda _stream: False,
        None,
        lambda *_a: None,
        lambda *_a: None,
    )

    expected = [
        ('progress', 'Resolving https://example.invalid/b'),
        ('extract', 'https://example.invalid/b', False),
    ]
    if media_download_enabled:
        expected += [
            ('progress', 'Downloading Second'),
            ('download', 'https://example.invalid/b', True),
        ]
    expected.append(('builtin', 'Playlist.PlayOffset(video,1)'))
    assert events == expected
    assert playlist.items[1] == 'resolved:https://example.invalid/b'


def _create_list_item_for_sponsorblock(playback, result, **extra):
    return playback.create_list_item_from_video(
        result=result,
        ydl_opts={},
        usemanifest=False,
        usedashbuilder=False,
        maxwidth=1920,
        strict_max_resolution=True,
        askstream=False,
        disable_opus_for_audio_only_hls_native=False,
        isa_supports=lambda _stream: False,
        youtube_dl_cls=None,
        log=lambda *_args, **_kwargs: None,
        show_error_notification=lambda *_args, **_kwargs: None,
        **extra,
    )


def test_create_list_item_from_video_publishes_youtube_videos_for_sponsorblock(monkeypatch):
    playback = _load_playback_module(monkeypatch)
    window_properties = {}
    playback.xbmcgui.Window = lambda _id: types.SimpleNamespace(setProperty=window_properties.__setitem__)
    monkeypatch.setattr(playback, '_resolve_subtitle_paths', lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        playback,
        'select_playback_source',
        lambda *_args, **_kwargs: {'url': 'https://example.com/v.mp4', 'isa': False, 'headers': {'User-Agent': 'UA'}},
    )

    list_item = _create_list_item_for_sponsorblock(
        playback, {'title': 'yt', 'formats': [], 'extractor_key': 'Youtube', 'id': 'abc'}
    )

    assert list_item.path == 'https://example.com/v.mp4|User-Agent=UA'
    assert list_item.properties[playback.sponsorblock.VIDEO_ID_PROPERTY] == 'abc'
    published = window_properties[playback.sponsorblock.PLAYBACK_PROPERTY]
    assert playback.sponsorblock.resolve_playing_video_id('', list_item.path, published) == 'abc'


def test_create_list_item_from_video_does_not_publish_other_sites(monkeypatch):
    playback = _load_playback_module(monkeypatch)
    monkeypatch.setattr(playback, '_resolve_subtitle_paths', lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        playback,
        'select_playback_source',
        lambda *_args, **_kwargs: {'url': 'https://example.com/v.mp4', 'isa': False, 'headers': None},
    )

    list_item = _create_list_item_for_sponsorblock(
        playback, {'title': 'vimeo', 'formats': [], 'extractor_key': 'Vimeo', 'id': '1'}
    )

    assert playback.sponsorblock.VIDEO_ID_PROPERTY not in list_item.properties


def test_create_list_item_from_video_collects_history_metadata_without_headers(monkeypatch):
    playback = _load_playback_module(monkeypatch)
    monkeypatch.setattr(playback, '_resolve_subtitle_paths', lambda *_args, **_kwargs: ['/tmp/subs.vtt'])
    monkeypatch.setattr(
        playback,
        'select_playback_source',
        lambda *_args, **_kwargs: {
            'url': 'http://127.0.0.1:8123/manifest/{}.mpd'.format('0' * 32),
            'isa': True,
            'headers': {'User-Agent': 'UA', 'Cookie': 'secret=1'},
            'manifest_type': 'mpd',
        },
    )
    captured = []

    _create_list_item_for_sponsorblock(
        playback,
        {
            'title': 'Video',
            'description': 'Plot',
            'thumbnail': 'https://example.invalid/thumb.jpg',
            'webpage_url': 'https://example.invalid/watch',
            'extractor': 'test',
            'duration': 12.5,
            'formats': [],
            'subtitles': {'en': ['https://example.invalid/sub.vtt']},
            'http_headers': {'User-Agent': 'UA', 'Cookie': 'secret=1'},
        },
        playback_meta_sink=captured.append,
    )

    # Only display fields and the page url: no headers, cookies or stream urls.
    assert captured == [
        {
            'webpage_url': 'https://example.invalid/watch',
            'title': 'Video',
            'thumbnail': 'https://example.invalid/thumb.jpg',
            'extractor': 'test',
            'duration': 12.5,
            'kind': 'video',
        }
    ]


def test_collect_playback_metadata_falls_back_to_the_original_url(monkeypatch):
    playback = _load_playback_module(monkeypatch)

    metadata = playback._collect_playback_metadata(
        {'original_url': 'https://example.invalid/page', 'url': 'https://cdn.invalid/v.mp4'},
        'audio',
    )

    assert metadata['webpage_url'] == 'https://example.invalid/page'
    assert metadata['kind'] == 'audio'


class _RecordingProgress:
    def __init__(self):
        self.updates = []
        self.closed = False

    def create(self, heading, *_args):
        self.heading = heading

    def update(self, percent, *_args):
        self.updates.append(percent)

    def close(self):
        self.closed = True


@pytest.mark.parametrize('status, expected', [
    ({'status': 'downloading', 'downloaded_bytes': 50, 'total_bytes': 200}, [25]),
    ({'status': 'downloading', 'downloaded_bytes': 30, 'total_bytes_estimate': 60}, [50]),
    ({'status': 'downloading', 'downloaded_bytes': 500, 'total_bytes': 200}, [100]),
    ({'status': 'downloading', 'downloaded_bytes': 50}, []),
    ({'status': 'downloading', 'downloaded_bytes': 50, 'total_bytes': 0}, []),
    ({'status': 'downloading', 'total_bytes': 200}, []),
    ({'status': 'finished'}, [100]),
    ({'status': 'error'}, []),
])
def test_download_progress_hook_updates_the_percent(monkeypatch, status, expected):
    playback = _load_playback_module(monkeypatch)
    progress = _RecordingProgress()

    playback._make_download_progress_hook(progress)(status)

    assert progress.updates == expected


def test_download_progress_hook_ignores_dialog_errors(monkeypatch):
    playback = _load_playback_module(monkeypatch)

    class BrokenProgress:
        def update(self, *_args):
            raise RuntimeError("dialog gone")

    playback._make_download_progress_hook(BrokenProgress())(
        {'status': 'downloading', 'downloaded_bytes': 1, 'total_bytes': 2}
    )


class _HookYdl:
    def __init__(self, statuses=(), error=None):
        self._progress_hooks = []
        self._statuses = statuses
        self._error = error

    def add_progress_hook(self, hook):
        self._progress_hooks.append(hook)

    def process_ie_result(self, result, download=False):
        assert download is True
        for status in self._statuses:
            for hook in list(self._progress_hooks):
                hook(status)
        if self._error is not None:
            raise self._error
        return dict(result, _filename='/tmp/video.mp4')


def test_download_result_with_progress_reports_progress_and_removes_the_hook(monkeypatch):
    playback = _load_playback_module(monkeypatch)
    progress = _RecordingProgress()
    monkeypatch.setattr(playback.xbmcgui, 'DialogProgressBG', lambda: progress)
    ydl = _HookYdl(statuses=[
        {'status': 'downloading', 'downloaded_bytes': 0, 'total_bytes': 100},
        {'status': 'downloading', 'downloaded_bytes': 40, 'total_bytes': 100},
        {'status': 'finished'},
    ])

    result = playback.download_result_with_progress(ydl, {'title': 'Video'})

    assert result['_filename'] == '/tmp/video.mp4'
    assert progress.heading == 'Downloading Video'
    assert progress.updates == [0, 40, 100]
    assert progress.closed is True
    assert ydl._progress_hooks == []


def test_download_result_with_progress_closes_the_dialog_on_errors(monkeypatch):
    playback = _load_playback_module(monkeypatch)
    progress = _RecordingProgress()
    monkeypatch.setattr(playback.xbmcgui, 'DialogProgressBG', lambda: progress)
    ydl = _HookYdl(error=RuntimeError("download failed"))

    with pytest.raises(RuntimeError):
        playback.download_result_with_progress(ydl, {'title': 'Video'})

    assert progress.closed is True
    assert ydl._progress_hooks == []


def test_resolve_downloaded_file_path_prefers_requested_downloads(monkeypatch):
    playback = _load_playback_module(monkeypatch)

    assert playback.resolve_downloaded_file_path(
        {'requested_downloads': [{'filename': ''}, {'filepath': '/media/a.mp4'}], '_filename': '/media/b.mp4'}
    ) == '/media/a.mp4'
    assert playback.resolve_downloaded_file_path({'_filename': '/media/b.mp4'}) == '/media/b.mp4'
    assert playback.resolve_downloaded_file_path({}) is None
