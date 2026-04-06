# -*- coding: utf-8 -*-
import importlib

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

from core.addon_params import resolve_deno_settings, resolve_ytdlp_settings
from core.runtime_management import (
    build_action_options,
    build_version_entries,
    merge_remote_and_installed_versions,
    normalize_installed_versions,
)


def _runtime_settings(runtime_name, handle):
    if runtime_name == "deno":
        return resolve_deno_settings(handle, xbmcplugin.getSetting)
    if runtime_name == "ytdlp":
        return resolve_ytdlp_settings(handle, xbmcplugin.getSetting)
    raise ValueError("Unknown runtime {}".format(runtime_name))


def _runtime_module(runtime_name):
    if runtime_name == "deno":
        return importlib.import_module("core.deno_manager")
    if runtime_name == "ytdlp":
        return importlib.import_module("core.ytdlp_manager")
    raise ValueError("Unknown runtime {}".format(runtime_name))


def _set_installed_version_display(runtime_name, version):
    setting_key = (
        "deno_installed_version_display"
        if runtime_name == "deno"
        else "ytdlp_installed_version_display"
    )
    display_value = (version or "").strip() or "not installed"
    xbmcaddon.Addon().setSetting(setting_key, display_value)


def _runtime_label(runtime_name):
    return "Deno" if runtime_name == "deno" else "yt-dlp"


def _get_runtime_status(runtime_name, manager_module, version):
    if runtime_name == "deno":
        return manager_module.get_runtime_status(version, include_latest=False)
    return manager_module.get_runtime_status(version)


def _list_available_versions(runtime_name, manager_module):
    if runtime_name == "deno":
        return manager_module.list_available_versions(limit=20)
    return manager_module.list_available_versions(limit=20)


def _install_runtime_version(
    runtime_name,
    selected_version,
    manager_module,
    run_with_progress,
    show_info_notification,
    show_error_notification,
):
    runtime_label = _runtime_label(runtime_name)

    if runtime_name == "deno":
        opts = run_with_progress(
            "SendToKodi",
            "Installing {} {}...".format(runtime_label, selected_version),
            lambda: manager_module.get_ydl_opts(
                auto_download=True,
                requested_version=selected_version,
                force_refresh_latest=True,
            ),
        )
        deno_path = opts.get("js_runtimes", {}).get("deno", {}).get("path")
        if deno_path:
            status = _get_runtime_status(runtime_name, manager_module, selected_version)
            installed_version = status.get("installed_version") or selected_version
            _set_installed_version_display(runtime_name, installed_version)
            show_info_notification("{} {} is installed".format(runtime_label, installed_version))
            return True

        show_error_notification("{} install failed".format(runtime_label))
        return False

    result = run_with_progress(
        "SendToKodi",
        "Installing {} {}...".format(runtime_label, selected_version),
        lambda: manager_module.ensure_ytdlp_ready(
            allow_install=True,
            requested_version=selected_version,
            force_refresh_latest=True,
        ),
    )
    if result["ready"]:
        _set_installed_version_display(
            runtime_name,
            result.get("installed_version") or result.get("version"),
        )
        show_info_notification("{} {} is installed".format(runtime_label, result["version"]))
        return True

    error_message = result.get("error") or result.get("reason") or "unknown error"
    show_error_notification("{} install failed: {}".format(runtime_label, error_message))
    return False


def _activate_runtime_version(runtime_name, selected_version, manager_module, show_info_notification, show_error_notification):
    runtime_label = _runtime_label(runtime_name)
    runtime_path = manager_module.activate_installed_version(selected_version)
    if runtime_path is None:
        show_error_notification("{} {} is not installed locally".format(runtime_label, selected_version))
        return False

    status = _get_runtime_status(runtime_name, manager_module, selected_version)
    installed_version = status.get("installed_version") or selected_version
    _set_installed_version_display(runtime_name, installed_version)
    show_info_notification("{} {} is active".format(runtime_label, installed_version))
    return True


def _delete_runtime_version(runtime_name, selected_version, manager_module, show_info_notification, show_error_notification):
    runtime_label = _runtime_label(runtime_name)
    should_delete = xbmcgui.Dialog().yesno(
        "SendToKodi",
        "Delete local {} version {}?".format(runtime_label, selected_version),
    )
    if not should_delete:
        return False

    deleted = manager_module.delete_installed_version(selected_version)
    if not deleted:
        show_error_notification("Could not delete {} {}".format(runtime_label, selected_version))
        return False

    status = _get_runtime_status(runtime_name, manager_module, None)
    remaining_version = status.get("installed_version")
    if remaining_version:
        _set_installed_version_display(runtime_name, remaining_version)
        show_info_notification(
            "{} {} deleted; {} is now active".format(
                runtime_label,
                selected_version,
                remaining_version,
            )
        )
    else:
        _set_installed_version_display(runtime_name, None)
        show_info_notification("{} {} deleted".format(runtime_label, selected_version))
    return True


