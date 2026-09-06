import pytest

from agent_sherlock.config import load_settings


def test_profile_cannot_escape_data_directory(tmp_path):
    for profile in ("../elsewhere", "/absolute", ".", "", "a/b"):
        if profile:
            with pytest.raises(ValueError):
                load_settings(tmp_path, profile)


def test_config_is_bound_to_selected_profile(tmp_path):
    config = tmp_path / "config.json"
    config.write_text('{"profile":"company-b"}')
    with pytest.raises(ValueError, match="does not match"):
        load_settings(tmp_path / "data", "company-a", config)


def test_profile_data_separation(tmp_path):
    a, b = load_settings(tmp_path, "a"), load_settings(tmp_path, "b")
    assert a.database != b.database
    assert a.profile_dir.is_dir() and b.profile_dir.is_dir()

