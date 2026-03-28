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
import shutil
import sys
import tarfile
import urllib.request


YTDLP_LATEST_SENTINEL = "latest"

_LATEST_RELEASE_API = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
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


def _find_installed_runtime():
    version = _read_installed_version()
    if version is None:
        return None, None

    runtime_path = _runtime_path_for_version(version)
    package_path = _yt_dlp_package_path(runtime_path)
    if os.path.isdir(package_path):
        return version, runtime_path
    return None, None


def _resolve_latest_version():
    _log("Resolving latest yt-dlp release version")
    with urllib.request.urlopen(_LATEST_RELEASE_API, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))

    tag = (payload.get("tag_name") or "").strip()
    if not tag:
        raise RuntimeError("GitHub latest release response has no tag_name")
    return tag


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

    with urllib.request.urlopen(url, timeout=60) as response:
        data = response.read()

    runtime_path = _runtime_path_for_version(version)
    _extract_yt_dlp_from_tarball(data, runtime_path)
    _write_installed_version(version)
    _log("yt-dlp {} installed at {}".format(version, runtime_path))
    return runtime_path


def get_runtime_status(requested_version=YTDLP_LATEST_SENTINEL):
    """Return managed yt-dlp status information for UI/diagnostics."""
    requested = _normalize_requested_version(requested_version)
    installed_version, installed_runtime_path = _find_installed_runtime()

    latest_version = None
    latest_error = None
    try:
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
        "latest_version": latest_version,
        "is_latest_installed": is_latest_installed,
        "latest_error": latest_error,
    }


def ensure_ytdlp_ready(auto_download=True, requested_version=YTDLP_LATEST_SENTINEL):
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
    try:
        requested = _normalize_requested_version(requested_version)
        installed_version, installed_runtime_path = _find_installed_runtime()

        target_version = requested
        if requested == YTDLP_LATEST_SENTINEL:
            if auto_download or installed_version is None:
                target_version = _resolve_latest_version()
            else:
                target_version = None

        if installed_version is not None and target_version is not None:
            if installed_version == target_version:
                return {
                    "ready": True,
                    "reason": None,
                    "version": installed_version,
                    "runtime_path": installed_runtime_path,
                    "installed_version": installed_version,
                    "installed_runtime_path": installed_runtime_path,
                    "error": None,
                }

            if auto_download:
                runtime_path = _download_and_install(target_version)
                return {
                    "ready": True,
                    "reason": None,
                    "version": target_version,
                    "runtime_path": runtime_path,
                    "installed_version": target_version,
                    "installed_runtime_path": runtime_path,
                    "error": None,
                }

            return {
                "ready": False,
                "reason": "version_mismatch",
                "version": target_version,
                "runtime_path": None,
                "installed_version": installed_version,
                "installed_runtime_path": installed_runtime_path,
                "error": None,
            }

        if installed_version is not None:
            return {
                "ready": True,
                "reason": None,
                "version": installed_version,
                "runtime_path": installed_runtime_path,
                "installed_version": installed_version,
                "installed_runtime_path": installed_runtime_path,
                "error": None,
            }

        if not auto_download:
            return {
                "ready": False,
                "reason": "missing",
                "version": target_version,
                "runtime_path": None,
                "installed_version": None,
                "installed_runtime_path": None,
                "error": None,
            }

        if target_version is None:
            target_version = _resolve_latest_version()
        runtime_path = _download_and_install(target_version)
        return {
            "ready": True,
            "reason": None,
            "version": target_version,
            "runtime_path": runtime_path,
            "installed_version": target_version,
            "installed_runtime_path": runtime_path,
            "error": None,
        }
    except Exception as exc:
        _warn("Could not ensure yt-dlp runtime: {}".format(exc))
        return {
            "ready": False,
            "reason": "error",
            "version": None,
            "runtime_path": None,
            "installed_version": None,
            "installed_runtime_path": None,
            "error": str(exc),
        }


def activate_runtime(runtime_path):
    """Prepend the managed runtime path to sys.path so yt_dlp imports from it."""
    if runtime_path is None:
        return
    if runtime_path in sys.path:
        return
    sys.path.insert(0, runtime_path)