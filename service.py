# -*- coding: utf-8 -*-
import sys
import importlib

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs
from core import dash_builder

from core.addon_params import (
    parse_cli_paramstring,
    parse_query_params,
    resolve_queue_request,
    build_ydl_opts_with_additional,
    resolve_js_runtime_opts,
    resolve_media_download_settings,
    resolve_ytdlp_plugin_dirs,
    resolve_ytdlp_additional_opts,
    resolve_dash_httpd_idle_timeout,
)
from core.runtime.playback import (
    create_list_item_from_video,
    download_result_with_progress,
    extract_result_with_progress,
    play_playlist_result,
)
from core.runtime.actions import (
    configure_managed_ytdlp,
    handle_runtime_action,
    refresh_runtime_displays,
)
from core.service_runtime import install_stderr_workaround, patch_strptime

def debug(content):
    log(content, xbmc.LOGDEBUG)


def log(msg, level=xbmc.LOGINFO):
    addon = xbmcaddon.Addon()
    addonID = addon.getAddonInfo('id')
    xbmc.log('%s: %s' % (addonID, msg), level)


def showInfoNotification(message):
    xbmcgui.Dialog().notification("SendToKodi", message, xbmcgui.NOTIFICATION_INFO, 5000)


def showErrorNotification(message):
    xbmcgui.Dialog().notification("SendToKodi", message,
                                  xbmcgui.NOTIFICATION_ERROR, 5000)


def showTextDialog(title, message):
    try:
        xbmcgui.Dialog().textviewer(title, message)
    except Exception:
        xbmcgui.Dialog().ok(title, message)


def run_with_progress(title, message, operation):
    progress = None
    try:
        progress = xbmcgui.DialogProgress()
        progress.create(title, message)
        progress.update(10, message)
    except Exception:
        progress = None

    try:
        result = operation()
        if progress is not None:
            progress.update(100, message)
        return result
    finally:
        if progress is not None:
            progress.close()


def _read_text_file_with_xbmcvfs(path):
    translated_path = xbmcvfs.translatePath(path)
    if not xbmcvfs.exists(translated_path):
        raise ValueError('yt-dlp options file not found: {}'.format(path))

    file_handle = xbmcvfs.File(translated_path)
    try:
        return file_handle.read()
    finally:
        file_handle.close()


# Get the plugin url in plugin:// notation.
__url__ = sys.argv[0]
# Get the plugin handle as an integer number.
__handle__ = int(sys.argv[1])


def _legacy_python_workarounds_enabled(handle):
    try:
        return xbmcplugin.getSetting(handle, "enable_legacy_python_workarounds") == 'true'
    except Exception:
        return False


legacy_python_workarounds_enabled = _legacy_python_workarounds_enabled(__handle__)
if legacy_python_workarounds_enabled:
    install_stderr_workaround()


try:
    import inputstreamhelper

    def isa_supports(stream):
        if stream is None or len(stream) < 1:
            return False
        return inputstreamhelper.Helper(stream).check_inputstream()
except ImportError:
    def isa_supports(stream):
        return False


def handle_resolve_failure(set_resolved_false=False):
    showErrorNotification("Could not resolve the url, check the log for more info")
    import traceback
    log(msg=traceback.format_exc(), level=xbmc.LOGERROR)
    if set_resolved_false:
        xbmcplugin.setResolvedUrl(__handle__, False, listitem=xbmcgui.ListItem())
    exit()


def resolve_action_param(paramstring):
    parsed = parse_query_params(paramstring)
    values = parsed.get("action")
    if not values:
        return None
    return values[0]


def handle_queue_action(paramstring):
    request = resolve_queue_request(paramstring)
    if request is None:
        return False

    playlist = xbmc.PlayList(1)

    queue_url = __url__ + "?" + request["url"]
    queue_title = request["title"] or request["url"]
    list_item = xbmcgui.ListItem(path=queue_url, label=queue_title)
    list_item.getVideoInfoTag().setTitle(queue_title)
    list_item.setProperty("IsPlayable", "true")
    playlist.add(list_item.getPath(), list_item)

    showInfoNotification("Added to queue: {}".format(queue_title))

    return True

# Open the settings if no parameters have been passed. Prevents crash.
# This happens when the addon is launched from within the Kodi OSD.
if not sys.argv[2]:
    refresh_runtime_displays(__handle__, log)
    xbmcaddon.Addon().openSettings()
    exit()

if handle_queue_action(sys.argv[2]):
    exit()

action = resolve_action_param(sys.argv[2])
if action is not None and handle_runtime_action(
    action,
    __handle__,
    run_with_progress,
    showInfoNotification,
    showErrorNotification,
    log,
):
    exit()

configure_managed_ytdlp(__handle__, log)

# yt-dlp is the only supported resolver
try:
    YoutubeDL = importlib.import_module("yt_dlp").YoutubeDL
