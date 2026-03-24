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
