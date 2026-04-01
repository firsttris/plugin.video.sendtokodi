from core import runtime_update_state


def test_default_update_state_contains_expected_keys():
    state = runtime_update_state.default_update_state()

    assert set(state.keys()) == {
        "last_checked_at",
        "next_check_at",
        "latest_known_version",
        "etag",
        "cooldown_until",
        "consecutive_failures",
        "last_error",
    }


def test_parse_retry_after_clamps_to_maximum():
    headers = {"Retry-After": "999"}

    assert runtime_update_state.parse_retry_after(headers, 120) == 120


def test_apply_success_state_resets_failures_and_sets_schedule():
    state = runtime_update_state.default_update_state()
    state["consecutive_failures"] = 2
    state["last_error"] = "boom"

    runtime_update_state.apply_success_state(
        state,
        latest_version="v2.7.5",
        etag="etag-1",
        check_interval_seconds=300,
        now=1000,
    )

    assert state["last_checked_at"] == 1000
    assert state["next_check_at"] == 1300
    assert state["consecutive_failures"] == 0
    assert state["last_error"] is None
    assert state["latest_known_version"] == "v2.7.5"
    assert state["etag"] == "etag-1"


def test_apply_failure_state_uses_retry_after_when_present():
    state = runtime_update_state.default_update_state()

    runtime_update_state.apply_failure_state(
        state,
        error_message="rate limit",
        backoff_steps_seconds=[60, 120, 240],
        retry_after=90,
        now=1000,
    )

    assert state["last_checked_at"] == 1000
    assert state["next_check_at"] == 1090
    assert state["cooldown_until"] == 1090
    assert state["consecutive_failures"] == 1
    assert state["last_error"] == "rate limit"
