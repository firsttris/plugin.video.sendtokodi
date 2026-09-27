from urllib.parse import quote

from core.playback_selection import (
    analyze_formats,
    append_headers_to_url,
    collect_subtitle_entries,
    collect_subtitle_urls,
    encode_inputstream_headers,
    find_playlist_start_index,
    evaluate_raw_format_candidate,
    guess_manifest_type,
    normalize_dash_audio_streams,
    should_allow_native_hls_without_isa,
    add_dash_formats_to_builder,
    build_dash_manifest_candidate,
    resolve_filtered_fallback_candidate,
    resolve_effective_headers,
    resolve_manifest_candidate,
    resolve_result_fallback_candidate,
    resolve_start_index,
    selection_log_messages,
    select_playback_source,
    should_prefer_manifest_over_raw_hls,
    should_filter_by_max_width,
    should_skip_manifest_candidate,
    should_skip_non_adaptive_candidate,
    should_try_dash_builder,
        split_playlist_entries,
        queueable_playlist_entries,
        resolve_starting_entry,
        resolve_playlist_insert_position,
)


def test_normalize_dash_audio_streams_keeps_last_when_multiple():
    streams = [
        {"format": "a-mp4-low", "container": "m4a_dash", "abr": 96},
        {"format": "a-webm-high", "container": "webm_dash", "abr": 192},
        {"format": "a-mp4-high", "container": "m4a_dash", "abr": 160},
    ]
    selected_video = {"format": "v1", "container": "mp4_dash"}

    assert normalize_dash_audio_streams(streams, preferred_video_format=selected_video) == [
        {"format": "a-mp4-high", "container": "m4a_dash", "abr": 160}
    ]


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
    assert [entry["format"] for entry in dash_audio] == ["a1", "a2"]


def test_normalize_dash_audio_streams_falls_back_to_highest_quality_without_compatible_container():
    streams = [
        {"format": "a-low", "container": "m4a_dash", "abr": 96},
        {"format": "a-high", "container": "webm_dash", "abr": 192},
    ]

    assert normalize_dash_audio_streams(streams) == [
        {"format": "a-high", "container": "webm_dash", "abr": 192}
    ]


def test_normalize_dash_audio_streams_keeps_one_stream_per_language_with_original_first():
    streams = [
        {"format": "251-0", "container": "webm_dash", "abr": 118, "language": "en-US", "language_preference": -1},
        {"format": "250-0", "container": "webm_dash", "abr": 66, "language": "en-US", "language_preference": -1},
        {"format": "251-1", "container": "webm_dash", "abr": 115, "language": "de-DE", "language_preference": 10},
        {"format": "250-1", "container": "webm_dash", "abr": 63, "language": "de-DE", "language_preference": 10},
        {"format": "251-2", "container": "webm_dash", "abr": 140, "language": "fr-FR", "language_preference": 5},
    ]
    selected_video = {"format": "v1", "container": "webm_dash"}

    assert normalize_dash_audio_streams(streams, preferred_video_format=selected_video) == [
        streams[2],
        streams[4],
        streams[0],
    ]


def test_normalize_dash_audio_streams_prefers_container_match_per_language():
    streams = [
        {"format": "140-0", "container": "m4a_dash", "abr": 129, "language": "en-US", "language_preference": -1},
        {"format": "251-0", "container": "webm_dash", "abr": 130, "language": "en-US", "language_preference": -1},
        {"format": "251-1", "container": "webm_dash", "abr": 115, "language": "de-DE", "language_preference": 10},
    ]
    selected_video = {"format": "v1", "container": "mp4_dash"}

    assert normalize_dash_audio_streams(streams, preferred_video_format=selected_video) == [
        streams[2],
        streams[0],
    ]


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


def test_collect_subtitle_urls_keeps_one_preferred_entry_per_language():
    subtitles = {
        "en": [{"url": "https://example.com/en.vtt", "ext": "vtt"}],
        "de": [
            {"url": "https://example.com/de.json3", "ext": "json3"},
            {"url": "https://example.com/de.srt", "ext": "srt"},
            {"url": "https://example.com/de.vtt", "ext": "vtt"},
        ],
    }

    urls = collect_subtitle_urls(subtitles)

    assert urls == [
        "https://example.com/en.vtt",
        "https://example.com/de.srt",
    ]


