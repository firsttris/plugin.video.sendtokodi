# -*- coding: utf-8 -*-
import sys
import os

# Ensures yt-dlp is on the python path
# Workaround for issue caused by upstream commit
dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(dir_path, 'lib'))

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs
from core import dash_builder

from core.addon_params import (
    parse_cli_paramstring,
    build_flat_playlist_item_url,
    resolve_playlist_item_title,
    build_ydl_opts,
    resolve_deno_opts,
    resolve_media_download_settings,
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

# Open the settings if no parameters have been passed. Prevents crash.
# This happens when the addon is launched from within the Kodi OSD.
if not sys.argv[2]:
    xbmcaddon.Addon().openSettings()
    exit()

# yt-dlp is the only supported resolver
from yt_dlp import YoutubeDL

# patch broken strptime (see above)
patch_strptime()

params = parse_cli_paramstring(sys.argv[2])
url = str(params['url'])

deno_opts = {}
try:
    from core.deno_manager import get_ydl_opts
    deno_opts = resolve_deno_opts(int(sys.argv[1]), xbmcplugin.getSetting, get_ydl_opts)
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
