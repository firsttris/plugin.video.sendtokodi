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
    build_flat_playlist_item_url,
    resolve_playlist_item_title,
    build_ydl_opts,
    resolve_deno_settings,
    resolve_deno_opts,
    resolve_media_download_settings,
    resolve_ytdlp_settings,
    resolve_dash_httpd_idle_timeout,
)
from core.service_runtime import install_stderr_workaround, patch_strptime
from core.playback_selection import (
    find_playlist_start_index,
    collect_subtitle_urls,
    encode_inputstream_headers,
    resolve_effective_headers,
    resolve_start_index,
    select_playback_source,
    selection_log_messages,
    split_playlist_entries,
    queueable_playlist_entries,
    resolve_starting_entry,
)
from core.runtime_management import (
    build_action_options,
    build_version_entries,
    merge_remote_and_installed_versions,
    normalize_installed_versions,
)

install_stderr_workaround()

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


def resolve_downloaded_file_path(result):
    requested_downloads = result.get('requested_downloads', [])
    for downloaded_item in requested_downloads:
        file_path = downloaded_item.get('filepath') or downloaded_item.get('filename')
        if file_path:
            return file_path

    if '_filename' in result:
        return result['_filename']

    return None


# Get the plugin url in plugin:// notation.
__url__ = sys.argv[0]
# Get the plugin handle as an integer number.
__handle__ = int(sys.argv[1])


try:
    import inputstreamhelper

    def isa_supports(stream):
        if stream is None or len(stream) < 1:
            return False
        return inputstreamhelper.Helper(stream).check_inputstream()
except ImportError:
    def isa_supports(stream):
        return False

def createListItemFromVideo(result):
    debug(result)

    selected_source = select_playback_source(
        result,
        usemanifest,
        usedashbuilder,
        maxwidth,
        isa_supports,
        dash_builder,
    )

    if selected_source is not None:
        for message in selection_log_messages(selected_source):
            log(message)

        url = selected_source['url']
        isa = selected_source['isa']
        headers = selected_source['headers']
    else:
        url = None
        isa = None
        headers = None

    if url is None:
        msg = "No supported streams found"
        showErrorNotification(msg)
        raise Exception("Error: " + msg)

    downloaded_file_path = resolve_downloaded_file_path(result)
    if downloaded_file_path is not None and xbmcvfs.exists(downloaded_file_path):
        log("using downloaded file {}".format(downloaded_file_path))
        url = downloaded_file_path
        isa = False
        headers = None
    elif downloaded_file_path is not None:
        log(
            "downloaded file does not exist, falling back to stream {}".format(downloaded_file_path),
            xbmc.LOGWARNING,
        )

    log("creating list item for url {}".format(url))
    list_item = xbmcgui.ListItem(result['title'], path=url)
    video_info = list_item.getVideoInfoTag()
    video_info.setTitle(result['title'])
    video_info.setPlot(result.get('description', None))
    if result.get('thumbnail', None) is not None:
        list_item.setArt({'thumb': result['thumbnail']})
    subtitles = result.get('subtitles', {})
    if subtitles:
        list_item.setSubtitles(collect_subtitle_urls(subtitles))
    if isa:
        list_item.setProperty('inputstream', 'inputstream.adaptive')

        # Many sites will throw a 403 unless the http headers (e.g. user agent and referer)
        # sent when downloading a manifest and streaming match those originally sent by yt-dlp.
        encoded_headers = encode_inputstream_headers(
            resolve_effective_headers(headers, result.get('http_headers'))
        )
        if encoded_headers is not None:
            list_item.setProperty('inputstream.adaptive.manifest_headers', encoded_headers)
            list_item.setProperty('inputstream.adaptive.stream_headers', encoded_headers)

    return list_item

def createListItemFromFlatPlaylistItem(video):
    listItemUrl = build_flat_playlist_item_url(__url__, video['url'], sys.argv[2])
    title = resolve_playlist_item_title(video)

    listItem = xbmcgui.ListItem(
        path            = listItemUrl,
        label           = title
    )

    video_info = listItem.getVideoInfoTag()
    video_info.setTitle(title)

    # both `true` and `false` are recommended here...
    listItem.setProperty("IsPlayable","true")

    return listItem