def test_collect_subtitle_entries_keep_language_name_and_ext():
    subtitles = {
        "de": [
            {"url": "https://example.com/de.json3", "ext": "json3", "name": "German"},
            {"url": "https://example.com/de.srt", "ext": "srt", "name": "German"},
        ],
        "en": [{"url": "https://example.com/en.vtt", "ext": "vtt", "name": "English"}],
    }

    subtitle_entries = collect_subtitle_entries(subtitles)

    assert subtitle_entries == [
        {"language": "de", "name": "German", "ext": "srt", "url": "https://example.com/de.srt"},
        {"language": "en", "name": "English", "ext": "vtt", "url": "https://example.com/en.vtt"},
    ]


def test_collect_subtitle_urls_ignores_malformed_entries():
    subtitles = {
        "en": None,
        "de": [{"url": "https://example.com/de.vtt", "ext": "vtt"}, {"name": "missing-url"}],
        "fr": "https://example.com/fr.vtt",
        "es": ["bad-entry"],
    }

    urls = collect_subtitle_urls(subtitles)

    assert urls == ["https://example.com/de.vtt"]


def test_collect_subtitle_urls_falls_back_to_first_unknown_format_when_needed():
    subtitles = {
        "de": [
            {"url": "https://example.com/de.custom", "ext": "custom"},
            {"url": "https://example.com/de.other", "ext": "other"},
        ]
    }

    urls = collect_subtitle_urls(subtitles)

    assert urls == ["https://example.com/de.custom"]


def test_collect_subtitle_urls_ignores_live_chat_tracks():
    subtitles = {
        "live_chat": [
            {
                "url": "https://example.com/api/live_chat_replay?fmt=json3",
                "ext": "json3",
                "name": "live_chat json",
            }
        ],
        "de": [
            {"url": "https://example.com/de.vtt", "ext": "vtt", "name": "German"},
        ],
    }

    urls = collect_subtitle_urls(subtitles)

    assert urls == ["https://example.com/de.vtt"]


def test_collect_subtitle_entries_drops_live_chat_when_only_track_present():
    subtitles = {
        "live_chat": [
            {
                "url": "https://example.com/api/live_chat?fmt=json3",
                "ext": "json3",
                "name": "live_chat json",
            }
        ]
    }

    subtitle_entries = collect_subtitle_entries(subtitles)

    assert subtitle_entries == []


def test_collect_subtitle_entries_drops_live_chat_protocol_under_other_language_key():
    subtitles = {
        "en": [
            {
                "url": "https://example.com/api/chat",
                "ext": "json3",
                "protocol": "youtube_live_chat_replay",
            }
        ]
    }

    assert collect_subtitle_entries(subtitles) == []


def test_collect_subtitle_entries_drops_plain_json_tracks():
    subtitles = {
        "rechat": [
            {"url": "https://example.com/rechat", "ext": "json"},
        ]
    }

    assert collect_subtitle_entries(subtitles) == []


def test_collect_subtitle_entries_keeps_real_subtitles_mentioning_live_chat():
    subtitles = {
        "en": [
            {
                "url": "https://example.com/shows/live_chat_replay/en.vtt",
                "ext": "vtt",
                "name": "Live Chat Replay - English",
            }
        ]
    }

    subtitle_entries = collect_subtitle_entries(subtitles)

    assert [entry["url"] for entry in subtitle_entries] == ["https://example.com/shows/live_chat_replay/en.vtt"]


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


def test_should_allow_native_hls_without_isa_for_muxed_hls_variant():
    allowed = should_allow_native_hls_without_isa(
        {
            "protocol": "m3u8_native",
            "vcodec": "avc1.64001f",
            "acodec": "mp4a.40.2",
        },
        manifest_type="hls",
    )

    assert allowed is True


def test_should_allow_native_hls_without_isa_for_audio_only_hls_variant():
    allowed = should_allow_native_hls_without_isa(
        {
            "protocol": "m3u8_native",
            "vcodec": "none",
            "acodec": "opus",
        },
        manifest_type="hls",
    )

    assert allowed is True


