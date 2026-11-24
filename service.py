# -*- coding: utf-8 -*-
import sys
import importlib

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs
from core import dash_builder, history

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
    resolve_avoided_video_codecs,
    resolve_max_resolution,
    resolve_ytdlp_config_location,
)
from core.runtime.playback import (
    create_list_item_from_video,
    download_result_with_progress,
    extract_result_with_progress,
    play_playlist_result,
    _resolve_downloaded_file_path,
)
from core.runtime.actions import (
    configure_managed_ytdlp,
    handle_runtime_action,
    refresh_runtime_displays,
    update_runtimes_after_playback,
)
from core.kodi_settings import get_setting
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
        return get_setting(handle, "enable_legacy_python_workarounds") == 'true'
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

        return resolve_js_runtime_opts(handle, get_setting, get_deno_ydl_opts)
    except Exception as e:
        log("Failed to configure JavaScript runtime: {}".format(str(e)), xbmc.LOGWARNING)
        return {}


def _load_config_ytdlp_opts(handle, yt_dlp_module):
    """Return the options of the configured yt-dlp config file, or None if it cannot be loaded."""
    ytdlp_config_location = resolve_ytdlp_config_location(handle, get_setting)
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


def _apply_media_download_settings(handle, ydl_opts, force=False):
    media_download_settings = resolve_media_download_settings(handle, get_setting)
    if not media_download_settings['enabled'] and not force:
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


def play(plugin_url, handle, paramstring, url_override=None, download_only=False, history_id=None):
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

    if url_override is None:
        params = parse_cli_paramstring(paramstring)
        url = str(params['url'])
    else:
        # History replay: the page url comes from the history entry.
        params = {'url': url_override, 'ydlOpts': {}}
        url = url_override

    js_runtime_opts = _resolve_js_runtime_opts(handle)

    config_ytdlp_opts = _load_config_ytdlp_opts(handle, yt_dlp_module)
    if config_ytdlp_opts is None:
        xbmcplugin.setResolvedUrl(handle, False, listitem=xbmcgui.ListItem())
        return

    ydl_opts = build_ydl_opts(params, config_ytdlp_opts, js_runtime_opts)
    if download_only:
        # An explicit download always targets the configured media download
        # folder, whether or not auto-download on play is enabled.
        _apply_media_download_settings(handle, ydl_opts, force=True)
        media_download_enabled = False
    else:
        media_download_enabled = _apply_media_download_settings(handle, ydl_opts)

    usemanifest = get_setting(handle, "usemanifest") == 'true'
    usedashbuilder = get_setting(handle, "usedashbuilder") == 'true'
    askstream = get_setting(handle, "askstream") == 'true'
    disable_opus_for_audio_only_hls_native = (
        get_setting(handle, "audio_only_hls_disable_opus_native") == 'true'
    )
    dash_httpd_idle_timeout_seconds = resolve_dash_httpd_idle_timeout(handle, get_setting)
    dash_builder.DASH_HTTPD_IDLE_TIMEOUT_SECONDS = dash_httpd_idle_timeout_seconds
    log("DASH manifest refresh delay: {}s".format(dash_httpd_idle_timeout_seconds))
    maxwidth, strict_max_resolution = resolve_max_resolution(handle, get_setting)
    avoided_video_codecs = resolve_avoided_video_codecs(handle, get_setting)

    ydl = YoutubeDL(ydl_opts)
    ydl.add_default_info_extractors()

    with ydl:
        try:
            result = extract_result_with_progress(ydl, url)
            if download_only:
                _download_result(ydl, result, history_id, log)
                return
            if media_download_enabled and 'entries' not in result:
                result = download_result_with_progress(ydl, result)
        except Exception:
            handle_resolve_failure(handle, set_resolved_false=True)
            return

    playback_meta = {}

    def capture_playback_meta(meta):
        playback_meta.clear()
        playback_meta.update(meta)

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
                playback_meta_sink=capture_playback_meta,
            )
        except Exception:
            handle_resolve_failure(handle)
            return
        _record_playback(playback_meta)
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
                avoided_video_codecs=avoided_video_codecs,
                playback_meta_sink=capture_playback_meta,
            )
            xbmcplugin.setResolvedUrl(handle, True, listitem=list_item)
        except Exception:
            handle_resolve_failure(handle, set_resolved_false=True)
            return
        _record_playback(playback_meta)


def _record_playback(playback_meta):
    """Record a successful playback in the history."""
    if not playback_meta.get('webpage_url'):
        return
    history.record(playback_meta)


