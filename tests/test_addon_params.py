from core.addon_params import (
    DEFAULT_DASH_HTTPD_IDLE_TIMEOUT_SECONDS,
    DEFAULT_DENO_VERSION,
    DEFAULT_JS_RUNTIME_MODE,
    MAX_DASH_HTTPD_IDLE_TIMEOUT_SECONDS,
    DEFAULT_MEDIA_DOWNLOAD_PATH,
    MIN_DASH_HTTPD_IDLE_TIMEOUT_SECONDS,
    DEFAULT_YTDLP_VERSION,
    parse_cli_paramstring,
    parse_query_params,
    resolve_queue_request,
    build_flat_playlist_item_url,
    build_ydl_opts_with_additional,
    resolve_playlist_item_title,
    build_ydl_opts,
    resolve_deno_settings,
    resolve_deno_opts,
    resolve_js_runtime_opts,
    resolve_quickjs_opts,
    resolve_dash_httpd_idle_timeout,
    resolve_media_download_settings,
    resolve_ytdlp_additional_opts,
    resolve_ytdlp_settings,
)


def test_parse_cli_paramstring_without_additional_options():
    parsed = parse_cli_paramstring("?https://example.com/video")

    assert parsed == {
        "url": "https://example.com/video",
        "ydlOpts": {},
    }


def test_parse_cli_paramstring_with_additional_options():
    parsed = parse_cli_paramstring('?https://example.com/video {"ydlOpts": {"extract_flat": "in_playlist"}}')

    assert parsed == {
        "url": "https://example.com/video",
        "ydlOpts": {"extract_flat": "in_playlist"},
    }


def test_parse_cli_paramstring_with_query_params_and_yt_dlp_options():
    parsed = parse_cli_paramstring(
        "?url=https%3A%2F%2Fexample.com%2Fvideo&yt-dlp-options=%7B%22format%22%3A%22best%22%7D"
    )

    assert parsed == {
        "url": "https://example.com/video",
        "ydlOpts": {"format": "best"},
    }


def test_parse_cli_paramstring_with_query_params_and_legacy_ydlopts():
    parsed = parse_cli_paramstring(
        "?url=https%3A%2F%2Fexample.com%2Fvideo&ydlOpts=%7B%22format%22%3A%22best%22%7D"
    )

    assert parsed == {
        "url": "https://example.com/video",
        "ydlOpts": {"format": "best"},
    }


def test_parse_query_params_extracts_query_before_ydl_opts_json():
    parsed = parse_query_params('?action=queue&url=https%3A%2F%2Fexample.com%2Fv%3Fa%3D1%26b%3D2 {"ydlOpts": {"format": "best"}}')

    assert parsed == {
        "action": ["queue"],
        "url": ["https://example.com/v?a=1&b=2"],
    }


def test_resolve_queue_request_reads_title():
    request = resolve_queue_request("?action=queue&url=https%3A%2F%2Fexample.com%2Fvideo&title=My%20Video")

    assert request == {
        "url": "https://example.com/video",
        "title": "My Video",
    }


def test_resolve_queue_request_supports_optional_title():
    request = resolve_queue_request("?action=queue&url=https%3A%2F%2Fexample.com%2Fvideo")

    assert request == {
        "url": "https://example.com/video",
        "title": None,
    }


def test_resolve_queue_request_returns_none_for_non_queue_actions():
    assert resolve_queue_request("?action=play&url=https%3A%2F%2Fexample.com%2Fvideo") is None


def test_resolve_queue_request_supports_short_action_alias_and_title_alias():
    request = resolve_queue_request("?action=q&url=https%3A%2F%2Fexample.com%2Fvideo&name=Alias%20Title")

    assert request == {
        "url": "https://example.com/video",
        "title": "Alias Title",
    }


def test_build_flat_playlist_item_url_without_additional_params():
    item_url = build_flat_playlist_item_url(
        "plugin://plugin.video.sendtokodi",
        "https://example.com/video",
        "?https://example.com/input",
    )

    assert item_url == "plugin://plugin.video.sendtokodi?https://example.com/video"