def extract_result_with_progress(ydl, target_url):
    progress = xbmcgui.DialogProgressBG()
    progress.create("Resolving " + target_url)
    try:
        return ydl.extract_info(target_url, download=False)
    finally:
        progress.close()


def download_result_with_progress(ydl, target_url):
    progress = xbmcgui.DialogProgressBG()
    progress.create("Downloading " + target_url)
    try:
        return ydl.extract_info(target_url, download=True)
    finally:
        progress.close()


def play_playlist_result(result, target_url, ydl):
    pl = xbmc.PlayList(1)
    pl.clear()

    index_to_start_at = resolve_start_index(find_playlist_start_index(target_url, result['entries']))
    starting_entry, unresolved_entries = split_playlist_entries(result['entries'], index_to_start_at)

    for video in queueable_playlist_entries(unresolved_entries):
        list_item = createListItemFromFlatPlaylistItem(video)
        pl.add(list_item.getPath(), list_item)

    def extract_starting_entry(url, download):
        return ydl.extract_info(url, download=media_download_enabled)

    starting_item = createListItemFromVideo(resolve_starting_entry(starting_entry, extract_starting_entry))
    pl.add(starting_item.getPath(), starting_item, index_to_start_at)

    xbmc.executebuiltin('Playlist.PlayOffset(%s,%d)' % ('video', index_to_start_at))


def play_single_result(result):
    list_item = createListItemFromVideo(result)
    xbmcplugin.setResolvedUrl(__handle__, True, listitem=list_item)


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


def _choose_runtime_version_from_release_list(
    runtime_label,
    status,
    list_available_versions,
):
    remote_versions = run_with_progress(
        "SendToKodi",
        "Loading {} versions...".format(runtime_label),
        lambda: list_available_versions(limit=20),
    )

    installed_version = status.get("installed_version")
    installed_versions = normalize_installed_versions(
        installed_version,
        status.get("installed_versions"),
    )

    if not remote_versions:
        if not installed_versions:
            showErrorNotification(
                "Could not load {} release list from GitHub".format(runtime_label)
            )
            return None
        showInfoNotification(
            "GitHub unavailable: showing installed {} versions".format(runtime_label)
        )
        log(
            "{} release list unavailable; showing locally installed versions".format(runtime_label),
            xbmc.LOGWARNING,
        )
    else:
        log("Loaded remote {} release list".format(runtime_label))

    versions = merge_remote_and_installed_versions(remote_versions, installed_versions)

    active_version = status.get("installed_version")
    entries = build_version_entries(versions, installed_versions, active_version)
    selected = xbmcgui.Dialog().select(
        "SendToKodi - manage {} version".format(runtime_label),
        entries,
    )
    if selected < 0:
        return None

    selected_version = versions[selected]
    action_options = build_action_options(selected_version, installed_versions, active_version)
    action_labels = [label for label, _action in action_options]
    action_values = [_action for _label, _action in action_options]

    if len(action_values) == 1:
        return selected_version, action_values[0]

    action_index = xbmcgui.Dialog().select(
        "SendToKodi - {} action ({})".format(runtime_label, selected_version),
        action_labels,
    )
    if action_index < 0:
        return None
    return selected_version, action_values[action_index]


def choose_deno_version_from_release_list(status, list_available_versions):
    return _choose_runtime_version_from_release_list("Deno", status, list_available_versions)


def set_deno_version_setting(version):
    xbmcaddon.Addon().setSetting("deno_version", version)


def set_deno_installed_version_display(version):
    display_value = (version or "").strip() or "not installed"
    xbmcaddon.Addon().setSetting("deno_installed_version_display", display_value)


def refresh_deno_installed_version_display(handle):
    try:
        settings = resolve_deno_settings(handle, xbmcplugin.getSetting)
        from core.deno_manager import get_runtime_status

        status = get_runtime_status(settings['version'], include_latest=False)
        set_deno_installed_version_display(status.get('installed_version'))
    except Exception as exc:
        log("Could not refresh Deno installed version display: {}".format(exc), xbmc.LOGWARNING)


