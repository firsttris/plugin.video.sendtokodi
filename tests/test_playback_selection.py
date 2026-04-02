from core.playback_selection import (
    analyze_formats,
    collect_subtitle_urls,
    encode_inputstream_headers,
    find_playlist_start_index,
    evaluate_raw_format_candidate,
    guess_manifest_type,
    normalize_dash_audio_streams,
    add_dash_formats_to_builder,
    build_dash_manifest_candidate,
    resolve_filtered_fallback_candidate,
    resolve_effective_headers,
    resolve_manifest_candidate,
    resolve_result_fallback_candidate,
    resolve_start_index,
    selection_log_messages,
    select_playback_source,
    should_filter_by_max_width,
    should_skip_manifest_candidate,
    should_skip_non_adaptive_candidate,
    should_try_dash_builder,
        split_playlist_entries,
        queueable_playlist_entries,
        resolve_starting_entry,
)


def test_normalize_dash_audio_streams_keeps_last_when_multiple():
    streams = [{"format": "a1"}, {"format": "a2"}, {"format": "a3"}]

    assert normalize_dash_audio_streams(streams) == [{"format": "a3"}]


def test_analyze_formats_detects_stream_types_and_dash_groups():
    formats = [
        {"vcodec": "avc1", "acodec": "none", "container": "mp4_dash", "format": "v1"},
        {"vcodec": "none", "acodec": "mp4a", "container": "m4a_dash", "format": "a1"},
        {"vcodec": "none", "acodec": "opus", "container": "webm_dash", "format": "a2"},
    ]

    have_video, have_audio, dash_video, dash_audio = analyze_formats(formats)

    assert have_video is True
    assert have_audio is True
    assert [entry["format"] for entry in dash_video] == ["v1"]
    assert [entry["format"] for entry in dash_audio] == ["a2"]


def test_find_playlist_start_index_prefers_matching_index_param():
    entries = [{"id": "a"}, {"id": "b"}, {"id": "c"}]

    index = find_playlist_start_index("https://youtube.com/watch?v=b&index=2", entries)

    assert index == 1


def test_find_playlist_start_index_falls_back_to_video_id_search():
    entries = [{"id": "a"}, {"id": "b"}, {"id": "c"}]

    index = find_playlist_start_index("https://youtube.com/watch?v=c&index=1", entries)

    assert index == 2


def test_find_playlist_start_index_returns_none_without_video_id():
    entries = [{"id": "a"}]

    index = find_playlist_start_index("https://youtube.com/watch?list=PL123", entries)

    assert index is None


def test_guess_manifest_type_prefers_protocol_when_present():
    assert guess_manifest_type({"protocol": "m3u8_native"}, "https://example.com/video") == "hls"


def test_guess_manifest_type_detects_manifest_from_url_suffix():
    assert guess_manifest_type({}, "https://example.com/stream.mpd?token=abc") == "mpd"


def test_guess_manifest_type_returns_none_for_plain_file_url():
    assert guess_manifest_type({}, "https://example.com/video.mp4") is None


def test_collect_subtitle_urls_flattens_all_languages():
    subtitles = {
        "en": [{"url": "https://example.com/en.vtt"}],
        "de": [{"url": "https://example.com/de1.vtt"}, {"url": "https://example.com/de2.vtt"}],
    }

    urls = collect_subtitle_urls(subtitles)

    assert urls == [
        "https://example.com/en.vtt",
        "https://example.com/de1.vtt",
        "https://example.com/de2.vtt",
    ]


def test_encode_inputstream_headers_returns_urlencoded_string():
    encoded = encode_inputstream_headers({"User-Agent": "UA", "Referer": "https://example.com"})

    assert "User-Agent=UA" in encoded
    assert "Referer=https%3A%2F%2Fexample.com" in encoded


def test_encode_inputstream_headers_returns_none_for_missing_headers():
    assert encode_inputstream_headers(None) is None


def test_should_skip_manifest_candidate_for_audio_only_when_video_exists():
    assert should_skip_manifest_candidate(True, "none", "aac") is True


def test_should_skip_manifest_candidate_for_video_only_when_no_video_detected():
    assert should_skip_manifest_candidate(False, "avc1", "none") is True


def test_should_skip_non_adaptive_candidate_for_missing_audio_when_audio_exists():
    assert should_skip_non_adaptive_candidate(False, True, "avc1", "none") is True


def test_should_filter_by_max_width_only_when_exceeding_limit():
    assert should_filter_by_max_width(1920, 1280) is True
    assert should_filter_by_max_width(1280, 1280) is False
    assert should_filter_by_max_width(None, 1280) is False


