from __future__ import annotations
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from src.state import State


@pytest.fixture()
def tmp_state(tmp_path, monkeypatch):
    monkeypatch.setattr("src.state.DATA_DIR",   tmp_path)
    monkeypatch.setattr("src.state.STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr("src.state.PID_FILE",   tmp_path / "daemon.pid")
    return tmp_path


def test_defaults():
    s = State()
    assert s.enabled is True
    assert s.paused is False
    assert s.annoyance_level == 0
    assert s.last_drink is None


def test_mark_drink_resets_level():
    s = State(annoyance_level=4, paused=True)
    s.mark_drink()
    assert s.annoyance_level == 0
    assert s.paused is False
    assert s.last_drink is not None


def test_mark_dismissed_increments():
    s = State(annoyance_level=0)
    s.mark_dismissed()
    assert s.annoyance_level == 1


def test_mark_dismissed_caps_at_max():
    s = State(annoyance_level=6)
    s.mark_dismissed(max_level=6)
    assert s.annoyance_level == 6


def test_mark_paused_no_expiry():
    s = State()
    s.mark_paused()
    assert s.paused is True
    assert s.paused_until is None


def test_mark_paused_with_expiry():
    s = State()
    s.mark_paused(minutes=30)
    assert s.paused is True
    assert s.paused_until is not None
    expiry = datetime.fromisoformat(s.paused_until)
    assert expiry > datetime.now()


def test_mark_resumed():
    s = State(paused=True, annoyance_level=3)
    s.mark_resumed()
    assert s.paused is False
    assert s.paused_until is None
    assert s.annoyance_level == 0


def test_check_pause_expired_clears():
    s = State(paused=True, paused_until=(datetime.now() - timedelta(seconds=1)).isoformat())
    s.check_pause_expired()
    assert s.paused is False


def test_check_pause_not_expired():
    s = State(paused=True, paused_until=(datetime.now() + timedelta(hours=1)).isoformat())
    s.check_pause_expired()
    assert s.paused is True


def test_save_and_load(tmp_state):
    s = State(annoyance_level=3, paused=True)
    s.save()
    loaded = State.load()
    assert loaded.annoyance_level == 3
    assert loaded.paused is True


def test_load_missing_returns_default(tmp_state):
    s = State.load()
    assert s.annoyance_level == 0


def test_load_corrupt_returns_default(tmp_state):
    (tmp_state / "state.json").write_text("{ invalid json }")
    s = State.load()
    assert s.annoyance_level == 0
