from __future__ import annotations
import os
import signal
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Button, Footer, Input, Label, Static, Switch
from textual import on

from .config import Config
from .state import State


# ── helpers ───────────────────────────────────────────────────────────────────

MOOD_LABELS = [
    "😌 Chill",
    "🙂 Gentle",
    "😐 Concerned",
    "😤 Annoyed",
    "😠 Very Annoyed",
    "🤬 FURIOUS",
    "☠️  MAXIMUM",
]


def _mins_ago(iso: str | None) -> str:
    if iso is None:
        return "never"
    delta = (datetime.now() - datetime.fromisoformat(iso)).total_seconds()
    m = int(delta / 60)
    s = int(delta % 60)
    return f"{m}m {s}s ago" if m else f"{s}s ago"


def _countdown(state: State, config: Config) -> str:
    if state.paused:
        return "paused"
    idx = min(state.annoyance_level, len(config.levels) - 1)
    interval = config.levels[idx].interval
    ref = state.last_reminder or state.last_drink
    if ref is None:
        return f"{interval // 60}m 0s"
    elapsed = (datetime.now() - datetime.fromisoformat(ref)).total_seconds()
    remaining = max(0.0, interval - elapsed)
    m, s = int(remaining / 60), int(remaining % 60)
    return f"{m}m {s}s"


# ── TUI ───────────────────────────────────────────────────────────────────────

CSS = """
Screen {
    background: #061a2e;
    color: #c8e8ff;
}

#app-title {
    text-align: center;
    color: #5bc8fa;
    text-style: bold;
    padding: 1 2;
    background: #061a2e;
}

.panel {
    border: solid #1a4a7a;
    border-title-color: #5bc8fa;
    border-title-style: bold;
    margin: 0 1 1 1;
    padding: 1 2;
    background: #0a2540;
}

.row {
    height: 1;
    margin-bottom: 1;
}

.lbl {
    color: #4a8ab0;
    width: 20;
}

.val {
    color: #c8e8ff;
    text-style: bold;
}

.accent {
    color: #5bc8fa;
    text-style: bold;
}

Button {
    margin: 0 1 0 0;
    min-width: 16;
}

Button.primary   { background: #0a5eb5; color: white; }
Button.muted     { background: #1a3a5c; color: #7aaad0; }
Button.danger    { background: #5a1010; color: #ff9999; }

.spacer { height: 1; }

#pane-controls Button { width: 100%; margin-bottom: 0; }

Input {
    background: #0a2540;
    border: solid #1a4a7a;
    color: #c8e8ff;
    width: 10;
}

Switch {
    background: #0a2540;
}

#split {
    height: auto;
}

#pane-status {
    width: 1fr;
}

#pane-controls {
    width: 1fr;
}
"""


