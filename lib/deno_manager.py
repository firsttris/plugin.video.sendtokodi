# -*- coding: utf-8 -*-
"""
Deno JavaScript runtime manager for yt-dlp
Downloads and manages Deno binaries for YouTube extraction with JS support
"""

import os
import sys
import platform
import subprocess
import zipfile
import tarfile
import tempfile
import shutil

try:
    import xbmc
    import xbmcvfs
    KODI_ENV = True
except ImportError:
    KODI_ENV = False

try:
    from urllib.request import urlopen, Request
    from urllib.error import URLError
except ImportError:
    from urllib2 import urlopen, Request, URLError


# Deno version to download
DENO_VERSION = "v2.6.4"  # Latest stable version compatible with yt-dlp

# GitHub release URL pattern
DENO_RELEASE_URL = "https://github.com/denoland/deno/releases/download/{version}/{filename}"


def log(msg, level=None):
    """Log messages to Kodi log or stdout"""
    if KODI_ENV and level is not None:
        addon_id = "plugin.video.sendtokodi"
        xbmc.log('{}: {}'.format(addon_id, msg), level)
    else:
        print(msg)


def get_platform_info():
    """
    Detect the current platform and return appropriate Deno binary info
    Returns: (platform_name, arch, file_extension, binary_name)
    """
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    # Normalize architecture names
    if machine in ['x86_64', 'amd64']:
        arch = 'x86_64'
    elif machine in ['aarch64', 'arm64']:
        arch = 'aarch64'
    elif machine in ['armv7l', 'armv7']:
        # Deno doesn't officially support 32-bit ARM, use aarch64 if possible
        arch = 'aarch64'
    else:
        arch = machine
    
    if system == 'linux':
        return ('linux', arch, 'zip', 'deno')
    elif system == 'darwin':
        return ('darwin', arch, 'zip', 'deno')
    elif system == 'windows':
        return ('windows', arch, 'zip', 'deno.exe')
    else:
        raise RuntimeError('Unsupported platform: {} {}'.format(system, machine))


def get_deno_filename(platform_name, arch):
    """
    Get the Deno release filename for the platform
    """
    # Deno release naming convention: deno-{arch}-{platform}.zip
    if platform_name == 'darwin':
        platform_name = 'apple-darwin'
    elif platform_name == 'linux':
        platform_name = 'unknown-linux-gnu'
    elif platform_name == 'windows':
        platform_name = 'pc-windows-msvc'
    
    return 'deno-{}-{}.zip'.format(arch, platform_name)


def get_deno_dir():
    """
    Get the directory where Deno binary should be stored
    Uses Kodi's special path if in Kodi environment, otherwise uses temp
    """
    if KODI_ENV:
        # Use Kodi's addon data directory
        addon_data = xbmcvfs.translatePath('special://profile/addon_data/plugin.video.sendtokodi/')
        deno_dir = os.path.join(addon_data, 'deno')
    else:
        # For testing outside Kodi
        deno_dir = os.path.join(tempfile.gettempdir(), 'sendtokodi_deno')
    
    if not os.path.exists(deno_dir):
        os.makedirs(deno_dir)
    
    return deno_dir


def get_deno_path():
    """
    Get the full path to the Deno binary
    """
    _, _, _, binary_name = get_platform_info()
    deno_dir = get_deno_dir()
    return os.path.join(deno_dir, binary_name)


