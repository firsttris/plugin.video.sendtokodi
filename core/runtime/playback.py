# -*- coding: utf-8 -*-
import os
from concurrent.futures import ThreadPoolExecutor

import requests
import xbmc
import xbmcgui
import xbmcvfs

from core import dash_builder
from core.addon_params import build_flat_playlist_item_url, resolve_playlist_item_title
from core.playback_selection import (
    append_headers_to_url,
    collect_subtitle_entries,
    collect_subtitle_urls,
    encode_inputstream_headers,
    find_playlist_start_index,
    resolve_effective_headers,
    resolve_start_index,
    resolve_starting_entry,
    select_playback_source,
    selection_log_messages,
    split_playlist_entries,
    queueable_playlist_entries,
    resolve_playlist_insert_position,
)
from core.subtitle_support import build_subtitle_file_name


_SUBTITLE_DOWNLOAD_TIMEOUT_SECONDS = 20
_SUBTITLE_DOWNLOAD_MAX_WORKERS = 6

_INPUTSTREAM_MIME_TYPES = {
    'hls': 'application/vnd.apple.mpegurl',
    'mpd': 'application/dash+xml',
    'ism': 'application/vnd.ms-sstr+xml',
}


def _resolve_downloaded_file_path(result):
    requested_downloads = result.get("requested_downloads", [])
    for downloaded_item in requested_downloads:
        file_path = downloaded_item.get("filepath") or downloaded_item.get("filename")
        if file_path:
            return file_path

    if "_filename" in result:
        return result["_filename"]
    return None


def _subtitle_download_dir():
    return xbmcvfs.translatePath("special://profile/addon_data/plugin.video.sendtokodi/subtitles")


def _download_subtitle_file(subtitle_url, destination_path, http_headers):
    response = requests.get(subtitle_url, headers=http_headers or None, timeout=_SUBTITLE_DOWNLOAD_TIMEOUT_SECONDS)
    try:
        response.raise_for_status()
        with open(destination_path, 'wb') as subtitle_file:
            subtitle_file.write(response.content)
    finally:
        response.close()


def _resolve_subtitle_paths(subtitles, http_headers, log):
    subtitle_entries = collect_subtitle_entries(subtitles)
    if not subtitle_entries:
        return []

    subtitle_directory = _subtitle_download_dir()
    try:
        os.makedirs(subtitle_directory, exist_ok=True)
    except Exception as exc:
        log('Failed to create subtitle directory {}: {}'.format(subtitle_directory, exc), xbmc.LOGWARNING)
        return collect_subtitle_urls(subtitles)

    # (url, local path or None); file names are assigned up front so they stay unique and stable.
    planned = []
    used_file_names = set()
    for subtitle_entry in subtitle_entries:
        subtitle_url = subtitle_entry.get('url')
        if not subtitle_url:
            continue

        if not subtitle_url.startswith(('http://', 'https://')):
            planned.append((subtitle_url, None))
            continue

        destination_path = os.path.join(
            subtitle_directory,
            build_subtitle_file_name(subtitle_entry, used_file_names=used_file_names),
        )
        planned.append((subtitle_url, destination_path))

    def resolve(item):
        subtitle_url, destination_path = item
        if destination_path is None:
            return subtitle_url
        try:
            _download_subtitle_file(subtitle_url, destination_path, http_headers)
            return destination_path
        except Exception as exc:
            log('Failed to download subtitle {}: {}'.format(subtitle_url, exc), xbmc.LOGWARNING)
            return subtitle_url

    downloads = sum(1 for _url, destination_path in planned if destination_path is not None)
    if downloads <= 1:
        return [resolve(item) for item in planned]

    # Playback waits for the subtitles; with many languages one-by-one adds up.
    with ThreadPoolExecutor(max_workers=min(downloads, _SUBTITLE_DOWNLOAD_MAX_WORKERS)) as executor:
        return list(executor.map(resolve, planned))


def _format_stream_option(format_info):
    format_label = format_info.get("format") or format_info.get("format_id") or "unknown"
    protocol = format_info.get("protocol") or "?"
    vcodec = format_info.get("vcodec") or "?"
    acodec = format_info.get("acodec") or "?"
    width = format_info.get("width")
    height = format_info.get("height")
    resolution = "{}x{}".format(width, height) if width and height else "?"
    return "{} | {} | {} / {} | {}".format(format_label, protocol, vcodec, acodec, resolution)


