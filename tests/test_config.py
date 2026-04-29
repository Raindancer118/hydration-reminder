from __future__ import annotations
from unittest.mock import patch

import pytest

from src.config import Config, DEFAULT_LEVELS, LevelConfig


@pytest.fixture()
def tmp_config(tmp_path, monkeypatch):
    monkeypatch.setattr("src.config.CONFIG_DIR",  tmp_path)
    monkeypatch.setattr("src.config.CONFIG_FILE", tmp_path / "config.json")
    return tmp_path


def test_default_levels_count():
    c = Config()
    assert len(c.levels) == len(DEFAULT_LEVELS)


def test_intervals_non_increasing():
    """Higher annoyance levels must have shorter or equal intervals."""
    for i in range(1, len(DEFAULT_LEVELS)):
        assert DEFAULT_LEVELS[i].interval <= DEFAULT_LEVELS[i - 1].interval, (
            f"Level {i} interval ({DEFAULT_LEVELS[i].interval}s) "
            f"> level {i-1} interval ({DEFAULT_LEVELS[i-1].interval}s)"
        )


def test_all_levels_have_required_fields():
    for lvl in DEFAULT_LEVELS:
        assert lvl.title
        assert lvl.message
        assert lvl.type in ("notification", "modal", "fullscreen")
        assert 0 <= lvl.urgency <= 2


def test_escalation_ends_in_fullscreen():
    assert DEFAULT_LEVELS[-1].type == "fullscreen"


def test_save_and_load_roundtrip(tmp_config):
    c = Config(base_interval=900, autostart=True)
    c.save()
    loaded = Config.load()
    assert loaded.base_interval == 900
    assert loaded.autostart is True
    assert len(loaded.levels) == len(DEFAULT_LEVELS)


def test_load_missing_returns_defaults(tmp_config):
    c = Config.load()
    assert c.base_interval == 1800


def test_load_corrupt_returns_defaults(tmp_config):
    (tmp_config / "config.json").write_text("not json")
    c = Config.load()
    assert c.base_interval == 1800
