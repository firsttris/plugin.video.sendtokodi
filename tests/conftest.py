import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import urllib.request

import pytest


@pytest.fixture(autouse=True)
def isolate_runtime_managers(monkeypatch, tmp_path):
    # Keep tests away from the real addon_data directory and the network.
    from core import deno_manager, ytdlp_manager

    monkeypatch.setattr(deno_manager, "_addon_data_dir", lambda: str(tmp_path / "deno"))
    monkeypatch.setattr(ytdlp_manager, "_addon_data_dir", lambda: str(tmp_path / "ytdlp"))

    def blocked_urlopen(*_args, **_kwargs):
        raise AssertionError("tests must not access the network")

    monkeypatch.setattr(urllib.request, "urlopen", blocked_urlopen)