def test_should_try_dash_builder_true_for_last_video_format_when_supported():
    current = {"id": "v2"}
    dash_video = [{"id": "v1"}, current]

    assert should_try_dash_builder(
        usedashbuilder=True,
        have_video=True,
        dash_video=dash_video,
        have_audio=False,
        dash_audio=[],
        current_format=current,
        mpd_supported=True,
    ) is True


def test_should_try_dash_builder_false_when_mpd_not_supported():
    current = {"id": "v2"}
    dash_video = [{"id": "v1"}, current]

    assert should_try_dash_builder(
        usedashbuilder=True,
        have_video=True,
        dash_video=dash_video,
        have_audio=False,
        dash_audio=[],
        current_format=current,
        mpd_supported=False,
    ) is False


def test_resolve_effective_headers_prefers_selected_headers():
    selected = {"User-Agent": "selected"}
    result_headers = {"User-Agent": "result"}

    assert resolve_effective_headers(selected, result_headers) == selected


def test_resolve_effective_headers_falls_back_to_result_headers():
    result_headers = {"User-Agent": "result"}

    assert resolve_effective_headers(None, result_headers) == result_headers


def test_resolve_start_index_defaults_to_zero():
    assert resolve_start_index(None) == 0
    assert resolve_start_index(3) == 3


def test_evaluate_raw_format_candidate_skips_when_url_is_missing():
    result = evaluate_raw_format_candidate(
        format_info={"vcodec": "avc1", "acodec": "aac"},
        have_video=True,
        have_audio=True,
        maxwidth=1920,
        manifest_type=None,
        manifest_supported=False,
    )

    assert result == {"decision": "skip"}


def test_evaluate_raw_format_candidate_marks_filtered_when_width_too_high():
    result = evaluate_raw_format_candidate(
        format_info={"url": "https://example.com/v", "vcodec": "avc1", "acodec": "aac", "width": 3840},
        have_video=True,
        have_audio=True,
        maxwidth=1920,
        manifest_type=None,
        manifest_supported=False,
    )

    assert result == {"decision": "filtered"}


def test_evaluate_raw_format_candidate_selects_playable_stream():
    result = evaluate_raw_format_candidate(
        format_info={
            "url": "https://example.com/v",
            "vcodec": "avc1",
            "acodec": "aac",
            "http_headers": {"User-Agent": "UA"},
        },
        have_video=True,
        have_audio=True,
        maxwidth=1920,
        manifest_type="hls",
        manifest_supported=True,
    )

    assert result == {
        "decision": "select",
        "url": "https://example.com/v",
        "isa": True,
        "headers": {"User-Agent": "UA"},
    }


def test_resolve_filtered_fallback_candidate_returns_none_without_filtered_format():
    assert resolve_filtered_fallback_candidate(None, manifest_supported=False) is None


def test_resolve_filtered_fallback_candidate_returns_expected_payload():
    fallback = resolve_filtered_fallback_candidate(
        {"url": "https://example.com/fallback", "http_headers": {"Referer": "https://example.com"}},
        manifest_supported=True,
    )

    assert fallback == {
        "url": "https://example.com/fallback",
        "isa": True,
        "headers": {"Referer": "https://example.com"},
    }


class DummyDashBuilder:
    def __init__(self, failing_video=None, failing_audio=None):
        self.failing_video = set(failing_video or [])
        self.failing_audio = set(failing_audio or [])
        self.video_added = []
        self.audio_added = []

    def add_video_format(self, format_info):
        format_id = format_info.get("format", "")
        if format_id in self.failing_video:
            raise RuntimeError("video boom")
        self.video_added.append(format_id)

    def add_audio_format(self, format_info):
        format_id = format_info.get("format", "")
        if format_id in self.failing_audio:
            raise RuntimeError("audio boom")
        self.audio_added.append(format_id)

    def emit(self):
        return "manifest-payload"


def test_add_dash_formats_to_builder_all_success():
    builder = DummyDashBuilder()

    result = add_dash_formats_to_builder(
        builder,
        dash_video=[{"format": "v1"}],
        dash_audio=[{"format": "a1"}],
        have_video=True,
        have_audio=True,
    )

    assert result["video_success"] is True
    assert result["audio_success"] is True
    assert builder.video_added == ["v1"]
    assert builder.audio_added == ["a1"]
    assert result["events"] == [
        {"type": "video_added", "format_id": "v1"},
        {"type": "audio_added", "format_id": "a1"},
    ]


