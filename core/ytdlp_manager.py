# -*- coding: utf-8 -*-
"""
ytdlp_manager.py — Download and manage yt-dlp versions in addon_data.

This module allows the addon to keep a managed yt-dlp installation under
``special://profile/addon_data/plugin.video.sendtokodi/ytdlp`` and switch
between versions based on addon settings.
"""

import importlib
import logging
import os
import time
import shutil
import sys
import tarfile
import urllib.error
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

YTDLP_SOURCE_STABLE = "stable"
YTDLP_SOURCE_NIGHTLY = "nightly"
YTDLP_SOURCE_SYSTEM = "system"
DEFAULT_YTDLP_SOURCE = YTDLP_SOURCE_STABLE
YTDLP_SOURCES = (YTDLP_SOURCE_STABLE, YTDLP_SOURCE_NIGHTLY, YTDLP_SOURCE_SYSTEM)

# Per-source release endpoints. "nightly" tracks yt-dlp/yt-dlp-nightly-builds
# (builds of master). Both channels publish a yt-dlp.tar.gz release asset whose
# layout matches the tag archive (<top>/yt_dlp/...), so one extractor serves both.
# The asset is built with "make all" and therefore ships
# yt_dlp/extractor/lazy_extractors.py; the plain tag archive does not, and
# without it every start imports all ~1800 extractor modules (several times
# slower). The nightly *repository* archive is only a README stub, so nightly
# has no fallback.
_SOURCE_REPOS = {
    YTDLP_SOURCE_STABLE: "yt-dlp/yt-dlp",
    YTDLP_SOURCE_NIGHTLY: "yt-dlp/yt-dlp-nightly-builds",
}
_SOURCE_TARBALL_URLS = {
    YTDLP_SOURCE_STABLE: "https://github.com/yt-dlp/yt-dlp/releases/download/{version}/yt-dlp.tar.gz",
    YTDLP_SOURCE_NIGHTLY: "https://github.com/yt-dlp/yt-dlp-nightly-builds/releases/download/{version}/yt-dlp.tar.gz",
}
# Used when a (very old) release has no yt-dlp.tar.gz asset.
_SOURCE_FALLBACK_TARBALL_URLS = {
    YTDLP_SOURCE_STABLE: "https://github.com/yt-dlp/yt-dlp/archive/refs/tags/{version}.tar.gz",
}


def normalize_source(source):
    """Return a known yt-dlp source, falling back to the default (stable)."""
    value = (source or "").strip().lower()
    if value in YTDLP_SOURCES:
        return value
    return DEFAULT_YTDLP_SOURCE


def is_managed_source(source):
    """True when the source is downloaded and installed by the manager.

    "system" is the opposite: the library is expected to already be importable
    (put there by the packaging), so nothing is downloaded.
    """
    return normalize_source(source) != YTDLP_SOURCE_SYSTEM


def resolve_system_ytdlp():
    """Return the version of an importable yt_dlp, or None when there is none.

    Where the package lives is a packaging concern: the addon only asks whether
    it can be imported. Nothing is added to sys.path here.
    """
    try:
        module = importlib.import_module("yt_dlp")
    except Exception:
        return None

    return getattr(getattr(module, "version", None), "__version__", None) or "unknown"


def _latest_release_api(source):
    return "https://api.github.com/repos/{}/releases/latest".format(_SOURCE_REPOS[source])


def _releases_api(source):
    return "https://api.github.com/repos/{}/releases?per_page=100&page={{page}}".format(
        _SOURCE_REPOS[source]
    )


def _tarball_url(source, version):
    return _SOURCE_TARBALL_URLS[source].format(version=version)


def _fallback_tarball_url(source, version):
    template = _SOURCE_FALLBACK_TARBALL_URLS.get(source)
    if template is None:
        return None
    return template.format(version=version)


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


def _update_state_file(source=DEFAULT_YTDLP_SOURCE):
    # One state file per source, so each channel keeps its own cached "latest".
    # The stable channel keeps the original file name used before sources existed.
    if source == YTDLP_SOURCE_STABLE:
        return os.path.join(_addon_data_dir(), "ytdlp_update_state.json")
    return os.path.join(_addon_data_dir(), "ytdlp_update_state_{}.json".format(source))


def _default_update_state():
    return default_update_state()


def _load_update_state(source=DEFAULT_YTDLP_SOURCE):
    return load_update_state(_update_state_file(source))


def _save_update_state(state, source=DEFAULT_YTDLP_SOURCE):
    save_update_state(_addon_data_dir(), _update_state_file(source), state)


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


def _resolve_latest_version(force_refresh=False, source=DEFAULT_YTDLP_SOURCE):
    _log("Resolving latest yt-dlp release version (source={})".format(source))
    return managed_runtime.resolve_latest_version(
        _latest_release_api(source),
        lambda: _load_update_state(source),
        lambda state: _save_update_state(state, source),
        force_refresh=force_refresh,
    )


def list_available_versions(limit=20, source=DEFAULT_YTDLP_SOURCE):
    """Return available yt-dlp release tags for a source (newest first)."""
    source = normalize_source(source)
    if not is_managed_source(source):
        # No release endpoint for a system install: nothing to download.
        return []
    return managed_runtime.list_available_versions(
        _releases_api(source), limit, _warn, _RUNTIME_LABEL
    )


