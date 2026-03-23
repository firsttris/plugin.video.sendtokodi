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
