#!/usr/bin/env python3
"""
hydration-reminder: entry point.

  python main.py           → open settings TUI
  python main.py --daemon  → run background daemon
"""
import sys


def main() -> None:
    if "--daemon" in sys.argv:
        from src.daemon import HydrationDaemon
        HydrationDaemon().run()
    else:
        from src.tui import HydrationTUI
        HydrationTUI().run()


if __name__ == "__main__":
    main()
