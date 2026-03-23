import pytest

from core import deno_manager


def test_detect_platform_supported(monkeypatch):
    monkeypatch.setattr(deno_manager.platform, "system", lambda: "Linux")
    monkeypatch.setattr(deno_manager.platform, "machine", lambda: "x86_64")

    assert deno_manager._detect_platform() == ("linux", "x86_64")


def test_detect_platform_unsupported(monkeypatch):
    monkeypatch.setattr(deno_manager.platform, "system", lambda: "Plan9")
    monkeypatch.setattr(deno_manager.platform, "machine", lambda: "mips")

    with pytest.raises(RuntimeError):
        deno_manager._detect_platform()


def test_deno_binary_name_windows(monkeypatch):
    monkeypatch.setattr(deno_manager.platform, "system", lambda: "Windows")
    assert deno_manager._deno_binary_name() == "deno.exe"


def test_deno_binary_name_posix(monkeypatch):
    monkeypatch.setattr(deno_manager.platform, "system", lambda: "Linux")
    assert deno_manager._deno_binary_name() == "deno"


def test_get_and_set_installed_version(monkeypatch, tmp_path):
    version_file = tmp_path / "deno_version.txt"
    monkeypatch.setattr(deno_manager, "_version_file", lambda: str(version_file))

    deno_manager._set_installed_version("v-test")

    assert deno_manager._get_installed_version() == "v-test"


def test_get_ydl_opts_prefers_existing_addon_binary(monkeypatch):
    monkeypatch.setattr(deno_manager, "_find_in_addon_data", lambda: "/addon/deno")
    monkeypatch.setattr(deno_manager, "_get_installed_version", lambda: deno_manager.DENO_VERSION)
    monkeypatch.setattr(deno_manager, "_find_in_path", lambda: None)
    monkeypatch.setattr(
        deno_manager,
        "_download_deno",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("download should not run")),
    )

    opts = deno_manager.get_ydl_opts(auto_download=True)

    assert opts["js_runtimes"]["deno"]["path"] == "/addon/deno"
    assert opts["remote_components"] == {"ejs:github"}


def test_get_ydl_opts_updates_on_version_mismatch(monkeypatch):
    monkeypatch.setattr(deno_manager, "_find_in_addon_data", lambda: "/addon/deno")
    monkeypatch.setattr(deno_manager, "_get_installed_version", lambda: "old-version")
    monkeypatch.setattr(deno_manager, "_addon_data_dir", lambda: "/addon")
    monkeypatch.setattr(deno_manager, "_download_deno", lambda *_args, **_kwargs: "/addon/deno-new")

    opts = deno_manager.get_ydl_opts(auto_download=True)

    assert opts["js_runtimes"]["deno"]["path"] == "/addon/deno-new"


def test_get_ydl_opts_uses_system_path_when_needed(monkeypatch):
    monkeypatch.setattr(deno_manager, "_find_in_addon_data", lambda: None)
    monkeypatch.setattr(deno_manager, "_find_in_path", lambda: "/usr/bin/deno")

    opts = deno_manager.get_ydl_opts(auto_download=True)

    assert opts["js_runtimes"]["deno"]["path"] == "/usr/bin/deno"


def test_get_ydl_opts_returns_empty_when_missing_and_download_disabled(monkeypatch):
    monkeypatch.setattr(deno_manager, "_find_in_addon_data", lambda: None)
    monkeypatch.setattr(deno_manager, "_find_in_path", lambda: None)

    opts = deno_manager.get_ydl_opts(auto_download=False)

    assert opts == {}


def test_get_ydl_opts_returns_empty_on_internal_error(monkeypatch):
    monkeypatch.setattr(
        deno_manager,
        "_find_in_addon_data",
        lambda: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    opts = deno_manager.get_ydl_opts(auto_download=True)

    assert opts == {}
