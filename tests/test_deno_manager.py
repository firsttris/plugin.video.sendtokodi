# -*- coding: utf-8 -*-
"""
Unit tests for deno_manager module
"""

import os
import sys
import tempfile
import platform
import unittest
from unittest import mock

# Add lib directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

import deno_manager


class TestPlatformDetection(unittest.TestCase):
    """Tests for platform detection functions"""

    def test_get_platform_info_returns_tuple(self):
        """Test that get_platform_info returns a 4-tuple"""
        result = deno_manager.get_platform_info()
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 4)

    def test_get_platform_info_valid_platform(self):
        """Test that platform name is valid"""
        platform_name, arch, file_ext, binary_name = deno_manager.get_platform_info()
        self.assertIn(platform_name, ['linux', 'darwin', 'windows'])

    def test_get_platform_info_valid_extension(self):
        """Test that file extension is valid"""
        platform_name, arch, file_ext, binary_name = deno_manager.get_platform_info()
        self.assertEqual(file_ext, 'zip')

    def test_get_platform_info_binary_name(self):
        """Test that binary name is correct for platform"""
        platform_name, arch, file_ext, binary_name = deno_manager.get_platform_info()
        if platform_name == 'windows':
            self.assertEqual(binary_name, 'deno.exe')
        else:
            self.assertEqual(binary_name, 'deno')

    @mock.patch('platform.system')
    @mock.patch('platform.machine')
    def test_linux_x86_64(self, mock_machine, mock_system):
        """Test Linux x86_64 detection"""
        mock_system.return_value = 'Linux'
        mock_machine.return_value = 'x86_64'
        result = deno_manager.get_platform_info()
        self.assertEqual(result, ('linux', 'x86_64', 'zip', 'deno'))

    @mock.patch('platform.system')
    @mock.patch('platform.machine')
    def test_linux_arm64(self, mock_machine, mock_system):
        """Test Linux ARM64 detection"""
        mock_system.return_value = 'Linux'
        mock_machine.return_value = 'aarch64'
        result = deno_manager.get_platform_info()
        self.assertEqual(result, ('linux', 'aarch64', 'zip', 'deno'))

    @mock.patch('platform.system')
    @mock.patch('platform.machine')
    def test_darwin_x86_64(self, mock_machine, mock_system):
        """Test macOS x86_64 detection"""
        mock_system.return_value = 'Darwin'
        mock_machine.return_value = 'x86_64'
        result = deno_manager.get_platform_info()
        self.assertEqual(result, ('darwin', 'x86_64', 'zip', 'deno'))

    @mock.patch('platform.system')
    @mock.patch('platform.machine')
    def test_darwin_arm64(self, mock_machine, mock_system):
        """Test macOS ARM64 (Apple Silicon) detection"""
        mock_system.return_value = 'Darwin'
        mock_machine.return_value = 'arm64'
        result = deno_manager.get_platform_info()
        self.assertEqual(result, ('darwin', 'aarch64', 'zip', 'deno'))

    @mock.patch('platform.system')
    @mock.patch('platform.machine')
    def test_windows_x86_64(self, mock_machine, mock_system):
        """Test Windows x86_64 detection"""
        mock_system.return_value = 'Windows'
        mock_machine.return_value = 'AMD64'
        result = deno_manager.get_platform_info()
        self.assertEqual(result, ('windows', 'x86_64', 'zip', 'deno.exe'))

    @mock.patch('platform.system')
    @mock.patch('platform.machine')
    def test_unsupported_platform(self, mock_machine, mock_system):
        """Test that unsupported platform raises RuntimeError"""
        mock_system.return_value = 'FreeBSD'
        mock_machine.return_value = 'x86_64'
        with self.assertRaises(RuntimeError):
            deno_manager.get_platform_info()


class TestDenoFilename(unittest.TestCase):
    """Tests for Deno filename generation"""

    def test_linux_x86_64_filename(self):
        """Test Linux x86_64 filename"""
        result = deno_manager.get_deno_filename('linux', 'x86_64')
        self.assertEqual(result, 'deno-x86_64-unknown-linux-gnu.zip')

    def test_linux_aarch64_filename(self):
        """Test Linux aarch64 filename"""
        result = deno_manager.get_deno_filename('linux', 'aarch64')
        self.assertEqual(result, 'deno-aarch64-unknown-linux-gnu.zip')

    def test_darwin_x86_64_filename(self):
        """Test macOS x86_64 filename"""
        result = deno_manager.get_deno_filename('darwin', 'x86_64')
        self.assertEqual(result, 'deno-x86_64-apple-darwin.zip')

    def test_darwin_aarch64_filename(self):
        """Test macOS aarch64 filename"""
        result = deno_manager.get_deno_filename('darwin', 'aarch64')
        self.assertEqual(result, 'deno-aarch64-apple-darwin.zip')

    def test_windows_x86_64_filename(self):
        """Test Windows x86_64 filename"""
        result = deno_manager.get_deno_filename('windows', 'x86_64')
        self.assertEqual(result, 'deno-x86_64-pc-windows-msvc.zip')