def test_build_flat_playlist_item_url_with_additional_params():
    item_url = build_flat_playlist_item_url(
        "plugin://plugin.video.sendtokodi",
        "https://example.com/video",
        '?https://example.com/input {"ydlOpts": {"extract_flat": "in_playlist"}}',
    )

    assert item_url == (
        'plugin://plugin.video.sendtokodi?https://example.com/video  '
        '{"ydlOpts": {"extract_flat": "in_playlist"}}'
    )


def test_build_flat_playlist_item_url_with_query_yt_dlp_options():
    item_url = build_flat_playlist_item_url(
        "plugin://plugin.video.sendtokodi",
        "https://example.com/video",
        "?url=https%3A%2F%2Fexample.com%2Finput&yt-dlp-options=%7B%22format%22%3A%22best%22%7D",
    )

    assert item_url == (
        "plugin://plugin.video.sendtokodi"
        "?url=https%3A%2F%2Fexample.com%2Fvideo&yt-dlp-options=%7B%22format%22%3A%22best%22%7D"
    )


def test_build_flat_playlist_item_url_with_query_legacy_ydlopts():
    item_url = build_flat_playlist_item_url(
        "plugin://plugin.video.sendtokodi",
        "https://example.com/video",
        "?url=https%3A%2F%2Fexample.com%2Finput&ydlOpts=%7B%22format%22%3A%22best%22%7D",
    )

    assert item_url == (
        "plugin://plugin.video.sendtokodi"
        "?url=https%3A%2F%2Fexample.com%2Fvideo&ydlOpts=%7B%22format%22%3A%22best%22%7D"
    )


def test_resolve_playlist_item_title_prefers_title_when_present():
    assert resolve_playlist_item_title({"title": "My Video", "url": "https://example.com"}) == "My Video"


def test_resolve_playlist_item_title_falls_back_to_url():
    assert resolve_playlist_item_title({"url": "https://example.com"}) == "https://example.com"


def test_build_ydl_opts_includes_extract_flat_and_params_opts():
    opts = build_ydl_opts({"ydlOpts": {"format": "best"}})

    assert opts == {
        "extract_flat": "in_playlist",
        "format": "best",
    }


def test_build_ydl_opts_merges_deno_opts_when_present():
    opts = build_ydl_opts(
        {"ydlOpts": {"format": "best"}},
        {"js_runtimes": {"deno": {"path": "/usr/bin/deno"}}},
    )

    assert opts == {
        "extract_flat": "in_playlist",
        "format": "best",
        "js_runtimes": {"deno": {"path": "/usr/bin/deno"}},
    }


def test_build_ydl_opts_with_additional_merges_all_sources():
    opts = build_ydl_opts_with_additional(
        {"ydlOpts": {"format": "best", "noplaylist": True}},
        {"cookiefile": "/tmp/cookies.txt", "format": "worst"},
        {"js_runtimes": {"deno": {"path": "/usr/bin/deno"}}},
    )

    assert opts == {
        "extract_flat": "in_playlist",
        "cookiefile": "/tmp/cookies.txt",
        "format": "best",
        "noplaylist": True,
        "js_runtimes": {"deno": {"path": "/usr/bin/deno"}},
    }


def test_resolve_ytdlp_additional_opts_from_inline_json():
    def get_setting(_handle, name):
        if name == "ytdlp_extra_options_json":
            return '{"cookiefile": "/tmp/cookies.txt"}'
        if name == "ytdlp_load_options_file":
            return "false"
        if name == "ytdlp_options_file_path":
            return ""
        return ""

    opts = resolve_ytdlp_additional_opts(1, get_setting)

    assert opts == {
        "cookiefile": "/tmp/cookies.txt",
    }


def test_resolve_ytdlp_additional_opts_from_file_json():
    def get_setting(_handle, name):
        if name == "ytdlp_extra_options_json":
            return ""
        if name == "ytdlp_load_options_file":
            return "true"
        if name == "ytdlp_options_file_path":
            return "special://profile/addon_data/plugin.video.sendtokodi/ytdlp-options.json"
        return ""

    opts = resolve_ytdlp_additional_opts(
        1,
        get_setting,
        read_file_contents=lambda _path: '{"extractor_args": {"youtube": {"player_client": ["tv"]}}}',
    )

    assert opts == {
        "extractor_args": {"youtube": {"player_client": ["tv"]}},
    }


