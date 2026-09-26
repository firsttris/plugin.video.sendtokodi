# -*- coding: utf-8 -*-
"""Shared helpers for the managed runtimes (yt-dlp and Deno) in addon_data.

The runtime modules keep their own thin module-level wrappers so callers and
tests can patch per-runtime paths; everything runtime-independent lives here.
"""

import json
import logging
import os
import shutil
import time
import urllib.error
import urllib.request

from core.runtime_management import select_versions_to_prune
from core.runtime_update_state import (
    apply_failure_state,
    apply_success_state,
    parse_retry_after,
)
from core.update_policy import (
    UPDATE_BACKOFF_STEPS_SECONDS,
    UPDATE_CHECK_INTERVAL_SECONDS,
    UPDATE_CHECK_NOT_MODIFIED_INTERVAL_SECONDS,
    UPDATE_MAX_COOLDOWN_SECONDS,
)


LATEST_SENTINEL = "latest"

# Installed versions kept on disk; older ones are pruned after each install.
MAX_INSTALLED_VERSIONS = 3

_DOWNLOAD_CHUNK_SIZE = 65536  # 64 KiB


def log(logger_name, msg, level=None):
    """Log via xbmc if available, otherwise fall back to stdlib logging."""
    try:
        import xbmc
        if level is None:
            level = xbmc.LOGINFO
        xbmc.log("plugin.video.sendtokodi {}: {}".format(logger_name, msg), level)
    except ImportError:
        logging.getLogger("core." + logger_name).info(msg)


def addon_data_dir(runtime_dir_name):
    """Return the addon_data directory used for one managed runtime."""
    try:
        import xbmcvfs
        return xbmcvfs.translatePath(
            "special://profile/addon_data/plugin.video.sendtokodi/{}/".format(runtime_dir_name)
        )
    except ImportError:
        pass

    # Fallback for running outside Kodi (tests / CI)
    return os.path.join(
        os.path.expanduser("~"),
        ".kodi",
        "userdata",
        "addon_data",
        "plugin.video.sendtokodi",
        runtime_dir_name,
    )


def normalize_requested_version(version):
    requested = (version or "").strip()
    if not requested or requested.lower() == LATEST_SENTINEL:
        return LATEST_SENTINEL
    return requested


def read_version_file(path):
    try:
        with open(path, "r") as f:
            return f.read().strip() or None
    except Exception:
        return None


def write_version_file(path, version, warn, runtime_label):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(version)
    except Exception as exc:
        warn("Could not write {} version file: {}".format(runtime_label, exc))


def clear_version_file(path):
    try:
        os.remove(path)
    except Exception:
        pass


def list_installed_versions(versions_dir, is_installed):
    if not os.path.isdir(versions_dir):
        return []

    versions = []
    for name in os.listdir(versions_dir):
        if os.path.isdir(os.path.join(versions_dir, name)) and is_installed(name):
            versions.append(name)
    return sorted(versions, reverse=True)


def delete_installed_version(
    version,
    runtime_dir,
    read_active_version,
    write_active_version,
    clear_active_version,
    list_installed,
    warn,
    runtime_label,
):
    """Delete one installed version; promote the newest remaining one if it was active."""
    target = (version or "").strip()
    if not target:
        return False

    path = runtime_dir(target)
    if not os.path.isdir(path):
        return False

    try:
        shutil.rmtree(path)
    except Exception as exc:
        warn("Could not delete {} version {}: {}".format(runtime_label, target, exc))
        return False

    if read_active_version() == target:
        remaining_versions = list_installed()
        if remaining_versions:
            write_active_version(remaining_versions[0])
        else:
            clear_active_version()

    return True