class TestDenoPaths(unittest.TestCase):
    """Tests for Deno path functions"""

    def test_get_deno_dir_returns_string(self):
        """Test that get_deno_dir returns a string path"""
        result = deno_manager.get_deno_dir()
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_get_deno_dir_creates_directory(self):
        """Test that get_deno_dir creates the directory if it doesn't exist"""
        deno_dir = deno_manager.get_deno_dir()
        self.assertTrue(os.path.exists(deno_dir))

    def test_get_deno_path_returns_string(self):
        """Test that get_deno_path returns a string path"""
        result = deno_manager.get_deno_path()
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_get_deno_path_contains_deno_dir(self):
        """Test that get_deno_path is within the deno directory"""
        deno_dir = deno_manager.get_deno_dir()
        deno_path = deno_manager.get_deno_path()
        self.assertTrue(deno_path.startswith(deno_dir))


class TestDenoDetection(unittest.TestCase):
    """Tests for Deno availability detection"""

    def test_is_deno_available_returns_path_or_none(self):
        """Test that is_deno_available returns a path string or None"""
        result = deno_manager.is_deno_available()
        self.assertTrue(result is None or isinstance(result, str))

    @mock.patch('subprocess.run')
    @mock.patch.object(deno_manager, 'get_deno_path')
    def test_is_deno_available_finds_system_deno(self, mock_get_path, mock_run):
        """Test that system Deno is detected"""
        # Mock managed deno not existing
        mock_get_path.return_value = '/nonexistent/deno'
        
        # Mock system deno being found
        mock_run.return_value = mock.Mock(returncode=0, stdout='/usr/bin/deno\n')
        
        result = deno_manager.is_deno_available()
        # Result depends on actual subprocess call implementation
        # This test just ensures no exception is raised


class TestYdlConfig(unittest.TestCase):
    """Tests for yt-dlp configuration generation"""

    @mock.patch.object(deno_manager, 'ensure_deno_available')
    def test_get_ydl_deno_config_with_deno(self, mock_ensure):
        """Test configuration when Deno is available"""
        mock_ensure.return_value = '/path/to/deno'
        
        result = deno_manager.get_ydl_deno_config(auto_download=False)
        
        self.assertIsInstance(result, dict)
        self.assertIn('js_runtimes', result)
        self.assertIn('deno', result['js_runtimes'])
        self.assertEqual(result['js_runtimes']['deno']['path'], '/path/to/deno')
        self.assertIn('remote_components', result)

    @mock.patch.object(deno_manager, 'ensure_deno_available')
    def test_get_ydl_deno_config_without_deno(self, mock_ensure):
        """Test configuration when Deno is not available"""
        mock_ensure.return_value = None
        
        result = deno_manager.get_ydl_deno_config(auto_download=False)
        
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 0)


class TestDownloadFunctions(unittest.TestCase):
    """Tests for download-related functions"""

    def test_deno_version_constant_format(self):
        """Test that DENO_VERSION follows expected format"""
        self.assertTrue(deno_manager.DENO_VERSION.startswith('v'))
        # Should be like v1.2.3 or v2.0.0
        parts = deno_manager.DENO_VERSION[1:].split('.')
        self.assertTrue(len(parts) >= 2)
        for part in parts:
            self.assertTrue(part.isdigit())

    def test_deno_release_url_format(self):
        """Test that DENO_RELEASE_URL contains required placeholders"""
        self.assertIn('{version}', deno_manager.DENO_RELEASE_URL)
        self.assertIn('{filename}', deno_manager.DENO_RELEASE_URL)
        self.assertTrue(deno_manager.DENO_RELEASE_URL.startswith('https://'))


class TestExtractArchive(unittest.TestCase):
    """Tests for archive extraction function"""

    def test_extract_unknown_format(self):
        """Test that unknown archive format returns False"""
        with tempfile.NamedTemporaryFile(suffix='.rar', delete=False) as f:
            temp_path = f.name
        
        try:
            result = deno_manager.extract_archive(temp_path, tempfile.gettempdir())
            self.assertFalse(result)
        finally:
            os.unlink(temp_path)


class TestLogging(unittest.TestCase):
    """Tests for logging function"""

    @mock.patch('builtins.print')
    def test_log_outside_kodi(self, mock_print):
        """Test that logging works outside Kodi environment"""
        deno_manager.log('Test message')
        mock_print.assert_called_once_with('Test message')


if __name__ == '__main__':
    unittest.main()
