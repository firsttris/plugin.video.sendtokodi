from core.addon_params import (
    parse_cli_paramstring,
    build_flat_playlist_item_url,
    resolve_playlist_item_title,
    build_ydl_opts,
    resolve_deno_opts,
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
        lambda auto_download: {"auto_download": auto_download},
    )

    assert opts == {"auto_download": False}