def _normalize_codec(codec):
    value = (codec or "").strip().lower()
    if value in ("", "none", "unknown", "null"):
        return "none"
    return value


def _infer_selected_stream_kind(result, selected_url):
    for format_info in reversed(result.get("formats", [])):
        if format_info.get("url") != selected_url:
            continue

        vcodec = _normalize_codec(format_info.get("vcodec"))
        acodec = _normalize_codec(format_info.get("acodec"))
        if vcodec == "none" and acodec != "none":
            return "audio"
        return "video"

    return "video"


def _prompt_preferred_stream_url(result):
    formats = result.get("formats", [])
    entries = []
    for format_info in reversed(formats):
        stream_url = format_info.get("url")
        if not stream_url:
            continue
        entries.append({
            "url": stream_url,
            "format_id": format_info.get("format_id"),
            "label": _format_stream_option(format_info),
        })

    if not entries:
        return None

    labels = ["Automatic selection"] + [entry["label"] for entry in entries]
    selected_index = xbmcgui.Dialog().select("Select stream", labels)
    if selected_index <= 0:
        return None
    return entries[selected_index - 1]


def create_list_item_from_video(
    result,
    ydl_opts,
    usemanifest,
    usedashbuilder,
    maxwidth,
    strict_max_resolution,
    askstream,
    disable_opus_for_audio_only_hls_native,
    isa_supports,
    youtube_dl_cls,
    log,
    show_error_notification,
):
    def resolve_fresh_result():
        refresh_url = result.get("webpage_url") or result.get("original_url") or result.get("url")
        if refresh_url is None:
            return None
        try:
            # Re-resolve source metadata so DASH manifests can be rebuilt with fresh stream URLs.
            refresh_ydl = youtube_dl_cls(ydl_opts)
            refresh_ydl.add_default_info_extractors()
            with refresh_ydl:
                return refresh_ydl.extract_info(refresh_url, download=False)
        except Exception as exc:
            log("DASH refresh re-resolve failed: {}".format(exc), xbmc.LOGWARNING)
            return None

    selection_result = dict(result)
    selection_result["resolve_fresh_result"] = resolve_fresh_result
    preferred_stream = _prompt_preferred_stream_url(selection_result) if askstream else None
    selected_source = select_playback_source(
        selection_result,
        usemanifest,
        usedashbuilder,
        maxwidth,
        isa_supports,
        dash_builder,
        preferred_format_url=preferred_stream.get("url") if preferred_stream is not None else None,
        preferred_format_id=preferred_stream.get("format_id") if preferred_stream is not None else None,
        disable_opus_for_audio_only_hls_native=disable_opus_for_audio_only_hls_native,
        strict_max_resolution=strict_max_resolution,
    )

    if selected_source is None and preferred_stream is not None:
        log("Selected stream is not playable, falling back to automatic selection", xbmc.LOGWARNING)
        selected_source = select_playback_source(
            selection_result,
            usemanifest,
            usedashbuilder,
            maxwidth,
            isa_supports,
            dash_builder,
            disable_opus_for_audio_only_hls_native=disable_opus_for_audio_only_hls_native,
            strict_max_resolution=strict_max_resolution,
        )

    if selected_source is not None:
        for message in selection_log_messages(selected_source):
            log(message)
        url = selected_source["url"]
        isa = selected_source["isa"]
        headers = selected_source["headers"]
        manifest_type = selected_source.get("manifest_type")
    else:
        url = None
        isa = None
        headers = None
        manifest_type = None

    if url is None:
        msg = "No supported streams found"
        show_error_notification(msg)
        raise Exception("Error: " + msg)

    downloaded_file_path = _resolve_downloaded_file_path(result)
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
    list_item = xbmcgui.ListItem(result["title"], path=url)
    stream_kind = _infer_selected_stream_kind(result, url)
    if stream_kind == "audio":
        music_info = list_item.getMusicInfoTag()
        music_info.setTitle(result["title"])
    else:
        video_info = list_item.getVideoInfoTag()
        video_info.setTitle(result["title"])
        video_info.setPlot(result.get("description", None))
    if result.get("thumbnail", None) is not None:
        list_item.setArt({"thumb": result["thumbnail"]})

    subtitles = result.get("subtitles", {})
    if subtitles:
        list_item.setSubtitles(_resolve_subtitle_paths(subtitles, result.get("http_headers"), log))

    # Many sites will throw a 403 unless the http headers (e.g. user agent and referer)
    # sent when downloading a manifest and streaming match those originally sent by yt-dlp.
    effective_headers = resolve_effective_headers(headers, result.get("http_headers"))

    if isa:
        list_item.setProperty("inputstream", "inputstream.adaptive")
        # Use the type detected during stream selection (protocol aware); guessing from the url alone
        # misdetects urls like ".ism/manifest(format=m3u8-aapl)". ISA only knows the types listed here.
        mime_type = _INPUTSTREAM_MIME_TYPES.get(manifest_type)
        if mime_type is not None:
            list_item.setProperty("inputstream.adaptive.manifest_type", manifest_type)
            list_item.setMimeType(mime_type)
        encoded_headers = encode_inputstream_headers(effective_headers)
        if encoded_headers is not None:
            list_item.setProperty("inputstream.adaptive.manifest_headers", encoded_headers)
            list_item.setProperty("inputstream.adaptive.stream_headers", encoded_headers)
    elif effective_headers and url and url.startswith(("http://", "https://")):
        url = append_headers_to_url(url, effective_headers)
        list_item.setPath(url)

    return list_item


