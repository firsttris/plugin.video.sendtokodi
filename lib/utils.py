# -*- coding: utf-8 -*-
"""
Utility functions for SendToKodi plugin
These functions are extracted to allow unit testing without Kodi dependencies
"""

import json


def parse_params(paramstring):
    """
    Parse plugin parameters from the URL parameter string.
    
    Args:
        paramstring: The parameter string from sys.argv[2], e.g. "?url" or "?url {json}"
    
    Returns:
        dict with 'url' and 'ydlOpts' keys
    """
    result = {}
    additionalParamsIndex = paramstring.find(' ')
    if additionalParamsIndex == -1:
        result['url'] = paramstring[1:]
        result['ydlOpts'] = {}
    else:
        result['url'] = paramstring[1:additionalParamsIndex]
        additionalParamsString = paramstring[additionalParamsIndex:]
        additionalParams = json.loads(additionalParamsString)
        result['ydlOpts'] = additionalParams['ydlOpts']
    return result


def guess_manifest_type(f, url):
    """
    Guess the manifest/stream type from format info and URL.
    
    Args:
        f: Format dictionary with optional 'protocol' key
        url: The stream URL
    
    Returns:
        String indicating manifest type ('hls', 'mpd', 'rtmp', 'ism') or None
    """
    protocol = f.get('protocol', "")
    if protocol.startswith("m3u"):
        return "hls"
    elif protocol.startswith("rtmp") or protocol == "rtsp":
        return "rtmp"
    elif protocol == "ism":
        return "ism"
    for s in [".m3u", ".m3u8", ".hls", ".mpd", ".rtmp", ".ism"]:
        offset = url.find(s, 0)
        while offset != -1:
            if offset == len(url) - len(s) or not url[offset + len(s)].isalnum():
                if s.startswith(".m3u"):
                    s = ".hls"
                return s[1:]
            offset = url.find(s, offset + 1)
    return None


def create_strptime_proxy():
    """
    Create a proxy datetime class that fixes strptime bug in Kodi's embedded Python.
    
    The python embedded (as used in kodi) has a known bug for second calls of strptime.
    See: https://bugs.python.org/issue27400
    
    Returns:
        A proxy datetime class with working strptime
    """
    import datetime
    import time
    
    class proxydt(datetime.datetime):
        @staticmethod
        def strptime(date_string, format):
            return datetime.datetime(*(time.strptime(date_string, format)[0:6]))
    
    return proxydt


def format_duration(seconds):
    """
    Format duration in seconds to a human-readable string.
    
    Args:
        seconds: Duration in seconds (int or float)
    
    Returns:
        Formatted string like "1:23:45" or "23:45"
    """
    if seconds is None:
        return ""
    
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return "{}:{:02d}:{:02d}".format(hours, minutes, secs)
    else:
        return "{}:{:02d}".format(minutes, secs)


def sanitize_filename(filename):
    """
    Sanitize a filename by removing/replacing invalid characters.
    
    Args:
        filename: The filename to sanitize
    
    Returns:
        Sanitized filename safe for filesystem use
    """
    if not filename:
        return filename
    
    # Characters not allowed in filenames on various systems
    invalid_chars = '<>:"/\\|?*'
    
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    
    return filename


def is_playlist_url(url):
    """
    Check if the URL appears to be a playlist URL.
    
    Args:
        url: URL string to check
    
    Returns:
        True if URL appears to be a playlist, False otherwise
    """
    if not url:
        return False
    
    playlist_indicators = [
        '/playlist',
        'list=',
        '/channel/',
        '/user/',
        '/c/',
        '@',  # YouTube handle
    ]
    
    url_lower = url.lower()
    return any(indicator in url_lower for indicator in playlist_indicators)


def extract_video_id(url):
    """
    Extract video ID from common video platform URLs.
    
    Args:
        url: Video URL
    
    Returns:
        Video ID string or None if not found
    """
    from urllib.parse import urlparse, parse_qs
    
    if not url:
        return None
    
    parsed = urlparse(url)
    
    # YouTube
    if 'youtube.com' in parsed.netloc or 'youtu.be' in parsed.netloc:
        if 'youtu.be' in parsed.netloc:
            # Short URL format: youtu.be/VIDEO_ID
            return parsed.path.lstrip('/')
        else:
            # Standard format: youtube.com/watch?v=VIDEO_ID
            query_params = parse_qs(parsed.query)
            if 'v' in query_params:
                return query_params['v'][0]
    
    # Vimeo
    if 'vimeo.com' in parsed.netloc:
        path_parts = parsed.path.strip('/').split('/')
        if path_parts:
            # Could be vimeo.com/VIDEO_ID or vimeo.com/channels/name/VIDEO_ID
            for part in reversed(path_parts):
                if part.isdigit():
                    return part
    
    return None