def install_deno_version(selected_version, get_deno_ydl_opts):
    opts = run_with_progress(
        "SendToKodi",
        "Installing Deno {}...".format(selected_version),
        lambda: get_deno_ydl_opts(
            auto_download=True,
            requested_version=selected_version,
            force_refresh_latest=True,
        ),
    )
    deno_path = opts.get("js_runtimes", {}).get("deno", {}).get("path")
    if deno_path:
        try:
            from core.deno_manager import get_runtime_status

            status = get_runtime_status(selected_version, include_latest=False)
            installed_version = status.get('installed_version') or selected_version
        except Exception:
            installed_version = selected_version

        set_deno_installed_version_display(installed_version)
        showInfoNotification("Deno {} is installed".format(installed_version))
        return True

    showErrorNotification("Deno install failed")
    return False


def _activate_runtime_version(
    runtime_label,
    selected_version,
    activate_installed_version,
    get_runtime_status,
    set_version_setting,
    set_installed_version_display,
):
    runtime_path = activate_installed_version(selected_version)
    if runtime_path is None:
        showErrorNotification(
            "{} {} is not installed locally".format(runtime_label, selected_version)
        )
        return False

    status = get_runtime_status(selected_version)
    installed_version = status.get('installed_version') or selected_version
    set_version_setting(installed_version)
    set_installed_version_display(installed_version)
    showInfoNotification("{} {} is active".format(runtime_label, installed_version))
    return True


def activate_deno_version(selected_version, activate_installed_version, get_runtime_status):
    return _activate_runtime_version(
        "Deno",
        selected_version,
        activate_installed_version,
        lambda version: get_runtime_status(version, include_latest=False),
        set_deno_version_setting,
        set_deno_installed_version_display,
    )


def _delete_runtime_version(
    runtime_label,
    selected_version,
    delete_installed_version,
    get_runtime_status,
    set_version_setting,
    set_installed_version_display,
):
    should_delete = xbmcgui.Dialog().yesno(
        "SendToKodi",
        "Delete local {} version {}?".format(runtime_label, selected_version),
    )
    if not should_delete:
        return False

    deleted = delete_installed_version(selected_version)
    if not deleted:
        showErrorNotification("Could not delete {} {}".format(runtime_label, selected_version))
        return False

    status = get_runtime_status(None)
    remaining_version = status.get('installed_version')
    if remaining_version:
        set_version_setting(remaining_version)
        set_installed_version_display(remaining_version)
        showInfoNotification(
            "{} {} deleted; {} is now active".format(
                runtime_label,
                selected_version,
                remaining_version,
            )
        )
    else:
        set_version_setting('latest')
        set_installed_version_display(None)
        showInfoNotification("{} {} deleted".format(runtime_label, selected_version))
    return True


def delete_deno_version(selected_version, delete_installed_version, get_runtime_status):
    return _delete_runtime_version(
        "Deno",
        selected_version,
        delete_installed_version,
        lambda version: get_runtime_status(version, include_latest=False),
        set_deno_version_setting,
        set_deno_installed_version_display,
    )


def open_deno_select_version_dialog(handle):
    settings = resolve_deno_settings(handle, xbmcplugin.getSetting)
    from core.deno_manager import (
        get_runtime_status,
        list_available_versions,
        get_ydl_opts,
        activate_installed_version,
        delete_installed_version,
    )

    status = get_runtime_status(settings['version'], include_latest=False)
    set_deno_installed_version_display(status.get('installed_version'))

    selection = choose_deno_version_from_release_list(status, list_available_versions)
    if selection is None:
        return

    selected_version, action = selection
    if action == "install":
        set_deno_version_setting(selected_version)
        install_deno_version(selected_version, get_ydl_opts)
    elif action == "activate":
        activate_deno_version(selected_version, activate_installed_version, get_runtime_status)
    elif action == "delete":
        delete_deno_version(selected_version, delete_installed_version, get_runtime_status)