def test_add_dash_formats_to_builder_partial_failure():
    builder = DummyDashBuilder(failing_audio={"a1"})

    result = add_dash_formats_to_builder(
        builder,
        dash_video=[{"format": "v1"}],
        dash_audio=[{"format": "a1"}],
        have_video=True,
        have_audio=True,
    )

    assert result["video_success"] is True
    assert result["audio_success"] is False
    assert result["events"][0] == {"type": "video_added", "format_id": "v1"}
    assert result["events"][1]["type"] == "audio_failed"
    assert result["events"][1]["format_id"] == "a1"
    assert "audio boom" in result["events"][1]["error"]


def test_add_dash_formats_to_builder_no_video_required_marks_video_success():
    builder = DummyDashBuilder()

    result = add_dash_formats_to_builder(
        builder,
        dash_video=[],
        dash_audio=[{"format": "a1"}],
        have_video=False,
        have_audio=True,
    )

    assert result["video_success"] is True
    assert result["audio_success"] is True


def test_build_dash_manifest_candidate_returns_url_on_success():
    builder = DummyDashBuilder()

    result = build_dash_manifest_candidate(
        duration="12",
        dash_video=[{"format": "v1"}],
        dash_audio=[{"format": "a1"}],
        have_video=True,
        have_audio=True,
        manifest_factory=lambda _duration: builder,
        start_httpd=lambda manifest: "http://localhost/mpd?data=" + manifest,
    )

    assert result["url"].startswith("http://localhost/mpd?data=")
    assert result["events"] == [
        {"type": "video_added", "format_id": "v1"},
        {"type": "audio_added", "format_id": "a1"},
    ]


def test_build_dash_manifest_candidate_returns_only_events_on_failure():
    builder = DummyDashBuilder(failing_audio={"a1"})

    result = build_dash_manifest_candidate(
        duration="12",
        dash_video=[{"format": "v1"}],
        dash_audio=[{"format": "a1"}],
        have_video=True,
        have_audio=True,
        manifest_factory=lambda _duration: builder,
        start_httpd=lambda _manifest: "http://localhost/should-not-happen",
    )

    assert "url" not in result
    assert result["events"][0] == {"type": "video_added", "format_id": "v1"}
    assert result["events"][1]["type"] == "audio_failed"


def test_build_dash_manifest_candidate_refresh_uses_fresh_result_formats():
    builders = []

    class BuilderWithPayload(DummyDashBuilder):
        def __init__(self, payload):
            super().__init__()
            self.payload = payload

        def emit(self):
            return self.payload

    def manifest_factory(_duration):
        payload = "manifest-payload-{}".format(len(builders) + 1)
        builder = BuilderWithPayload(payload)
        builders.append(builder)
        return builder

    captured_refresh = {"callback": None}

    def start_httpd(manifest, refresh_manifest=None):
        captured_refresh["callback"] = refresh_manifest
        return "http://localhost/mpd?data=" + manifest

    result = build_dash_manifest_candidate(
        duration="12",
        dash_video=[{"format": "v-initial"}],
        dash_audio=[{"format": "a-initial"}],
        have_video=True,
        have_audio=True,
        manifest_factory=manifest_factory,
        start_httpd=start_httpd,
        resolve_fresh_result=lambda: {
            "duration": "20",
            "formats": [
                {"format": "v-fresh", "vcodec": "avc1", "acodec": "none", "container": "mp4_dash"},
                {"format": "a-fresh", "vcodec": "none", "acodec": "aac", "container": "m4a_dash"},
            ],
        },
    )

    refreshed_manifest = captured_refresh["callback"]()

    assert result["url"].startswith("http://localhost/mpd?data=")
    assert builders[0].video_added == ["v-initial"]
    assert builders[0].audio_added == ["a-initial"]
    assert builders[1].video_added == ["v-fresh"]
    assert builders[1].audio_added == ["a-fresh"]
    assert refreshed_manifest == "manifest-payload-2"


def test_resolve_manifest_candidate_returns_none_without_url():
    assert resolve_manifest_candidate(None, manifest_supported=True, headers={"A": "B"}) is None


def test_resolve_manifest_candidate_returns_none_when_not_supported():
    assert resolve_manifest_candidate("https://example.com/manifest.mpd", manifest_supported=False, headers={}) is None


