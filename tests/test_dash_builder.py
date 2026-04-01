from core import dash_builder


class DummyResponse:
    def __init__(self, content):
        self.content = content


def test_webm_decode_int_prefix_lengths():
    assert dash_builder._webm_decode_int(0b10000000) == (1, 0)
    assert dash_builder._webm_decode_int(0b01000001) == (2, 1)
    assert dash_builder._webm_decode_int(0b00100010) == (3, 2)
    assert dash_builder._webm_decode_int(0b00010011) == (4, 3)
    assert dash_builder._webm_decode_int(0b00000000) == (8, 0)


def test_webm_find_ranges_returns_default_for_non_ebml_payload():
    response = DummyResponse(b"not-ebml-content")
    init_range, index_range = dash_builder._webm_find_init_and_index_ranges(response)
    assert init_range == (0, 0)
    assert index_range == (0, 0)


def test_mp4_find_ranges_finds_sidx_box():
    ftyp_box = b"\x00\x00\x00\x10" + b"ftyp" + b"isom0000"
    free_box = b"\x00\x00\x00\x08" + b"free"
    sidx_box = b"\x00\x00\x00\x18" + b"sidx" + (b"\x00" * 16)
    response = DummyResponse(ftyp_box + free_box + sidx_box)

    init_range, index_range = dash_builder._mp4_find_init_and_index_ranges(response)

    assert init_range == (0, 23)
    assert index_range == (24, 47)


def test_mp4_find_ranges_returns_default_when_missing_sidx():
    payload = b"\x00\x00\x00\x10" + b"ftyp" + b"isom0000"
    response = DummyResponse(payload)

    init_range, index_range = dash_builder._mp4_find_init_and_index_ranges(response)

    assert init_range == (0, 0)
    assert index_range == (0, 0)


def test_iso8601_duration_formatting():
    assert dash_builder._iso8601_duration(1.5) == "P0DT0H0M1.5S"
    assert dash_builder._iso8601_duration(3661) == "P0DT1H1M1S"


def test_transform_url_replaces_query_separators():
    url = "https://example.com/v?id=123&quality=high"
    assert dash_builder.transform_url(url) == "https://example.com/v/id/123/quality/high"


def test_webm_decode_int_covers_longer_prefix_lengths():
    assert dash_builder._webm_decode_int(0b00001000) == (5, 0)
    assert dash_builder._webm_decode_int(0b00000100) == (6, 0)
    assert dash_builder._webm_decode_int(0b00000010) == (7, 0)


def test_webm_find_ranges_finds_cues_element():
    ebml = bytes.fromhex("1A45DFA3")
    filler = b"\x00"
    segment = bytes.fromhex("1853806780")
    cues = bytes.fromhex("1C53BB6B80")
    payload = ebml + filler + segment + cues + (b"\x00" * 20)

    init_range, index_range = dash_builder._webm_find_init_and_index_ranges(DummyResponse(payload))

    assert init_range == (0, 9)
    assert index_range == (10, 14)


def test_find_init_and_index_ranges_dispatches_by_container(monkeypatch):
    called = []

    class DummyRequestsResponse:
        content = b"dummy"

    def fake_get(url, headers):
        called.append((url, headers))
        return DummyRequestsResponse()

    monkeypatch.setattr(dash_builder.requests, "get", fake_get)
    monkeypatch.setattr(dash_builder, "_webm_find_init_and_index_ranges", lambda _r: ((1, 2), (3, 4)))
    monkeypatch.setattr(dash_builder, "_mp4_find_init_and_index_ranges", lambda _r: ((5, 6), (7, 8)))

    assert dash_builder.find_init_and_index_ranges("https://x", "webm_dash") == ((1, 2), (3, 4))
    assert dash_builder.find_init_and_index_ranges("https://x", "mp4_dash") == ((5, 6), (7, 8))
    assert called[0][1]["Range"] == "bytes=0-1023"


def test_manifest_add_formats_and_emit(monkeypatch):
    monkeypatch.setattr(dash_builder, "find_init_and_index_ranges", lambda *_args, **_kwargs: ((0, 9), (10, 19)))

    manifest = dash_builder.Manifest(duration=12.5)
    manifest.add_audio_format(
        {
            "format_id": "140-dash",
            "acodec": "mp4a.40.2",
            "asr": 44100,
            "ext": "mp4",
            "tbr": 128,
            "audio_channels": 2,
            "url": "https://example.com/a?id=1&x=2",
            "container": "mp4_dash",
        }
    )
    manifest.add_video_format(
        {
            "format_id": "137-dash",
            "vcodec": "avc1.640028",
            "fps": 30,
            "resolution": "1920x1080",
            "ext": "mp4",
            "vbr": 2500,
            "url": "https://example.com/v?id=1&x=2",
            "container": "mp4_dash",
        }
    )

    xml_bytes = manifest.emit()
    xml_text = xml_bytes.decode("utf-8")

    assert "<MPD" in xml_text
    assert "audio/mp4" in xml_text
    assert "video/mp4" in xml_text
    assert "indexRange=\"10-19\"" in xml_text
    assert "range=\"0-9\"" in xml_text


