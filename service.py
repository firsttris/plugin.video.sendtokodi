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
    resolve_plugin_invocation,
    build_ydl_opts,
    load_ytdlp_config_options,
    resolve_js_runtime_opts,
    resolve_local_ytdlp_config_path,
    resolve_media_download_settings,
    resolve_dash_httpd_idle_timeout,
    resolve_max_resolution,
    resolve_ytdlp_config_location,
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
    update_runtimes_after_playback,
)
from core.service_runtime import install_stderr_workaround, patch_strptime

def debug(content):
    log(content, xbmc.LOGDEBUG)


ADDON_ID = 'plugin.video.sendtokodi'


def log(msg, level=xbmc.LOGINFO):
    xbmc.log('%s: %s' % (ADDON_ID, msg), level)


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


YTDLP_CONFIG_LOCAL_COPY_PATH = 'special://profile/addon_data/plugin.video.sendtokodi/yt-dlp-config-copy.conf'


def _legacy_python_workarounds_enabled(handle):
    try:
        return xbmcplugin.getSetting(handle, "enable_legacy_python_workarounds") == 'true'
    except Exception:
        return False


_isa_support_cache = {}

try:
    import inputstreamhelper

    def isa_supports(stream):
        if stream is None or len(stream) < 1:
            return False
        # Stream selection asks for the same types once per format; check each only once.
        if stream not in _isa_support_cache:
            _isa_support_cache[stream] = inputstreamhelper.Helper(stream).check_inputstream()
        return _isa_support_cache[stream]
except ImportError:
    def isa_supports(stream):
        return False


def handle_resolve_failure(handle, set_resolved_false=False):
    showErrorNotification("Could not resolve the url, check the log for more info")
    import traceback
    log(msg=traceback.format_exc(), level=xbmc.LOGERROR)
    if set_resolved_false:
        xbmcplugin.setResolvedUrl(handle, False, listitem=xbmcgui.ListItem())


def resolve_action_param(paramstring):
    parsed = parse_query_params(paramstring)
    values = parsed.get("action")
    if not values:
        return None
    return values[0]


def handle_queue_action(plugin_url, paramstring):
    request = resolve_queue_request(paramstring)
    if request is None:
        return False

    playlist = xbmc.PlayList(1)

    queue_url = plugin_url + "?" + request["url"]
    queue_title = request["title"] or request["url"]
    list_item = xbmcgui.ListItem(path=queue_url, label=queue_title)
    list_item.getVideoInfoTag().setTitle(queue_title)
    list_item.setProperty("IsPlayable", "true")
    playlist.add(list_item.getPath(), list_item)

    showInfoNotification("Added to queue: {}".format(queue_title))

    return True


def _resolve_js_runtime_opts(handle):
    try:
        from core.deno_manager import get_ydl_opts

        def get_deno_ydl_opts(**kwargs):
            # An installed Deno is used right away; updates run after playback started.
            return get_ydl_opts(prefer_installed=True, **kwargs)

        return resolve_js_runtime_opts(handle, xbmcplugin.getSetting, get_deno_ydl_opts)
    except Exception as e:
        log("Failed to configure JavaScript runtime: {}".format(str(e)), xbmc.LOGWARNING)
        return {}


def _load_config_ytdlp_opts(handle, yt_dlp_module):
    """Return the options of the configured yt-dlp config file, or None if it cannot be loaded."""
    ytdlp_config_location = resolve_ytdlp_config_location(handle, xbmcplugin.getSetting)
    if not ytdlp_config_location:
        return {}
    try:
        return load_ytdlp_config_options(
            resolve_local_ytdlp_config_path(
                ytdlp_config_location,
                xbmcvfs.translatePath,
                xbmcvfs.copy,
                YTDLP_CONFIG_LOCAL_COPY_PATH,
            ),
            getattr(yt_dlp_module, 'parse_options', None),
        )
    # yt-dlp reports invalid configs via optparse errors or SystemExit (e.g. from parser.error).
    except (Exception, SystemExit) as exc:
        showErrorNotification("Could not load yt-dlp config")
        log("Could not load yt-dlp config: {}".format(exc), xbmc.LOGERROR)
        return None


