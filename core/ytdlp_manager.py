# -*- coding: utf-8 -*-
"""
ytdlp_manager.py — Download and manage yt-dlp versions in addon_data.

This module allows the addon to keep a managed yt-dlp installation under
``special://profile/addon_data/plugin.video.sendtokodi/ytdlp`` and switch
between versions based on addon settings.
"""

import io
import json
import logging
import os
import time
import shutil
import sys
import tarfile
import urllib.error
import urllib.request
from core.update_policy import (
    UPDATE_CHECK_INTERVAL_SECONDS,
    UPDATE_CHECK_NOT_MODIFIED_INTERVAL_SECONDS,
    UPDATE_BACKOFF_STEPS_SECONDS,
    UPDATE_MAX_COOLDOWN_SECONDS,
)


YTDLP_LATEST_SENTINEL = "latest"

_LATEST_RELEASE_API = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
_RELEASES_API = "https://api.github.com/repos/yt-dlp/yt-dlp/releases?per_page=100&page={page}"
_TARBALL_URL = "https://github.com/yt-dlp/yt-dlp/archive/refs/tags/{version}.tar.gz"


def _log(msg, level=None):
    """Log via xbmc if available, otherwise fall back to stdlib logging."""
    try:
        import xbmc
        if level is None:
            level = xbmc.LOGINFO
        xbmc.log("plugin.video.sendtokodi ytdlp_manager: {}".format(msg), level)
    except ImportError:
        logging.getLogger(__name__).info(msg)


def _warn(msg):
    try:
        import xbmc
        _log(msg, xbmc.LOGWARNING)
    except ImportError:
        logging.getLogger(__name__).warning(msg)


def _addon_data_dir():
    """Return the addon_data path used for managed yt-dlp installations."""
    try:
        import xbmcvfs
        return xbmcvfs.translatePath(
            "special://profile/addon_data/plugin.video.sendtokodi/ytdlp/"
        )
    except ImportError:
        pass

    return os.path.join(
        os.path.expanduser("~"),
        ".kodi",
        "userdata",
        "addon_data",
        "plugin.video.sendtokodi",
        "ytdlp",
    )


def _versions_dir():
    return os.path.join(_addon_data_dir(), "versions")


def _installed_version_file():
    return os.path.join(_addon_data_dir(), "ytdlp_version.txt")


def _update_state_file():
    return os.path.join(_addon_data_dir(), "ytdlp_update_state.json")


def _default_update_state():
    return {
        "last_checked_at": 0,
        "next_check_at": 0,
        "latest_known_version": None,
        "etag": None,
        "cooldown_until": 0,
        "consecutive_failures": 0,
        "last_error": None,
    }


def _load_update_state():
    path = _update_state_file()
    try:
        with open(path, "r") as f:
            raw = json.load(f)
    except Exception:
        return _default_update_state()

    state = _default_update_state()
    if isinstance(raw, dict):
        state.update(raw)
    return state


def _save_update_state(state):
    os.makedirs(_addon_data_dir(), exist_ok=True)
    path = _update_state_file()
    tmp_path = path + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(state, f)
    os.replace(tmp_path, path)


def _parse_retry_after(headers):
    if headers is None:
        return None

    value = headers.get("Retry-After")
    if not value:
        return None

    try:
        seconds = int(value)
    except Exception:
        return None

    if seconds <= 0:
        return None
    return min(seconds, UPDATE_MAX_COOLDOWN_SECONDS)


def _compute_failure_cooldown(consecutive_failures):
    index = max(0, min(consecutive_failures - 1, len(UPDATE_BACKOFF_STEPS_SECONDS) - 1))
    return UPDATE_BACKOFF_STEPS_SECONDS[index]


def _apply_success_state(state, latest_version, etag, check_interval_seconds):
    now = int(time.time())
    state["last_checked_at"] = now
    state["next_check_at"] = now + check_interval_seconds
    state["cooldown_until"] = 0
    state["consecutive_failures"] = 0
    state["last_error"] = None
    state["latest_known_version"] = latest_version
    if etag:
        state["etag"] = etag


