from urllib.parse import parse_qs, urlparse, quote, urlencode


_SUBTITLE_FORMAT_PREFERENCE = (
    'srt',
    'vtt',
    'ttml',
    'srv3',
    'srv2',
    'srv1',
    'json3',
)

# yt-dlp lists YouTube's live chat as a subtitle track under this language key.
_LIVE_CHAT_LANGUAGE_CODE = 'live_chat'
_LIVE_CHAT_PROTOCOL_PREFIX = 'youtube_live_chat'


def _dash_container_family(format_info):
    container = (format_info.get('container') or '').lower()
    if container in ('mp4_dash', 'm4a_dash'):
        return 'mp4'
    if container == 'webm_dash':
        return 'webm'
    return None


def _coerce_quality_value(value):
    if value is None:
        return 0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0


def _dash_audio_quality_key(format_info):
    return (
        _coerce_quality_value(format_info.get('abr')),
        _coerce_quality_value(format_info.get('tbr')),
        _coerce_quality_value(format_info.get('asr')),
        _coerce_quality_value(format_info.get('filesize') or format_info.get('filesize_approx')),
    )


def normalize_dash_audio_streams(dash_audio, preferred_video_format=None):
    if len(dash_audio) <= 1:
        return list(dash_audio)

    preferred_family = _dash_container_family(preferred_video_format or {})
    if preferred_family is not None:
        compatible_streams = [
            format_info for format_info in dash_audio
            if _dash_container_family(format_info) == preferred_family
        ]
        if compatible_streams:
            return [max(compatible_streams, key=_dash_audio_quality_key)]

    return [max(dash_audio, key=_dash_audio_quality_key)]


def match_preferred_format(format_info, preferred_format_url=None, preferred_format_id=None):
    if preferred_format_id is not None:
        return format_info.get('format_id') == preferred_format_id
    if preferred_format_url is not None:
        return format_info.get('url') == preferred_format_url
    return True


def filter_preferred_dash_video_formats(dash_video, preferred_format_url=None, preferred_format_id=None):
    if preferred_format_id is not None:
        matching_formats = [
            format_info for format_info in dash_video
            if format_info.get('format_id') == preferred_format_id
        ]
        if matching_formats:
            return matching_formats

    if preferred_format_url is not None:
        matching_formats = [
            format_info for format_info in dash_video
            if format_info.get('url') == preferred_format_url
        ]
        if matching_formats:
            return matching_formats

    return dash_video


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


def _is_non_subtitle_track(language_code, subtitle_list_entry):
    if language_code == _LIVE_CHAT_LANGUAGE_CODE:
        return True

    protocol = (subtitle_list_entry.get('protocol') or '').strip().lower()
    if protocol.startswith(_LIVE_CHAT_PROTOCOL_PREFIX):
        return True

    # Chat dumps (e.g. Twitch rechat) come as plain json, which Kodi cannot display as subtitles.
    ext = (subtitle_list_entry.get('ext') or '').strip().lower()
    return ext in ('json', 'jsonl')


def collect_subtitle_entries(subtitles):
    subtitle_entries = []
    for language_code, subtitle_variants in (subtitles or {}).items():
        if not isinstance(subtitle_variants, list):
            continue

        best_subtitle_entry = None
        best_subtitle_rank = len(_SUBTITLE_FORMAT_PREFERENCE)

        for subtitle_list_entry in subtitle_variants:
            if not isinstance(subtitle_list_entry, dict):
                continue

            if _is_non_subtitle_track(language_code, subtitle_list_entry):
                continue

            subtitle_url = subtitle_list_entry.get('url')
            if not subtitle_url:
                continue

            subtitle_ext = (subtitle_list_entry.get('ext') or '').lower()
            try:
                subtitle_rank = _SUBTITLE_FORMAT_PREFERENCE.index(subtitle_ext)
            except ValueError:
                subtitle_rank = len(_SUBTITLE_FORMAT_PREFERENCE)

            if best_subtitle_entry is None or subtitle_rank < best_subtitle_rank:
                best_subtitle_entry = {
                    'language': language_code,
                    'name': subtitle_list_entry.get('name') or language_code,
                    'ext': subtitle_ext,
                    'url': subtitle_url,
                }
                best_subtitle_rank = subtitle_rank

        if best_subtitle_entry is not None:
            subtitle_entries.append(best_subtitle_entry)

    return subtitle_entries


