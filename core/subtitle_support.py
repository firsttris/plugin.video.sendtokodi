import re


def _sanitize_filename_component(value):
    ascii_value = (value or '').encode('ascii', 'ignore').decode('ascii')
    normalized = re.sub(r'\s+', ' ', ascii_value)
    sanitized = re.sub(r'[^A-Za-z0-9._ -]+', '', normalized)
    return re.sub(r'\s+', ' ', sanitized).strip(' ._-')


def normalize_subtitle_extension(extension):
    sanitized = _sanitize_filename_component(extension).lower()
    if sanitized:
        return sanitized
    return 'srt'


def build_subtitle_file_name(subtitle_entry, used_file_names=None):
    base_name = _sanitize_filename_component(subtitle_entry.get('name'))
    if not base_name:
        base_name = _sanitize_filename_component(subtitle_entry.get('language'))
    if not base_name:
        base_name = 'subtitle'

    file_name = base_name
    if used_file_names is not None:
        existing_names = used_file_names
        candidate_name = file_name
        suffix = 2
        while candidate_name.lower() in existing_names:
            candidate_name = '{}-{}'.format(file_name, suffix)
            suffix += 1
        existing_names.add(candidate_name.lower())
        file_name = candidate_name

    return '{}.{}'.format(file_name, normalize_subtitle_extension(subtitle_entry.get('ext')))