def update_deno_now(handle):
    settings = resolve_deno_settings(handle, xbmcplugin.getSetting)
    from core.deno_manager import get_ydl_opts

    install_deno_version(settings['version'], get_ydl_opts)


def choose_ytdlp_version_from_release_list(status, list_available_versions):
    return _choose_runtime_version_from_release_list("yt-dlp", status, list_available_versions)


def set_ytdlp_version_setting(version):
    xbmcaddon.Addon().setSetting("ytdlp_version", version)


def set_ytdlp_installed_version_display(version):
    display_value = (version or "").strip() or "not installed"
    xbmcaddon.Addon().setSetting("ytdlp_installed_version_display", display_value)


def refresh_ytdlp_installed_version_display(handle):
    try:
        settings = resolve_ytdlp_settings(handle, xbmcplugin.getSetting)
        from core.ytdlp_manager import get_runtime_status

        status = get_runtime_status(settings['version'])
        set_ytdlp_installed_version_display(status.get('installed_version'))
    except Exception as exc:
        log("Could not refresh yt-dlp installed version display: {}".format(exc), xbmc.LOGWARNING)


def install_ytdlp_version(selected_version, ensure_ytdlp_ready):
    result = run_with_progress(
        "SendToKodi",
        "Installing yt-dlp {}...".format(selected_version),
        lambda: ensure_ytdlp_ready(
            allow_install=True,
            requested_version=selected_version,
            force_refresh_latest=True,
        ),
    )
    if result['ready']:
        set_ytdlp_installed_version_display(result.get('installed_version') or result.get('version'))
        showInfoNotification("yt-dlp {} is installed".format(result['version']))
        return True

    error_message = result.get('error') or result.get('reason') or "unknown error"
    showErrorNotification("yt-dlp install failed: {}".format(error_message))
    return False


def activate_ytdlp_version(selected_version, activate_installed_version, get_runtime_status):
    return _activate_runtime_version(
        "yt-dlp",
        selected_version,
        activate_installed_version,
        get_runtime_status,
        set_ytdlp_version_setting,
        set_ytdlp_installed_version_display,
    )


def delete_ytdlp_version(selected_version, delete_installed_version, get_runtime_status):
    return _delete_runtime_version(
        "yt-dlp",
        selected_version,
        delete_installed_version,
        get_runtime_status,
        set_ytdlp_version_setting,
        set_ytdlp_installed_version_display,
    )


def open_ytdlp_select_version_dialog(handle):
    settings = resolve_ytdlp_settings(handle, xbmcplugin.getSetting)
    from core.ytdlp_manager import (
        get_runtime_status,
        ensure_ytdlp_ready,
        list_available_versions,
        activate_installed_version,
        delete_installed_version,
    )

    status = get_runtime_status(settings['version'])
    set_ytdlp_installed_version_display(status.get('installed_version'))
    selection = choose_ytdlp_version_from_release_list(status, list_available_versions)
    if selection is None:
        return

    selected_version, action = selection
    if action == "install":
        set_ytdlp_version_setting(selected_version)
        install_ytdlp_version(selected_version, ensure_ytdlp_ready)
    elif action == "activate":
        activate_ytdlp_version(selected_version, activate_installed_version, get_runtime_status)
    elif action == "delete":
        delete_ytdlp_version(selected_version, delete_installed_version, get_runtime_status)


def update_ytdlp_now(handle):
    settings = resolve_ytdlp_settings(handle, xbmcplugin.getSetting)
    from core.ytdlp_manager import ensure_ytdlp_ready

    install_ytdlp_version(settings['version'], ensure_ytdlp_ready)


def handle_preplay_action(handle, paramstring):
    if handle_queue_action(paramstring):
        return True

    action = resolve_action_param(paramstring)
    if action == "deno_select_version":
        open_deno_select_version_dialog(handle)
        return True

    if action == "deno_update_now":
        update_deno_now(handle)
        return True

    if action == "ytdlp_select_version":
        open_ytdlp_select_version_dialog(handle)
        return True

    if action == "ytdlp_update_now":
        update_ytdlp_now(handle)
        return True
    return False


