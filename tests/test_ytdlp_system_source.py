"""Tests for the "system" yt-dlp source.

"system" is the opposite of the managed sources: nothing is downloaded, the
addon only asks whether yt_dlp is importable. Where the package lives is a
packaging concern (the same way deno_manager resolves a system binary without
any path setting).
"""

import sys
import types

import pytest

from core import ytdlp_manager


def _fake_yt_dlp(version="2099.01.02"):
    module = types.ModuleType("yt_dlp")
    module.version = types.SimpleNamespace(__version__=version)
    return module


@pytest.fixture
def no_yt_dlp(monkeypatch):
    """Make sure nothing named yt_dlp can be imported."""
    monkeypatch.setitem(sys.modules, "yt_dlp", None)


def test_system_is_a_known_source():
    assert ytdlp_manager.YTDLP_SOURCE_SYSTEM == "system"
    assert "system" in ytdlp_manager.YTDLP_SOURCES
    # The default must stay a managed source: on most platforms nothing is
    # importable, so silently skipping the download would be the wrong default.
    assert ytdlp_manager.DEFAULT_YTDLP_SOURCE == "stable"


def test_system_is_normalized_like_the_others():
    assert ytdlp_manager.normalize_source("system") == "system"
    assert ytdlp_manager.normalize_source("  SYSTEM ") == "system"


def test_is_managed_source_distinguishes_system():
    assert ytdlp_manager.is_managed_source("stable") is True
    assert ytdlp_manager.is_managed_source("nightly") is True
    assert ytdlp_manager.is_managed_source("system") is False


def test_system_has_no_download_endpoints():
    """A system install must never resolve a release URL."""
    assert "system" not in ytdlp_manager._SOURCE_REPOS
    assert "system" not in ytdlp_manager._SOURCE_TARBALL_URLS


def test_resolve_system_ytdlp_returns_none_when_not_importable(no_yt_dlp):
    assert ytdlp_manager.resolve_system_ytdlp() is None


def test_resolve_system_ytdlp_reports_the_version(monkeypatch):
    monkeypatch.setitem(sys.modules, "yt_dlp", _fake_yt_dlp("2099.01.02"))
    assert ytdlp_manager.resolve_system_ytdlp() == "2099.01.02"


def test_resolve_system_ytdlp_tolerates_a_missing_version_attribute(monkeypatch):
    module = types.ModuleType("yt_dlp")  # no .version at all
    monkeypatch.setitem(sys.modules, "yt_dlp", module)
    assert ytdlp_manager.resolve_system_ytdlp() == "unknown"


def test_ensure_ready_system_reports_missing_without_downloading(no_yt_dlp, monkeypatch):
    def _explode(*_args, **_kwargs):
        raise AssertionError("the system source must not download anything")

    monkeypatch.setattr(ytdlp_manager, "_download_and_install", _explode)
    monkeypatch.setattr(ytdlp_manager, "_resolve_latest_version", _explode)

    status = ytdlp_manager.ensure_ytdlp_ready(allow_install=True, source="system")

    assert status["ready"] is False
    assert status["reason"] == "missing"
    assert status["runtime_path"] is None


def test_ensure_ready_system_is_ready_when_importable(monkeypatch):
    monkeypatch.setitem(sys.modules, "yt_dlp", _fake_yt_dlp("2099.01.02"))

    def _explode(*_args, **_kwargs):
        raise AssertionError("the system source must not download anything")

    monkeypatch.setattr(ytdlp_manager, "_download_and_install", _explode)

    status = ytdlp_manager.ensure_ytdlp_ready(allow_install=True, source="system")

    assert status["ready"] is True
    assert status["reason"] is None
    assert status["version"] == "2099.01.02"
    # No runtime_path: the caller must not activate anything.
    assert status["runtime_path"] is None


def test_ensure_ready_system_ignores_allow_install(no_yt_dlp):
    """allow_install=False and True must behave the same for system."""
    without = ytdlp_manager.ensure_ytdlp_ready(allow_install=False, source="system")
    with_install = ytdlp_manager.ensure_ytdlp_ready(allow_install=True, source="system")

    assert without["reason"] == with_install["reason"] == "missing"


def test_get_runtime_status_reports_the_system_version(monkeypatch):
    monkeypatch.setitem(sys.modules, "yt_dlp", _fake_yt_dlp("2099.01.02"))

    status = ytdlp_manager.get_runtime_status(source="system")

    assert status["source"] == "system"
    assert status["installed_version"] == "2099.01.02"
    assert status["installed_runtime_path"] is None
    # No release lookup for a system install.
    assert status["latest_version"] is None


def test_get_runtime_status_system_without_library(no_yt_dlp):
    status = ytdlp_manager.get_runtime_status(source="system")

    assert status["source"] == "system"
    assert status["installed_version"] is None