def test_should_prefer_manifest_over_raw_hls_for_live_hls_streams():
    preferred = should_prefer_manifest_over_raw_hls(
        {"is_live": True},
        {
            "url": "https://example.com/stream.m3u8",
            "protocol": "m3u8_native",
        },
        {"url": "https://example.com/master.m3u8", "isa": True, "headers": None},
        maxwidth=1920,
        strict_max_resolution=True,
    )

    assert preferred is True


def test_should_not_prefer_manifest_over_raw_hls_for_non_live_streams():
    preferred = should_prefer_manifest_over_raw_hls(
        {},
        {
            "url": "https://example.com/stream.m3u8",
            "protocol": "m3u8_native",
        },
        {"url": "https://example.com/master.m3u8", "isa": True, "headers": None},
        maxwidth=1920,
        strict_max_resolution=True,
    )

    assert preferred is False


def _live_hls_variant(width, manifest_url="https://example.com/master.m3u8"):
    return {
        "url": "https://example.com/{}.m3u8".format(width),
        "manifest_url": manifest_url,
        "protocol": "m3u8_native",
        "width": width,
    }


def test_should_not_prefer_manifest_over_raw_hls_when_variant_exceeds_strict_limit():
    variant_720 = _live_hls_variant(1280)
    result = {"is_live": True, "formats": [variant_720, _live_hls_variant(1920)]}

    preferred = should_prefer_manifest_over_raw_hls(
        result,
        variant_720,
        {"url": "https://example.com/master.m3u8", "isa": False, "headers": None},
        maxwidth=1280,
        strict_max_resolution=True,
    )

    assert preferred is False


def test_should_prefer_manifest_over_raw_hls_ignores_limit_when_not_strict():
    variant_720 = _live_hls_variant(1280)
    result = {"is_live": True, "formats": [variant_720, _live_hls_variant(1920)]}

    preferred = should_prefer_manifest_over_raw_hls(
        result,
        variant_720,
        {"url": "https://example.com/master.m3u8", "isa": False, "headers": None},
        maxwidth=1280,
        strict_max_resolution=False,
    )

    assert preferred is True


def test_should_prefer_manifest_over_raw_hls_ignores_variants_of_other_manifests():
    variant_720 = _live_hls_variant(1280)
    result = {
        "is_live": True,
        "formats": [variant_720, _live_hls_variant(1920, "https://example.com/other.m3u8")],
    }

    preferred = should_prefer_manifest_over_raw_hls(
        result,
        variant_720,
        {"url": "https://example.com/master.m3u8", "isa": False, "headers": None},
        maxwidth=1280,
        strict_max_resolution=True,
    )

    assert preferred is True


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
        "manifest_type": "hls",
    }


def test_evaluate_raw_format_candidate_uses_native_for_muxed_hls_when_isa_unavailable():
    result = evaluate_raw_format_candidate(
        format_info={
            "url": "https://example.com/stream.m3u8",
            "protocol": "m3u8_native",
            "vcodec": "avc1.64001f",
            "acodec": "mp4a.40.2",
            "http_headers": {"User-Agent": "UA"},
        },
        have_video=True,
        have_audio=True,
        maxwidth=1920,
        manifest_type="hls",
        manifest_supported=False,
    )

    assert result == {
        "decision": "select",
        "url": "https://example.com/stream.m3u8",
        "isa": False,
        "headers": {"User-Agent": "UA"},
        "manifest_type": "hls",
    }


def test_evaluate_raw_format_candidate_uses_native_for_audio_only_hls_when_isa_available():
    result = evaluate_raw_format_candidate(
        format_info={
            "url": "https://example.com/audio.m3u8",
            "protocol": "m3u8_native",
            "vcodec": "none",
            "acodec": "opus",
            "http_headers": {"User-Agent": "UA"},
        },
        have_video=False,
        have_audio=True,
        maxwidth=1920,
        manifest_type="hls",
        manifest_supported=True,
    )

    assert result == {
        "decision": "select",
        "url": "https://example.com/audio.m3u8",
        "isa": False,
        "headers": {"User-Agent": "UA"},
        "manifest_type": "hls",
    }


