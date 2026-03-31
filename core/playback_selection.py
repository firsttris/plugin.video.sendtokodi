from urllib.parse import parse_qs, urlparse
from urllib.parse import urlencode


def normalize_dash_audio_streams(dash_audio):
    if len(dash_audio) > 1:
        return [dash_audio[-1]]
    return dash_audio


def guess_manifest_type(format_info, url):
    protocol = format_info.get('protocol', "")
    if protocol.startswith("m3u"):
        return "hls"
    if protocol.startswith("rtmp") or protocol == "rtsp":
        return "rtmp"
    if protocol == "ism":
        return "ism"

    for suffix in [".m3u", ".m3u8", ".hls", ".mpd", ".rtmp", ".ism"]:
        offset = url.find(suffix, 0)
        while offset != -1:
            if offset == len(url) - len(suffix) or not url[offset + len(suffix)].isalnum():
                if suffix.startswith(".m3u"):
                    suffix = ".hls"
                return suffix[1:]
            offset = url.find(suffix, offset + 1)
    return None


def collect_subtitle_urls(subtitles):
    return [
        subtitle_list_entry['url']
        for lang in subtitles
        for subtitle_list_entry in subtitles[lang]
    ]


def encode_inputstream_headers(headers):
    if headers is None:
        return None
    return urlencode(headers)


def should_skip_manifest_candidate(have_video, vcodec, acodec):
    return (have_video and vcodec == "none") or (not have_video and acodec == "none")


def should_skip_non_adaptive_candidate(have_video, have_audio, vcodec, acodec):
    return (have_video and vcodec == "none") or (have_audio and acodec == "none")


def should_filter_by_max_width(width, maxwidth):
    return width is not None and width > maxwidth


def audio_manifest_candidate_score(format_info):
    """Higher score means better fallback candidate for audio-only manifest playback."""
    score = 0
    acodec = (format_info.get('acodec') or '').lower()
    format_label = (format_info.get('format') or format_info.get('format_id') or '').lower()
    stream_url = (format_info.get('url') or '').lower()

    # Prefer broadly compatible mp3 streams over opus for SoundCloud HLS manifests.
    if acodec == 'mp3' or 'hls_mp3' in format_label or '.mp3/' in stream_url:
        score += 100
    elif acodec == 'opus' or 'hls_opus' in format_label or '.opus/' in stream_url:
        score += 10

    abr = format_info.get('abr')
    if isinstance(abr, (int, float)):
        score += int(abr)

    return score


def pick_better_audio_manifest_candidate(current, candidate):
    if current is None:
        return candidate
    if audio_manifest_candidate_score(candidate) > audio_manifest_candidate_score(current):
        return candidate
    return current


def should_try_dash_builder(usedashbuilder, have_video, dash_video, have_audio, dash_audio, current_format, mpd_supported):
    return (
        usedashbuilder
        and (not have_video or len(dash_video) > 0)
        and (not have_audio or len(dash_audio) > 0)
        and (
            (have_video and current_format == dash_video[-1])
            or (not have_video and have_audio and current_format == dash_audio[-1])
        )
        and mpd_supported
    )


def resolve_effective_headers(selected_headers, result_headers):
    if selected_headers is not None:
        return selected_headers
    return result_headers


def resolve_start_index(index):
    if index is None:
        return 0
    return index


def resolve_manifest_candidate(manifest_url, manifest_supported, headers):
    if manifest_url is None:
        return None
    if not manifest_supported:
        return None
    return {
        'url': manifest_url,
        'isa': True,
        'headers': headers,
    }


def resolve_result_fallback_candidate(result_url, manifest_supported, headers):
    if result_url is None:
        return None
    return {
        'url': result_url,
        'isa': manifest_supported,
        'headers': headers,
    }


def evaluate_raw_format_candidate(format_info, have_video, have_audio, maxwidth, manifest_type, manifest_supported):
    if 'url' not in format_info:
        return {'decision': 'skip'}

    if should_skip_non_adaptive_candidate(
        have_video,
        have_audio,
        format_info.get('vcodec'),
        format_info.get('acodec'),
    ):
        return {'decision': 'skip'}

    if manifest_type is not None and not manifest_supported:
        return {'decision': 'skip'}

    width = format_info.get('width', 0)
    if should_filter_by_max_width(width, maxwidth):
        return {'decision': 'filtered'}

    return {
        'decision': 'select',
        'url': format_info['url'],
        'isa': manifest_supported,
        'headers': format_info.get('http_headers'),
    }


def resolve_filtered_fallback_candidate(filtered_format, manifest_supported):
    if filtered_format is None:
        return None

    return {
        'url': filtered_format['url'],
        'isa': manifest_supported,
        'headers': filtered_format.get('http_headers'),
    }