def _choose_runtime_version(runtime_name, status, list_available_versions, run_with_progress, show_info_notification, show_error_notification, log):
    runtime_label = _runtime_label(runtime_name)
    remote_versions = run_with_progress(
        "SendToKodi",
        "Loading {} versions...".format(runtime_label),
        list_available_versions,
    )

    installed_version = status.get("installed_version")
    installed_versions = normalize_installed_versions(
        installed_version,
        status.get("installed_versions"),
    )

    if not remote_versions:
        if not installed_versions:
            show_error_notification(
                "Could not load {} release list from GitHub".format(runtime_label)
            )
            return None
        show_info_notification(
            "GitHub unavailable: showing installed {} versions".format(runtime_label)
        )
        log(
            "{} release list unavailable; showing locally installed versions".format(runtime_label),
            xbmc.LOGWARNING,
        )
    else:
        log("Loaded remote {} release list".format(runtime_label))

    versions = merge_remote_and_installed_versions(remote_versions, installed_versions)
    active_version = status.get("installed_version")
    entries = build_version_entries(versions, installed_versions, active_version)
    selected = xbmcgui.Dialog().select(
        "SendToKodi - manage {} version".format(runtime_label),
        entries,
    )
    if selected < 0:
        return None

    selected_version = versions[selected]
    action_options = build_action_options(selected_version, installed_versions, active_version)
    action_labels = [label for label, _action in action_options]
    action_values = [_action for _label, _action in action_options]
    if len(action_values) == 1:
        return selected_version, action_values[0]

    action_index = xbmcgui.Dialog().select(
        "SendToKodi - {} action ({})".format(runtime_label, selected_version),
        action_labels,
    )
    if action_index < 0:
        return None

    return selected_version, action_values[action_index]


def _open_select_version_dialog(runtime_name, handle, run_with_progress, show_info_notification, show_error_notification, log):
    settings = _runtime_settings(runtime_name, handle)
    manager_module = _runtime_module(runtime_name)

    status = _get_runtime_status(runtime_name, manager_module, settings["version"])
    _set_installed_version_display(runtime_name, status.get("installed_version"))

    selection = _choose_runtime_version(
        runtime_name,
        status,
        lambda: _list_available_versions(runtime_name, manager_module),
        run_with_progress,
        show_info_notification,
        show_error_notification,
        log,
    )
    if selection is None:
        return

    selected_version, action = selection
    if action == "install":
        _install_runtime_version(
            runtime_name,
            selected_version,
            manager_module,
            run_with_progress,
            show_info_notification,
            show_error_notification,
        )
    elif action == "activate":
        _activate_runtime_version(
            runtime_name,
            selected_version,
            manager_module,
            show_info_notification,
            show_error_notification,
        )
    elif action == "delete":
        _delete_runtime_version(
            runtime_name,
            selected_version,
            manager_module,
            show_info_notification,
            show_error_notification,
        )


def _update_runtime_now(runtime_name, handle, run_with_progress, show_info_notification, show_error_notification):
    settings = _runtime_settings(runtime_name, handle)
    manager_module = _runtime_module(runtime_name)
    _install_runtime_version(
        runtime_name,
        settings["version"],
        manager_module,
        run_with_progress,
        show_info_notification,
        show_error_notification,
    )


def refresh_runtime_displays(handle, log):
    for runtime_name in ("deno", "ytdlp"):
        try:
            settings = _runtime_settings(runtime_name, handle)
            manager_module = _runtime_module(runtime_name)
            status = _get_runtime_status(runtime_name, manager_module, settings["version"])
            _set_installed_version_display(runtime_name, status.get("installed_version"))
        except Exception as exc:
            log(
                "Could not refresh {} installed version display: {}".format(
                    _runtime_label(runtime_name),
                    exc,
                ),
                xbmc.LOGWARNING,
            )


def handle_runtime_action(action, handle, run_with_progress, show_info_notification, show_error_notification, log):
    action_map = {
        "deno_select_version": ("deno", "select"),
        "deno_update_now": ("deno", "update"),
        "ytdlp_select_version": ("ytdlp", "select"),
        "ytdlp_update_now": ("ytdlp", "update"),
    }

    mapped = action_map.get(action)
    if mapped is None:
        return False

    runtime_name, operation = mapped
    if operation == "select":
        _open_select_version_dialog(
            runtime_name,
            handle,
            run_with_progress,
            show_info_notification,
            show_error_notification,
            log,
        )
    else:
        _update_runtime_now(
            runtime_name,
            handle,
            run_with_progress,
            show_info_notification,
            show_error_notification,
        )
    return True


def configure_managed_ytdlp(handle, log):
    settings = resolve_ytdlp_settings(handle, xbmcplugin.getSetting)
    manager_module = _runtime_module("ytdlp")

    status = manager_module.ensure_ytdlp_ready(
        allow_install=settings["auto_update"],
        requested_version=settings["version"],
    )
    _set_installed_version_display("ytdlp", status.get("installed_version"))

    if not status["ready"] and status["reason"] in ("missing", "version_mismatch"):
        wanted = settings["version"]
        if wanted == "latest":
            prompt_msg = "Managed yt-dlp is not available. Download latest version now?"
        else:
            prompt_msg = "Managed yt-dlp {} is not installed. Download it now?".format(wanted)

        should_download = xbmcgui.Dialog().yesno("SendToKodi", prompt_msg)
        if should_download:
            status = manager_module.ensure_ytdlp_ready(
                allow_install=True,
                requested_version=settings["version"],
            )
            _set_installed_version_display("ytdlp", status.get("installed_version"))

    if status["ready"] and status["runtime_path"] is not None:
        manager_module.activate_runtime(status["runtime_path"])
        log("Using managed yt-dlp version {}".format(status["version"]))
        return

    error_message = status.get("error")
    if error_message:
        log(
            "Managed yt-dlp unavailable, falling back to bundled/system yt-dlp: {}".format(
                error_message
            ),
            xbmc.LOGWARNING,
        )
    else:
        log(
            "Managed yt-dlp unavailable, falling back to bundled/system yt-dlp",
            xbmc.LOGWARNING,
        )
