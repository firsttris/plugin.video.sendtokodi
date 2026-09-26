# -*- coding: utf-8 -*-
"""
ytdlp_manager.py — Download and manage yt-dlp versions in addon_data.

This module allows the addon to keep a managed yt-dlp installation under
``special://profile/addon_data/plugin.video.sendtokodi/ytdlp`` and switch
between versions based on addon settings.
"""

import io
import logging
import os
import time
import shutil
import sys
import tarfile
from core import managed_runtime
from core.runtime_update_state import (
    default_update_state,
    load_update_state,
    save_update_state,
)
from core.update_policy import INSTALL_PROMPT_SNOOZE_SECONDS


YTDLP_LATEST_SENTINEL = managed_runtime.LATEST_SENTINEL
MAX_INSTALLED_VERSIONS = managed_runtime.MAX_INSTALLED_VERSIONS
_RUNTIME_LABEL = "yt-dlp"

_LATEST_RELEASE_API = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
_RELEASES_API = "https://api.github.com/repos/yt-dlp/yt-dlp/releases?per_page=100&page={page}"
_TARBALL_URL = "https://github.com/yt-dlp/yt-dlp/archive/refs/tags/{version}.tar.gz"


def _log(msg, level=None):
    managed_runtime.log("ytdlp_manager", msg, level)


def _warn(msg):
    try:
        import xbmc
        _log(msg, xbmc.LOGWARNING)
    except ImportError:
        logging.getLogger(__name__).warning(msg)


def _addon_data_dir():
    """Return the addon_data path used for managed yt-dlp installations."""
    return managed_runtime.addon_data_dir("ytdlp")


def _versions_dir():
    return os.path.join(_addon_data_dir(), "versions")


def _installed_version_file():
    return os.path.join(_addon_data_dir(), "ytdlp_version.txt")


def _update_state_file():
    return os.path.join(_addon_data_dir(), "ytdlp_update_state.json")


def _default_update_state():
    return default_update_state()


def _load_update_state():
    return load_update_state(_update_state_file())


def _save_update_state(state):
    save_update_state(_addon_data_dir(), _update_state_file(), state)


def _normalize_requested_version(version):
    return managed_runtime.normalize_requested_version(version)


def _read_installed_version():
    return managed_runtime.read_version_file(_installed_version_file())


def _write_installed_version(version):
    managed_runtime.write_version_file(_installed_version_file(), version, _warn, _RUNTIME_LABEL)


def _clear_installed_version():
    managed_runtime.clear_version_file(_installed_version_file())


def _runtime_path_for_version(version):
    # Runtime path must be the parent directory that contains the yt_dlp package.
    return os.path.join(_versions_dir(), version)


def _yt_dlp_package_path(runtime_path):
    return os.path.join(runtime_path, "yt_dlp")


def _prune_old_versions(keep_version):
    managed_runtime.prune_old_versions(
        keep_version,
        list_installed_versions(),
        _runtime_path_for_version,
        _log,
        _warn,
        _RUNTIME_LABEL,
    )


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
    return managed_runtime.list_installed_versions(
        _versions_dir(),
        lambda name: os.path.isdir(_yt_dlp_package_path(_runtime_path_for_version(name))),
    )


def activate_installed_version(version):
    target = (version or "").strip()
    if not target:
        return None

    runtime_path = _find_runtime_for_version(target)
    if runtime_path is None:
        return None

    _write_installed_version(target)
    return runtime_path


def delete_installed_version(version):
    return managed_runtime.delete_installed_version(
        version,
        _runtime_path_for_version,
        _read_installed_version,
        _write_installed_version,
        _clear_installed_version,
        list_installed_versions,
        _warn,
        _RUNTIME_LABEL,
    )


def _resolve_latest_version(force_refresh=False):
    _log("Resolving latest yt-dlp release version")
    return managed_runtime.resolve_latest_version(
        _LATEST_RELEASE_API,
        _load_update_state,
        _save_update_state,
        force_refresh=force_refresh,
    )


def list_available_versions(limit=20):
    """Return available yt-dlp release tags (newest first)."""
    return managed_runtime.list_available_versions(_RELEASES_API, limit, _warn, _RUNTIME_LABEL)


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

    data = managed_runtime.download_with_progress(url, _RUNTIME_LABEL, version)

    runtime_path = _runtime_path_for_version(version)
    _extract_yt_dlp_from_tarball(data, runtime_path)
    _write_installed_version(version)
    _log("yt-dlp {} installed at {}".format(version, runtime_path))
    _prune_old_versions(version)
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


def is_install_prompt_snoozed(now=None):
    now = int(time.time()) if now is None else int(now)
    declined_at = int(_load_update_state().get("install_prompt_declined_at") or 0)
    return declined_at > 0 and now - declined_at < INSTALL_PROMPT_SNOOZE_SECONDS


def snooze_install_prompt(now=None):
    state = _load_update_state()
    state["install_prompt_declined_at"] = int(time.time()) if now is None else int(now)
    try:
        _save_update_state(state)
    except Exception as exc:
        _warn("Could not save yt-dlp prompt state: {}".format(exc))


def activate_runtime(runtime_path):
    """Prepend the managed runtime path to sys.path so yt_dlp imports from it."""
    if runtime_path is None:
        return
    if runtime_path in sys.path:
        return
    sys.path.insert(0, runtime_path)