def add_dash_formats_to_builder(builder, dash_video, dash_audio, have_video, have_audio):
    video_success = not have_video
    audio_success = not have_audio
    events = []

    for fvideo in dash_video:
        format_id = fvideo.get('format', "")
        try:
            builder.add_video_format(fvideo)
            video_success = True
            events.append({'type': 'video_added', 'format_id': format_id})
        except Exception as exc:
            events.append({'type': 'video_failed', 'format_id': format_id, 'error': str(exc)})

    for faudio in dash_audio:
        format_id = faudio.get('format', "")
        try:
            builder.add_audio_format(faudio)
            audio_success = True
            events.append({'type': 'audio_added', 'format_id': format_id})
        except Exception as exc:
            events.append({'type': 'audio_failed', 'format_id': format_id, 'error': str(exc)})

    return {
        'video_success': video_success,
        'audio_success': audio_success,
        'events': events,
    }


def build_dash_manifest_candidate(
    duration,
    dash_video,
    dash_audio,
    have_video,
    have_audio,
    manifest_factory,
    start_httpd,
    resolve_fresh_result=None,
):
    def build_manifest_bytes():
        refreshed_duration = duration
        refreshed_dash_video = dash_video
        refreshed_dash_audio = dash_audio
        refreshed_have_video = have_video
        refreshed_have_audio = have_audio

        if resolve_fresh_result is not None:
            fresh_result = resolve_fresh_result()
            if fresh_result is None:
                return None

            refreshed_duration = fresh_result.get('duration', duration)
            refreshed_have_video, refreshed_have_audio, refreshed_dash_video, refreshed_dash_audio = analyze_formats(
                fresh_result.get('formats', [])
            )

        refreshed_builder = manifest_factory(refreshed_duration)
        refreshed_result = add_dash_formats_to_builder(
            refreshed_builder,
            refreshed_dash_video,
            refreshed_dash_audio,
            refreshed_have_video,
            refreshed_have_audio,
        )
        if refreshed_result['video_success'] and refreshed_result['audio_success']:
            return refreshed_builder.emit()
        return None

    builder = manifest_factory(duration)
    build_result = add_dash_formats_to_builder(
        builder,
        dash_video,
        dash_audio,
        have_video,
        have_audio,
    )
    if build_result['video_success'] and build_result['audio_success']:
        manifest = builder.emit()
        try:
            manifest_url = start_httpd(manifest, refresh_manifest=build_manifest_bytes)
        except TypeError:
            manifest_url = start_httpd(manifest)
        return {
            'url': manifest_url,
            'events': build_result['events'],
        }
    return {'events': build_result['events']}


def analyze_formats(formats):
    have_video = False
    have_audio = False
    dash_video = []
    dash_audio = []

    for fmt in formats:
        vcodec = fmt.get('vcodec', 'none')
        acodec = fmt.get('acodec', 'none')

        if vcodec != 'none':
            have_video = True
        if acodec != 'none':
            have_audio = True

        container = fmt.get('container', '')
        if vcodec != 'none' and acodec == 'none' and container in ['mp4_dash', 'webm_dash']:
            dash_video.append(fmt)
        if vcodec == 'none' and acodec != 'none' and container in ['m4a_dash', 'webm_dash']:
            dash_audio.append(fmt)

    return have_video, have_audio, dash_video, normalize_dash_audio_streams(dash_audio)


def find_playlist_start_index(url, entries):
    query_params = parse_qs(urlparse(url).query)

    if 'v' not in query_params:
        return None

    video_id = query_params['v'][0]

    try:
        index_values = query_params.get('index')
        if index_values:
            index = int(index_values[0]) - 1
            if 0 <= index < len(entries) and entries[index].get('id') == video_id:
                return index
    except (TypeError, ValueError):
        pass

    for i, entry in enumerate(entries):
        if entry.get('id') == video_id:
            return i

    return None


def split_playlist_entries(entries, start_index):
    unresolved_entries = list(entries)
    starting_entry = unresolved_entries.pop(start_index)
    return starting_entry, unresolved_entries


def queueable_playlist_entries(entries):
    return [entry for entry in entries if 'url' in entry]


def resolve_starting_entry(starting_entry, extract_info):
    if 'url' in starting_entry:
        return extract_info(starting_entry['url'], download=False)
    return starting_entry