def _safe_join(base_dir, relative_path):
    joined = os.path.normpath(os.path.join(base_dir, relative_path))
    base_norm = os.path.normpath(base_dir)
    if joined != base_norm and not joined.startswith(base_norm + os.sep):
        raise RuntimeError("Refusing to extract outside target directory")
    return joined


def _extract_yt_dlp_from_tarball(archive_path, destination_runtime_path):
    tmp_path = destination_runtime_path + ".tmp"
    if os.path.isdir(tmp_path):
        shutil.rmtree(tmp_path)
    os.makedirs(tmp_path, exist_ok=True)

    try:
        with tarfile.open(name=archive_path, mode="r:gz") as tf:
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
                with src, open(target_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)

        expected_init = os.path.join(tmp_path, "yt_dlp", "__init__.py")
        if not os.path.isfile(expected_init):
            raise RuntimeError("Downloaded archive does not contain a valid yt_dlp package")

        if os.path.isdir(destination_runtime_path):
            shutil.rmtree(destination_runtime_path)
        os.makedirs(os.path.dirname(destination_runtime_path), exist_ok=True)
        os.rename(tmp_path, destination_runtime_path)
    except Exception:
        if os.path.isdir(tmp_path):
            shutil.rmtree(tmp_path)
        raise


def _download_and_install(version, source=DEFAULT_YTDLP_SOURCE, show_progress=True):
    url = _tarball_url(source, version)
    _log("Downloading yt-dlp {} ({}) from {}".format(version, source, url))

    runtime_path = _runtime_path_for_version(version)
    archive_path = runtime_path + ".tar.gz"
    try:
        try:
            managed_runtime.download_with_progress(
                url, archive_path, _RUNTIME_LABEL, version, show_progress=show_progress
            )
        except urllib.error.HTTPError as exc:
            fallback_url = _fallback_tarball_url(source, version)
            if exc.code != 404 or fallback_url is None:
                raise
            _log("No yt-dlp.tar.gz asset for {}, using the tag archive {}".format(version, fallback_url))
            managed_runtime.download_with_progress(
                fallback_url, archive_path, _RUNTIME_LABEL, version, show_progress=show_progress
            )

        _extract_yt_dlp_from_tarball(archive_path, runtime_path)
    finally:
        managed_runtime.remove_download(archive_path)
    _write_installed_version(version)
    _log("yt-dlp {} ({}) installed at {}".format(version, source, runtime_path))
    _prune_old_versions(version)
    return runtime_path


def get_runtime_status(
    requested_version=YTDLP_LATEST_SENTINEL,
    force_refresh_latest=False,
    source=DEFAULT_YTDLP_SOURCE,
):
    """Return yt-dlp status information for UI/diagnostics."""
    source = normalize_source(source)

    if not is_managed_source(source):
        system_version = resolve_system_ytdlp()
        return {
            "source": source,
            "requested_version": _normalize_requested_version(requested_version),
            "installed_version": system_version,
            "installed_runtime_path": None,
            # No managed version is in use, so none is listed: showing the
            # managed ones would suggest they can be selected.
            "installed_versions": [],
            "latest_version": None,
            "is_latest_installed": None,
            "latest_error": None,
        }

    requested = _normalize_requested_version(requested_version)
    installed_version, installed_runtime_path = _find_installed_runtime()

    latest_version = None
    latest_error = None
    try:
        if force_refresh_latest:
            latest_version = _resolve_latest_version(force_refresh=True, source=source)
        else:
            latest_version = _resolve_latest_version(source=source)
    except Exception as exc:
        latest_error = str(exc)

    is_latest_installed = None
    if installed_version is not None and latest_version is not None:
        is_latest_installed = installed_version == latest_version

    return {
        "source": source,
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
    source=DEFAULT_YTDLP_SOURCE,
):
    """
    Ensure a yt-dlp runtime is available.

    Returns a status dict with:
      - ready (bool)
      - reason (None | "missing" | "version_mismatch" | "error")
      - version (resolved target version when known)
      - runtime_path (path to use when ready; None for the system source)
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

    source = normalize_source(source)

    if not is_managed_source(source):
        # Nothing to download: the addon only asks whether yt_dlp is importable,
        # and the entry point raises its own error when it is not.
        version = resolve_system_ytdlp()
        if version is None:
            return _not_ready("missing", None, None, None)
        return _ready(version, None)

    try:
        requested = _normalize_requested_version(requested_version)
        installed_version, installed_runtime_path = _find_installed_runtime()

        target_version = requested
        if requested == YTDLP_LATEST_SENTINEL:
            if allow_install:
                if force_refresh_latest:
                    target_version = _resolve_latest_version(force_refresh=True, source=source)
                else:
                    target_version = _resolve_latest_version(source=source)
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
                runtime_path = _download_and_install(target_version, source=source)
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
                target_version = _resolve_latest_version(force_refresh=True, source=source)
            else:
                target_version = _resolve_latest_version(source=source)
        runtime_path = _download_and_install(target_version, source=source)
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