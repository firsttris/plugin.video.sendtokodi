# -*- coding: utf-8 -*-
"""
deno_manager.py — Download and locate the Deno JavaScript runtime for yt-dlp.

yt-dlp requires a JS runtime (Deno) for YouTube extraction.  This module
checks for an existing Deno binary (in the addon_data directory or system
PATH) and optionally downloads it from GitHub Releases when not found.

Public API
----------
get_ydl_opts(auto_download=True) -> dict
    Returns a yt-dlp options dict ready to merge into your ydl_opts, e.g.::

        {'js_runtimes': {'deno': {'path': '/path/to/deno'}},
         'remote_components': {'ejs:github'}}

    Returns an empty dict on any failure so the caller can continue without
    Deno rather than crashing.
"""

import os
import platform
import shutil
import stat
import urllib.request
import zipfile
import io
import logging

DENO_VERSION = "v2.7.5"

# GitHub release URL template — {version} and {filename} are filled at runtime
_RELEASE_URL = (
    "https://github.com/denoland/deno/releases/download/{version}/{filename}"
)

# Map (system, machine) -> release asset filename (without version prefix)
_PLATFORM_MAP = {
    ("linux",   "x86_64"):  "deno-x86_64-unknown-linux-gnu.zip",
    ("linux",   "aarch64"): "deno-aarch64-unknown-linux-gnu.zip",
    ("darwin",  "x86_64"):  "deno-x86_64-apple-darwin.zip",
    ("darwin",  "arm64"):   "deno-aarch64-apple-darwin.zip",   # Kodi uses arm64
    ("darwin",  "aarch64"): "deno-aarch64-apple-darwin.zip",
    ("windows", "x86_64"):  "deno-x86_64-pc-windows-msvc.zip",
    ("windows", "AMD64"):   "deno-x86_64-pc-windows-msvc.zip",
}


def _log(msg, level=None):
    """Log via xbmc if available, otherwise fall back to the stdlib logger."""
    try:
        import xbmc
        if level is None:
            level = xbmc.LOGINFO
        xbmc.log("plugin.video.sendtokodi deno_manager: {}".format(msg), level)
    except ImportError:
        logging.getLogger(__name__).info(msg)


def _warn(msg):
    try:
        import xbmc
        _log(msg, xbmc.LOGWARNING)
    except ImportError:
        logging.getLogger(__name__).warning(msg)


def _addon_data_dir():
    """Return the addon_data directory path, using xbmc.translatePath when available."""
    try:
        import xbmcvfs
        path = xbmcvfs.translatePath(
            "special://profile/addon_data/plugin.video.sendtokodi/deno/"
        )
        return path
    except ImportError:
        pass
    # Fallback for running outside Kodi (tests / CI)
    return os.path.join(
        os.path.expanduser("~"), ".kodi", "userdata",
        "addon_data", "plugin.video.sendtokodi", "deno"
    )


def _deno_binary_name():
    """Return the expected deno executable name for this OS."""
    return "deno.exe" if platform.system().lower() == "windows" else "deno"


def _detect_platform():
    """Return (system_lower, machine) or raise RuntimeError for unsupported platforms."""
    system = platform.system().lower()
    machine = platform.machine()
    key = (system, machine)
    if key not in _PLATFORM_MAP:
        raise RuntimeError(
            "Unsupported platform: system={!r} machine={!r}".format(system, machine)
        )
    return system, machine


def _version_file():
    """Return path to the file that tracks the installed Deno version."""
    return os.path.join(_addon_data_dir(), "deno_version.txt")


def _get_installed_version():
    """Return the installed Deno version string, or None if not recorded."""
    try:
        with open(_version_file(), "r") as f:
            return f.read().strip()
    except Exception:
        return None


def _set_installed_version(version):
    """Write the installed Deno version to the version tracking file."""
    try:
        with open(_version_file(), "w") as f:
            f.write(version)
    except Exception as e:
        _warn("Could not write Deno version file: {}".format(e))


def _find_in_addon_data():
    """Return the deno binary path if it exists in the addon_data directory, else None."""
    deno_dir = _addon_data_dir()
    candidate = os.path.join(deno_dir, _deno_binary_name())
    if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
        return candidate
    return None


