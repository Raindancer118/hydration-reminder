from __future__ import annotations
import logging
import os
import signal
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    import dbus
    from dbus.mainloop.glib import DBusGMainLoop
    from gi.repository import GLib
except ImportError:
    print("Missing system packages. Install with:", file=sys.stderr)
    print("  sudo pacman -S python-dbus python-gobject", file=sys.stderr)
    sys.exit(1)

from .config import Config, LevelConfig
from .state import State, DATA_DIR, PID_FILE, LOG_FILE


class HydrationDaemon:
    def __init__(self) -> None:
        DBusGMainLoop(set_as_default=True)
        self.loop = GLib.MainLoop()
        self.config = Config.load()
        self.state = State.load()
        self._current_notif_id: int = 0
        self._action_handled: bool = False
        self._pending: bool = False
        self._setup_logging()
        self._setup_dbus()

    def _setup_logging(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            filename=str(LOG_FILE),
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
        )
        self.log = logging.getLogger("hydration")

    def _setup_dbus(self) -> None:
        self.bus = dbus.SessionBus()
        proxy = self.bus.get_object("org.freedesktop.Notifications", "/org/freedesktop/Notifications")
        self._notify = dbus.Interface(proxy, "org.freedesktop.Notifications")
        self.bus.add_signal_receiver(self._on_action_invoked,    "ActionInvoked",        "org.freedesktop.Notifications")
        self.bus.add_signal_receiver(self._on_notification_closed, "NotificationClosed", "org.freedesktop.Notifications")

    # ── PID management ────────────────────────────────────────────────

    def _write_pid(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        PID_FILE.write_text(str(os.getpid()))

    def _cleanup(self) -> None:
        PID_FILE.unlink(missing_ok=True)

    # ── Scheduling ────────────────────────────────────────────────────

    def _time_until_next(self) -> float:
        self.state.check_pause_expired()
        idx = min(self.state.annoyance_level, len(self.config.levels) - 1)
        interval = self.config.levels[idx].interval
        if self.state.last_reminder is None:
            return float(interval)
        elapsed = (datetime.now() - datetime.fromisoformat(self.state.last_reminder)).total_seconds()
        return max(0.0, interval - elapsed)

    def _reschedule(self) -> None:
        wait = self._time_until_next()
        ms = max(500, int(wait * 1000))
        self.log.debug(f"Next reminder in {wait:.1f}s")
        GLib.timeout_add(ms, self._tick)

    def _tick(self) -> bool:
        self.state = State.load()
        self.state.check_pause_expired()
        self.state.save()

        if self.state.enabled and not self.state.paused and not self._pending:
            if self._time_until_next() <= 0:
                self._send_reminder()
                return False

        self._reschedule()
        return False

    # ── Sending reminders ─────────────────────────────────────────────

    def _send_reminder(self) -> None:
        idx = min(self.state.annoyance_level, len(self.config.levels) - 1)
        level = self.config.levels[idx]

        self.state.last_reminder = datetime.now().isoformat()
        self.state.save()
        self._pending = True

        self.log.info(f"Reminder level {idx} ({level.type})")

        if level.type == "notification":
            self._send_dbus_notification(level)
        else:
            self._run_blocker(level)

    def _send_dbus_notification(self, level: LevelConfig) -> None:
        hints: dict = {"urgency": dbus.Byte(level.urgency)}
        notif_id = self._notify.Notify(
            "Hydration Reminder", 0, "dialog-information",
            level.title, level.message,
            ["done", "Done! 💧", "pause", "Pause ⏸"],
            hints, 30000,
        )
        self._current_notif_id = int(notif_id)
        self._action_handled = False

    def _run_blocker(self, level: LevelConfig) -> None:
        blocker = Path(__file__).parent / "blocker.py"
        proc = subprocess.Popen([sys.executable, str(blocker), level.type, level.title, level.message])

        def poll() -> bool:
            code = proc.poll()
            if code is None:
                return True  # still running
            self._pending = False
            self.state = State.load()
            if code == 0:
                self.state.mark_drink()
                self.log.info("Drink confirmed (blocker)")
            elif code == 1:
                self.state.mark_paused()
                self.log.info("Paused (blocker)")
            else:
                self.state.mark_dismissed(max_level=len(self.config.levels) - 1)
                self.log.info(f"Dismissed → level {self.state.annoyance_level}")
            self.state.save()
            self._reschedule()
            return False

        GLib.timeout_add(500, poll)

    # ── DBus signal handlers ──────────────────────────────────────────

    def _on_action_invoked(self, notif_id: int, action_key: str) -> None:
        if int(notif_id) != self._current_notif_id:
            return
        self._action_handled = True
        self._pending = False
        self.state = State.load()

        if action_key == "done":
            self.state.mark_drink()
            self.log.info("Drink confirmed (notification)")
        elif action_key == "pause":
            self.state.mark_paused()
            self.log.info("Paused (notification)")

        self.state.save()
        self._reschedule()

    def _on_notification_closed(self, notif_id: int, reason: int) -> None:
        if int(notif_id) != self._current_notif_id:
            return
        if self._action_handled:
            return

        self._pending = False
        self.state = State.load()

        if int(reason) == 2:  # explicitly dismissed by user
            self.state.mark_dismissed(max_level=len(self.config.levels) - 1)
            self.log.info(f"Dismissed → level {self.state.annoyance_level}")
            self.state.save()
        # reason 1 = timeout (AFK) → no escalation, no save needed

        self._reschedule()

    # ── Main loop ─────────────────────────────────────────────────────

    def run(self) -> None:
        self._write_pid()
        GLib.unix_signal_add(GLib.PRIORITY_HIGH, signal.SIGHUP,  self._on_sighup)
        GLib.unix_signal_add(GLib.PRIORITY_HIGH, signal.SIGTERM, self._on_sigterm)
        GLib.unix_signal_add(GLib.PRIORITY_HIGH, signal.SIGINT,  self._on_sigterm)

        self.log.info(f"Daemon started (PID {os.getpid()})")
        # Anchor the countdown from startup so the TUI shows a live timer immediately
        if self.state.last_reminder is None:
            self.state.last_reminder = datetime.now().isoformat()
            self.state.save()
        self._reschedule()
        try:
            self.loop.run()
        finally:
            self._cleanup()
            self.log.info("Daemon stopped")

    def _on_sighup(self) -> bool:
        self.config = Config.load()
        self.state = State.load()
        self.log.info("Reloaded config/state")
        return True  # keep GLib signal source active

    def _on_sigterm(self) -> bool:
        self.loop.quit()
        return True
