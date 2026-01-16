# -*- coding: utf-8 -*-
"""
Unit tests for service module utility functions
Tests the actual utility functions from lib/utils.py
"""

import os
import sys
import unittest

# Add lib directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from utils import (
    parse_params,
    guess_manifest_type,
    create_strptime_proxy,
    format_duration,
    sanitize_filename,
    is_playlist_url,
    extract_video_id
)


class TestGuessManifestType(unittest.TestCase):
    """Tests for manifest type guessing"""

    def test_m3u_protocol(self):
        """Test m3u8 protocol detection"""
        f = {'protocol': 'm3u8'}
        result = guess_manifest_type(f, 'http://example.com/stream')
        self.assertEqual(result, 'hls')

    def test_m3u8_protocol(self):
        """Test m3u8_native protocol detection"""
        f = {'protocol': 'm3u8_native'}
        result = guess_manifest_type(f, 'http://example.com/stream')
        self.assertEqual(result, 'hls')

    def test_rtmp_protocol(self):
        """Test RTMP protocol detection"""
        f = {'protocol': 'rtmp'}
        result = guess_manifest_type(f, 'http://example.com/stream')
        self.assertEqual(result, 'rtmp')

    def test_rtsp_protocol(self):
        """Test RTSP protocol detection"""
        f = {'protocol': 'rtsp'}
        result = guess_manifest_type(f, 'http://example.com/stream')
        self.assertEqual(result, 'rtmp')

    def test_ism_protocol(self):
        """Test ISM protocol detection"""
        f = {'protocol': 'ism'}
        result = guess_manifest_type(f, 'http://example.com/stream')
        self.assertEqual(result, 'ism')

    def test_m3u8_url_extension(self):
        """Test .m3u8 URL extension detection"""
        f = {}
        result = guess_manifest_type(f, 'http://example.com/stream.m3u8')
        self.assertEqual(result, 'hls')

    def test_m3u_url_extension(self):
        """Test .m3u URL extension detection"""
        f = {}
        result = guess_manifest_type(f, 'http://example.com/stream.m3u')
        self.assertEqual(result, 'hls')

    def test_mpd_url_extension(self):
        """Test .mpd URL extension detection"""
        f = {}
        result = guess_manifest_type(f, 'http://example.com/stream.mpd')
        self.assertEqual(result, 'mpd')

    def test_ism_url_extension(self):
        """Test .ism URL extension detection"""
        f = {}
        result = guess_manifest_type(f, 'http://example.com/stream.ism')
        self.assertEqual(result, 'ism')

    def test_m3u8_url_with_query(self):
        """Test .m3u8 URL with query parameters"""
        f = {}
        result = guess_manifest_type(f, 'http://example.com/stream.m3u8?token=abc')
        self.assertEqual(result, 'hls')

    def test_no_manifest_type(self):
        """Test when no manifest type can be determined"""
        f = {}
        result = guess_manifest_type(f, 'http://example.com/video.mp4')
        self.assertIsNone(result)

    def test_empty_format_and_url(self):
        """Test with empty format and basic URL"""
        f = {}
        result = guess_manifest_type(f, 'http://example.com/')
        self.assertIsNone(result)

    def test_hls_url_extension(self):
        """Test .hls URL extension detection"""
        f = {}
        result = guess_manifest_type(f, 'http://example.com/stream.hls')
        self.assertEqual(result, 'hls')

    def test_rtmp_url_extension(self):
        """Test .rtmp URL extension detection"""
        f = {}
        result = guess_manifest_type(f, 'http://example.com/stream.rtmp')
        self.assertEqual(result, 'rtmp')

    def test_extension_in_middle_followed_by_alphanum(self):
        """Test that extensions followed by alphanumeric chars are not matched"""
        f = {}
        result = guess_manifest_type(f, 'http://example.com/stream.m3u8abc')
        self.assertIsNone(result)


class TestParseParams(unittest.TestCase):
    """Tests for URL parameter parsing using parse_params from utils"""

    def test_simple_url(self):
        """Test parsing simple URL"""
        paramstring = '?https://youtube.com/watch?v=test'
        result = parse_params(paramstring)
        self.assertEqual(result['url'], 'https://youtube.com/watch?v=test')
        self.assertEqual(result['ydlOpts'], {})

    def test_url_with_ydl_opts(self):
        """Test parsing URL with ydl options"""
        paramstring = '?https://youtube.com/watch?v=test {"ydlOpts": {"format": "best"}}'
        result = parse_params(paramstring)
        self.assertEqual(result['url'], 'https://youtube.com/watch?v=test')
        self.assertEqual(result['ydlOpts'], {'format': 'best'})

    def test_url_with_complex_ydl_opts(self):
        """Test parsing URL with complex ydl options"""
        paramstring = '?https://example.com/video {"ydlOpts": {"format": "bestvideo+bestaudio", "subtitleslangs": ["en", "de"]}}'
        result = parse_params(paramstring)
        self.assertEqual(result['url'], 'https://example.com/video')
        self.assertEqual(result['ydlOpts']['format'], 'bestvideo+bestaudio')
        self.assertEqual(result['ydlOpts']['subtitleslangs'], ['en', 'de'])

    def test_url_without_query_prefix(self):
        """Test URL that starts with ? prefix"""
        paramstring = '?http://example.com'
        result = parse_params(paramstring)
        self.assertEqual(result['url'], 'http://example.com')

    def test_empty_ydl_opts(self):
        """Test that ydlOpts defaults to empty dict"""
        paramstring = '?http://example.com'
        result = parse_params(paramstring)
        self.assertIsInstance(result['ydlOpts'], dict)
        self.assertEqual(len(result['ydlOpts']), 0)