def collect_subtitle_urls(subtitles):
    urls = []
    for subtitle_entry in collect_subtitle_entries(subtitles):
        urls.append(subtitle_entry['url'])
    return urls


def append_headers_to_url(url, headers):
    if not headers:
        return url
    parts = []
    for key, value in headers.items():
        if key and value:
            parts.append("{}={}".format(quote(str(key)), quote(str(value))))
    if parts:
        return url + '|' + '&'.join(parts)
    return url


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


def should_replace_raw_candidate(current_format, candidate_format):
    if current_format is None:
        return True

    current_width = current_format.get('width')
    candidate_width = candidate_format.get('width')

    if candidate_width is None:
        return False
    if current_width is None:
        return True

    return candidate_width > current_width


def pick_best_dash_video_format(dash_video, maxwidth):
    if not dash_video:
        return None

    best_within_limit = None
    for format_info in dash_video:
        width = format_info.get('width')
        if width is None or width > maxwidth:
            continue
        if best_within_limit is None or width > best_within_limit.get('width', 0):
            best_within_limit = format_info

    if best_within_limit is not None:
        return best_within_limit
    return dash_video[-1]


def should_allow_native_hls_without_isa(format_info, manifest_type):
    if manifest_type != 'hls':
        return False

    protocol = (format_info.get('protocol') or '').lower()
    if not protocol.startswith('m3u'):
        return False

    vcodec = (format_info.get('vcodec') or '').lower()
    acodec = (format_info.get('acodec') or '').lower()
    unknown_values = ('', 'none', 'unknown')
    is_audio_only = vcodec in unknown_values and acodec not in unknown_values
    is_muxed_av = vcodec not in unknown_values and acodec not in unknown_values
    return is_audio_only or is_muxed_av


def should_prefer_manifest_over_raw_hls(result, format_info, manifest_candidate, maxwidth, strict_max_resolution):
    if manifest_candidate is None:
        return False
    if not result.get('is_live'):
        return False
    if guess_manifest_type(format_info, format_info.get('url')) != 'hls':
        return False
    if strict_max_resolution:
        # The master playlist lets the player pick any variant, so only use it when none exceeds the limit.
        manifest_url = format_info.get('manifest_url')
        for other_format in result.get('formats', []):
            if other_format.get('manifest_url') != manifest_url:
                continue
            if should_filter_by_max_width(other_format.get('width'), maxwidth):
                return False
    return True


def should_skip_audio_only_hls_native_opus(format_info, manifest_type, disable_opus_for_audio_only_hls_native):
    if not disable_opus_for_audio_only_hls_native:
        return False
    if manifest_type != 'hls':
        return False

    protocol = (format_info.get('protocol') or '').lower()
    if not protocol.startswith('m3u'):
        return False

    vcodec = (format_info.get('vcodec') or '').lower()
    acodec = (format_info.get('acodec') or '').lower()
    unknown_values = ('', 'none', 'unknown')
    is_audio_only = vcodec in unknown_values and acodec not in unknown_values
    return is_audio_only and acodec == 'opus'


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


def is_dash_video_format(format_info):
    return (
        format_info.get('vcodec', 'none') != 'none'
        and format_info.get('acodec', 'none') == 'none'
        and format_info.get('container', '') in ['mp4_dash', 'webm_dash']
    )


def resolve_effective_headers(selected_headers, result_headers):
    if selected_headers is not None:
        return selected_headers
    return result_headers


def resolve_start_index(index):
    if index is None:
        return 0
    return index


