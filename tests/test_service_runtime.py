import datetime
import sys

from core import service_runtime


def test_replacement_stderr_reports_not_tty():
    assert service_runtime.replacement_stderr.isatty(sys.stderr) is False


def test_install_stderr_workaround_sets_replacement_class():
    original_stderr_class = sys.stderr.__class__
    try:
        service_runtime.install_stderr_workaround()

        assert sys.stderr.__class__ is service_runtime.replacement_stderr
    finally:
        sys.stderr.__class__ = original_stderr_class


def test_patch_strptime_produces_datetime_instances():
    original_datetime_class = datetime.datetime
    try:
        service_runtime.patch_strptime()

        parsed = datetime.datetime.strptime("2026-03-23 12:30:45", "%Y-%m-%d %H:%M:%S")

        assert parsed.year == 2026
        assert parsed.month == 3
        assert parsed.day == 23
        assert parsed.hour == 12
        assert parsed.minute == 30
        assert parsed.second == 45
    finally:
        datetime.datetime = original_datetime_class


def test_patch_strptime_is_idempotent():
    original_datetime_class = datetime.datetime
    try:
        service_runtime.patch_strptime()
        patched_class = datetime.datetime
        service_runtime.patch_strptime()

        assert datetime.datetime is patched_class
        assert patched_class.__mro__[1] is original_datetime_class
    finally:
        datetime.datetime = original_datetime_class


_SUBINTERPRETER_SCENARIO = r"""
import sys
import _testcapi

project_root = sys.argv[1]
first = "import datetime; datetime.datetime.strptime('1970-01-01', '%Y-%m-%d')"
patched = (
    "import sys; sys.path.insert(0, {!r});"
    "from core.service_runtime import patch_strptime; patch_strptime(); patch_strptime();"
    "import datetime; datetime.datetime.strptime('2026-01-02', '%Y-%m-%d')"
).format(project_root)

# Two add-on invocations as Kodi runs them: each in its own, destroyed sub-interpreter.
assert _testcapi.run_in_subinterp(first) == 0
sys.exit(0 if _testcapi.run_in_subinterp(patched) == 0 else 1)
"""


def test_patch_strptime_survives_kodi_style_sub_interpreters(tmp_path):
    # Runs in a child process: the bug poisons datetime for the whole process.
    import subprocess
    from pathlib import Path

    try:
        import _testcapi

        _testcapi.run_in_subinterp
    except (ImportError, AttributeError):
        import pytest

        pytest.skip("this Python has no _testcapi.run_in_subinterp")

    script = tmp_path / "scenario.py"
    script.write_text(_SUBINTERPRETER_SCENARIO)
    project_root = str(Path(__file__).resolve().parents[1])

    completed = subprocess.run(
        [sys.executable, "-I", str(script), project_root],
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert completed.returncode == 0, completed.stderr
