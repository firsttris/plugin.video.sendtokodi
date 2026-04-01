# -*- coding: utf-8 -*-
"""Pure helpers for managed runtime version/action selection."""


def normalize_installed_versions(installed_version, installed_versions):
    versions = set(installed_versions or [])
    if installed_version:
        versions.add(installed_version)
    return versions


def merge_remote_and_installed_versions(remote_versions, installed_versions):
    if not remote_versions:
        return sorted(installed_versions, reverse=True)

    versions = list(remote_versions)
    for local_version in sorted(installed_versions, reverse=True):
        if local_version not in versions:
            versions.append(local_version)
    return versions


def build_version_entries(versions, installed_versions, active_version):
    entries = []
    for version in versions:
        flags = []
        if version == active_version:
            flags.append("active")
        if version in installed_versions:
            flags.append("installed")

        label = version
        if flags:
            label = "{} [{}]".format(version, ", ".join(flags))
        entries.append(label)
    return entries


def build_action_options(selected_version, installed_versions, active_version):
    is_installed = selected_version in installed_versions
    is_active = selected_version == active_version

    options = []
    if is_installed and not is_active:
        options.append(("Activate local version", "activate"))
    if not is_installed:
        options.append(("Install version", "install"))
    if is_installed:
        options.append(("Delete local version", "delete"))

    return options
