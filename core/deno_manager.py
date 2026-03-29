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
import json
import time
import urllib.request
import urllib.error
import zipfile
import io
import logging
from core.runtime_update_state import (
    apply_failure_state,
    apply_success_state,
    compute_failure_cooldown,
    default_update_state,
    load_update_state,
    parse_retry_after,
    save_update_state,
)
from core.update_policy import (
    UPDATE_CHECK_INTERVAL_SECONDS,
    UPDATE_CHECK_NOT_MODIFIED_INTERVAL_SECONDS,
    UPDATE_BACKOFF_STEPS_SECONDS,
    UPDATE_MAX_COOLDOWN_SECONDS,
)

DENO_LATEST_SENTINEL = "latest"

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


def _update_state_file():
    return os.path.join(_addon_data_dir(), "deno_update_state.json")


def _default_update_state():
    return default_update_state()


def _load_update_state():
    return load_update_state(_update_state_file())


def _save_update_state(state):
    save_update_state(_addon_data_dir(), _update_state_file(), state)


def _parse_retry_after(headers):
    return parse_retry_after(headers, UPDATE_MAX_COOLDOWN_SECONDS)


def _compute_failure_cooldown(consecutive_failures):
    return compute_failure_cooldown(consecutive_failures, UPDATE_BACKOFF_STEPS_SECONDS)


def _apply_success_state(state, latest_version, etag, check_interval_seconds):
    apply_success_state(state, latest_version, etag, check_interval_seconds)


def _apply_failure_state(state, error_message, retry_after=None):
    apply_failure_state(
        state,
        error_message,
        UPDATE_BACKOFF_STEPS_SECONDS,
        retry_after=retry_after,
    )


def _versions_dir():
    return os.path.join(_addon_data_dir(), "versions")


def _runtime_dir_for_version(version):
    return os.path.join(_versions_dir(), version)


def _binary_path_for_version(version):
    return os.path.join(_runtime_dir_for_version(version), _deno_binary_name())


def _find_runtime_for_version(version):
    runtime_path = _binary_path_for_version(version)
    if os.path.isfile(runtime_path) and os.access(runtime_path, os.X_OK):
        return runtime_path
    return None


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
        os.makedirs(_addon_data_dir(), exist_ok=True)
        with open(_version_file(), "w") as f:
            f.write(version)
    except Exception as e:
        _warn("Could not write Deno version file: {}".format(e))


def _clear_installed_version():
    try:
        os.remove(_version_file())
    except Exception:
        pass


def _normalize_requested_version(version):
    if version is None:
        return DENO_LATEST_SENTINEL

    requested = (version or "").strip()
    if not requested:
        return DENO_LATEST_SENTINEL
    if requested.lower() == DENO_LATEST_SENTINEL:
        return DENO_LATEST_SENTINEL
    return requested


def _resolve_latest_version(force_refresh=False):
    state = _load_update_state()
    now = int(time.time())
    cached_version = state.get("latest_known_version")

    if not force_refresh:
        next_check_at = int(state.get("next_check_at") or 0)
        cooldown_until = int(state.get("cooldown_until") or 0)
        if cached_version and now < max(next_check_at, cooldown_until):
            return cached_version

    request = urllib.request.Request(_LATEST_RELEASE_API)
    etag = state.get("etag")
    if etag:
        request.add_header("If-None-Match", etag)

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))

        tag = (payload.get("tag_name") or "").strip()
        if not tag:
            raise RuntimeError("GitHub latest release response has no tag_name")

        _apply_success_state(
            state,
            tag,
            response.headers.get("ETag"),
            UPDATE_CHECK_INTERVAL_SECONDS,
        )
        _save_update_state(state)
        return tag
    except urllib.error.HTTPError as exc:
        if exc.code == 304 and cached_version:
            _apply_success_state(
                state,
                cached_version,
                exc.headers.get("ETag") or etag,
                UPDATE_CHECK_NOT_MODIFIED_INTERVAL_SECONDS,
            )
            _save_update_state(state)
            return cached_version

        if exc.code == 429:
            retry_after = _parse_retry_after(exc.headers)
            error_message = "GitHub API rate limit hit (HTTP 429)"
            _apply_failure_state(state, error_message, retry_after=retry_after)
            _save_update_state(state)
            if cached_version:
                return cached_version
            raise RuntimeError(error_message)

        error_message = "GitHub latest release lookup failed: HTTP {}".format(exc.code)
        _apply_failure_state(state, error_message)
        _save_update_state(state)
        if cached_version:
            return cached_version
        raise RuntimeError(error_message)
    except Exception as exc:
        _apply_failure_state(state, str(exc))
        _save_update_state(state)
        if cached_version:
            return cached_version
        raise


def list_available_versions(limit=20):
    if limit <= 0:
        return []

    versions = []
    page = 1

    try:
        while len(versions) < limit:
            url = _RELEASES_API.format(page=page)
            with urllib.request.urlopen(url, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))

            if not isinstance(payload, list) or not payload:
                break

            for release in payload:
                if release.get("prerelease") or release.get("draft"):
                    continue
                tag = (release.get("tag_name") or "").strip()
                if not tag or tag in versions:
                    continue
                versions.append(tag)
                if len(versions) >= limit:
                    break

            if len(payload) < 100:
                break
            page += 1
    except Exception as exc:
        _warn("Could not list Deno releases: {}".format(exc))

    return versions


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
    versions_dir = _versions_dir()
    if not os.path.isdir(versions_dir):
        return []

    versions = []
    for name in os.listdir(versions_dir):
        runtime_dir = os.path.join(versions_dir, name)
        if not os.path.isdir(runtime_dir):
            continue
        if _find_runtime_for_version(name) is not None:
            versions.append(name)
    return sorted(versions, reverse=True)


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
    target = (version or "").strip()
    if not target:
        return False

    runtime_dir = _runtime_dir_for_version(target)
    if not os.path.isdir(runtime_dir):
        return False

    try:
        shutil.rmtree(runtime_dir)
    except Exception as exc:
        _warn("Could not delete Deno version {}: {}".format(target, exc))
        return False

    if _get_installed_version() == target:
        remaining_versions = list_installed_versions()
        if remaining_versions:
            _set_installed_version(remaining_versions[0])
        else:
            _clear_installed_version()

    return True


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

    # --- optional Kodi background progress (top-right, non-blocking) ---
    progress = None
    if show_progress:
        try:
            import xbmcgui
            progress = xbmcgui.DialogProgressBG()
            progress.create(
                "SendToKodi",
                "Downloading Deno JavaScript runtime {}…".format(target_version),
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
                            target_version,
                            downloaded // (1024 * 1024),
                            total // (1024 * 1024),
                        ),
                    )
            data = b"".join(chunks)
    finally:
        if progress is not None:
            progress.close()

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
            deno_path = _download_deno(show_progress=True, version=target_version)

        return {
            "js_runtimes": {"deno": {"path": deno_path}},
            "remote_components": {"ejs:github"},
        }

    except Exception as exc:
        _warn("Could not configure Deno: {}".format(exc))
        return {}
