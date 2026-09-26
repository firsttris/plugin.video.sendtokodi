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

import logging
import os
import platform
import shutil
import stat
import zipfile
import io
from core import managed_runtime
from core.runtime_update_state import (
    default_update_state,
    load_update_state,
    save_update_state,
)

DENO_LATEST_SENTINEL = managed_runtime.LATEST_SENTINEL
MAX_INSTALLED_VERSIONS = managed_runtime.MAX_INSTALLED_VERSIONS
_RUNTIME_LABEL = "Deno"

_LATEST_RELEASE_API = "https://api.github.com/repos/denoland/deno/releases/latest"
_RELEASES_API = "https://api.github.com/repos/denoland/deno/releases?per_page=100&page={page}"

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
    managed_runtime.log("deno_manager", msg, level)


def _warn(msg):
    try:
        import xbmc
        _log(msg, xbmc.LOGWARNING)
    except ImportError:
        logging.getLogger(__name__).warning(msg)


def _addon_data_dir():
    """Return the addon_data directory path, using xbmc.translatePath when available."""
    return managed_runtime.addon_data_dir("deno")


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


def _update_state_file():
    return os.path.join(_addon_data_dir(), "deno_update_state.json")


def _default_update_state():
    return default_update_state()


def _load_update_state():
    return load_update_state(_update_state_file())


def _save_update_state(state):
    save_update_state(_addon_data_dir(), _update_state_file(), state)


def _versions_dir():
    return os.path.join(_addon_data_dir(), "versions")


def _runtime_dir_for_version(version):
    return os.path.join(_versions_dir(), version)


def _binary_path_for_version(version):
    return os.path.join(_runtime_dir_for_version(version), _deno_binary_name())


def _prune_old_versions(keep_version):
    managed_runtime.prune_old_versions(
        keep_version,
        list_installed_versions(),
        _runtime_dir_for_version,
        _log,
        _warn,
        _RUNTIME_LABEL,
    )


def _find_runtime_for_version(version):
    runtime_path = _binary_path_for_version(version)
    if os.path.isfile(runtime_path) and os.access(runtime_path, os.X_OK):
        return runtime_path
    return None


def _get_installed_version():
    """Return the installed Deno version string, or None if not recorded."""
    return managed_runtime.read_version_file(_version_file())


def _set_installed_version(version):
    """Write the installed Deno version to the version tracking file."""
    managed_runtime.write_version_file(_version_file(), version, _warn, _RUNTIME_LABEL)


def _clear_installed_version():
    managed_runtime.clear_version_file(_version_file())


def _normalize_requested_version(version):
    return managed_runtime.normalize_requested_version(version)


def _resolve_latest_version(force_refresh=False):
    return managed_runtime.resolve_latest_version(
        _LATEST_RELEASE_API,
        _load_update_state,
        _save_update_state,
        force_refresh=force_refresh,
    )


def list_available_versions(limit=20):
    return managed_runtime.list_available_versions(
        _RELEASES_API,
        limit,
        _warn,
        _RUNTIME_LABEL,
        skip_prereleases=True,
    )


def _find_in_addon_data():
    """Return legacy deno binary path in addon_data root, else None."""
    deno_dir = _addon_data_dir()
    candidate = os.path.join(deno_dir, _deno_binary_name())
    if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
        return candidate
    return None


def _find_installed_runtime():
    installed_version = _get_installed_version()
    if installed_version:
        versioned_binary = _find_runtime_for_version(installed_version)
        if versioned_binary is not None:
            return installed_version, versioned_binary

    # Backward compatibility: old flat layout in addon_data root.
    legacy_binary = _find_in_addon_data()
    if legacy_binary:
        return installed_version or "unknown", legacy_binary

    return None, None


def list_installed_versions():
    return managed_runtime.list_installed_versions(
        _versions_dir(),
        lambda name: _find_runtime_for_version(name) is not None,
    )


def activate_installed_version(version):
    target = (version or "").strip()
    if not target:
        return None

    runtime_path = _find_runtime_for_version(target)
    if runtime_path is None:
        return None

    _set_installed_version(target)
    return runtime_path


def delete_installed_version(version):
    return managed_runtime.delete_installed_version(
        version,
        _runtime_dir_for_version,
        _get_installed_version,
        _set_installed_version,
        _clear_installed_version,
        list_installed_versions,
        _warn,
        _RUNTIME_LABEL,
    )


def _find_in_path():
    """Return the path to a deno binary on the system PATH, or None."""
    return shutil.which("deno")


