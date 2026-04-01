# -*- coding: utf-8 -*-
"""Shared helpers for managed runtime update-check state."""

import json
import os
import time


def default_update_state():
    return {
        "last_checked_at": 0,
        "next_check_at": 0,
        "latest_known_version": None,
        "etag": None,
        "cooldown_until": 0,
        "consecutive_failures": 0,
        "last_error": None,
    }


def load_update_state(state_file):
    try:
        with open(state_file, "r") as f:
            raw = json.load(f)
    except Exception:
        return default_update_state()

    state = default_update_state()
    if isinstance(raw, dict):
        state.update(raw)
    return state


def save_update_state(base_dir, state_file, state):
    os.makedirs(base_dir, exist_ok=True)
    tmp_path = state_file + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(state, f)
    os.replace(tmp_path, state_file)


def parse_retry_after(headers, max_cooldown_seconds):
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
    return min(seconds, max_cooldown_seconds)


def compute_failure_cooldown(consecutive_failures, backoff_steps_seconds):
    index = max(0, min(consecutive_failures - 1, len(backoff_steps_seconds) - 1))
    return backoff_steps_seconds[index]


def apply_success_state(state, latest_version, etag, check_interval_seconds, now=None):
    checked_at = int(time.time()) if now is None else int(now)
    state["last_checked_at"] = checked_at
    state["next_check_at"] = checked_at + check_interval_seconds
    state["cooldown_until"] = 0
    state["consecutive_failures"] = 0
    state["last_error"] = None
    state["latest_known_version"] = latest_version
    if etag:
        state["etag"] = etag


def apply_failure_state(
    state,
    error_message,
    backoff_steps_seconds,
    retry_after=None,
    now=None,
):
    checked_at = int(time.time()) if now is None else int(now)
    failures = int(state.get("consecutive_failures") or 0) + 1
    cooldown = retry_after or compute_failure_cooldown(failures, backoff_steps_seconds)

    state["last_checked_at"] = checked_at
    state["next_check_at"] = checked_at + cooldown
    state["cooldown_until"] = checked_at + cooldown
    state["consecutive_failures"] = failures
    state["last_error"] = error_message
