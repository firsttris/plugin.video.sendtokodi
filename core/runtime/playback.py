# -*- coding: utf-8 -*-
import xbmc
import xbmcgui
import xbmcvfs

from core import dash_builder
from core.addon_params import build_flat_playlist_item_url, resolve_playlist_item_title
from core.playback_selection import (
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
)


def _resolve_downloaded_file_path(result):
    requested_downloads = result.get("requested_downloads", [])
    for downloaded_item in requested_downloads:
        file_path = downloaded_item.get("filepath") or downloaded_item.get("filename")
        if file_path:
            return file_path

    if "_filename" in result:
        return result["_filename"]
    return None


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
    seen_urls = set()
    for format_info in reversed(formats):
        stream_url = format_info.get("url")
        if not stream_url or stream_url in seen_urls:
            continue
        seen_urls.add(stream_url)
        entries.append((stream_url, _format_stream_option(format_info)))

    if not entries:
        return None

    labels = ["Automatic selection"] + [label for _, label in entries]
    selected_index = xbmcgui.Dialog().select("Select stream", labels)
    if selected_index <= 0:
        return None
    return entries[selected_index - 1][0]


def create_list_item_from_video(
    result,
    ydl_opts,
    usemanifest,
    usedashbuilder,
    maxwidth,
    askstream,
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
    preferred_stream_url = _prompt_preferred_stream_url(selection_result) if askstream else None
    selected_source = select_playback_source(
        selection_result,
        usemanifest,
        usedashbuilder,
        maxwidth,
        isa_supports,
        dash_builder,
        preferred_stream_url,
    )

    if selected_source is None and preferred_stream_url is not None:
        log("Selected stream is not playable, falling back to automatic selection", xbmc.LOGWARNING)
        selected_source = select_playback_source(
            selection_result,
            usemanifest,
            usedashbuilder,
            maxwidth,
            isa_supports,
            dash_builder,
        )

    if selected_source is not None:
        for message in selection_log_messages(selected_source):
            log(message)
        url = selected_source["url"]
        isa = selected_source["isa"]
        headers = selected_source["headers"]
    else:
        url = None
        isa = None
        headers = None

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
        list_item.setSubtitles(collect_subtitle_urls(subtitles))

    if isa:
        list_item.setProperty("inputstream", "inputstream.adaptive")

        # Many sites will throw a 403 unless the http headers (e.g. user agent and referer)
        # sent when downloading a manifest and streaming match those originally sent by yt-dlp.
        encoded_headers = encode_inputstream_headers(
            resolve_effective_headers(headers, result.get("http_headers"))
        )
        if encoded_headers is not None:
            list_item.setProperty("inputstream.adaptive.manifest_headers", encoded_headers)
            list_item.setProperty("inputstream.adaptive.stream_headers", encoded_headers)

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


def download_result_with_progress(ydl, target_url):
    progress = xbmcgui.DialogProgressBG()
    progress.create("Downloading " + target_url)
    try:
        return ydl.extract_info(target_url, download=True)
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
    askstream,
    isa_supports,
    youtube_dl_cls,
    log,
    show_error_notification,
):
    playlist = xbmc.PlayList(1)
    playlist.clear()

    index_to_start_at = resolve_start_index(find_playlist_start_index(target_url, result["entries"]))
    starting_entry, unresolved_entries = split_playlist_entries(result["entries"], index_to_start_at)

    for video in queueable_playlist_entries(unresolved_entries):
        list_item = _create_list_item_from_flat_playlist_item(video, plugin_url, paramstring)
        playlist.add(list_item.getPath(), list_item)

    def extract_starting_entry(url, _download):
        return ydl.extract_info(url, download=media_download_enabled)

    starting_item = create_list_item_from_video(
        resolve_starting_entry(starting_entry, extract_starting_entry),
        ydl_opts,
        usemanifest,
        usedashbuilder,
        maxwidth,
        askstream,
        isa_supports,
        youtube_dl_cls,
        log,
        show_error_notification,
    )
    playlist.add(starting_item.getPath(), starting_item, index_to_start_at)
    xbmc.executebuiltin("Playlist.PlayOffset(%s,%d)" % ("video", index_to_start_at))