def _download_deno(show_progress=True, version=None):
    """
    Download and extract the Deno binary into *deno_dir*.

    Uses a Kodi progress dialog when running inside Kodi and *show_progress*
    is True.  Raises on failure.
    """
    target_version = _normalize_requested_version(version)
    if target_version == DENO_LATEST_SENTINEL:
        target_version = _resolve_latest_version()

    system, machine = _detect_platform()
    filename = _PLATFORM_MAP[(system, machine)]
    url = _RELEASE_URL.format(version=target_version, filename=filename)

    _log("Downloading Deno {} from {}".format(target_version, url))

    data = managed_runtime.download_with_progress(
        url,
        _RUNTIME_LABEL,
        target_version,
        show_progress=show_progress,
    )

    # Extract the zip — it contains a single "deno" (or "deno.exe") binary
    runtime_dir = _runtime_dir_for_version(target_version)
    tmp_runtime_dir = runtime_dir + ".tmp"
    if os.path.isdir(tmp_runtime_dir):
        shutil.rmtree(tmp_runtime_dir)
    os.makedirs(tmp_runtime_dir, exist_ok=True)

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
        dest = os.path.join(tmp_runtime_dir, binary_name)
        with zf.open(member) as src, open(dest, "wb") as dst:
            dst.write(src.read())

    # Ensure the binary is executable on POSIX systems
    if platform.system().lower() != "windows":
        current = os.stat(dest).st_mode
        os.chmod(dest, current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    if os.path.isdir(runtime_dir):
        shutil.rmtree(runtime_dir)
    os.makedirs(os.path.dirname(runtime_dir), exist_ok=True)
    os.rename(tmp_runtime_dir, runtime_dir)

    _log("Deno installed to {}".format(dest))
    _set_installed_version(target_version)
    _prune_old_versions(target_version)
    return os.path.join(runtime_dir, binary_name)


def get_runtime_status(
    requested_version=DENO_LATEST_SENTINEL,
    include_latest=False,
    force_refresh_latest=False,
):
    requested = _normalize_requested_version(requested_version)
    installed_version, installed_path = _find_installed_runtime()

    latest_version = None
    latest_error = None
    if include_latest:
        try:
            if force_refresh_latest:
                latest_version = _resolve_latest_version(force_refresh=True)
            else:
                latest_version = _resolve_latest_version()
        except Exception as exc:
            latest_error = str(exc)

    is_latest_installed = None
    if installed_version is not None and latest_version is not None:
        is_latest_installed = installed_version == latest_version

    return {
        "requested_version": requested,
        "installed_version": installed_version,
        "installed_path": installed_path,
        "installed_versions": list_installed_versions(),
        "latest_version": latest_version,
        "latest_error": latest_error,
        "is_latest_installed": is_latest_installed,
    }


def get_ydl_opts(auto_download=True, requested_version=None, force_refresh_latest=False):
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
        requested = _normalize_requested_version(requested_version)
        installed_version, deno_path = _find_installed_runtime()

        target_version = requested
        if requested == DENO_LATEST_SENTINEL:
            if auto_download:
                try:
                    if force_refresh_latest:
                        target_version = _resolve_latest_version(force_refresh=True)
                    else:
                        target_version = _resolve_latest_version()
                except Exception as exc:
                    _warn("Could not resolve latest Deno version: {}".format(exc))
                    # In auto-update mode we should not silently downgrade/pin to
                    # a hardcoded version when latest resolution fails.
                    if installed_version is not None:
                        target_version = installed_version
                    else:
                        return {}
            elif installed_version is not None:
                target_version = installed_version

        if deno_path is not None and auto_download:
            if installed_version != target_version:
                existing_runtime = _find_runtime_for_version(target_version)
                if existing_runtime is not None:
                    _set_installed_version(target_version)
                    deno_path = existing_runtime
                else:
                    _log(
                        "Deno version mismatch (installed={}, expected={});"
                        " updating…".format(installed_version, target_version)
                    )
                    deno_path = _download_deno(show_progress=True, version=target_version)

        # An explicit version or forced update must install a managed Deno, not
        # silently fall back to a system binary.
        explicit_install = auto_download and (
            force_refresh_latest or requested != DENO_LATEST_SENTINEL
        )
        if deno_path is None and not explicit_install:
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
            deno_path = _download_deno(show_progress=True, version=target_version)

        return {
            "js_runtimes": {"deno": {"path": deno_path}},
            "remote_components": {"ejs:github"},
        }

    except Exception as exc:
        _warn("Could not configure Deno: {}".format(exc))
        return {}