def test_resolve_manifest_candidate_returns_payload_when_supported():
    payload = resolve_manifest_candidate(
        "https://example.com/manifest.mpd",
        manifest_supported=True,
        headers={"User-Agent": "UA"},
    )

    assert payload == {
        "url": "https://example.com/manifest.mpd",
        "isa": True,
        "headers": {"User-Agent": "UA"},
    }


def test_resolve_result_fallback_candidate_returns_none_without_url():
    assert resolve_result_fallback_candidate(None, manifest_supported=False, headers=None) is None


def test_resolve_result_fallback_candidate_returns_payload():
    payload = resolve_result_fallback_candidate(
        "https://example.com/video.mp4",
        manifest_supported=False,
        headers={"Referer": "https://example.com"},
    )

    assert payload == {
        "url": "https://example.com/video.mp4",
        "isa": False,
        "headers": {"Referer": "https://example.com"},
    }


def test_select_playback_source_prefers_original_manifest():
    result = {
        "manifest_url": "https://example.com/master.m3u8",
        "http_headers": {"User-Agent": "UA"},
    }

    selected = select_playback_source(
        result=result,
        usemanifest=True,
        usedashbuilder=False,
        maxwidth=1920,
        isa_supports=lambda stream: stream == "hls",
    )

    assert selected["source"] == "original_manifest"
    assert selected["url"] == "https://example.com/master.m3u8"
    assert selected["isa"] is True


def test_select_playback_source_uses_format_manifest_when_original_missing():
    result = {
        "formats": [
            {
                "format": "f1",
                "vcodec": "avc1",
                "acodec": "aac",
                "manifest_url": "https://example.com/format.m3u8",
                "http_headers": {"Referer": "https://example.com"},
            }
        ]
    }

    selected = select_playback_source(
        result=result,
        usemanifest=True,
        usedashbuilder=False,
        maxwidth=1920,
        isa_supports=lambda stream: stream == "hls",
    )

    assert selected["source"] == "format_manifest"
    assert selected["format_label"] == "f1"


def test_select_playback_source_uses_raw_format_when_playable():
    result = {
        "formats": [
            {
                "format": "fraw",
                "url": "https://example.com/video.mp4",
                "vcodec": "avc1",
                "acodec": "aac",
                "width": 1280,
            }
        ]
    }

    selected = select_playback_source(
        result=result,
        usemanifest=False,
        usedashbuilder=False,
        maxwidth=1920,
        isa_supports=lambda _stream: False,
    )

    assert selected["source"] == "raw_format"
    assert selected["url"] == "https://example.com/video.mp4"


def test_select_playback_source_prefers_user_selected_stream_url():
    result = {
        "manifest_url": "https://example.com/master.m3u8",
        "formats": [
            {
                "format": "f360",
                "url": "https://example.com/360.mp4",
                "vcodec": "avc1",
                "acodec": "aac",
                "width": 640,
            },
            {
                "format": "f720",
                "url": "https://example.com/720.mp4",
                "vcodec": "avc1",
                "acodec": "aac",
                "width": 1280,
            },
        ],
    }

    selected = select_playback_source(
        result=result,
        usemanifest=True,
        usedashbuilder=False,
        maxwidth=1920,
        isa_supports=lambda stream: stream == "hls",
        preferred_format_url="https://example.com/360.mp4",
    )

    assert selected["source"] == "raw_format"
    assert selected["url"] == "https://example.com/360.mp4"


def test_select_playback_source_returns_none_for_unplayable_user_selected_stream_url():
    result = {
        "manifest_url": "https://example.com/master.m3u8",
        "formats": [
            {
                "format": "f720",
                "url": "https://example.com/720.mp4",
                "vcodec": "avc1",
                "acodec": "aac",
                "width": 1280,
            },
        ],
    }

    selected = select_playback_source(
        result=result,
        usemanifest=True,
        usedashbuilder=False,
        maxwidth=1920,
        isa_supports=lambda stream: stream == "hls",
        preferred_format_url="https://example.com/missing.mp4",
    )

    assert selected is None


def test_select_playback_source_uses_filtered_fallback_when_only_over_limit_formats_exist():
    result = {
        "formats": [
            {
                "format": "f4k",
                "url": "https://example.com/video4k.mp4",
                "vcodec": "avc1",
                "acodec": "aac",
                "width": 3840,
            }
        ]
    }

    selected = select_playback_source(
        result=result,
        usemanifest=False,
        usedashbuilder=False,
        maxwidth=1920,
        isa_supports=lambda _stream: False,
    )

    assert selected["source"] == "filtered_fallback"
    assert selected["url"] == "https://example.com/video4k.mp4"