def resolve_manifest_candidate(manifest_url, manifest_type, isa_supports, headers, is_live=False):
    if manifest_url is None:
        return None
    # Kodi's native HLS player offers an automatic quality for live masters, so these
    # are played without ISA, and therefore also work when ISA is not installed.
    native_live_hls = is_live and manifest_type == 'hls'
    if not native_live_hls and not isa_supports(manifest_type):
        return None
    return {
        'url': manifest_url,
        'isa': not native_live_hls,
        'headers': headers,
        'manifest_type': manifest_type,
    }


def resolve_result_fallback_candidate(result_url, manifest_type, manifest_supported, headers):
    if result_url is None:
        return None
    return {
        'url': result_url,
        'isa': manifest_supported,
        'headers': headers,
        'manifest_type': manifest_type,
    }


def evaluate_raw_format_candidate(
    format_info,
    have_video,
    have_audio,
    maxwidth,
    manifest_type,
    manifest_supported,
    disable_opus_for_audio_only_hls_native=False,
):
    if 'url' not in format_info:
        return {'decision': 'skip'}

    if should_skip_non_adaptive_candidate(
        have_video,
        have_audio,
        format_info.get('vcodec'),
        format_info.get('acodec'),
    ):
        return {'decision': 'skip'}

    if should_skip_audio_only_hls_native_opus(
        format_info,
        manifest_type,
        disable_opus_for_audio_only_hls_native,
    ):
        return {'decision': 'skip'}

    native_hls_without_isa = should_allow_native_hls_without_isa(format_info, manifest_type)
    if manifest_type is not None and not manifest_supported and not native_hls_without_isa:
        return {'decision': 'skip'}

    width = format_info.get('width', 0)
    if should_filter_by_max_width(width, maxwidth):
        return {'decision': 'filtered'}

    return {
        'decision': 'select',
        'url': format_info['url'],
        # For muxed HLS variants this can be more reliable than ISA on some Kodi setups.
        'isa': False if native_hls_without_isa else manifest_supported,
        'headers': format_info.get('http_headers'),
        'manifest_type': manifest_type,
    }