def configure_managed_ytdlp(handle):
    ytdlp_settings = resolve_ytdlp_settings(handle, xbmcplugin.getSetting)
    from core.ytdlp_manager import ensure_ytdlp_ready, activate_runtime

    status = ensure_ytdlp_ready(
        allow_install=ytdlp_settings['auto_update'],
        requested_version=ytdlp_settings['version'],
    )
    set_ytdlp_installed_version_display(status.get('installed_version'))

    if not status['ready'] and status['reason'] in ('missing', 'version_mismatch'):
        wanted = ytdlp_settings['version']
        if wanted == 'latest':
            prompt_msg = "Managed yt-dlp is not available. Download latest version now?"
        else:
            prompt_msg = "Managed yt-dlp {} is not installed. Download it now?".format(wanted)

        should_download = xbmcgui.Dialog().yesno(
            "SendToKodi",
            prompt_msg,
        )
        if should_download:
            status = ensure_ytdlp_ready(
                allow_install=True,
                requested_version=ytdlp_settings['version'],
            )
            set_ytdlp_installed_version_display(status.get('installed_version'))

    if status['ready'] and status['runtime_path'] is not None:
        activate_runtime(status['runtime_path'])
        log("Using managed yt-dlp version {}".format(status['version']))
        return

    error_message = status.get('error')
    if error_message:
        log(
            "Managed yt-dlp unavailable, falling back to bundled/system yt-dlp: {}".format(
                error_message
            ),
            xbmc.LOGWARNING,
        )
    else:
        log(
            "Managed yt-dlp unavailable, falling back to bundled/system yt-dlp",
            xbmc.LOGWARNING,
        )

# Open the settings if no parameters have been passed. Prevents crash.
# This happens when the addon is launched from within the Kodi OSD.
if not sys.argv[2]:
    refresh_deno_installed_version_display(int(sys.argv[1]))
    refresh_ytdlp_installed_version_display(int(sys.argv[1]))
    xbmcaddon.Addon().openSettings()
    exit()

if handle_preplay_action(int(sys.argv[1]), sys.argv[2]):
    exit()

configure_managed_ytdlp(int(sys.argv[1]))

# yt-dlp is the only supported resolver
try:
    YoutubeDL = importlib.import_module("yt_dlp").YoutubeDL
except Exception as exc:
    showErrorNotification("yt-dlp is unavailable")
    log("yt-dlp import failed: {}".format(exc), xbmc.LOGERROR)
    exit()

# patch broken strptime (see above)
patch_strptime()

params = parse_cli_paramstring(sys.argv[2])
url = str(params['url'])

deno_opts = {}
try:
    from core.deno_manager import get_ydl_opts
    deno_opts = resolve_deno_opts(int(sys.argv[1]), xbmcplugin.getSetting, get_ydl_opts)
    refresh_deno_installed_version_display(int(sys.argv[1]))
except Exception as e:
    log("Failed to configure Deno: {}".format(str(e)), xbmc.LOGWARNING)

ydl_opts = build_ydl_opts(params, deno_opts)

media_download_settings = resolve_media_download_settings(int(sys.argv[1]), xbmcplugin.getSetting)
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

usemanifest = xbmcplugin.getSetting(int(sys.argv[1]),"usemanifest") == 'true'
usedashbuilder = xbmcplugin.getSetting(int(sys.argv[1]),"usedashbuilder") == 'true'
dash_httpd_idle_timeout_seconds = resolve_dash_httpd_idle_timeout(int(sys.argv[1]), xbmcplugin.getSetting)
dash_builder.DASH_HTTPD_IDLE_TIMEOUT_SECONDS = dash_httpd_idle_timeout_seconds
log("DASH MPD server idle timeout: {}s".format(dash_httpd_idle_timeout_seconds))
maxwidth = int(xbmcplugin.getSetting(int(sys.argv[1]), "maxresolution"))

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
        play_playlist_result(result, url, ydl)
    except Exception:
        handle_resolve_failure()
else:
    try:
        play_single_result(result)
    except Exception:
        handle_resolve_failure(set_resolved_false=True)