def test_resolve_ytdlp_additional_opts_inline_overrides_file_keys():
    def get_setting(_handle, name):
        if name == "ytdlp_extra_options_json":
            return '{"format": "best"}'
        if name == "ytdlp_load_options_file":
            return "true"
        if name == "ytdlp_options_file_path":
            return "any.json"
        return ""

    opts = resolve_ytdlp_additional_opts(
        1,
        get_setting,
        read_file_contents=lambda _path: '{"format": "worst", "cookiefile": "/tmp/cookies.txt"}',
    )

    assert opts == {
        "format": "best",
        "cookiefile": "/tmp/cookies.txt",
    }


def test_resolve_ytdlp_additional_opts_raises_for_invalid_inline_json():
    def get_setting(_handle, name):
        if name == "ytdlp_extra_options_json":
            return "{oops"
        if name == "ytdlp_load_options_file":
            return "false"
        if name == "ytdlp_options_file_path":
            return ""
        return ""

    try:
        resolve_ytdlp_additional_opts(1, get_setting)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "ytdlp_extra_options_json" in str(exc)


def test_resolve_ytdlp_additional_opts_raises_when_file_enabled_without_path():
    def get_setting(_handle, name):
        if name == "ytdlp_extra_options_json":
            return ""
        if name == "ytdlp_load_options_file":
            return "true"
        if name == "ytdlp_options_file_path":
            return ""
        return ""

    try:
        resolve_ytdlp_additional_opts(1, get_setting, read_file_contents=lambda _path: "{}")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "ytdlp_options_file_path" in str(exc)


def test_resolve_ytdlp_additional_opts_raises_for_non_object_json():
    def get_setting(_handle, name):
        if name == "ytdlp_extra_options_json":
            return ""
        if name == "ytdlp_load_options_file":
            return "true"
        if name == "ytdlp_options_file_path":
            return "opts.json"
        return ""

    try:
        resolve_ytdlp_additional_opts(
            1,
            get_setting,
            read_file_contents=lambda _path: '["not", "an", "object"]',
        )
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "JSON object" in str(exc)


def test_resolve_deno_opts_reads_settings_without_enable_toggle():
    def get_setting(_handle, name):
        if name == "deno_autodownload":
            return "false"
        if name == "deno_version":
            return "v2.7.5"
        return ""

    opts = resolve_deno_opts(
        1,
        get_setting,
        lambda auto_download, requested_version: {
            "auto_update": auto_download,
            "requested_version": requested_version,
        },
    )

    assert opts == {
        "auto_update": False,
        "requested_version": "v2.7.5",
    }


def test_resolve_deno_opts_uses_autodownload_setting_when_enabled():
    def get_setting(_handle, name):
        if name == "deno_autodownload":
            return "false"
        return ""

    opts = resolve_deno_opts(
        1,
        get_setting,
        lambda auto_download, requested_version: {
            "auto_update": auto_download,
            "requested_version": requested_version,
        },
    )

    assert opts == {
        "auto_update": False,
        "requested_version": DEFAULT_DENO_VERSION,
    }


def test_resolve_deno_settings_reads_all_values():
    def get_setting(_handle, name):
        if name == "deno_autodownload":
            return "false"
        if name == "deno_version":
            return "v2.7.4"
        return ""

    settings = resolve_deno_settings(1, get_setting)

    assert settings == {
        "enabled": False,
        "auto_update": False,
        "version": "v2.7.4",
    }


def test_resolve_deno_opts_forces_latest_when_auto_update_enabled():
    def get_setting(_handle, name):
        if name == "deno_autodownload":
            return "true"
        if name == "deno_version":
            return "v2.7.5"
        return ""

    opts = resolve_deno_opts(
        1,
        get_setting,
        lambda auto_download, requested_version: {
            "auto_update": auto_download,
            "requested_version": requested_version,
        },
    )

    assert opts == {
        "auto_update": True,
        "requested_version": DEFAULT_DENO_VERSION,
    }


def test_resolve_quickjs_opts_returns_empty_when_path_missing():
    def get_setting(_handle, name):
        if name == "quickjs_path":
            return ""
        return ""

    opts = resolve_quickjs_opts(1, get_setting)

    assert opts == {}