def test_manifest_add_formats_without_bandwidth(monkeypatch):
    monkeypatch.setattr(dash_builder, "find_init_and_index_ranges", lambda *_args, **_kwargs: ((0, 1), (2, 3)))
    manifest = dash_builder.Manifest(duration=1)

    manifest.add_audio_format(
        {
            "format_id": "251",
            "acodec": "opus",
            "asr": 48000,
            "ext": "webm",
            "audio_channels": 2,
            "url": "https://example.com/a",
            "container": "webm_dash",
        }
    )
    manifest.add_video_format(
        {
            "format_id": "248",
            "vcodec": "vp9",
            "fps": 24,
            "resolution": "1280x720",
            "ext": "webm",
            "url": "https://example.com/v",
            "container": "webm_dash",
        }
    )

    xml_text = manifest.emit().decode("utf-8")
    assert "bandwidth=" not in xml_text


def test_http_handler_head_and_get_methods_write_headers_and_body():
    class DummyWFile:
        def __init__(self):
            self.written = b""

        def write(self, data):
            self.written += data

    class DummyHandler:
        def __init__(self):
            self.mpd = b"manifest"
            self.calls = []
            self.wfile = DummyWFile()

        def send_response(self, code, msg):
            self.calls.append(("response", code, msg))

        def send_header(self, key, value):
            self.calls.append(("header", key, value))

        def end_headers(self):
            self.calls.append(("end",))

        def do_HEAD(self):
            dash_builder.HttpHandler.do_HEAD(self)

    handler = DummyHandler()
    dash_builder.HttpHandler.do_HEAD(handler)
    dash_builder.HttpHandler.do_GET(handler)

    assert ("response", 200, "OK") in handler.calls
    assert ("header", "Content-type", "application/dash+xml") in handler.calls
    assert ("header", "Content-Length", str(len(b"manifest"))) in handler.calls
    assert handler.wfile.written == b"manifest"


def test_handle_request_stops_after_timeout():
    class DummyHttpd:
        def __init__(self):
            self.calls = 0

        def handle_request(self):
            self.calls += 1
            raise TimeoutError()

    httpd = DummyHttpd()
    dash_builder._handle_request(httpd)
    assert httpd.calls == 1


def test_start_httpd_uses_server_and_thread(monkeypatch):
    started = {"called": False}

    dash_builder._reset_httpd_state_for_tests()

    class FakeHTTPServer:
        def __init__(self, server_address, handler):
            self.server_address = server_address
            self.handler = handler
            self.server_port = 8123
            self.timeout = None
            self.handle_timeout = None

        def handle_request(self):
            raise TimeoutError()

    class FakeThread:
        def __init__(self, target, args):
            self.target = target
            self.args = args

        def start(self):
            started["called"] = True

    monkeypatch.setattr(dash_builder, "HTTPServer", FakeHTTPServer)
    monkeypatch.setattr(dash_builder, "Thread", FakeThread)

    url = dash_builder.start_httpd(b"manifest")

    assert started["called"] is True
    assert url.startswith("http://127.0.0.1:8123/manifest/")
    assert url.endswith(".mpd")


def test_start_httpd_refreshes_manifest_after_timeout(monkeypatch):
    dash_builder._reset_httpd_state_for_tests()

    class FakeHTTPServer:
        def __init__(self, _server_address, _handler):
            self.server_port = 8123
            self.timeout = None
            self.handle_timeout = None

        def handle_request(self):
            raise TimeoutError()

    class FakeThread:
        def __init__(self, target, args):
            self.target = target
            self.args = args
            self.daemon = False

        def start(self):
            return None

    monkeypatch.setattr(dash_builder, "HTTPServer", FakeHTTPServer)
    monkeypatch.setattr(dash_builder, "Thread", FakeThread)
    monkeypatch.setattr(dash_builder, "DASH_HTTPD_IDLE_TIMEOUT_SECONDS", 1)

    state = {"version": 1}

    def refresh_manifest():
        state["version"] += 1
        return "manifest-v{}".format(state["version"]).encode("utf-8")

    url = dash_builder.start_httpd(b"manifest-v1", refresh_manifest=refresh_manifest)
    manifest_id = url.rsplit("/", 1)[-1].replace(".mpd", "")

    entry = dash_builder._MANIFESTS[manifest_id]
    entry["refreshed_at"] = 0

    class DummyHandler:
        def __init__(self, path):
            self.path = path

    payload = dash_builder.HttpHandler._resolve_manifest_payload(DummyHandler(url.replace("http://127.0.0.1:8123", "")))

    assert payload == b"manifest-v2"