def _apply_failure_state(state, error_message, retry_after=None):
    now = int(time.time())
    failures = int(state.get("consecutive_failures") or 0) + 1
    cooldown = retry_after or _compute_failure_cooldown(failures)

    state["last_checked_at"] = now
    state["next_check_at"] = now + cooldown
    state["cooldown_until"] = now + cooldown
    state["consecutive_failures"] = failures
    state["last_error"] = error_message


def _normalize_requested_version(version):
    requested = (version or "").strip()
    if not requested:
        return YTDLP_LATEST_SENTINEL
    if requested.lower() == YTDLP_LATEST_SENTINEL:
        return YTDLP_LATEST_SENTINEL
    return requested


def _read_installed_version():
    try:
        with open(_installed_version_file(), "r") as f:
            value = f.read().strip()
            return value or None
    except Exception:
        return None


def _write_installed_version(version):
    os.makedirs(_addon_data_dir(), exist_ok=True)
    try:
        with open(_installed_version_file(), "w") as f:
            f.write(version)
    except Exception as exc:
        _warn("Could not write yt-dlp version file: {}".format(exc))


def _runtime_path_for_version(version):
    # Runtime path must be the parent directory that contains the yt_dlp package.
    return os.path.join(_versions_dir(), version)


def _yt_dlp_package_path(runtime_path):
    return os.path.join(runtime_path, "yt_dlp")


def _find_runtime_for_version(version):
    runtime_path = _runtime_path_for_version(version)
    package_path = _yt_dlp_package_path(runtime_path)
    if os.path.isdir(package_path):
        return runtime_path
    return None


def _find_installed_runtime():
    version = _read_installed_version()
    if version is None:
        return None, None

    runtime_path = _find_runtime_for_version(version)
    if runtime_path is not None:
        return version, runtime_path
    return None, None


def list_installed_versions():
    versions_dir = _versions_dir()
    if not os.path.isdir(versions_dir):
        return []

    versions = []
    for name in os.listdir(versions_dir):
        runtime_path = os.path.join(versions_dir, name)
        if not os.path.isdir(runtime_path):
            continue
        if os.path.isdir(_yt_dlp_package_path(runtime_path)):
            versions.append(name)
    return sorted(versions, reverse=True)


def _resolve_latest_version(force_refresh=False):
    _log("Resolving latest yt-dlp release version")

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
    """Return available yt-dlp release tags (newest first)."""
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
        _warn("Could not list yt-dlp releases: {}".format(exc))

    return versions


def _safe_join(base_dir, relative_path):
    joined = os.path.normpath(os.path.join(base_dir, relative_path))
    base_norm = os.path.normpath(base_dir)
    if joined != base_norm and not joined.startswith(base_norm + os.sep):
        raise RuntimeError("Refusing to extract outside target directory")
    return joined


def _extract_yt_dlp_from_tarball(tar_bytes, destination_runtime_path):
    tmp_path = destination_runtime_path + ".tmp"
    if os.path.isdir(tmp_path):
        shutil.rmtree(tmp_path)
    os.makedirs(tmp_path, exist_ok=True)

    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:gz") as tf:
        for member in tf.getmembers():
            name = member.name.replace("\\", "/")
            if "/" not in name:
                continue

            rel_name = name.split("/", 1)[1]
            if rel_name != "yt_dlp" and not rel_name.startswith("yt_dlp/"):
                continue

            target_path = _safe_join(tmp_path, rel_name)
            if member.isdir():
                os.makedirs(target_path, exist_ok=True)
                continue

            src = tf.extractfile(member)
            if src is None:
                continue

            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            with open(target_path, "wb") as dst:
                dst.write(src.read())

    expected_init = os.path.join(tmp_path, "yt_dlp", "__init__.py")
    if not os.path.isfile(expected_init):
        raise RuntimeError("Downloaded archive does not contain a valid yt_dlp package")

    if os.path.isdir(destination_runtime_path):
        shutil.rmtree(destination_runtime_path)
    os.makedirs(os.path.dirname(destination_runtime_path), exist_ok=True)
    os.rename(tmp_path, destination_runtime_path)


