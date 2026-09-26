import requests
import struct
from io import BytesIO
from xml.etree.ElementTree import ElementTree, Element, SubElement
from threading import Thread, Lock
from http.server import BaseHTTPRequestHandler, HTTPServer
from time import monotonic
from uuid import uuid4


DASH_HTTPD_IDLE_TIMEOUT_SECONDS = 120

_HTTPD_STATE_LOCK = Lock()
_HTTPD = None
_HTTPD_THREAD = None
_MANIFESTS = {}
_LATEST_MANIFEST_ID = None
_RANGE_REQUEST_TIMEOUT_SECONDS = 20
# The init/index boxes usually sit in the first few KiB; grow the probe until found.
_RANGE_PROBE_INITIAL_BYTES = 4096
_RANGE_PROBE_MAX_BYTES = 256 * 1024

def _webm_decode_int(byte):
    # Returns size and value
    if byte >= 128:
        return 1, byte & 0b1111111
    elif byte >= 64:
        return 2, byte & 0b111111
    elif byte >= 32:
        return 3, byte & 0b11111
    elif byte >= 16:
        return 4, byte & 0b1111
    elif byte >= 8:
        return 5, byte & 0b111
    elif byte >= 4:
        return 6, byte & 0b11
    elif byte >= 2:
        return 7, byte & 0b1
    return 8, 0

def _webm_find_init_and_index_ranges(r):
    # Walk over the stream and find the offset of the 'Cues' element
    # This isn't so easy due to the EBML encoding
    init_range = (0,0)
    index_range = (0,0)

    # Verify the EMBL signature / root element
    signature = struct.unpack('>I', r.content[0:4])[0]
    if signature != 0x1A45DFA3:
        return init_range, index_range

    offset = 5
    while offset < len(r.content) - 16:
        # Get the element ID
        id_len, _ = _webm_decode_int(r.content[offset])
        id = int.from_bytes(r.content[offset:offset+id_len], byteorder='big', signed=False)

        # Get the size of the element
        size_len, sz = _webm_decode_int(r.content[offset+id_len])
        size_bytes = bytearray() + sz.to_bytes(1, 'big')
        begin = offset + id_len + 1
        end = offset + id_len + size_len
        size_bytes += r.content[begin:end]
        size = int.from_bytes(size_bytes, byteorder='big', signed=False)

        # Check if we have found the 'Cues' element we are looking for
        if id == 0x1C53BB6B:
            init_range = (0, offset - 1)
            index_range = (offset, offset + id_len + size_len + size - 1)
            break

        # Check if we have found the Matroska Segment, which is of unknown size,
        # and advance through the stream to the next element
        if id == 0x18538067:
            offset += id_len + size_len
        else:
            offset += id_len + size_len + size

    return init_range, index_range

def _mp4_find_init_and_index_ranges(r):
    # Walk over the stream and find the offset of the sidx box
    # Fortunately this is much easier than webm
    init_range = (0,0)
    index_range = (0,0)
    offset = 0
    while offset < len(r.content) - 8:
        box_size = struct.unpack('>I', r.content[offset:offset + 4])[0]
        box_type = struct.unpack('4s', r.content[offset + 4:offset + 8])[0]
        if box_size == 1:
            # 64-bit "largesize" follows the box type.
            if offset + 16 > len(r.content):
                break
            box_size = struct.unpack('>Q', r.content[offset + 8:offset + 16])[0]
        elif box_size == 0:
            # Box extends to the end of the file, so no sidx can follow it.
            if box_type != b"sidx":
                break
            box_size = len(r.content) - offset
        if box_size < 8:
            break
        if box_type == b"sidx":
            init_range = (0, offset - 1)
            index_range = (offset, offset + box_size - 1)
            break
        offset = offset + box_size
    return init_range, index_range

class _Prefix():
    def __init__(self, content):
        self.content = content


def _fetch_prefix(url, size):
    # stream=True so a server that ignores the Range header does not make us
    # download the whole media file.
    r = requests.get(
        url,
        headers={'Range': 'bytes=0-' + str(size - 1)},
        timeout=_RANGE_REQUEST_TIMEOUT_SECONDS,
        stream=True,
    )
    try:
        r.raise_for_status()
        data = bytearray()
        for chunk in r.iter_content(chunk_size=16384):
            data += chunk
            if len(data) >= size:
                break
        return bytes(data[:size])
    finally:
        r.close()


def find_init_and_index_ranges(url, container):
    if container == 'webm_dash':
        find_ranges = _webm_find_init_and_index_ranges
    else:
        find_ranges = _mp4_find_init_and_index_ranges

    size = _RANGE_PROBE_INITIAL_BYTES
    while True:
        data = _fetch_prefix(url, size)
        init_range, index_range = find_ranges(_Prefix(data))
        if index_range != (0, 0):
            return init_range, index_range
        if len(data) < size or size >= _RANGE_PROBE_MAX_BYTES:
            raise RuntimeError(
                "No segment index found in the first {} bytes of the {} stream".format(len(data), container)
            )
        size = min(size * 4, _RANGE_PROBE_MAX_BYTES)

