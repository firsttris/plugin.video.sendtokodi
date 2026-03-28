from core.addon_params import (
    DEFAULT_DENO_VERSION,
    DEFAULT_MEDIA_DOWNLOAD_PATH,
    DEFAULT_YTDLP_VERSION,
    parse_cli_paramstring,
    build_flat_playlist_item_url,
    resolve_playlist_item_title,
    build_ydl_opts,
    resolve_deno_settings,
    resolve_deno_opts,
    resolve_media_download_settings,
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


def test_resolve_deno_opts_returns_empty_when_disabled():
    get_setting = lambda _handle, name: "false" if name == "deno_enabled" else "true"

    opts = resolve_deno_opts(1, get_setting, lambda **_kwargs: {"should": "not-run"})

    assert opts == {}


def test_resolve_deno_opts_uses_autodownload_setting_when_enabled():
    def get_setting(_handle, name):
        if name == "deno_enabled":
            return "true"
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
        if name == "deno_enabled":
            return "true"
        if name == "deno_autodownload":
            return "false"
        if name == "deno_version":
            return "v2.7.4"
        return ""

    settings = resolve_deno_settings(1, get_setting)

    assert settings == {
        "enabled": True,
        "auto_update": False,
        "version": "v2.7.4",
    }


def test_resolve_deno_opts_forces_latest_when_auto_update_enabled():
    def get_setting(_handle, name):
        if name == "deno_enabled":
            return "true"
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
