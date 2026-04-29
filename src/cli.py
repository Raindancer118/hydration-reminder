from __future__ import annotations
import os
import signal
import subprocess
import sys
from pathlib import Path

from .state import State

_MAIN = Path(__file__).parent.parent / "main.py"


def main() -> None:
    args = set(sys.argv[1:])

    if "--stop" in args:
        _stop()
    elif "--start" in args:
        _start()
    elif "--daemon" in args:
        from .daemon import HydrationDaemon
        HydrationDaemon().run()
    else:
        from .tui import HydrationTUI
        HydrationTUI().run()


def _stop() -> None:
    pid = State.load().get_daemon_pid()
    if pid:
        os.kill(pid, signal.SIGTERM)
        print(f"Daemon stopped (PID {pid}).")
    else:
        print("Daemon is not running.")
    sys.exit(0)


def _start() -> None:
    pid = State.load().get_daemon_pid()
    if pid:
        print(f"Daemon already running (PID {pid}).")
        sys.exit(0)

    proc = subprocess.Popen(
        [sys.executable, str(_MAIN), "--daemon"],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print(f"Daemon started (PID {proc.pid}).")
    sys.exit(0)