def _iso8601_duration(secs):
    # yt-dlp may report no duration (None) and callers default to the string "0".
    if not isinstance(secs, (int, float)):
        try:
            secs = float(secs)
        except (TypeError, ValueError):
            secs = 0
    m, s = divmod(secs, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    return "P{}DT{}H{}M{}S".format(int(d), int(h), int(m), s)

def transform_url(url):
    return url


class Manifest():
    def __init__(self, duration):
        self.mpd = Element('MPD')
        self.mpd.set('xmlns', 'urn:mpeg:DASH:schema:MPD:2011')
        self.mpd.set('profiles', 'urn:mpeg:dash:profile:isoff-main:2011')
        self.mpd.set('type', 'static')
        self.mpd.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
        self.mpd.set('xsi:schemaLocation', 'urn:mpeg:DASH:schema:MPD:2011 DASH-MPD.xsd')
        self.mpd.set('minBufferTime', _iso8601_duration(1.5))
        self.mpd.set('mediaPresentationDuration', _iso8601_duration(duration))

        self.period = SubElement(self.mpd, 'Period')

        self.audio_set = SubElement(self.period, 'AdaptationSet')
        self.audio_set.set('id', '0')
        self.audio_set.set('subsegmentAlignment', 'true')
        self.audio_set.set('contentType', 'audio')

        self.audio_set_role = SubElement(self.audio_set, 'Role')
        self.audio_set_role.set('schemeIdUri', 'urn:mpeg:DASH:role:2011')
        self.audio_set_role.set('value', 'main')

        self.video_set = SubElement(self.period, 'AdaptationSet')
        self.video_set.set('id', '1')
        self.video_set.set('subsegmentAlignment', 'true')
        self.video_set.set('contentType', 'video')

        self.video_set_role = SubElement(self.video_set, 'Role')
        self.video_set_role.set('schemeIdUri', 'urn:mpeg:DASH:role:2011')
        self.video_set_role.set('value', 'main')

        self.tree = ElementTree(self.mpd)

    def add_audio_format(self, format):
        url = format['url']
        # Resolve ranges first so a failing format leaves no partial Representation behind.
        init_range, idx_range = find_init_and_index_ranges(url, format['container'])

        rep = SubElement(self.audio_set, 'Representation')
        rep.set('id', format['format_id'].split('-',1)[0])
        rep.set('codecs', format['acodec'])
        rep.set('audioSamplingRate', str(format['asr']))
        rep.set('startWithSAP', '1')
        rep.set('mimeType', "audio/{}".format(format['ext']))
        kbps = format.get('tbr', format.get('abr'))
        if kbps is not None:
            rep.set('bandwidth', str(int(kbps * 1000)))

        channels = SubElement(rep, 'AudioChannelConfiguration')
        channels.set('schemeIdUri', 'urn:mpeg:dash:23003:3:audio_channel_configuration:2011')
        channels.set('value', str(format['audio_channels']))

        base_url = SubElement(rep, 'BaseURL')
        base_url.text = url

        segment_base = SubElement(rep, 'SegmentBase')
        segment_base.set('indexRange', '{}-{}'.format(idx_range[0], idx_range[1]))

        init = SubElement(segment_base, 'Initialization')
        init.set('range', '{}-{}'.format(init_range[0], init_range[1]))

    def add_video_format(self, format):
        url = format['url']
        # Resolve ranges first so a failing format leaves no partial Representation behind.
        init_range, idx_range = find_init_and_index_ranges(url, format['container'])
        width, height = str(format['resolution']).split('x', 1)

        rep = SubElement(self.video_set, 'Representation')
        rep.set('id', format['format_id'].split('-',1)[0])
        rep.set('codecs', format['vcodec'])
        rep.set('startWithSAP', '1')
        rep.set('maxPlayoutRate', '1')
        rep.set('frameRate', str(format['fps']))
        rep.set('width', width)
        rep.set('height', height)
        rep.set('mimeType', "video/{}".format(format['ext']))
        kbps = format.get('tbr', format.get('vbr'))
        if kbps is not None:
            rep.set('bandwidth', str(int(kbps * 1000)))

        base_url = SubElement(rep, 'BaseURL')
        base_url.text = url

        segment_base = SubElement(rep, 'SegmentBase')
        segment_base.set('indexRange', '{}-{}'.format(idx_range[0], idx_range[1]))

        init = SubElement(segment_base, 'Initialization')
        init.set('range', '{}-{}'.format(init_range[0], init_range[1]))

    def emit(self):
        try:
            from xml.etree.ElementTree import indent
            indent(self.tree)
        except:
            pass
        f = BytesIO()
        self.tree.write(f, encoding='utf-8', xml_declaration=True)
        #self.tree.write('manifest.mpd', encoding='utf-8', xml_declaration=True)
        return f.getvalue()


class HttpHandler(BaseHTTPRequestHandler):
    def log_message(self, _format, *_args):
        # BaseHTTPRequestHandler writes to stderr by default, which Kodi surfaces
        # as error <general>. Suppress noisy per-request logs for local manifest
        # serving to avoid false error reports during normal playback.
        return

    def _resolve_manifest_payload(self):
        # Preserve compatibility for direct handler tests where mpd is set on self.
        local_manifest = getattr(self, 'mpd', None)
        if local_manifest is not None:
            return bytes(local_manifest)

        path = self.path.split('?', 1)[0]
        if path == '/manifest.mpd':
            with _HTTPD_STATE_LOCK:
                manifest_id = _LATEST_MANIFEST_ID
        elif path.startswith('/manifest/') and path.endswith('.mpd'):
            manifest_id = path[len('/manifest/'):-len('.mpd')]
        else:
            manifest_id = None

        if not manifest_id:
            return None

        with _HTTPD_STATE_LOCK:
            entry = _MANIFESTS.get(manifest_id)
            if entry is None:
                return None
            refresh_manifest = entry.get('refresh_manifest')
            refreshed_at = entry.get('refreshed_at', 0)

        now = monotonic()
        refreshed_payload = None
        should_refresh = (
            refresh_manifest is not None
            and now - refreshed_at >= DASH_HTTPD_IDLE_TIMEOUT_SECONDS
        )
        if should_refresh:
            try:
                refreshed = refresh_manifest()
            except Exception:
                refreshed = None
            if refreshed is not None:
                refreshed_payload = bytes(refreshed)

        with _HTTPD_STATE_LOCK:
            entry = _MANIFESTS.get(manifest_id)
            if entry is None:
                return None

            if refreshed_payload is not None:
                entry['manifest'] = refreshed_payload
                entry['refreshed_at'] = now

            entry['last_access_at'] = now
            return entry['manifest']

    def do_HEAD(self):
        payload = HttpHandler._resolve_manifest_payload(self)
        if payload is None:
            self.send_response(404, 'Not Found')
            self.end_headers()
            return

        self.send_response(200, 'OK')
        self.send_header('Content-type', 'application/dash+xml')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()

    def do_GET(self):
        payload = HttpHandler._resolve_manifest_payload(self)
        if payload is None:
            self.send_response(404, 'Not Found')
            self.end_headers()
            return

        self.send_response(200, 'OK')
        self.send_header('Content-type', 'application/dash+xml')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def _stop_httpd_if_idle(httpd, now=None):
    # Caller must not hold _HTTPD_STATE_LOCK.
    global _HTTPD, _HTTPD_THREAD, _LATEST_MANIFEST_ID
    now = monotonic() if now is None else now
    with _HTTPD_STATE_LOCK:
        if _HTTPD is not httpd:
            return True
        last_access_at = max(
            (entry.get('last_access_at', 0) for entry in _MANIFESTS.values()),
            default=0,
        )
        if now - last_access_at < DASH_HTTPD_IDLE_TIMEOUT_SECONDS:
            return False
        _HTTPD = None
        _HTTPD_THREAD = None
        _MANIFESTS.clear()
        _LATEST_MANIFEST_ID = None
    try:
        httpd.server_close()
    except Exception:
        pass
    return True


def _handle_request(httpd):
    try:
        while True:
            httpd.handle_request()
            if _stop_httpd_if_idle(httpd):
                return
    except TimeoutError:
        return


def _ensure_httpd_started_locked():
    global _HTTPD, _HTTPD_THREAD
    if _HTTPD is not None:
        return _HTTPD

    server_address = ('127.0.0.1', 0)
    httpd = HTTPServer(server_address, HttpHandler)
    # Return from handle_request periodically so the idle check can stop the server.
    httpd.timeout = 1
    httpd.handle_timeout = lambda: None

    thread = Thread(target=_handle_request, args=(httpd,))
    thread.daemon = True
    thread.start()

    _HTTPD = httpd
    _HTTPD_THREAD = thread
    return _HTTPD


def _register_manifest_locked(manifest, refresh_manifest=None):
    global _LATEST_MANIFEST_ID
    manifest_id = uuid4().hex
    now = monotonic()
    _MANIFESTS[manifest_id] = {
        'manifest': bytes(manifest),
        'refresh_manifest': refresh_manifest,
        'refreshed_at': now,
        'last_access_at': now,
    }
    _LATEST_MANIFEST_ID = manifest_id
    return manifest_id


def start_httpd(manifest, refresh_manifest=None):
    # Start and register atomically so the idle check cannot stop the server in between.
    with _HTTPD_STATE_LOCK:
        httpd = _ensure_httpd_started_locked()
        manifest_id = _register_manifest_locked(manifest, refresh_manifest=refresh_manifest)
    return "http://127.0.0.1:{}/manifest/{}.mpd".format(httpd.server_port, manifest_id)


def _reset_httpd_state_for_tests():
    global _HTTPD, _HTTPD_THREAD, _MANIFESTS, _LATEST_MANIFEST_ID
    with _HTTPD_STATE_LOCK:
        _HTTPD = None
        _HTTPD_THREAD = None
        _MANIFESTS = {}
        _LATEST_MANIFEST_ID = None
