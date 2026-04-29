# Design: Hydration Reminder

## Direction: Calm Water

Ruhige, ozeanische Ästhetik. Der Kontrast zum eskalierenden Inhalt ist bewusst.

## Farbpalette

| Token          | Hex       | Verwendung                    |
|----------------|-----------|-------------------------------|
| `ocean-deep`   | `#061a2e` | Hintergrund                   |
| `ocean-mid`    | `#0a2540` | Panel-Hintergründe            |
| `ocean-border` | `#1a4a7a` | Rahmen, Struktur              |
| `sky-reflect`  | `#5bc8fa` | Akzent, Titel, Highlights     |
| `foam`         | `#c8e8ff` | Haupttext                     |
| `deep-muted`   | `#4a8ab0` | Labels, sekundärer Text       |
| `btn-primary`  | `#0a5eb5` | Done-Button                   |
| `btn-muted`    | `#1a3a5c` | Pause/Reset-Buttons           |
| `danger`       | `#8b1a1a` | Stop-Daemon                   |

## Eskalationsstufen

| Level | Intervall | Typ          | Ton                          |
|-------|-----------|--------------|------------------------------|
| 0     | 30 min    | Notification | Freundlich                   |
| 1     | 10 min    | Notification | Sanft mahnend                |
| 2     | 5 min     | Notification | Besorgt                      |
| 3     | 3 min     | Notification | Direkt/Fordernd              |
| 4     | 2 min     | Modal        | Aggressiv                    |
| 5     | 1 min     | Modal        | Sehr aggressiv               |
| 6     | 1 min     | Fullscreen   | Vollbild-Block               |

## TUI Layout

```
╔══════════════════════════════════════════════╗
║        💧  Hydration Reminder               ║
╠═══════════════════╦══════════════════════════╣
║ Status            ║ Controls                ║
║ ─────────────     ║ ──────────────────────  ║
║ Daemon: ● Running ║  [✅ I drank!]          ║
║ Last drink: 5m    ║  [⏸ Pause] [▶ Resume]  ║
║ Next: in 25m 10s  ║  [🔄 Reset Level]       ║
║ Level: ████░░ 4/6 ║                         ║
║ Mood: 😤 Annoyed  ║                         ║
╠═══════════════════╩══════════════════════════╣
║ Settings                                     ║
║ ─────────────────────────────────────────── ║
║  Base interval (min):  [30    ]             ║
║  Auto-start:           [ ON ]               ║
╠══════════════════════════════════════════════╣
║ d:Drink  p:Pause  r:Resume  R:Reset  q:Quit ║
╚══════════════════════════════════════════════╝
```

## Blocker-Fenster (Modal/Fullscreen)

- Hintergrund: `#0a1628`
- Riesiger Text in Foam-Weiß
- Nur zwei Buttons: **Done! 💧** und **Stop reminding me ⏸**
- Fullscreen: `overrideredirect`, immer im Vordergrund
