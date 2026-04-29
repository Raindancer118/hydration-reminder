from __future__ import annotations
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Literal

CONFIG_DIR = Path.home() / ".config" / "hydration-reminder"
CONFIG_FILE = CONFIG_DIR / "config.json"

NotifType = Literal["notification", "modal", "fullscreen"]


@dataclass
class LevelConfig:
    interval: int
    title: str
    message: str
    type: NotifType
    urgency: int = 1


DEFAULT_LEVELS: list[LevelConfig] = [
    LevelConfig(1800, "Drink up! 💧",           "Hey! Time for a hydration break. Have some water!",                "notification", 0),
    LevelConfig(600,  "Still thirsty? 💧",      "You forgot to drink. Please have some water soon.",                "notification", 1),
    LevelConfig(300,  "Seriously though...",    "You haven't had anything in a while. Drink some water. Now.",      "notification", 1),
    LevelConfig(180,  "DRINK SOMETHING.",       "This is getting ridiculous. Have some water. Right now.",          "notification", 2),
    LevelConfig(120,  "⚠️ Are you KIDDING me?", "YOU STILL HAVEN'T HAD ANYTHING TO DRINK.\nI will not stop until you hydrate.", "modal", 2),
    LevelConfig(60,   "🚨 CRITICAL HYDRATION",  "I AM DONE BEING NICE.\nDRINK WATER.\nNOW.",                       "modal",        2),
    LevelConfig(60,   "DRINK",                  "WATER\nNOW",                                                       "fullscreen",   2),
]


@dataclass
class Config:
    base_interval: int = 1800
    autostart: bool = False
    levels: list[LevelConfig] = field(default_factory=lambda: [l for l in DEFAULT_LEVELS])

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "base_interval": self.base_interval,
            "autostart": self.autostart,
            "levels": [asdict(l) for l in self.levels],
        }
        CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    @classmethod
    def load(cls) -> Config:
        if not CONFIG_FILE.exists():
            return cls()
        try:
            raw = json.loads(CONFIG_FILE.read_text())
            levels = [LevelConfig(**l) for l in raw.get("levels", [])]
            return cls(
                base_interval=raw.get("base_interval", 1800),
                autostart=raw.get("autostart", False),
                levels=levels or [l for l in DEFAULT_LEVELS],
            )
        except Exception:
            return cls()