class TestCreateStrptimeProxy(unittest.TestCase):
    """Tests for strptime proxy creation"""

    def test_proxy_strptime_date(self):
        """Test that the proxy creates a working strptime for dates"""
        proxydt = create_strptime_proxy()
        result = proxydt.strptime('2023-01-15', '%Y-%m-%d')
        self.assertEqual(result.year, 2023)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 15)

    def test_proxy_strptime_datetime(self):
        """Test that the proxy handles datetime formats"""
        proxydt = create_strptime_proxy()
        result = proxydt.strptime('2023-01-15 14:30:45', '%Y-%m-%d %H:%M:%S')
        self.assertEqual(result.hour, 14)
        self.assertEqual(result.minute, 30)
        self.assertEqual(result.second, 45)

    def test_proxy_is_datetime_subclass(self):
        """Test that proxy is a datetime subclass"""
        import datetime
        proxydt = create_strptime_proxy()
        self.assertTrue(issubclass(proxydt, datetime.datetime))


class TestFormatDuration(unittest.TestCase):
    """Tests for duration formatting"""

    def test_format_seconds_only(self):
        """Test formatting seconds only"""
        result = format_duration(45)
        self.assertEqual(result, '0:45')

    def test_format_minutes_and_seconds(self):
        """Test formatting minutes and seconds"""
        result = format_duration(125)
        self.assertEqual(result, '2:05')

    def test_format_hours(self):
        """Test formatting with hours"""
        result = format_duration(3665)
        self.assertEqual(result, '1:01:05')

    def test_format_zero(self):
        """Test formatting zero"""
        result = format_duration(0)
        self.assertEqual(result, '0:00')

    def test_format_none(self):
        """Test formatting None"""
        result = format_duration(None)
        self.assertEqual(result, '')

    def test_format_float(self):
        """Test formatting float seconds"""
        result = format_duration(65.7)
        self.assertEqual(result, '1:05')


class TestSanitizeFilename(unittest.TestCase):
    """Tests for filename sanitization"""

    def test_remove_invalid_chars(self):
        """Test removal of invalid characters"""
        result = sanitize_filename('video<>:"/\\|?*.mp4')
        self.assertNotIn('<', result)
        self.assertNotIn('>', result)
        self.assertNotIn(':', result)
        self.assertNotIn('"', result)
        self.assertNotIn('/', result)
        self.assertNotIn('\\', result)
        self.assertNotIn('|', result)
        self.assertNotIn('?', result)
        self.assertNotIn('*', result)

    def test_preserve_valid_chars(self):
        """Test that valid characters are preserved"""
        result = sanitize_filename('my_video-2023.mp4')
        self.assertEqual(result, 'my_video-2023.mp4')

    def test_strip_spaces_and_dots(self):
        """Test stripping leading/trailing spaces and dots"""
        result = sanitize_filename('  .video.mp4.  ')
        self.assertEqual(result, 'video.mp4')

    def test_empty_filename(self):
        """Test empty filename"""
        result = sanitize_filename('')
        self.assertEqual(result, '')

    def test_none_filename(self):
        """Test None filename"""
        result = sanitize_filename(None)
        self.assertIsNone(result)


class TestIsPlaylistUrl(unittest.TestCase):
    """Tests for playlist URL detection"""

    def test_youtube_playlist(self):
        """Test YouTube playlist URL"""
        self.assertTrue(is_playlist_url('https://youtube.com/playlist?list=PLxxxxxx'))

    def test_youtube_channel(self):
        """Test YouTube channel URL"""
        self.assertTrue(is_playlist_url('https://youtube.com/channel/UCxxxxxx'))

    def test_youtube_user(self):
        """Test YouTube user URL"""
        self.assertTrue(is_playlist_url('https://youtube.com/user/username'))

    def test_youtube_handle(self):
        """Test YouTube handle URL"""
        self.assertTrue(is_playlist_url('https://youtube.com/@channelname'))

    def test_single_video(self):
        """Test single video URL"""
        self.assertFalse(is_playlist_url('https://youtube.com/watch?v=dQw4w9WgXcQ'))

    def test_empty_url(self):
        """Test empty URL"""
        self.assertFalse(is_playlist_url(''))

    def test_none_url(self):
        """Test None URL"""
        self.assertFalse(is_playlist_url(None))


class TestExtractVideoId(unittest.TestCase):
    """Tests for video ID extraction"""

    def test_youtube_standard_url(self):
        """Test YouTube standard URL"""
        result = extract_video_id('https://www.youtube.com/watch?v=dQw4w9WgXcQ')
        self.assertEqual(result, 'dQw4w9WgXcQ')

    def test_youtube_short_url(self):
        """Test YouTube short URL"""
        result = extract_video_id('https://youtu.be/dQw4w9WgXcQ')
        self.assertEqual(result, 'dQw4w9WgXcQ')

    def test_vimeo_url(self):
        """Test Vimeo URL"""
        result = extract_video_id('https://vimeo.com/123456789')
        self.assertEqual(result, '123456789')

    def test_unknown_platform(self):
        """Test unknown platform URL"""
        result = extract_video_id('https://example.com/video')
        self.assertIsNone(result)

    def test_empty_url(self):
        """Test empty URL"""
        result = extract_video_id('')
        self.assertIsNone(result)

    def test_none_url(self):
        """Test None URL"""
        result = extract_video_id(None)
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
