# -*- coding: utf-8 -*-
"""Pure helpers for managed runtime version/action selection."""

import re


def version_sort_key(version):
    value = (version or '').strip().lower()
    return [int(part) if part.isdigit() else part for part in re.findall(r'\d+|[a-z]+', value)]


def sort_versions_descending(versions):
    return sorted(versions, key=version_sort_key, reverse=True)


def normalize_installed_versions(installed_version, installed_versions):
    versions = set(installed_versions or [])
    if installed_version:
        versions.add(installed_version)
    return versions


def merge_remote_and_installed_versions(remote_versions, installed_versions):
    if not remote_versions:
        return sort_versions_descending(installed_versions)

    versions = list(remote_versions)
    for local_version in sort_versions_descending(installed_versions):
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


def select_versions_to_prune(versions_newest_first, keep_version, max_versions):
    kept = 1 if keep_version in versions_newest_first else 0
    to_prune = []
    for version in versions_newest_first:
        if version == keep_version:
            continue
        if kept < max_versions:
            kept += 1
        else:
            to_prune.append(version)
    return to_prune