def is_deno_available():
    """
    Check if Deno is available either in PATH or in our managed location
    Returns the path to Deno if found, None otherwise
    """
    # First check if it's already downloaded in our managed location
    managed_deno = get_deno_path()
    if os.path.isfile(managed_deno):
        # Check if it's executable
        if os.access(managed_deno, os.X_OK):
            log('Found managed Deno at: {}'.format(managed_deno))
            return managed_deno
    
    # Check if Deno is in PATH
    try:
        if platform.system().lower() == 'windows':
            result = subprocess.run(['where', 'deno'], 
                                   capture_output=True, text=True, timeout=5)
        else:
            result = subprocess.run(['which', 'deno'], 
                                   capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            deno_path = result.stdout.strip()
            if deno_path:
                log('Found system Deno at: {}'.format(deno_path))
                return deno_path
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        log('Error checking for system Deno: {}'.format(str(e)))
    
    return None


def download_file(url, destination, progress_callback=None):
    """
    Download a file from URL to destination
    """
    log('Downloading from: {}'.format(url))
    
    try:
        request = Request(url)
        request.add_header('User-Agent', 'Mozilla/5.0')
        
        response = urlopen(request, timeout=30)
        total_size = int(response.headers.get('content-length', 0))
        
        downloaded = 0
        block_size = 8192
        
        with open(destination, 'wb') as f:
            while True:
                chunk = response.read(block_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                
                if progress_callback and total_size > 0:
                    progress = int((downloaded / total_size) * 100)
                    progress_callback(progress)
        
        log('Download completed: {}'.format(destination))
        return True
        
    except Exception as e:
        log('Download failed: {}'.format(str(e)))
        if os.path.exists(destination):
            os.remove(destination)
        return False


def extract_archive(archive_path, destination_dir):
    """
    Extract a zip or tar.gz archive
    """
    log('Extracting: {}'.format(archive_path))
    
    try:
        if archive_path.endswith('.zip'):
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(destination_dir)
        elif archive_path.endswith('.tar.gz') or archive_path.endswith('.tgz'):
            with tarfile.open(archive_path, 'r:gz') as tar_ref:
                tar_ref.extractall(destination_dir)
        else:
            log('Unknown archive format: {}'.format(archive_path))
            return False
        
        log('Extraction completed')
        return True
        
    except Exception as e:
        log('Extraction failed: {}'.format(str(e)))
        return False


def download_deno(progress_callback=None):
    """
    Download and install Deno binary
    Returns the path to the installed Deno binary or None on failure
    """
    try:
        platform_name, arch, file_ext, binary_name = get_platform_info()
        filename = get_deno_filename(platform_name, arch)
        url = DENO_RELEASE_URL.format(version=DENO_VERSION, filename=filename)
        
        deno_dir = get_deno_dir()
        archive_path = os.path.join(deno_dir, filename)
        
        log('Downloading Deno {} for {} {}'.format(DENO_VERSION, platform_name, arch))
        
        # Download the archive
        if not download_file(url, archive_path, progress_callback):
            return None
        
        # Extract the archive
        if not extract_archive(archive_path, deno_dir):
            return None
        
        # Clean up the archive
        try:
            os.remove(archive_path)
        except:
            pass
        
        # Make sure the binary is executable (Unix-like systems)
        deno_path = get_deno_path()
        if platform.system().lower() != 'windows':
            os.chmod(deno_path, 0o755)
        
        # Verify the binary works
        try:
            result = subprocess.run([deno_path, '--version'], 
                                   capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                log('Deno installed successfully: {}'.format(result.stdout.strip()))
                return deno_path
            else:
                log('Deno verification failed')
                return None
        except Exception as e:
            log('Deno verification error: {}'.format(str(e)))
            return None
            
    except Exception as e:
        log('Failed to download Deno: {}'.format(str(e)))
        return None


def ensure_deno_available(auto_download=True):
    """
    Ensure Deno is available, downloading it if necessary
    
    Args:
        auto_download: If True, download Deno if not found
    
    Returns:
        Path to Deno binary if available, None otherwise
    """
    deno_path = is_deno_available()
    
    if deno_path:
        return deno_path
    
    if not auto_download:
        log('Deno not found and auto-download is disabled')
        return None
    
    log('Deno not found, downloading...')
    
    # Show progress dialog in Kodi
    if KODI_ENV:
        import xbmcgui
        progress = xbmcgui.DialogProgressBG()
        progress.create('SendToKodi', 'Downloading Deno JavaScript runtime...')
        
        def update_progress(percent):
            progress.update(percent, 'SendToKodi', 
                          'Downloading Deno JavaScript runtime... {}%'.format(percent))
        
        try:
            deno_path = download_deno(update_progress)
        finally:
            progress.close()
    else:
        deno_path = download_deno()
    
    return deno_path


def get_ydl_deno_config(auto_download=True):
    """
    Get yt-dlp configuration for Deno support
    
    Args:
        auto_download: If True, download Deno if not found
    
    Returns:
        Dictionary with yt-dlp options for Deno, or empty dict if Deno not available
    """
    deno_path = ensure_deno_available(auto_download)
    
    if not deno_path:
        return {}
    
    return {
        'js_runtimes': {
            'deno': {'path': deno_path}
        },
        'remote_components': ['ejs:github']
    }


if __name__ == '__main__':
    # Test the module
    print('Testing Deno manager...')
    print('Platform:', get_platform_info())
    print('Deno dir:', get_deno_dir())
    print('Deno path:', get_deno_path())
    print('Checking for Deno...')
    deno = ensure_deno_available(auto_download=True)
    if deno:
        print('Deno is available at:', deno)
        config = get_ydl_deno_config()
        print('yt-dlp config:', config)
    else:
        print('Failed to get Deno')
