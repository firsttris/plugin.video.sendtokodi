import requests
import struct
from io import BytesIO
from xml.etree.ElementTree import ElementTree, Element, SubElement, Comment
import http.server
from threading import Thread

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
        box_size = max(struct.unpack('>I', r.content[offset:offset + 4])[0], 8)
        box_type = struct.unpack('4s', r.content[offset + 4:offset + 8])[0]
        if box_type == b"sidx":
            init_range = (0, offset - 1)
            index_range = (offset, offset + box_size - 1)
            break
        offset = offset + box_size
    return init_range, index_range

def find_init_and_index_ranges(url, container):
    # Download the first 1KiB of the stream
    size = 1024
    r = requests.get(url, headers={'Range':'bytes=0-' + str(size - 1)})
    if container == 'webm_dash':
        return _webm_find_init_and_index_ranges(r)
    return _mp4_find_init_and_index_ranges(r)

def _iso8601_duration(secs):
    m, s = divmod(secs, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    return "P{}DT{}H{}M{}S".format(int(d), int(h), int(m), s)

def transform_url(url):
    return url.replace('&', '/').replace('?', '/').replace('=', '/')


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

        url = transform_url(format['url'])
        base_url = SubElement(rep, 'BaseURL')
        base_url.text = url

        init_range, idx_range = find_init_and_index_ranges(url, format['container'])
        segment_base = SubElement(rep, 'SegmentBase')
        segment_base.set('indexRange', '{}-{}'.format(idx_range[0], idx_range[1]))

        init = SubElement(segment_base, 'Initialization')
        init.set('range', '{}-{}'.format(init_range[0], init_range[1]))

    def add_video_format(self, format):
        rep = SubElement(self.video_set, 'Representation')
        rep.set('id', format['format_id'].split('-',1)[0])
        rep.set('codecs', format['vcodec'])
        rep.set('startWithSAP', '1')
        rep.set('maxPlayoutRate', '1')
        rep.set('frameRate', str(format['fps']))
        rep.set('width', str(format['resolution']).split('x',1)[0])
        rep.set('height', str(format['resolution']).split('x',1)[1])
        rep.set('mimeType', "video/{}".format(format['ext']))
        kbps = format.get('tbr', format.get('vbr'))
        if kbps is not None:
            rep.set('bandwidth', str(int(kbps * 1000)))

        url = transform_url(format['url'])
        base_url = SubElement(rep, 'BaseURL')
        base_url.text = url

        init_range, idx_range = find_init_and_index_ranges(url, format['container'])
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


class HttpHandler(http.server.BaseHTTPRequestHandler):
    def __init__(self, request, client_address, server):
        super().__init__(request, client_address, server)
        self.mpd = None

    def do_HEAD(self):
        self.send_response(200, 'OK')
        self.send_header('Content-type', 'application/dash+xml')
        self.send_header('Content-Length', str(len(bytes(self.mpd))))
        self.end_headers()

    def do_GET(self):
        self.do_HEAD()
        self.wfile.write(bytes(self.mpd))


def _handle_request(httpd):
    try:
        while True:
            httpd.handle_request()
    except TimeoutError:
        return

def start_httpd(manifest):
    handler = HttpHandler
    handler.mpd = manifest

    server_address = ('127.0.0.1', 0)
    httpd = http.server.HTTPServer(server_address, handler)
    httpd.timeout = 2  # Seconds
    httpd.handle_timeout = lambda: (_ for _ in ()).throw(TimeoutError())

    thread = Thread(target=_handle_request, args=(httpd,))
    thread.start()
    return "http://127.0.0.1:{}/manifest.mpd".format(httpd.server_port)
