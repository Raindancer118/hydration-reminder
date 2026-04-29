from __future__ import annotations
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path.home() / ".local" / "share" / "hydration-reminder"
STATE_FILE = DATA_DIR / "state.json"
PID_FILE   = DATA_DIR / "daemon.pid"
LOG_FILE   = DATA_DIR / "daemon.log"

_FIELDS = {"enabled", "paused", "paused_until", "annoyance_level", "last_drink", "last_reminder"}


@dataclass
class State:
    enabled: bool = True
    paused: bool = False
    paused_until: str | None = None
    annoyance_level: int = 0
    last_drink: str | None = None
    last_reminder: str | None = None

    def mark_drink(self) -> None:
        self.last_drink = datetime.now().isoformat()
        self.annoyance_level = 0
        self.paused = False
        self.paused_until = None

    def mark_dismissed(self, max_level: int = 6) -> None:
        self.annoyance_level = min(self.annoyance_level + 1, max_level)

    def mark_paused(self, minutes: int | None = None) -> None:
        self.paused = True
        if minutes is not None:
            self.paused_until = (datetime.now() + timedelta(minutes=minutes)).isoformat()
        else:
            self.paused_until = None

    def mark_resumed(self) -> None:
        self.paused = False
        self.paused_until = None
        self.annoyance_level = 0

    def check_pause_expired(self) -> None:
        if self.paused and self.paused_until:
            if datetime.now() >= datetime.fromisoformat(self.paused_until):
                self.paused = False
                self.paused_until = None

    def save(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = STATE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps({
            "enabled": self.enabled,
            "paused": self.paused,
            "paused_until": self.paused_until,
            "annoyance_level": self.annoyance_level,
            "last_drink": self.last_drink,
            "last_reminder": self.last_reminder,
        }, indent=2))
        tmp.replace(STATE_FILE)

    @classmethod
    def load(cls) -> State:
        if not STATE_FILE.exists():
            return cls()
        try:
            raw = json.loads(STATE_FILE.read_text())
            return cls(**{k: v for k, v in raw.items() if k in _FIELDS})
        except Exception:
            return cls()

    def get_daemon_pid(self) -> int | None:
        if not PID_FILE.exists():
            return None
        try:
            pid = int(PID_FILE.read_text().strip())
            os.kill(pid, 0)
            return pid
        except (ValueError, ProcessLookupError, PermissionError):
            PID_FILE.unlink(missing_ok=True)
            return None