def test_resolve_quickjs_opts_returns_expected_opts_when_enabled_and_valid_path():
    def get_setting(_handle, name):
        if name == "quickjs_path":
            return "/storage/downloads/qjs"
        return ""

    opts = resolve_quickjs_opts(
        1,
        get_setting,
        path_exists=lambda _path: True,
        is_executable=lambda _path, _flag: True,
    )

    assert opts == {
        "js_runtimes": {"quickjs": {"path": "/storage/downloads/qjs"}},
        "remote_components": {"ejs:github"},
    }


def test_resolve_js_runtime_opts_mode_deno_prefers_deno():
    def get_setting(_handle, name):
        if name == "js_runtime_mode":
            return "deno"
        if name == "deno_autodownload":
            return "false"
        if name == "deno_version":
            return ""
        if name == "quickjs_path":
            return "/storage/downloads/qjs"
        return ""

    opts = resolve_js_runtime_opts(
        1,
        get_setting,
        lambda auto_download, requested_version: {
            "js_runtimes": {"deno": {"path": "/usr/bin/deno"}},
            "requested_version": requested_version,
            "auto_download": auto_download,
        },
        get_machine=lambda: "armv7l",
        path_exists=lambda _path: True,
        is_executable=lambda _path, _flag: True,
    )

    assert opts["js_runtimes"] == {"deno": {"path": "/usr/bin/deno"}}


def test_resolve_js_runtime_opts_mode_quickjs_prefers_quickjs():
    def get_setting(_handle, name):
        if name == "js_runtime_mode":
            return "quickjs"
        if name == "deno_autodownload":
            return "true"
        if name == "deno_version":
            return ""
        if name == "quickjs_path":
            return "/storage/downloads/qjs"
        return ""

    opts = resolve_js_runtime_opts(
        1,
        get_setting,
        lambda **_kwargs: {"js_runtimes": {"deno": {"path": "/usr/bin/deno"}}},
        get_machine=lambda: "x86_64",
        path_exists=lambda _path: True,
        is_executable=lambda _path, _flag: True,
    )

    assert opts == {
        "js_runtimes": {"quickjs": {"path": "/storage/downloads/qjs"}},
        "remote_components": {"ejs:github"},
    }


def test_resolve_js_runtime_opts_mode_quickjs_does_not_call_deno():
    def get_setting(_handle, name):
        if name == "js_runtime_mode":
            return "quickjs"
        if name == "quickjs_path":
            return "/storage/downloads/qjs"
        return ""

    def fail_if_called(**_kwargs):
        raise AssertionError("deno resolver should not run in quickjs mode")

    opts = resolve_js_runtime_opts(
        1,
        get_setting,
        fail_if_called,
        get_machine=lambda: "x86_64",
        path_exists=lambda _path: True,
        is_executable=lambda _path, _flag: True,
    )

    assert opts == {
        "js_runtimes": {"quickjs": {"path": "/storage/downloads/qjs"}},
        "remote_components": {"ejs:github"},
    }


def test_resolve_js_runtime_opts_auto_prefers_quickjs_on_armv7():
    def get_setting(_handle, name):
        if name == "js_runtime_mode":
            return "auto"
        if name == "deno_autodownload":
            return "true"
        if name == "deno_version":
            return ""
        if name == "quickjs_path":
            return "/storage/downloads/qjs"
        return ""

    opts = resolve_js_runtime_opts(
        1,
        get_setting,
        lambda **_kwargs: {"js_runtimes": {"deno": {"path": "/usr/bin/deno"}}},
        get_machine=lambda: "armv7l",
        path_exists=lambda _path: True,
        is_executable=lambda _path, _flag: True,
    )

    assert opts == {
        "js_runtimes": {"quickjs": {"path": "/storage/downloads/qjs"}},
        "remote_components": {"ejs:github"},
    }


def test_resolve_js_runtime_opts_auto_falls_back_to_deno_when_quickjs_missing():
    def get_setting(_handle, name):
        if name == "js_runtime_mode":
            return "auto"
        if name == "deno_autodownload":
            return "false"
        if name == "deno_version":
            return "v2.7.5"
        if name == "quickjs_path":
            return ""
        return ""

    opts = resolve_js_runtime_opts(
        1,
        get_setting,
        lambda auto_download, requested_version: {
            "js_runtimes": {"deno": {"path": "/usr/bin/deno"}},
            "requested_version": requested_version,
            "auto_download": auto_download,
        },
        get_machine=lambda: "armv7l",
    )

    assert opts["js_runtimes"] == {"deno": {"path": "/usr/bin/deno"}}