def prune_old_versions(keep_version, installed_versions, runtime_dir, log_info, warn, runtime_label):
    versions_newest_first = sorted(
        installed_versions,
        key=lambda version: os.path.getmtime(runtime_dir(version)),
        reverse=True,
    )
    for version in select_versions_to_prune(versions_newest_first, keep_version, MAX_INSTALLED_VERSIONS):
        try:
            shutil.rmtree(runtime_dir(version))
            log_info("Removed old {} version {}".format(runtime_label, version))
        except Exception as exc:
            warn("Could not remove old {} version {}: {}".format(runtime_label, version, exc))


def resolve_latest_version(latest_release_api, load_state, save_state, force_refresh=False):
    """Return the latest release tag, honoring the cached check interval, ETag and backoff."""
    state = load_state()
    now = int(time.time())
    cached_version = state.get("latest_known_version")

    if not force_refresh:
        next_check_at = int(state.get("next_check_at") or 0)
        cooldown_until = int(state.get("cooldown_until") or 0)
        if cached_version and now < max(next_check_at, cooldown_until):
            return cached_version

    request = urllib.request.Request(latest_release_api)
    etag = state.get("etag")
    if etag:
        request.add_header("If-None-Match", etag)

    def record_failure(error_message, retry_after=None):
        apply_failure_state(
            state,
            error_message,
            UPDATE_BACKOFF_STEPS_SECONDS,
            retry_after=retry_after,
        )
        save_state(state)

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
            response_etag = response.headers.get("ETag")

        tag = (payload.get("tag_name") or "").strip()
        if not tag:
            raise RuntimeError("GitHub latest release response has no tag_name")

        apply_success_state(state, tag, response_etag, UPDATE_CHECK_INTERVAL_SECONDS)
        save_state(state)
        return tag
    except urllib.error.HTTPError as exc:
        if exc.code == 304 and cached_version:
            apply_success_state(
                state,
                cached_version,
                exc.headers.get("ETag") or etag,
                UPDATE_CHECK_NOT_MODIFIED_INTERVAL_SECONDS,
            )
            save_state(state)
            return cached_version

        if exc.code == 429:
            error_message = "GitHub API rate limit hit (HTTP 429)"
            retry_after = parse_retry_after(exc.headers, UPDATE_MAX_COOLDOWN_SECONDS)
        else:
            error_message = "GitHub latest release lookup failed: HTTP {}".format(exc.code)
            retry_after = None

        record_failure(error_message, retry_after=retry_after)
        if cached_version:
            return cached_version
        raise RuntimeError(error_message)
    except Exception as exc:
        record_failure(str(exc))
        if cached_version:
            return cached_version
        raise


def list_available_versions(releases_api, limit, warn, runtime_label, skip_prereleases=False):
    """Return available release tags (newest first); empty on failure."""
    if limit <= 0:
        return []

    versions = []
    page = 1

    try:
        while len(versions) < limit:
            url = releases_api.format(page=page)
            with urllib.request.urlopen(url, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))

            if not isinstance(payload, list) or not payload:
                break

            for release in payload:
                if skip_prereleases and (release.get("prerelease") or release.get("draft")):
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
        warn("Could not list {} releases: {}".format(runtime_label, exc))

    return versions


def download_with_progress(url, runtime_label, version, show_progress=True):
    """Download url into memory, showing a Kodi background progress dialog when possible."""
    progress = None
    if show_progress:
        try:
            import xbmcgui

            progress = xbmcgui.DialogProgressBG()
            progress.create("SendToKodi", "Downloading {} {}...".format(runtime_label, version))
        except Exception:
            progress = None

    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            total = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            chunks = []
            while True:
                chunk = response.read(_DOWNLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                chunks.append(chunk)
                downloaded += len(chunk)
                if progress is not None and total > 0:
                    progress.update(
                        int(downloaded * 100 / total),
                        "Downloading {} {} ({}/{} MB)...".format(
                            runtime_label,
                            version,
                            downloaded // (1024 * 1024),
                            total // (1024 * 1024),
                        ),
                    )
            return b"".join(chunks)
    finally:
        if progress is not None:
            progress.close()