class HydrationTUI(App):
    CSS = CSS

    BINDINGS = [
        Binding("d", "drink",        "I drank!"),
        Binding("p", "pause",        "Pause"),
        Binding("r", "resume",       "Resume"),
        Binding("R", "reset_level",  "Reset level"),
        Binding("q", "quit",         "Quit"),
    ]

    _state: reactive[State] = reactive(State.load, recompose=False)
    _config: Config = Config.load()

    def compose(self) -> ComposeResult:
        yield Static("💧  Hydration Reminder", id="app-title")

        with Horizontal(id="split"):
            with Container(id="pane-status", classes="panel") as c:
                c.border_title = "Status"
                yield Static(id="status-text")

            with Container(id="pane-controls", classes="panel") as c:
                c.border_title = "Controls"
                yield Button("✅  I drank!",       id="btn-drink",  classes="primary")
                yield Button("⏸  Pause",           id="btn-pause",  classes="muted")
                yield Button("▶  Resume",          id="btn-resume", classes="muted")
                yield Button("🔄 Reset level",     id="btn-reset",  classes="muted")
                yield Static(" ", classes="spacer")
                yield Button("▶  Start daemon",   id="btn-start",  classes="primary")
                yield Button("⏹  Stop daemon",    id="btn-stop",   classes="danger")

        with Container(classes="panel") as c:
            c.border_title = "Settings"
            with Horizontal(classes="row"):
                yield Label("Base interval (min)", classes="lbl")
                yield Input(
                    value=str(self._config.base_interval // 60),
                    id="input-interval",
                    restrict=r"[0-9]*",
                )
            with Horizontal(classes="row"):
                yield Label("Auto-start", classes="lbl")
                yield Switch(value=self._config.autostart, id="switch-autostart")

        yield Footer()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def on_mount(self) -> None:
        self._refresh_status()
        self.set_interval(1, self._tick)

    def _tick(self) -> None:
        self._state = State.load()
        self._refresh_status()

    def _refresh_status(self) -> None:
        s = self._state
        c = self._config
        pid = s.get_daemon_pid()

        daemon_str  = f"[green]● Running (PID {pid})[/]" if pid else "[red]○ Stopped[/]"
        status_str  = "[yellow]Paused[/]" if s.paused else ("[green]Active[/]" if s.enabled else "[red]Disabled[/]")
        max_level   = len(c.levels) - 1
        lvl         = min(s.annoyance_level, max_level)
        bar         = "█" * lvl + "░" * (max_level - lvl)
        mood        = MOOD_LABELS[min(lvl, len(MOOD_LABELS) - 1)]
        next_str    = _countdown(s, c)
        drink_str   = _mins_ago(s.last_drink)

        text = (
            f"[b]Daemon:[/b]      {daemon_str}\n"
            f"[b]Status:[/b]      {status_str}\n"
            f"[b]Last drink:[/b]  [#5bc8fa]{drink_str}[/]\n"
            f"[b]Next:[/b]        [#5bc8fa]{next_str}[/]\n"
            f"[b]Level:[/b]       [#5bc8fa]{bar}[/] {lvl}/{max_level}\n"
            f"[b]Mood:[/b]        {mood}"
        )
        self.query_one("#status-text", Static).update(text)

    # ── Core actions (called by both buttons and keybindings) ─────────────────

    def _do_drink(self) -> None:
        s = State.load()
        s.mark_drink()
        s.save()
        self._state = s
        self._signal_daemon()
        self.notify("Stay hydrated! 💧")

    def _do_pause(self) -> None:
        s = State.load()
        s.mark_paused()
        s.save()
        self._state = s
        self._signal_daemon()
        self.notify("Reminders paused.")

    def _do_resume(self) -> None:
        s = State.load()
        s.mark_resumed()
        s.save()
        self._state = s
        self._signal_daemon()
        self.notify("Reminders resumed!")

    def _do_reset_level(self) -> None:
        s = State.load()
        s.annoyance_level = 0
        s.save()
        self._state = s
        self._signal_daemon()
        self.notify("Annoyance level reset.")

    # ── Button handlers ───────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-drink")
    def _btn_drink(self) -> None:
        self._do_drink()

    @on(Button.Pressed, "#btn-pause")
    def _btn_pause(self) -> None:
        self._do_pause()

    @on(Button.Pressed, "#btn-resume")
    def _btn_resume(self) -> None:
        self._do_resume()

    @on(Button.Pressed, "#btn-reset")
    def _btn_reset(self) -> None:
        self._do_reset_level()

    @on(Button.Pressed, "#btn-start")
    def _start_daemon(self) -> None:
        if State.load().get_daemon_pid():
            self.notify("Daemon is already running.")
            return
        # Use the hydration binary from the same venv as this process
        hydration_bin = Path(sys.executable).parent / "hydration"
        cmd = (
            [str(hydration_bin), "--daemon"]
            if hydration_bin.exists()
            else [sys.executable, str(Path(__file__).parent.parent / "main.py"), "--daemon"]
        )
        subprocess.Popen(cmd, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.set_timer(0.5, self._tick)
        self.notify("Daemon started.")

    @on(Button.Pressed, "#btn-stop")
    def _stop_daemon(self) -> None:
        pid = State.load().get_daemon_pid()
        if not pid:
            self.notify("Daemon is not running.")
            return
        os.kill(pid, signal.SIGTERM)
        self.set_timer(0.5, self._tick)
        self.notify("Daemon stopped.")

    # ── Settings changes ──────────────────────────────────────────────────────

    @on(Input.Changed, "#input-interval")
    def _on_interval(self, event: Input.Changed) -> None:
        try:
            mins = int(event.value)
            if mins < 1:
                return
            self._config.base_interval = mins * 60
            self._config.levels[0].interval = mins * 60
            self._config.save()
        except ValueError:
            pass

    @on(Switch.Changed, "#switch-autostart")
    def _on_autostart(self, event: Switch.Changed) -> None:
        self._config.autostart = event.value
        self._config.save()
        self._apply_autostart(event.value)
        self.notify(f"Auto-start {'enabled' if event.value else 'disabled'}.")

    # ── Keybinding actions ────────────────────────────────────────────────────

    def action_drink(self) -> None:
        self._do_drink()

    def action_pause(self) -> None:
        self._do_pause()

    def action_resume(self) -> None:
        self._do_resume()

    def action_reset_level(self) -> None:
        self._do_reset_level()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _signal_daemon(self) -> None:
        pid = State.load().get_daemon_pid()
        if pid:
            os.kill(pid, signal.SIGHUP)

    def _apply_autostart(self, enabled: bool) -> None:
        autostart_dir = Path.home() / ".config" / "autostart"
        desktop_file  = autostart_dir / "hydration-reminder.desktop"
        main_py = Path(__file__).parent.parent / "main.py"

        if enabled:
            autostart_dir.mkdir(parents=True, exist_ok=True)
            desktop_file.write_text(
                "[Desktop Entry]\n"
                "Type=Application\n"
                "Name=Hydration Reminder\n"
                f"Exec={sys.executable} {main_py} --daemon\n"
                "Hidden=false\n"
                "X-KDE-autostart-enabled=true\n"
            )
        else:
            desktop_file.unlink(missing_ok=True)
