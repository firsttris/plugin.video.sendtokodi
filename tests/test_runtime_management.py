from core import runtime_management


def test_normalize_installed_versions_adds_active_version():
    result = runtime_management.normalize_installed_versions("v2.7.5", ["v2.7.4"])

    assert result == {"v2.7.4", "v2.7.5"}


def test_merge_remote_and_installed_versions_appends_missing_local_versions():
    result = runtime_management.merge_remote_and_installed_versions(
        ["v2.7.5", "v2.7.4"],
        {"v2.7.5", "v2.7.3"},
    )

    assert result == ["v2.7.5", "v2.7.4", "v2.7.3"]


def test_build_version_entries_includes_active_and_installed_flags():
    result = runtime_management.build_version_entries(
        ["v2.7.5", "v2.7.4", "v2.7.3"],
        {"v2.7.5", "v2.7.3"},
        "v2.7.5",
    )

    assert result == [
        "v2.7.5 [active, installed]",
        "v2.7.4",
        "v2.7.3 [installed]",
    ]


def test_build_action_options_for_installed_inactive_version():
    result = runtime_management.build_action_options(
        "v2.7.4",
        {"v2.7.5", "v2.7.4"},
        "v2.7.5",
    )

    assert result == [
        ("Activate local version", "activate"),
        ("Delete local version", "delete"),
    ]
