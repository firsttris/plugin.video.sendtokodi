# -*- coding: utf-8 -*-
"""Shared update/check cadence policy used by managed runtimes."""

UPDATE_CHECK_INTERVAL_SECONDS = 6 * 60 * 60
UPDATE_BACKOFF_STEPS_SECONDS = (5 * 60, 15 * 60, 60 * 60, 6 * 60 * 60, 24 * 60 * 60)

# Keep this derived to avoid duplicated configuration values.
UPDATE_CHECK_NOT_MODIFIED_INTERVAL_SECONDS = UPDATE_CHECK_INTERVAL_SECONDS * 4
UPDATE_MAX_COOLDOWN_SECONDS = max(UPDATE_BACKOFF_STEPS_SECONDS)