def _find_in_path():
    """Return the path to a deno binary on the system PATH, or None."""
    return shutil.which("deno")


def _download_deno(deno_dir, show_progress=True):
    """
    Download and extract the Deno binary into *deno_dir*.

    Uses a Kodi progress dialog when running inside Kodi and *show_progress*
    is True.  Raises on failure.
    """
    system, machine = _detect_platform()
    filename = _PLATFORM_MAP[(system, machine)]
    url = _RELEASE_URL.format(version=DENO_VERSION, filename=filename)

    _log("Downloading Deno {} from {}".format(DENO_VERSION, url))

    # --- optional Kodi progress dialog ---
    progress = None
    if show_progress:
        try:
            import xbmcgui
            progress = xbmcgui.DialogProgress()
            progress.create(
                "SendToKodi",
                "Downloading Deno JavaScript runtime {}…".format(DENO_VERSION),
            )
        except Exception:
            progress = None

    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            total = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            chunks = []
            chunk_size = 65536  # 64 KiB
            while True:
                if progress is not None and progress.iscanceled():
                    raise RuntimeError("Deno download cancelled by user")
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                chunks.append(chunk)
                downloaded += len(chunk)
                if progress is not None and total > 0:
                    pct = int(downloaded * 100 / total)
                    progress.update(
                        pct,
                        "Downloading Deno {} ({}/{} MB)…".format(
                            DENO_VERSION,
                            downloaded // (1024 * 1024),
                            total // (1024 * 1024),
                        ),
                    )
            data = b"".join(chunks)
    finally:
        if progress is not None:
            progress.close()

    # Extract the zip — it contains a single "deno" (or "deno.exe") binary
    os.makedirs(deno_dir, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        binary_name = _deno_binary_name()
        # The zip may contain the binary at the root or in a subdirectory
        candidates = [n for n in zf.namelist()
                      if os.path.basename(n) == binary_name]
        if not candidates:
            raise RuntimeError(
                "Could not find {} inside the downloaded zip".format(binary_name)
            )
        # Use the first (usually only) match
        member = candidates[0]
        dest = os.path.join(deno_dir, binary_name)
        with zf.open(member) as src, open(dest, "wb") as dst:
            dst.write(src.read())

    # Ensure the binary is executable on POSIX systems
    if platform.system().lower() != "windows":
        current = os.stat(dest).st_mode
        os.chmod(dest, current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    _log("Deno installed to {}".format(dest))
    _set_installed_version(DENO_VERSION)
    return dest


def get_ydl_opts(auto_download=True):
    """
    Return a yt-dlp options dict that configures Deno as the JS runtime.

    Searches for Deno in this order:
      1. Addon-data directory (``special://profile/addon_data/…/deno/``)
      2. System PATH
      3. Downloads from GitHub Releases (when *auto_download* is True)

    Returns an empty dict on any failure so the caller is unaffected.

    Parameters
    ----------
    auto_download : bool
        When True (the default), download Deno automatically if it is not
        already present.  When False, only use a pre-existing installation.
    """
    try:
        deno_path = _find_in_addon_data()

        if deno_path is not None and auto_download:
            installed_version = _get_installed_version()
            if installed_version != DENO_VERSION:
                _log(
                    "Deno version mismatch (installed={}, expected={});"
                    " updating…".format(installed_version, DENO_VERSION)
                )
                deno_dir = _addon_data_dir()
                deno_path = _download_deno(deno_dir, show_progress=True)

        if deno_path is None:
            deno_path = _find_in_path()
            if deno_path is not None:
                _log("Using system Deno at {}".format(deno_path))

        if deno_path is None:
            if not auto_download:
                _warn(
                    "Deno not found and auto-download is disabled; "
                    "YouTube extraction may fail"
                )
                return {}
            deno_dir = _addon_data_dir()
            deno_path = _download_deno(deno_dir, show_progress=True)

        return {
            "js_runtimes": {"deno": {"path": deno_path}},
            "remote_components": {"ejs:github"},
        }

    except Exception as exc:
        _warn("Could not configure Deno: {}".format(exc))
        return {}