def resolve_filtered_fallback_candidate(filtered_format, manifest_type, manifest_supported):
    if filtered_format is None:
        return None

    return {
        'url': filtered_format['url'],
        'isa': manifest_supported,
        'headers': filtered_format.get('http_headers'),
        'manifest_type': manifest_type,
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
    preferred_video_format=None,
    preferred_video_format_id=None,
    preferred_video_url=None,
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
            refreshed_dash_video = filter_preferred_dash_video_formats(
                refreshed_dash_video,
                preferred_format_url=preferred_video_url,
                preferred_format_id=preferred_video_format_id,
            )

        refreshed_builder = manifest_factory(refreshed_duration)
        refreshed_preferred_video = preferred_video_format
        if refreshed_dash_video:
            refreshed_preferred_video = refreshed_dash_video[0]
        refreshed_result = add_dash_formats_to_builder(
            refreshed_builder,
            refreshed_dash_video,
            normalize_dash_audio_streams(
                refreshed_dash_audio,
                preferred_video_format=refreshed_preferred_video,
            ),
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
        normalize_dash_audio_streams(
            dash_audio,
            preferred_video_format=preferred_video_format,
        ),
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


def resolve_format_acodec(fmt):
    # An explicit acodec=None means "unknown codec" in yt-dlp and counts as audio.
    if 'acodec' in fmt:
        return fmt['acodec']
    # yt-dlp omits acodec for some audio-only formats (e.g. YouTube live HLS audio
    # renditions); fall back to audio_ext so they are not mistaken for silent streams.
    if fmt.get('vcodec', 'none') == 'none' and fmt.get('audio_ext') not in (None, 'none'):
        return 'unknown'
    return 'none'


def analyze_formats(formats):
    have_video = False
    have_audio = False
    dash_video = []
    dash_audio = []

    for fmt in formats:
        vcodec = fmt.get('vcodec', 'none')
        acodec = resolve_format_acodec(fmt)

        if vcodec != 'none':
            have_video = True
        if acodec != 'none':
            have_audio = True

        container = fmt.get('container', '')
        if vcodec != 'none' and acodec == 'none' and container in ['mp4_dash', 'webm_dash']:
            dash_video.append(fmt)
        if vcodec == 'none' and acodec != 'none' and container in ['m4a_dash', 'webm_dash']:
            dash_audio.append(fmt)

    return have_video, have_audio, dash_video, dash_audio


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
    if not unresolved_entries:
        return None, []

    if start_index is None or start_index < 0 or start_index >= len(unresolved_entries):
        start_index = 0

    starting_entry = unresolved_entries.pop(start_index)
    return starting_entry, unresolved_entries


def queueable_playlist_entries(entries):
    return [entry for entry in entries if 'url' in entry]


def resolve_playlist_insert_position(unresolved_entries, start_index):
    # Entries without a url are not queued, so the start position shifts accordingly.
    return len(queueable_playlist_entries(unresolved_entries[:start_index]))


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
    preferred_format_url=None,
    preferred_format_id=None,
    disable_opus_for_audio_only_hls_native=False,
    strict_max_resolution=True,
):
    dash_manifest_factory = None
    dash_start_httpd = None
    if usedashbuilder and dashbuilder is not None:
        dash_manifest_factory = dashbuilder.Manifest
        dash_start_httpd = dashbuilder.start_httpd

    has_manual_stream_preference = preferred_format_id is not None or preferred_format_url is not None

    if not strict_max_resolution and preferred_format_url is None:
        manifest_url = result.get('manifest_url') if usemanifest else None
        manifest_type = guess_manifest_type(result, manifest_url) if manifest_url is not None else None
        original_manifest_candidate = resolve_manifest_candidate(
            manifest_url,
            manifest_type,
            isa_supports,
            result.get('http_headers'),
            is_live=result.get('is_live', False),
        )
        if original_manifest_candidate is not None:
            original_manifest_candidate['source'] = 'original_manifest'
            return original_manifest_candidate

    format_manifest_fallback = None
    filtered_format = None
    best_raw_format = None
    best_raw_candidate = None

    all_formats = result.get('formats', [])
    have_video, have_audio, dash_video, dash_audio = analyze_formats(all_formats)

    for format_info in reversed(all_formats):
        vcodec = format_info.get('vcodec')
        acodec = format_info.get('acodec')
        if should_skip_manifest_candidate(have_video, vcodec, acodec):
            continue

        if not match_preferred_format(
            format_info,
            preferred_format_url=preferred_format_url,
            preferred_format_id=preferred_format_id,
        ):
            continue

        if (
            has_manual_stream_preference
            and usedashbuilder
            and isa_supports("mpd")
            and is_dash_video_format(format_info)
        ):
            dash_result = None
            if dash_manifest_factory is not None and dash_start_httpd is not None:
                dash_result = build_dash_manifest_candidate(
                    result.get('duration', "0"),
                    [format_info],
                    dash_audio,
                    True,
                    have_audio,
                    dash_manifest_factory,
                    dash_start_httpd,
                    result.get('resolve_fresh_result'),
                    preferred_video_format=format_info,
                    preferred_video_format_id=format_info.get('format_id'),
                    preferred_video_url=format_info.get('url'),
                )
            dash_url = dash_result.get('url') if dash_result is not None else None
            if dash_url is not None:
                return {
                    'url': dash_url,
                    'isa': True,
                    'headers': format_info.get('http_headers'),
                    'manifest_type': 'mpd',
                    'source': 'dash_manifest',
                    'events': dash_result.get('events', []),
                }

        if preferred_format_url is None:
            manifest_url = format_info.get('manifest_url') if usemanifest else None
            manifest_type = guess_manifest_type(format_info, manifest_url) if manifest_url is not None else None
            format_manifest_candidate = resolve_manifest_candidate(
                manifest_url,
                manifest_type,
                isa_supports,
                format_info.get('http_headers'),
                is_live=result.get('is_live', False),
            )
            if format_manifest_candidate is not None and not strict_max_resolution:
                format_manifest_candidate['source'] = 'format_manifest'
                format_manifest_candidate['format_label'] = format_info.get('format', "")
                return format_manifest_candidate
            if should_prefer_manifest_over_raw_hls(
                result,
                format_info,
                format_manifest_candidate,
                maxwidth,
                strict_max_resolution,
            ):
                format_manifest_candidate['source'] = 'format_manifest'
                format_manifest_candidate['format_label'] = format_info.get('format', "")
                return format_manifest_candidate
            if format_manifest_candidate is not None and format_manifest_fallback is None:
                format_manifest_candidate['source'] = 'format_manifest'
                format_manifest_candidate['format_label'] = format_info.get('format', "")
                format_manifest_fallback = format_manifest_candidate

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
                selected_dash_video = pick_best_dash_video_format(dash_video, maxwidth) if strict_max_resolution else None
                preferred_dash_video = selected_dash_video
                if preferred_dash_video is None and dash_video:
                    preferred_dash_video = dash_video[-1]
                dash_result = build_dash_manifest_candidate(
                    result.get('duration', "0"),
                    [selected_dash_video] if selected_dash_video is not None else dash_video,
                    dash_audio,
                    have_video,
                    have_audio,
                    dash_manifest_factory,
                    dash_start_httpd,
                    result.get('resolve_fresh_result'),
                    preferred_video_format=preferred_dash_video,
                    preferred_video_format_id=preferred_dash_video.get('format_id') if preferred_dash_video is not None else None,
                    preferred_video_url=preferred_dash_video.get('url') if preferred_dash_video is not None else None,
                )
            dash_url = dash_result.get('url') if dash_result is not None else None
            if dash_url is not None:
                return {
                    'url': dash_url,
                    'isa': True,
                    'headers': format_info.get('http_headers'),
                    'manifest_type': 'mpd',
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
            disable_opus_for_audio_only_hls_native,
        )
        if raw_candidate['decision'] == 'skip':
            continue
        if raw_candidate['decision'] == 'filtered':
            if filtered_format is None:
                filtered_format = format_info
            continue

        if not strict_max_resolution:
            raw_candidate['source'] = 'raw_format'
            raw_candidate['format_label'] = format_info.get('format', "")
            return raw_candidate

        if should_replace_raw_candidate(best_raw_format, format_info):
            raw_candidate['source'] = 'raw_format'
            raw_candidate['format_label'] = format_info.get('format', "")
            best_raw_candidate = raw_candidate
            best_raw_format = format_info

    if best_raw_candidate is not None:
        return best_raw_candidate

    if format_manifest_fallback is not None:
        return format_manifest_fallback

    manifest_url = result.get('manifest_url') if usemanifest else None
    manifest_type = guess_manifest_type(result, manifest_url) if manifest_url is not None else None
    original_manifest_candidate = resolve_manifest_candidate(
        manifest_url,
        manifest_type,
        isa_supports,
        result.get('http_headers'),
        is_live=result.get('is_live', False),
    )
    if original_manifest_candidate is not None and preferred_format_url is None:
        original_manifest_candidate['source'] = 'original_manifest'
        return original_manifest_candidate

    filtered_manifest_type = (
        guess_manifest_type(filtered_format, filtered_format['url']) if filtered_format is not None else None
    )
    filtered_fallback = resolve_filtered_fallback_candidate(
        filtered_format,
        filtered_manifest_type,
        isa_supports(filtered_manifest_type) if filtered_format is not None else False,
    )
    if filtered_fallback is not None:
        filtered_fallback['source'] = 'filtered_fallback'
        return filtered_fallback

    result_manifest_type = guess_manifest_type(result, result.get('url')) if result.get('url') is not None else None
    result_fallback = resolve_result_fallback_candidate(
        result.get('url'),
        result_manifest_type,
        isa_supports(result_manifest_type) if result.get('url') is not None else False,
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