def _download_and_install(version):
    url = _TARBALL_URL.format(version=version)
    _log("Downloading yt-dlp {} from {}".format(version, url))

    progress = None
    try:
        import xbmcgui

        progress = xbmcgui.DialogProgressBG()
        progress.create("SendToKodi", "Downloading yt-dlp {}...".format(version))
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
                        "Downloading yt-dlp {} ({}/{} MB)...".format(
                            version,
                            downloaded // (1024 * 1024),
                            total // (1024 * 1024),
                        ),
                    )
            data = b"".join(chunks)
    finally:
        if progress is not None:
            progress.close()

    runtime_path = _runtime_path_for_version(version)
    _extract_yt_dlp_from_tarball(data, runtime_path)
    _write_installed_version(version)
    _log("yt-dlp {} installed at {}".format(version, runtime_path))
    return runtime_path


def get_runtime_status(requested_version=YTDLP_LATEST_SENTINEL, force_refresh_latest=False):
    """Return managed yt-dlp status information for UI/diagnostics."""
    requested = _normalize_requested_version(requested_version)
    installed_version, installed_runtime_path = _find_installed_runtime()

    latest_version = None
    latest_error = None
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
        "installed_runtime_path": installed_runtime_path,
        "installed_versions": list_installed_versions(),
        "latest_version": latest_version,
        "is_latest_installed": is_latest_installed,
        "latest_error": latest_error,
    }


def ensure_ytdlp_ready(
    allow_install=True,
    requested_version=YTDLP_LATEST_SENTINEL,
    force_refresh_latest=False,
):
    """
    Ensure a managed yt-dlp runtime is available.

    Returns a status dict with:
      - ready (bool)
      - reason (None | "missing" | "version_mismatch" | "error")
      - version (resolved target version when known)
      - runtime_path (path to use when ready)
      - installed_version (currently installed managed version, if any)
      - installed_runtime_path (path of installed managed runtime, if any)
      - error (error message when reason == "error")
    """
    def _ready(version, runtime_path, error=None):
        return {
            "ready": True,
            "reason": None,
            "version": version,
            "runtime_path": runtime_path,
            "installed_version": version,
            "installed_runtime_path": runtime_path,
            "error": error,
        }

    def _not_ready(reason, version, installed_version, installed_runtime_path, error=None):
        return {
            "ready": False,
            "reason": reason,
            "version": version,
            "runtime_path": None,
            "installed_version": installed_version,
            "installed_runtime_path": installed_runtime_path,
            "error": error,
        }

    try:
        requested = _normalize_requested_version(requested_version)
        installed_version, installed_runtime_path = _find_installed_runtime()

        target_version = requested
        if requested == YTDLP_LATEST_SENTINEL:
            if allow_install:
                if force_refresh_latest:
                    target_version = _resolve_latest_version(force_refresh=True)
                else:
                    target_version = _resolve_latest_version()
            elif installed_version is not None:
                target_version = None

        if installed_version is not None and target_version is not None:
            if installed_version == target_version:
                return _ready(installed_version, installed_runtime_path)

            existing_runtime = _find_runtime_for_version(target_version)
            if existing_runtime is not None:
                _write_installed_version(target_version)
                return _ready(target_version, existing_runtime)

            if allow_install:
                runtime_path = _download_and_install(target_version)
                return _ready(target_version, runtime_path)

            return _not_ready(
                "version_mismatch",
                target_version,
                installed_version,
                installed_runtime_path,
            )

        if installed_version is not None:
            return _ready(installed_version, installed_runtime_path)

        if not allow_install:
            return _not_ready("missing", target_version, None, None)

        if target_version is None:
            if force_refresh_latest:
                target_version = _resolve_latest_version(force_refresh=True)
            else:
                target_version = _resolve_latest_version()
        runtime_path = _download_and_install(target_version)
        return _ready(target_version, runtime_path)
    except Exception as exc:
        _warn("Could not ensure yt-dlp runtime: {}".format(exc))

        fallback_version, fallback_runtime_path = _find_installed_runtime()
        if fallback_version is not None and fallback_runtime_path is not None:
            _warn(
                "Falling back to installed yt-dlp version {}".format(
                    fallback_version
                )
            )
            return _ready(fallback_version, fallback_runtime_path, error=str(exc))

        return _not_ready("error", None, None, None, error=str(exc))


def activate_runtime(runtime_path):
    """Prepend the managed runtime path to sys.path so yt_dlp imports from it."""
    if runtime_path is None:
        return
    if runtime_path in sys.path:
        return
    sys.path.insert(0, runtime_path)