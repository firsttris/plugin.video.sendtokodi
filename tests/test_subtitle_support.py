from core.subtitle_support import build_subtitle_file_name, normalize_subtitle_extension


def test_build_subtitle_file_name_prefers_readable_name():
    file_name = build_subtitle_file_name(
        {"name": "German", "language": "de", "ext": "srt"},
        used_file_names=set(),
    )

    assert file_name == "German.srt"


def test_build_subtitle_file_name_falls_back_to_language_and_sanitizes():
    file_name = build_subtitle_file_name(
        {"name": "Deutsch / German", "language": "de", "ext": "vtt"},
        used_file_names=set(),
    )

    assert file_name == "Deutsch German.vtt"


def test_build_subtitle_file_name_deduplicates_equal_names():
    used_file_names = set()

    first_name = build_subtitle_file_name(
        {"name": "German", "language": "de", "ext": "srt"},
        used_file_names=used_file_names,
    )
    second_name = build_subtitle_file_name(
        {"name": "German", "language": "de-orig", "ext": "srt"},
        used_file_names=used_file_names,
    )

    assert first_name == "German.srt"
    assert second_name == "German-2.srt"


def test_normalize_subtitle_extension_defaults_to_srt():
    assert normalize_subtitle_extension("") == "srt"