def _apply_media_download_settings(handle, ydl_opts):
    media_download_settings = resolve_media_download_settings(handle, xbmcplugin.getSetting)
    if not media_download_settings['enabled']:
        return False

    translated_media_download_path = xbmcvfs.translatePath(media_download_settings['path'])
    if not xbmcvfs.exists(translated_media_download_path):
        if not xbmcvfs.mkdirs(translated_media_download_path):
            log(
                "Failed to create media download path {}".format(translated_media_download_path),
                xbmc.LOGWARNING,
            )
    ydl_opts['paths'] = {'home': translated_media_download_path}
    log("Media auto-download enabled. Target path: {}".format(translated_media_download_path))
    return True


def play(plugin_url, handle, paramstring):
    """Resolve the sent url with yt-dlp and hand the result to Kodi."""
    configure_managed_ytdlp(handle, log)

    # yt-dlp is the only supported resolver
    try:
        yt_dlp_module = importlib.import_module("yt_dlp")
        YoutubeDL = yt_dlp_module.YoutubeDL
    except Exception as exc:
        showErrorNotification("yt-dlp is unavailable")
        log("yt-dlp import failed: {}".format(exc), xbmc.LOGERROR)
        xbmcplugin.setResolvedUrl(handle, False, listitem=xbmcgui.ListItem())
        return

    params = parse_cli_paramstring(paramstring)
    url = str(params['url'])

    js_runtime_opts = _resolve_js_runtime_opts(handle)

    config_ytdlp_opts = _load_config_ytdlp_opts(handle, yt_dlp_module)
    if config_ytdlp_opts is None:
        xbmcplugin.setResolvedUrl(handle, False, listitem=xbmcgui.ListItem())
        return

    ydl_opts = build_ydl_opts(params, config_ytdlp_opts, js_runtime_opts)
    media_download_enabled = _apply_media_download_settings(handle, ydl_opts)

    usemanifest = xbmcplugin.getSetting(handle, "usemanifest") == 'true'
    usedashbuilder = xbmcplugin.getSetting(handle, "usedashbuilder") == 'true'
    askstream = xbmcplugin.getSetting(handle, "askstream") == 'true'
    disable_opus_for_audio_only_hls_native = (
        xbmcplugin.getSetting(handle, "audio_only_hls_disable_opus_native") == 'true'
    )
    dash_httpd_idle_timeout_seconds = resolve_dash_httpd_idle_timeout(handle, xbmcplugin.getSetting)
    dash_builder.DASH_HTTPD_IDLE_TIMEOUT_SECONDS = dash_httpd_idle_timeout_seconds
    log("DASH MPD server idle timeout: {}s".format(dash_httpd_idle_timeout_seconds))
    maxwidth, strict_max_resolution = resolve_max_resolution(handle, xbmcplugin.getSetting)

    ydl = YoutubeDL(ydl_opts)
    ydl.add_default_info_extractors()

    with ydl:
        try:
            result = extract_result_with_progress(ydl, url)
            if media_download_enabled and 'entries' not in result:
                result = download_result_with_progress(ydl, result)
        except Exception:
            handle_resolve_failure(handle, set_resolved_false=True)
            return

    if 'entries' in result:
        try:
            play_playlist_result(
                result,
                url,
                ydl,
                plugin_url,
                paramstring,
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
            handle_resolve_failure(handle)
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
            xbmcplugin.setResolvedUrl(handle, True, listitem=list_item)
        except Exception:
            handle_resolve_failure(handle, set_resolved_false=True)


def main(argv):
    invocation = resolve_plugin_invocation(argv)
    # The plugin url in plugin:// notation, the plugin handle and the query.
    plugin_url = invocation['url']
    handle = invocation['handle']
    paramstring = invocation['paramstring']

    if _legacy_python_workarounds_enabled(handle):
        install_stderr_workaround()

    # Kodi's sub-interpreters break datetime.strptime up to Python 3.12 (see
    # core/service_runtime.py, #177), so always patch it, before yt-dlp is used.
    patch_strptime()

    # Open the settings if no parameters have been passed. Prevents crash.
    # This happens when the addon is launched from within the Kodi OSD.
    if not paramstring:
        refresh_runtime_displays(handle, log)
        xbmcaddon.Addon().openSettings()
        return

    if handle_queue_action(plugin_url, paramstring):
        return

    action = resolve_action_param(paramstring)
    if action is not None and handle_runtime_action(
        action,
        handle,
        run_with_progress,
        showInfoNotification,
        showErrorNotification,
        log,
    ):
        return

    try:
        play(plugin_url, handle, paramstring)
    finally:
        # Kodi already plays (or has given up on) the stream at this point, so
        # checking for runtime updates no longer delays playback.
        update_runtimes_after_playback(handle, log)


main(sys.argv)
