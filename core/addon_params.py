import json


DEFAULT_MEDIA_DOWNLOAD_PATH = 'special://profile/addon_data/plugin.video.sendtokodi/downloads'
DEFAULT_YTDLP_VERSION = 'latest'
DEFAULT_DENO_VERSION = 'latest'


def parse_cli_paramstring(paramstring):
    additional_params_index = paramstring.find(' ')
    if additional_params_index == -1:
        return {'url': paramstring[1:], 'ydlOpts': {}}

    additional_params = json.loads(paramstring[additional_params_index:])
    return {
        'url': paramstring[1:additional_params_index],
        'ydlOpts': additional_params['ydlOpts'],
    }


def build_flat_playlist_item_url(plugin_url, video_url, paramstring):
    list_item_url = plugin_url + "?" + video_url
    additional_params_index = paramstring.find(' ')
    if additional_params_index != -1:
        list_item_url = list_item_url + " " + paramstring[additional_params_index:]
    return list_item_url


def resolve_playlist_item_title(video):
    if 'title' in video:
        return video['title']
    return video['url']


def build_ydl_opts(parsed_params, deno_opts=None):
    ydl_opts = {'extract_flat': 'in_playlist'}
    ydl_opts.update(parsed_params.get('ydlOpts', {}))
    if deno_opts:
        ydl_opts.update(deno_opts)
    return ydl_opts


def resolve_deno_opts(handle, get_setting, get_deno_ydl_opts):
    deno_enabled = get_setting(handle, "deno_enabled") == 'true'
    if not deno_enabled:
        return {}

    auto_update = get_setting(handle, "deno_autodownload") == 'true'
    version = (get_setting(handle, "deno_version") or '').strip()
    # Auto-update mode should track latest, not a previously pinned version.
    if auto_update:
        requested_version = DEFAULT_DENO_VERSION
    else:
        requested_version = version or DEFAULT_DENO_VERSION
    return get_deno_ydl_opts(auto_download=auto_update, requested_version=requested_version)


def resolve_deno_settings(handle, get_setting):
    enabled = get_setting(handle, "deno_enabled") == 'true'
    auto_update = get_setting(handle, "deno_autodownload") == 'true'
    version = (get_setting(handle, "deno_version") or '').strip()
    return {
        'enabled': enabled,
        'auto_update': auto_update,
        'version': version or DEFAULT_DENO_VERSION,
    }


def resolve_media_download_settings(handle, get_setting):
    enabled = get_setting(handle, "media_autodownload") == 'true'
    custom_path = get_setting(handle, "media_download_path")
    return {
        'enabled': enabled,
        'path': custom_path or DEFAULT_MEDIA_DOWNLOAD_PATH,
    }


def resolve_ytdlp_settings(handle, get_setting):
    auto_update = get_setting(handle, "ytdlp_autodownload") == 'true'
    version = (get_setting(handle, "ytdlp_version") or '').strip()
    return {
        'auto_update': auto_update,
        'version': version or DEFAULT_YTDLP_VERSION,
    }