def select_playback_source(
    result,
    usemanifest,
    usedashbuilder,
    maxwidth,
    isa_supports,
    dashbuilder=None,
):
    dash_manifest_factory = None
    dash_start_httpd = None
    if usedashbuilder and dashbuilder is not None:
        dash_manifest_factory = dashbuilder.Manifest
        dash_start_httpd = dashbuilder.start_httpd

    manifest_url = result.get('manifest_url') if usemanifest else None
    original_manifest_candidate = resolve_manifest_candidate(
        manifest_url,
        isa_supports(guess_manifest_type(result, manifest_url)) if manifest_url is not None else False,
        result.get('http_headers'),
    )
    if original_manifest_candidate is not None:
        original_manifest_candidate['source'] = 'original_manifest'
        return original_manifest_candidate

    filtered_format = None
    deferred_audio_manifest_candidate = None
    deferred_audio_manifest_format = None
    all_formats = result.get('formats', [])
    have_video, have_audio, dash_video, dash_audio = analyze_formats(all_formats)

    for format_info in reversed(all_formats):
        vcodec = format_info.get('vcodec')
        acodec = format_info.get('acodec')
        if should_skip_manifest_candidate(have_video, vcodec, acodec):
            continue

        manifest_url = format_info.get('manifest_url') if usemanifest else None
        format_manifest_candidate = resolve_manifest_candidate(
            manifest_url,
            isa_supports(guess_manifest_type(format_info, manifest_url)) if manifest_url is not None else False,
            format_info.get('http_headers'),
        )
        if format_manifest_candidate is not None:
            format_manifest_candidate['source'] = 'format_manifest'
            format_manifest_candidate['format_label'] = format_info.get('format', "")
            return format_manifest_candidate

        if should_try_dash_builder(
            usedashbuilder,
            have_video,
            dash_video,
            have_audio,
            dash_audio,
            format_info,
            isa_supports("mpd"),
        ):
            dash_result = None
            if dash_manifest_factory is not None and dash_start_httpd is not None:
                dash_result = build_dash_manifest_candidate(
                    result.get('duration', "0"),
                    dash_video,
                    dash_audio,
                    have_video,
                    have_audio,
                    dash_manifest_factory,
                    dash_start_httpd,
                    result.get('resolve_fresh_result'),
                )
            dash_url = dash_result.get('url') if dash_result is not None else None
            if dash_url is not None:
                return {
                    'url': dash_url,
                    'isa': True,
                    'headers': format_info.get('http_headers'),
                    'source': 'dash_manifest',
                    'events': dash_result.get('events', []),
                }

        manifest_type = guess_manifest_type(format_info, format_info['url']) if 'url' in format_info else None
        raw_candidate = evaluate_raw_format_candidate(
            format_info,
            have_video,
            have_audio,
            maxwidth,
            manifest_type,
            isa_supports(manifest_type),
        )
        if raw_candidate['decision'] == 'skip':
            continue
        if raw_candidate['decision'] == 'filtered':
            if filtered_format is None:
                filtered_format = format_info
            continue

        # For audio-only results, prefer direct media URLs over manifest URLs.
        # Some HLS audio manifests (for example SoundCloud hls_opus) can fail demux/decoder init.
        if not have_video and have_audio and manifest_type is not None:
            raw_candidate['source'] = 'raw_format'
            raw_candidate['format_label'] = format_info.get('format', "")
            # Audio-only HLS manifests are more reliable through Kodi's native path
            # than through inputstream.adaptive on some platforms.
            raw_candidate['isa'] = False
            better_format = pick_better_audio_manifest_candidate(
                deferred_audio_manifest_format,
                format_info,
            )
            if better_format is format_info:
                deferred_audio_manifest_candidate = raw_candidate
                deferred_audio_manifest_format = format_info
            continue

        raw_candidate['source'] = 'raw_format'
        raw_candidate['format_label'] = format_info.get('format', "")
        return raw_candidate

    if deferred_audio_manifest_candidate is not None:
        return deferred_audio_manifest_candidate

    filtered_fallback = resolve_filtered_fallback_candidate(
        filtered_format,
        isa_supports(guess_manifest_type(filtered_format, filtered_format['url'])) if filtered_format is not None else False,
    )
    if filtered_fallback is not None:
        filtered_fallback['source'] = 'filtered_fallback'
        return filtered_fallback

    result_fallback = resolve_result_fallback_candidate(
        result.get('url'),
        isa_supports(guess_manifest_type(result, result.get('url'))) if result.get('url') is not None else False,
        result.get('http_headers'),
    )
    if result_fallback is not None:
        result_fallback['source'] = 'result_fallback'
        return result_fallback

    return None


def selection_log_messages(selected_source):
    if selected_source is None:
        return []

    source = selected_source.get('source')
    if source == 'original_manifest':
        return ["Picked original manifest"]

    if source == 'format_manifest':
        return ["Picked format " + selected_source.get('format_label', "") + " manifest"]

    if source == 'raw_format':
        return ["Picked raw format " + selected_source.get('format_label', "")]

    if source == 'dash_manifest':
        messages = []
        for event in selected_source.get('events', []):
            event_type = event['type']
            format_id = event['format_id']
            if event_type == 'video_added':
                messages.append("Added video stream {} to DASH manifest".format(format_id))
            elif event_type == 'video_failed':
                messages.append("Failed to add DASH video stream {}: {}".format(format_id, event['error']))
            elif event_type == 'audio_added':
                messages.append("Added audio stream {} to DASH manifest".format(format_id))
            elif event_type == 'audio_failed':
                messages.append("Failed to add DASH audio stream {}: {}".format(format_id, event['error']))
        messages.append("Picked DASH with custom manifest")
        return messages

    return []