def _download_result(ydl, result, history_id, log):
    """Download a single video without playing it; reports via notifications.

    Playlists are not downloadable yet: downloading a whole playlist would
    require per-entry handling.
    """
    if 'entries' in result:
        showErrorNotification("Playlists cannot be downloaded yet")
        log("Download refused for a playlist result", xbmc.LOGWARNING)
        return
    try:
        result = download_result_with_progress(ydl, result)
    except Exception as exc:
        log("Could not download: {}".format(exc), xbmc.LOGERROR)
        showErrorNotification("Could not download the video, check the log for more info")
        return
    downloaded_file_path = _resolve_downloaded_file_path(result)
    if not downloaded_file_path:
        log("Download finished but no file path was reported", xbmc.LOGWARNING)
        showErrorNotification("Could not download the video, check the log for more info")
        return
    showInfoNotification("Downloaded to {}".format(downloaded_file_path))
    # A successful download refreshes the entry like a successful play and
    # sets its downloaded_at marker.
    if history_id:
        history.mark_downloaded(history_id)


def _resolve_action_id(paramstring):
    parsed = parse_query_params(paramstring)
    values = parsed.get("id")
    if not values:
        return None
    return values[0]


def _show_history_list(handle, plugin_url):
    """Render the playback history list; always a directory, even when empty."""
    entries = history.list_entries()
    xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_NONE)
    if not entries:
        empty_item = xbmcgui.ListItem("No recent playback", path=plugin_url + "?action=noop")
        # A folder, so selecting it re-renders the list instead of trying to play it.
        xbmcplugin.addDirectoryItem(handle, empty_item.getPath(), empty_item, isFolder=True)
    for entry in entries:
        title = entry.get('title') or entry.get('url') or ''
        if entry.get('downloaded_at') is not None:
            title += " [downloaded]"
        item = xbmcgui.ListItem(title, path="{}?action=replay&id={}".format(plugin_url, entry['id']))
        item.setProperty("IsPlayable", "true")
        item.addContextMenuItems([
            ("Download", "RunPlugin({})".format(plugin_url + "?action=download&id=" + entry['id'])),
        ])
        video_info = item.getVideoInfoTag()
        video_info.setTitle(title)
        if entry.get('thumbnail'):
            item.setArt({"thumb": entry['thumbnail']})
        xbmcplugin.addDirectoryItem(handle, item.getPath(), item, isFolder=False)
    settings_item = xbmcgui.ListItem("Settings", path=plugin_url + "?action=settings")
    # A folder: the settings action re-renders the list after the modal dialog.
    xbmcplugin.addDirectoryItem(handle, settings_item.getPath(), settings_item, isFolder=True)
    xbmcplugin.endOfDirectory(handle, succeeded=True, cacheToDisc=False)


def _handle_settings_action(handle, plugin_url):
    # openSettings is modal; re-render the list on the same handle afterwards.
    xbmcaddon.Addon().openSettings()
    _show_history_list(handle, plugin_url)


def _handle_replay_action(handle, plugin_url, paramstring, history_id):
    """Play a history entry: its page url goes through the normal resolve path."""
    entry = history.get(history_id)
    if entry is None:
        showErrorNotification("Unknown history entry")
        xbmcplugin.setResolvedUrl(handle, False, listitem=xbmcgui.ListItem())
        return
    play(plugin_url, handle, paramstring, url_override=entry['url'])


def _handle_download_action(handle, plugin_url, paramstring, history_id):
    """Download the video of a history entry without playing it."""
    entry = history.get(history_id)
    if entry is None:
        showErrorNotification("Unknown history entry")
        return
    play(
        plugin_url,
        handle,
        paramstring,
        url_override=entry['url'],
        download_only=True,
        history_id=history_id,
    )


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

    # Show the playback history when no parameters have been passed. Prevents
    # crash. This happens when the addon is launched from within the Kodi OSD.
    if not paramstring:
        refresh_runtime_displays(handle, log)
        _show_history_list(handle, plugin_url)
        return

    if handle_queue_action(plugin_url, paramstring):
        return

    action = resolve_action_param(paramstring)
    if action == 'settings':
        _handle_settings_action(handle, plugin_url)
        return
    if action == 'noop':
        _show_history_list(handle, plugin_url)
        return
    if action == 'replay':
        history_id = _resolve_action_id(paramstring)
        if not history_id:
            showErrorNotification("Missing history entry id")
            xbmcplugin.setResolvedUrl(handle, False, listitem=xbmcgui.ListItem())
            return
        try:
            _handle_replay_action(handle, plugin_url, paramstring, history_id)
        finally:
            update_runtimes_after_playback(handle, log)
        return
    if action == 'download':
        history_id = _resolve_action_id(paramstring)
        if not history_id:
            showErrorNotification("Missing history entry id")
            return
        try:
            _handle_download_action(handle, plugin_url, paramstring, history_id)
        finally:
            update_runtimes_after_playback(handle, log)
        return

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