def test_evaluate_raw_format_candidate_skips_audio_only_native_hls_opus_when_disabled_by_setting():
    result = evaluate_raw_format_candidate(
        format_info={
            "url": "https://example.com/audio.m3u8",
            "protocol": "m3u8_native",
            "vcodec": "none",
            "acodec": "opus",
            "http_headers": {"User-Agent": "UA"},
        },
        have_video=False,
        have_audio=True,
        maxwidth=1920,
        manifest_type="hls",
        manifest_supported=True,
        disable_opus_for_audio_only_hls_native=True,
    )

    assert result == {"decision": "skip"}


def test_resolve_filtered_fallback_candidate_returns_none_without_filtered_format():
    assert resolve_filtered_fallback_candidate(None, manifest_type=None, manifest_supported=False) is None


def test_resolve_filtered_fallback_candidate_returns_expected_payload():
    fallback = resolve_filtered_fallback_candidate(
        {"url": "https://example.com/fallback", "http_headers": {"Referer": "https://example.com"}},
        manifest_type="hls",
        manifest_supported=True,
    )

    assert fallback == {
        "url": "https://example.com/fallback",
        "isa": True,
        "headers": {"Referer": "https://example.com"},
        "manifest_type": "hls",
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


def test_add_dash_formats_to_builder_prefetches_all_formats_first():
    calls = []

    class PrefetchingBuilder(DummyDashBuilder):
        def prefetch_ranges(self, formats):
            calls.append(("prefetch", [format_info["format"] for format_info in formats]))

        def add_video_format(self, format_info):
            calls.append(("video", format_info["format"]))

        def add_audio_format(self, format_info):
            calls.append(("audio", format_info["format"]))

    add_dash_formats_to_builder(
        PrefetchingBuilder(),
        dash_video=[{"format": "v1"}],
        dash_audio=[{"format": "a-de"}, {"format": "a-en"}],
        have_video=True,
        have_audio=True,
    )

    assert calls == [
        ("prefetch", ["v1", "a-de", "a-en"]),
        ("video", "v1"),
        ("audio", "a-de"),
        ("audio", "a-en"),
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


def test_build_dash_manifest_candidate_refresh_keeps_selected_video_and_compatible_audio():
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
        dash_video=[{"format": "v4k", "format_id": "401", "url": "https://example.com/v4k", "container": "mp4_dash"}],
        dash_audio=[{"format": "a-init", "container": "m4a_dash", "abr": 128}],
        have_video=True,
        have_audio=True,
        manifest_factory=manifest_factory,
        start_httpd=start_httpd,
        resolve_fresh_result=lambda: {
            "duration": "20",
            "formats": [
                {
                    "format": "v1080",
                    "format_id": "137",
                    "url": "https://example.com/v1080",
                    "vcodec": "avc1",
                    "acodec": "none",
                    "container": "mp4_dash",
                },
                {
                    "format": "v4k",
                    "format_id": "401",
                    "url": "https://example.com/v4k",
                    "vcodec": "avc1",
                    "acodec": "none",
                    "container": "mp4_dash",
                },
                {
                    "format": "a-webm",
                    "vcodec": "none",
                    "acodec": "opus",
                    "container": "webm_dash",
                    "abr": 192,
                },
                {
                    "format": "a-mp4",
                    "vcodec": "none",
                    "acodec": "aac",
                    "container": "m4a_dash",
                    "abr": 128,
                },
            ],
        },
        preferred_video_format={"format": "v4k", "format_id": "401", "url": "https://example.com/v4k", "container": "mp4_dash"},
        preferred_video_format_id="401",
        preferred_video_url="https://example.com/v4k",
    )

    refreshed_manifest = captured_refresh["callback"]()

    assert result["url"].startswith("http://localhost/mpd?data=")
    assert builders[1].video_added == ["v4k"]
    assert builders[1].audio_added == ["a-mp4"]
    assert refreshed_manifest == "manifest-payload-2"


def test_resolve_manifest_candidate_returns_none_without_url():
    assert resolve_manifest_candidate(None, "hls", lambda _stream: True, headers={"A": "B"}) is None


def test_resolve_manifest_candidate_returns_none_when_not_supported():
    assert resolve_manifest_candidate(
        "https://example.com/manifest.mpd",
        "mpd",
        lambda _stream: False,
        headers={},
    ) is None


def test_resolve_manifest_candidate_returns_payload_when_supported():
    payload = resolve_manifest_candidate(
        "https://example.com/manifest.mpd",
        "mpd",
        lambda stream: stream == "mpd",
        headers={"User-Agent": "UA"},
    )

    assert payload == {
        "url": "https://example.com/manifest.mpd",
        "isa": True,
        "headers": {"User-Agent": "UA"},
        "manifest_type": "mpd",
    }


def test_resolve_manifest_candidate_plays_live_hls_natively_without_isa():
    payload = resolve_manifest_candidate(
        "https://example.com/master.m3u8",
        "hls",
        lambda _stream: False,
        headers={"User-Agent": "UA"},
        is_live=True,
    )

    assert payload == {
        "url": "https://example.com/master.m3u8",
        "isa": False,
        "headers": {"User-Agent": "UA"},
        "manifest_type": "hls",
    }


def test_resolve_manifest_candidate_keeps_isa_for_non_live_hls():
    payload = resolve_manifest_candidate(
        "https://example.com/master.m3u8",
        "hls",
        lambda stream: stream == "hls",
        headers=None,
    )

    assert payload["isa"] is True


def test_resolve_result_fallback_candidate_returns_none_without_url():
    assert resolve_result_fallback_candidate(None, None, manifest_supported=False, headers=None) is None


def test_resolve_result_fallback_candidate_returns_payload():
    payload = resolve_result_fallback_candidate(
        "https://example.com/video.mp4",
        None,
        manifest_supported=False,
        headers={"Referer": "https://example.com"},
    )

    assert payload == {
        "url": "https://example.com/video.mp4",
        "isa": False,
        "headers": {"Referer": "https://example.com"},
        "manifest_type": None,
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


def test_select_playback_source_uses_master_manifest_for_split_live_hls():
    # YouTube live: audio-only HLS renditions come without an acodec key.
    master = "https://manifest.googlevideo.com/api/manifest/hls_variant/master.m3u8"
    result = {
        "is_live": True,
        "formats": [
            {
                "format": "234 - audio only",
                "url": "https://manifest.googlevideo.com/api/manifest/hls_playlist/itag/234/index.m3u8",
                "manifest_url": master,
                "protocol": "m3u8_native",
                "vcodec": "none",
                "audio_ext": "mp4",
                "video_ext": "none",
            },
            {
                "format": "312 - 1920x1080",
                "url": "https://manifest.googlevideo.com/api/manifest/hls_playlist/itag/312/index.m3u8",
                "manifest_url": master,
                "protocol": "m3u8_native",
                "vcodec": "avc1.64002A",
                "acodec": "none",
                "audio_ext": "none",
                "video_ext": "mp4",
                "width": 1920,
            },
        ],
    }

    selected = select_playback_source(
        result=result,
        usemanifest=True,
        usedashbuilder=True,
        maxwidth=1920,
        isa_supports=lambda stream: stream in ("hls", "mpd"),
    )

    assert selected["source"] == "format_manifest"
    assert selected["url"] == master
    assert selected["isa"] is False


def test_analyze_formats_treats_audio_only_without_acodec_as_audio():
    formats = [
        {"vcodec": "none", "audio_ext": "mp4", "video_ext": "none"},
        {"vcodec": "none", "acodec": "none", "audio_ext": "none", "ext": "mhtml"},
    ]

    have_video, have_audio, _dash_video, _dash_audio = analyze_formats(formats)

    assert have_video is False
    assert have_audio is True


def test_analyze_formats_treats_explicit_none_acodec_as_audio():
    have_video, have_audio, _dash_video, _dash_audio = analyze_formats(
        [{"vcodec": "avc1", "acodec": None}]
    )

    assert have_video is True
    assert have_audio is True


def test_select_playback_source_prefers_muxed_unknown_acodec_over_wider_silent_video():
    result = {
        "formats": [
            {
                "format": "muxed",
                "url": "https://example.com/muxed.mp4",
                "vcodec": "avc1",
                "acodec": None,
                "width": 1280,
            },
            {
                "format": "silent",
                "url": "https://example.com/silent.mp4",
                "vcodec": "avc1",
                "acodec": "none",
                "width": 1920,
            },
        ]
    }

    selected = select_playback_source(
        result=result,
        usemanifest=False,
        usedashbuilder=False,
        maxwidth=1920,
        isa_supports=lambda stream: False,
    )

    assert selected["format_label"] == "muxed"


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


def test_select_playback_source_prefers_highest_raw_width_within_limit():
    result = {
        "formats": [
            {
                "format": "f4k",
                "url": "https://example.com/video4k.mp4",
                "vcodec": "avc1",
                "acodec": "aac",
                "width": 3840,
            },
            {
                "format": "f1080",
                "url": "https://example.com/video1080.mp4",
                "vcodec": "avc1",
                "acodec": "aac",
                "width": 1920,
            },
        ]
    }

    selected = select_playback_source(
        result=result,
        usemanifest=False,
        usedashbuilder=False,
        maxwidth=3840,
        isa_supports=lambda _stream: False,
    )

    assert selected["source"] == "raw_format"
    assert selected["url"] == "https://example.com/video4k.mp4"


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


def test_select_playback_source_prefers_user_selected_format_id_when_urls_match():
    result = {
        "formats": [
            {
                "format": "f360",
                "format_id": "18",
                "url": "https://example.com/master.m3u8",
                "protocol": "m3u8_native",
                "vcodec": "avc1",
                "acodec": "aac",
                "width": 640,
            },
            {
                "format": "f1080",
                "format_id": "37",
                "url": "https://example.com/master.m3u8",
                "protocol": "m3u8_native",
                "vcodec": "avc1",
                "acodec": "aac",
                "width": 1920,
            },
        ],
    }

    selected = select_playback_source(
        result=result,
        usemanifest=False,
        usedashbuilder=False,
        maxwidth=1920,
        isa_supports=lambda _stream: False,
        preferred_format_url="https://example.com/master.m3u8",
        preferred_format_id="18",
    )

    assert selected["source"] == "raw_format"
    assert selected["url"] == "https://example.com/master.m3u8"
    assert selected["format_label"] == "f360"


def test_select_playback_source_prefers_raw_4k_over_original_manifest_when_allowed():
    result = {
        "manifest_url": "https://example.com/master.mpd",
        "http_headers": {"User-Agent": "UA"},
        "formats": [
            {
                "format": "f1080",
                "url": "https://example.com/1080.mp4",
                "vcodec": "avc1",
                "acodec": "aac",
                "width": 1920,
            },
            {
                "format": "f4k",
                "url": "https://example.com/4k.mp4",
                "vcodec": "avc1",
                "acodec": "aac",
                "width": 3840,
            },
        ],
    }

    selected = select_playback_source(
        result=result,
        usemanifest=True,
        usedashbuilder=False,
        maxwidth=3840,
        isa_supports=lambda stream: stream == "mpd",
    )

    assert selected["source"] == "raw_format"
    assert selected["url"] == "https://example.com/4k.mp4"


def test_select_playback_source_adaptive_first_prefers_original_manifest():
    result = {
        "manifest_url": "https://example.com/master.m3u8",
        "http_headers": {"User-Agent": "UA"},
        "formats": [
            {
                "format": "f4k",
                "url": "https://example.com/4k.mp4",
                "vcodec": "avc1",
                "acodec": "aac",
                "width": 3840,
            },
        ],
    }

    selected = select_playback_source(
        result=result,
        usemanifest=True,
        usedashbuilder=False,
        maxwidth=3840,
        isa_supports=lambda stream: stream == "hls",
        strict_max_resolution=False,
    )

    assert selected["source"] == "original_manifest"
    assert selected["url"] == "https://example.com/master.m3u8"


def test_select_playback_source_prefers_live_hls_manifest_over_raw_variant_when_available():
    result = {
        "is_live": True,
        "formats": [
            {
                "format": "301 - 1920x1080",
                "url": "https://example.com/live-1080-playlist.m3u8",
                "manifest_url": "https://example.com/live-master.m3u8",
                "protocol": "m3u8_native",
                "vcodec": "avc1.4D402A",
                "acodec": "mp4a.40.2",
                "width": 1920,
            },
        ],
    }

    selected = select_playback_source(
        result=result,
        usemanifest=True,
        usedashbuilder=False,
        maxwidth=1920,
        isa_supports=lambda stream: stream == "hls",
    )

    assert selected["source"] == "format_manifest"
    assert selected["url"] == "https://example.com/live-master.m3u8"
    assert selected["isa"] is False


def test_select_playback_source_prefers_live_hls_manifest_without_isa_installed():
    result = {
        "is_live": True,
        "formats": [
            {
                "format": "301 - 1920x1080",
                "url": "https://example.com/live-1080-playlist.m3u8",
                "manifest_url": "https://example.com/live-master.m3u8",
                "protocol": "m3u8_native",
                "vcodec": "avc1.4D402A",
                "acodec": "mp4a.40.2",
                "width": 1920,
            },
        ],
    }

    selected = select_playback_source(
        result=result,
        usemanifest=True,
        usedashbuilder=False,
        maxwidth=1920,
        isa_supports=lambda _stream: False,
    )

    assert selected["source"] == "format_manifest"
    assert selected["url"] == "https://example.com/live-master.m3u8"
    assert selected["isa"] is False


def test_select_playback_source_keeps_strict_limit_for_live_hls():
    master = "https://example.com/live-master.m3u8"
    result = {
        "is_live": True,
        "formats": [
            {
                "format": "720",
                "url": "https://example.com/live-720.m3u8",
                "manifest_url": master,
                "protocol": "m3u8_native",
                "vcodec": "avc1",
                "acodec": "mp4a.40.2",
                "width": 1280,
            },
            {
                "format": "1080",
                "url": "https://example.com/live-1080.m3u8",
                "manifest_url": master,
                "protocol": "m3u8_native",
                "vcodec": "avc1",
                "acodec": "mp4a.40.2",
                "width": 1920,
            },
        ],
    }

    selected = select_playback_source(
        result=result,
        usemanifest=True,
        usedashbuilder=False,
        maxwidth=1280,
        isa_supports=lambda stream: stream == "hls",
        strict_max_resolution=True,
    )

    assert selected["source"] == "raw_format"
    assert selected["url"] == "https://example.com/live-720.m3u8"
    assert selected["isa"] is False
    assert selected["manifest_type"] == "hls"


def test_select_playback_source_reports_protocol_manifest_type():
    result = {
        "formats": [
            {
                "format": "azure-hls",
                "url": "https://x.streaming.media.azure.net/a/b.ism/manifest(format=m3u8-aapl)",
                "protocol": "m3u8_native",
                "vcodec": "avc1",
                "acodec": "mp4a.40.2",
                "width": 1280,
            },
        ],
    }

    selected = select_playback_source(
        result=result,
        usemanifest=False,
        usedashbuilder=False,
        maxwidth=1920,
        isa_supports=lambda _stream: True,
    )

    assert selected["manifest_type"] == "hls"


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


def test_select_playback_source_user_selected_stream_skips_format_manifest_path():
    result = {
        "formats": [
            {
                "format": "hls-choice",
                "url": "https://example.com/stream-360.m3u8",
                "manifest_url": "https://example.com/master.m3u8",
                "protocol": "m3u8_native",
                "vcodec": "avc1.64001f",
                "acodec": "mp4a.40.2",
                "width": 640,
            }
        ]
    }

    selected = select_playback_source(
        result=result,
        usemanifest=True,
        usedashbuilder=False,
        maxwidth=1920,
        isa_supports=lambda _stream: False,
        preferred_format_url="https://example.com/stream-360.m3u8",
    )

    assert selected["source"] == "raw_format"
    assert selected["url"] == "https://example.com/stream-360.m3u8"
    assert selected["isa"] is False


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


def test_select_playback_source_skips_audio_only_native_hls_opus_when_setting_enabled():
    result = {
        "formats": [
            {
                "format": "aac-audio",
                "url": "https://example.com/audio-aac.m3u8",
                "protocol": "m3u8_native",
                "vcodec": "none",
                "acodec": "aac",
            },
            {
                "format": "opus-audio",
                "url": "https://example.com/audio-opus.m3u8",
                "protocol": "m3u8_native",
                "vcodec": "none",
                "acodec": "opus",
            },
        ]
    }

    selected = select_playback_source(
        result=result,
        usemanifest=False,
        usedashbuilder=False,
        maxwidth=1920,
        isa_supports=lambda stream: stream == "hls",
        disable_opus_for_audio_only_hls_native=True,
    )

    assert selected["source"] == "raw_format"
    assert selected["url"] == "https://example.com/audio-aac.m3u8"


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


def test_select_playback_source_manual_dash_selection_uses_selected_video_stream_only():
    class SelectedDashModule:
        class Manifest:
            def __init__(self, _duration):
                self.video_formats = []
                self.audio_formats = []

            def add_video_format(self, format_info):
                self.video_formats.append(format_info.get("format"))

            def add_audio_format(self, format_info):
                self.audio_formats.append(format_info.get("format"))

            def emit(self):
                return "manifest-video-{}-audio-{}".format(
                    ",".join(self.video_formats),
                    ",".join(self.audio_formats),
                )

        @staticmethod
        def start_httpd(manifest):
            return "http://dummy.local/" + manifest

    result = {
        "duration": "10",
        "formats": [
            {
                "format": "v1080",
                "format_id": "137",
                "url": "https://example.com/v1080",
                "vcodec": "avc1",
                "acodec": "none",
                "container": "mp4_dash",
                "width": 1920,
            },
            {
                "format": "v4k",
                "format_id": "401",
                "url": "https://example.com/v4k",
                "vcodec": "avc1",
                "acodec": "none",
                "container": "mp4_dash",
                "width": 3840,
            },
            {
                "format": "a1",
                "url": "https://example.com/a1",
                "vcodec": "none",
                "acodec": "aac",
                "container": "m4a_dash",
            },
        ],
    }

    selected = select_playback_source(
        result=result,
        usemanifest=False,
        usedashbuilder=True,
        maxwidth=1920,
        isa_supports=lambda stream: stream == "mpd",
        dashbuilder=SelectedDashModule,
        preferred_format_url="https://example.com/v4k",
    )

    assert selected["source"] == "dash_manifest"
    assert selected["url"] == "http://dummy.local/manifest-video-v4k-audio-a1"


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


def test_split_playlist_entries_returns_none_for_empty_entries():
    starting, remaining = split_playlist_entries([], 0)

    assert starting is None
    assert remaining == []


def test_split_playlist_entries_defaults_to_first_entry_for_invalid_index():
    starting, remaining = split_playlist_entries([
        {"id": "a"},
        {"id": "b"},
    ], 99)

    assert starting == {"id": "a"}
    assert remaining == [{"id": "b"}]


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


def test_append_headers_to_url_returns_url_when_headers_none():
    result = append_headers_to_url(
        url="https://example.com/stream.mp4",
        headers=None
    )

    assert result == "https://example.com/stream.mp4"


def test_append_headers_to_url_returns_url_when_headers_empty():
    result = append_headers_to_url(
        url="https://example.com/stream.mp4",
        headers={}
    )

    assert result == "https://example.com/stream.mp4"


def test_append_headers_to_url_appends_headers_correctly():
    ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
    referer = "https://example.com"

    result = append_headers_to_url(
        url="https://example.com/stream.mp4",
        headers={"User-Agent": ua, "Referer": referer},
    )

    assert result == "https://example.com/stream.mp4|User-Agent={}&Referer={}".format(quote(ua), quote(referer))


def test_append_headers_to_url_preserves_url_with_query_params():
    result = append_headers_to_url(
        url="https://example.com/stream.mp4?token=abc",
        headers={"User-Agent": "TestAgent"},
    )

    assert result == "https://example.com/stream.mp4?token=abc|User-Agent=TestAgent"


def test_resolve_playlist_insert_position_skips_entries_without_url():
    entries = [{"url": "a"}, {"id": "no-url"}, {"url": "c"}, {"url": "d"}]
    starting_entry, unresolved = split_playlist_entries(entries, 3)

    assert starting_entry == {"url": "d"}
    assert resolve_playlist_insert_position(unresolved, 3) == 2


def test_resolve_playlist_insert_position_at_start():
    assert resolve_playlist_insert_position([{"url": "b"}], 0) == 0