except Exception as exc:
    showErrorNotification("yt-dlp is unavailable")
    log("yt-dlp import failed: {}".format(exc), xbmc.LOGERROR)
    exit()

# patch broken strptime (see above)
if legacy_python_workarounds_enabled:
    patch_strptime()

params = parse_cli_paramstring(sys.argv[2])
url = str(params['url'])

js_runtime_opts = {}
try:
    from core.deno_manager import get_ydl_opts
    js_runtime_opts = resolve_js_runtime_opts(__handle__, xbmcplugin.getSetting, get_ydl_opts)
except Exception as e:
    log("Failed to configure JavaScript runtime: {}".format(str(e)), xbmc.LOGWARNING)

additional_ytdlp_opts = {}
try:
    additional_ytdlp_opts = resolve_ytdlp_additional_opts(
        __handle__,
        xbmcplugin.getSetting,
        _read_text_file_with_xbmcvfs,
    )
except Exception as e:
    log("Ignoring invalid additional yt-dlp options: {}".format(str(e)), xbmc.LOGWARNING)
    showErrorNotification("Invalid additional yt-dlp options (see log)")

ydl_opts = build_ydl_opts_with_additional(params, additional_ytdlp_opts, js_runtime_opts)

try:
    plugin_dirs = resolve_ytdlp_plugin_dirs(__handle__, xbmcplugin.getSetting, xbmcvfs.translatePath)
    if plugin_dirs and 'plugin_dirs' not in ydl_opts:
        # Keep default yt-dlp plugin discovery while adding SendToKodi-managed paths.
        ydl_opts['plugin_dirs'] = plugin_dirs + ['default']
        log('Enabled yt-dlp plugin directories: {}'.format(', '.join(plugin_dirs)))
except Exception as e:
    log('Ignoring invalid yt-dlp plugin directory settings: {}'.format(str(e)), xbmc.LOGWARNING)
    showErrorNotification('Invalid yt-dlp plugin directories (see log)')

media_download_settings = resolve_media_download_settings(__handle__, xbmcplugin.getSetting)
media_download_enabled = media_download_settings['enabled']
media_download_path = media_download_settings['path']

if media_download_enabled:
    translated_media_download_path = xbmcvfs.translatePath(media_download_path)
    if not xbmcvfs.exists(translated_media_download_path):
        if not xbmcvfs.mkdirs(translated_media_download_path):
            log(
                "Failed to create media download path {}".format(translated_media_download_path),
                xbmc.LOGWARNING,
            )
    ydl_opts['paths'] = {'home': translated_media_download_path}
    log("Media auto-download enabled. Target path: {}".format(translated_media_download_path))

usemanifest = xbmcplugin.getSetting(__handle__,"usemanifest") == 'true'
usedashbuilder = xbmcplugin.getSetting(__handle__,"usedashbuilder") == 'true'
askstream = xbmcplugin.getSetting(__handle__,"askstream") == 'true'
disable_opus_for_audio_only_hls_native = (
    xbmcplugin.getSetting(__handle__, "audio_only_hls_disable_opus_native") == 'true'
)
dash_httpd_idle_timeout_seconds = resolve_dash_httpd_idle_timeout(__handle__, xbmcplugin.getSetting)
dash_builder.DASH_HTTPD_IDLE_TIMEOUT_SECONDS = dash_httpd_idle_timeout_seconds
log("DASH MPD server idle timeout: {}s".format(dash_httpd_idle_timeout_seconds))
maxresolution_setting = int(xbmcplugin.getSetting(__handle__, "maxresolution"))
strict_max_resolution = maxresolution_setting >= 0
maxwidth = maxresolution_setting if strict_max_resolution else 7680

ydl = YoutubeDL(ydl_opts)
ydl.add_default_info_extractors()

with ydl:
    try:
        result = extract_result_with_progress(ydl, url)
        if media_download_enabled and 'entries' not in result:
            result = download_result_with_progress(ydl, url)
    except Exception:
        handle_resolve_failure()

if 'entries' in result:
    try:
        play_playlist_result(
            result,
            url,
            ydl,
            __url__,
            sys.argv[2],
            media_download_enabled,
            ydl_opts,
            usemanifest,
            usedashbuilder,
            maxwidth,
            strict_max_resolution,
            askstream,
            disable_opus_for_audio_only_hls_native,
            isa_supports,
            YoutubeDL,
            log,
            showErrorNotification,
        )
    except Exception:
        handle_resolve_failure()
else:
    try:
        list_item = create_list_item_from_video(
            result,
            ydl_opts,
            usemanifest,
            usedashbuilder,
            maxwidth,
            strict_max_resolution,
            askstream,
            disable_opus_for_audio_only_hls_native,
            isa_supports,
            YoutubeDL,
            log,
            showErrorNotification,
        )
        xbmcplugin.setResolvedUrl(__handle__, True, listitem=list_item)
    except Exception:
        handle_resolve_failure(set_resolved_false=True)