def test_resolve_js_runtime_opts_invalid_mode_defaults_to_auto():
    def get_setting(_handle, name):
        if name == "js_runtime_mode":
            return "invalid"
        if name == "deno_autodownload":
            return "false"
        if name == "deno_version":
            return ""
        if name == "quickjs_path":
            return ""
        return ""

    opts = resolve_js_runtime_opts(
        1,
        get_setting,
        lambda **_kwargs: {},
        get_machine=lambda: "x86_64",
    )

    assert DEFAULT_JS_RUNTIME_MODE == "auto"
    assert opts == {}


def test_resolve_js_runtime_opts_disabled_returns_empty_even_when_runtimes_exist():
    def get_setting(_handle, name):
        if name == "js_runtime_mode":
            return "disabled"
        if name == "deno_autodownload":
            return "true"
        if name == "deno_version":
            return ""
        if name == "quickjs_path":
            return "/storage/downloads/qjs"
        return ""

    opts = resolve_js_runtime_opts(
        1,
        get_setting,
        lambda **_kwargs: {"js_runtimes": {"deno": {"path": "/usr/bin/deno"}}},
        get_machine=lambda: "armv7l",
        path_exists=lambda _path: True,
        is_executable=lambda _path, _flag: True,
    )

    assert opts == {}


def test_resolve_media_download_settings_defaults_to_disabled_and_default_path():
    def get_setting(_handle, name):
        if name == "media_autodownload":
            return "false"
        if name == "media_download_path":
            return ""
        return ""

    settings = resolve_media_download_settings(1, get_setting)

    assert settings == {
        "enabled": False,
        "path": DEFAULT_MEDIA_DOWNLOAD_PATH,
    }


def test_resolve_media_download_settings_uses_custom_path_when_set():
    def get_setting(_handle, name):
        if name == "media_autodownload":
            return "true"
        if name == "media_download_path":
            return "/tmp/sendtokodi-downloads"
        return ""

    settings = resolve_media_download_settings(1, get_setting)

    assert settings == {
        "enabled": True,
        "path": "/tmp/sendtokodi-downloads",
    }


def test_resolve_ytdlp_settings_uses_defaults_when_version_empty():
    def get_setting(_handle, name):
        if name == "ytdlp_autodownload":
            return "true"
        if name == "ytdlp_version":
            return ""
        return ""

    settings = resolve_ytdlp_settings(1, get_setting)

    assert settings == {
        "auto_update": True,
        "version": DEFAULT_YTDLP_VERSION,
    }


def test_resolve_ytdlp_settings_reads_all_values():
    def get_setting(_handle, name):
        if name == "ytdlp_autodownload":
            return "false"
        if name == "ytdlp_version":
            return "2026.03.26"
        return ""

    settings = resolve_ytdlp_settings(1, get_setting)

    assert settings == {
        "auto_update": False,
        "version": "2026.03.26",
    }


def test_resolve_dash_httpd_idle_timeout_uses_default_when_missing():
    value = resolve_dash_httpd_idle_timeout(1, lambda _handle, _name: "")

    assert value == DEFAULT_DASH_HTTPD_IDLE_TIMEOUT_SECONDS


def test_resolve_dash_httpd_idle_timeout_uses_default_when_invalid():
    value = resolve_dash_httpd_idle_timeout(1, lambda _handle, _name: "abc")

    assert value == DEFAULT_DASH_HTTPD_IDLE_TIMEOUT_SECONDS


def test_resolve_dash_httpd_idle_timeout_clamps_to_minimum():
    value = resolve_dash_httpd_idle_timeout(1, lambda _handle, _name: "1")

    assert value == MIN_DASH_HTTPD_IDLE_TIMEOUT_SECONDS


def test_resolve_dash_httpd_idle_timeout_clamps_to_maximum():
    value = resolve_dash_httpd_idle_timeout(1, lambda _handle, _name: "9999")

    assert value == MAX_DASH_HTTPD_IDLE_TIMEOUT_SECONDS


def test_resolve_dash_httpd_idle_timeout_accepts_valid_integer():
    value = resolve_dash_httpd_idle_timeout(1, lambda _handle, _name: "180")

    assert value == 180
