"""
Full-screen / modal blocker window for high annoyance levels.

Usage: python blocker.py <type> <title> <message>
  type: "modal" | "fullscreen"

Exit codes:
  0 = Done (user drank)
  1 = Pause (stop reminding)
  2 = fallback / error
"""
from __future__ import annotations
import sys
import tkinter as tk
from tkinter import font as tkfont


def run(btype: str, title: str, message: str) -> None:
    root = tk.Tk()
    root.title("Hydration Reminder")

    is_fullscreen = btype == "fullscreen"

    if is_fullscreen:
        root.attributes("-fullscreen", True)
        root.attributes("-topmost", True)
        root.overrideredirect(True)
        bg, fg = "#0a1628", "#c8e8ff"
        msg_size = 56
        pad = 60
    else:
        root.attributes("-topmost", True)
        w, h = 520, 340
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        root.resizable(False, False)
        bg, fg = "#0d2137", "#c8e8ff"
        msg_size = 22
        pad = 30

    root.configure(bg=bg)
    root.protocol("WM_DELETE_WINDOW", lambda: None)

    result: list[int] = [2]

    frame = tk.Frame(root, bg=bg)
    frame.pack(expand=True, fill="both", padx=pad, pady=pad)

    tk.Label(
        frame, text=title,
        font=tkfont.Font(family="monospace", size=13, weight="bold"),
        bg=bg, fg="#5bc8fa",
    ).pack(pady=(0, 16))

    tk.Label(
        frame, text=message,
        font=tkfont.Font(family="monospace", size=msg_size, weight="bold"),
        bg=bg, fg=fg,
        wraplength=root.winfo_screenwidth() - 120 if is_fullscreen else 460,
        justify="center",
    ).pack(expand=True)

    btn_frame = tk.Frame(frame, bg=bg)
    btn_frame.pack(pady=28)

    btn_font = tkfont.Font(family="monospace", size=15 if is_fullscreen else 11, weight="bold")

    def done() -> None:
        result[0] = 0
        root.destroy()

    def pause() -> None:
        result[0] = 1
        root.destroy()

    tk.Button(
        btn_frame, text="Done! 💧", command=done,
        font=btn_font, bg="#0a5eb5", fg="white",
        relief="flat", padx=28, pady=10, cursor="hand2",
        activebackground="#0d80e0", activeforeground="white",
    ).pack(side="left", padx=12)

    tk.Button(
        btn_frame, text="Stop reminding me ⏸", command=pause,
        font=btn_font, bg="#1a3a5c", fg="#7aaad0",
        relief="flat", padx=28, pady=10, cursor="hand2",
        activebackground="#2a5080", activeforeground="#c8e8ff",
    ).pack(side="left", padx=12)

    root.bind("<Return>", lambda _: done())
    root.bind("<Escape>", lambda _: None)
    root.focus_force()
    root.lift()

    root.mainloop()
    sys.exit(result[0])


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(2)
    run(sys.argv[1], sys.argv[2], sys.argv[3])