def test_select_playback_source_uses_result_fallback_when_no_formats_selected():
    result = {
        "formats": [{"format": "broken", "vcodec": "avc1", "acodec": "aac"}],
        "url": "https://example.com/fallback.mp4",
        "http_headers": {"User-Agent": "UA"},
    }

    selected = select_playback_source(
        result=result,
        usemanifest=False,
        usedashbuilder=False,
        maxwidth=1920,
        isa_supports=lambda _stream: False,
    )

    assert selected["source"] == "result_fallback"
    assert selected["url"] == "https://example.com/fallback.mp4"


def test_select_playback_source_returns_none_when_nothing_is_playable():
    selected = select_playback_source(
        result={"formats": []},
        usemanifest=False,
        usedashbuilder=False,
        maxwidth=1920,
        isa_supports=lambda _stream: False,
    )

    assert selected is None


def test_select_playback_source_uses_passed_dashbuilder_dependency():
    class DummyDashModule:
        class Manifest:
            def __init__(self, _duration):
                self._emitted = "manifest-from-dummy"

            def add_video_format(self, _format_info):
                return None

            def add_audio_format(self, _format_info):
                return None

            def emit(self):
                return self._emitted

        @staticmethod
        def start_httpd(manifest):
            return "http://dummy.local/" + manifest

    result = {
        "duration": "10",
        "formats": [
            {
                "format": "dash-candidate",
                "vcodec": "avc1",
                "acodec": "none",
                "container": "mp4_dash",
                "http_headers": {"Referer": "https://example.com"},
            },
            {
                "format": "dash-audio",
                "vcodec": "none",
                "acodec": "aac",
                "container": "m4a_dash",
                "http_headers": {"Referer": "https://example.com"},
            },
        ],
    }

    selected = select_playback_source(
        result=result,
        usemanifest=False,
        usedashbuilder=True,
        maxwidth=1920,
        isa_supports=lambda stream: stream == "mpd",
        dashbuilder=DummyDashModule,
    )

    assert selected["source"] == "dash_manifest"
    assert selected["url"] == "http://dummy.local/manifest-from-dummy"


def test_selection_log_messages_for_original_manifest():
    messages = selection_log_messages({"source": "original_manifest"})

    assert messages == ["Picked original manifest"]


def test_selection_log_messages_for_format_manifest():
    messages = selection_log_messages({"source": "format_manifest", "format_label": "f1"})

    assert messages == ["Picked format f1 manifest"]


def test_selection_log_messages_for_raw_format():
    messages = selection_log_messages({"source": "raw_format", "format_label": "fraw"})

    assert messages == ["Picked raw format fraw"]


def test_selection_log_messages_for_dash_manifest_with_events():
    messages = selection_log_messages(
        {
            "source": "dash_manifest",
            "events": [
                {"type": "video_added", "format_id": "v1"},
                {"type": "audio_failed", "format_id": "a1", "error": "boom"},
            ],
        }
    )

    assert messages == [
        "Added video stream v1 to DASH manifest",
        "Failed to add DASH audio stream a1: boom",
        "Picked DASH with custom manifest",
    ]


def test_selection_log_messages_for_unknown_source_returns_empty():
    assert selection_log_messages({"source": "unknown"}) == []

def test_split_playlist_entries_returns_starting_and_remaining_entries():
    starting, remaining = split_playlist_entries([
        {"id": "a"},
        {"id": "b"},
        {"id": "c"},
    ], 1)

    assert starting == {"id": "b"}
    assert remaining == [{"id": "a"}, {"id": "c"}]


def test_queueable_playlist_entries_filters_entries_without_url():
    entries = [
        {"id": "a", "url": "https://example.com/a"},
        {"id": "b"},
        {"id": "c", "url": "https://example.com/c"},
    ]

    assert queueable_playlist_entries(entries) == [
        {"id": "a", "url": "https://example.com/a"},
        {"id": "c", "url": "https://example.com/c"},
    ]


def test_resolve_starting_entry_extracts_when_url_present():
    extracted = resolve_starting_entry(
        {"url": "https://example.com/start"},
        lambda url, download: {"url": url, "download": download, "title": "resolved"},
    )

    assert extracted == {
        "url": "https://example.com/start",
        "download": False,
        "title": "resolved",
    }


def test_resolve_starting_entry_returns_entry_when_url_missing():
    entry = {"id": "local", "title": "already resolved"}

    assert resolve_starting_entry(entry, lambda *_args, **_kwargs: {"should": "not-run"}) == entry