def _create_list_item_from_flat_playlist_item(video, plugin_url, paramstring):
    list_item_url = build_flat_playlist_item_url(plugin_url, video["url"], paramstring)
    title = resolve_playlist_item_title(video)

    list_item = xbmcgui.ListItem(path=list_item_url, label=title)
    list_item.getVideoInfoTag().setTitle(title)
    list_item.setProperty("IsPlayable", "true")
    return list_item


def extract_result_with_progress(ydl, target_url):
    progress = xbmcgui.DialogProgressBG()
    progress.create("Resolving " + target_url)
    try:
        return ydl.extract_info(target_url, download=False)
    finally:
        progress.close()


def download_result_with_progress(ydl, result):
    progress = xbmcgui.DialogProgressBG()
    progress.create("Downloading " + (result.get("title") or result.get("webpage_url") or ""))
    try:
        # Reuse the extracted info instead of resolving the url a second time.
        return ydl.process_ie_result(result, download=True)
    finally:
        progress.close()


def play_playlist_result(
    result,
    target_url,
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
    youtube_dl_cls,
    log,
    show_error_notification,
):
    playlist = xbmc.PlayList(1)
    playlist.clear()

    entries = list(result.get("entries") or [])
    if not entries:
        show_error_notification("Playlist contains no playable entries")
        log("Playlist contains no playable entries", xbmc.LOGWARNING)
        return

    index_to_start_at = resolve_start_index(find_playlist_start_index(target_url, entries))
    starting_entry, unresolved_entries = split_playlist_entries(entries, index_to_start_at)

    for video in queueable_playlist_entries(unresolved_entries):
        list_item = _create_list_item_from_flat_playlist_item(video, plugin_url, paramstring)
        playlist.add(list_item.getPath(), list_item)

    index_to_start_at = resolve_playlist_insert_position(unresolved_entries, index_to_start_at)

    def extract_starting_entry(url, download=False):
        return ydl.extract_info(url, download=media_download_enabled)

    starting_item = create_list_item_from_video(
        resolve_starting_entry(starting_entry, extract_starting_entry),
        ydl_opts,
        usemanifest,
        usedashbuilder,
        maxwidth,
        strict_max_resolution,
        askstream,
        disable_opus_for_audio_only_hls_native,
        isa_supports,
        youtube_dl_cls,
        log,
        show_error_notification,
    )
    playlist.add(starting_item.getPath(), starting_item, index_to_start_at)
    xbmc.executebuiltin("Playlist.PlayOffset(%s,%d)" % ("video", index_to_start_at))
