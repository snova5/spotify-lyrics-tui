# spotify-lyrics-tui

Animated, synced lyrics for whatever you're playing on Spotify — right in your terminal, with a live audio visualizer in the background.

Built for Fedora (works on most Linux desktops with MPRIS and PipeWire/PulseAudio).

## Features

- **Synced lyrics** fetched automatically from [LRCLIB](https://lrclib.net) — free, no account or API key
- **Karaoke fill** on the current line with a shimmering green → cyan → pink gradient
- **Big text**: the current line is drawn in large block letters, as big as your terminal allows
- **Audio visualizer** in the background, reacting to the real system audio via [cava](https://github.com/karlstav/cava) (falls back to a simulated one if cava isn't installed)
- Smooth scrolling, fading past lines, typewriter title, animated equalizer, breathing dots during instrumental breaks
- Progress bar, pause indicator, unsynced-lyrics fallback, instrumental detection
- Handles diacritics, CJK and emoji widths correctly
- Single file, pure Python standard library — no pip packages

## Requirements

- Python 3.8+
- [`playerctl`](https://github.com/altdesktop/playerctl) — reads what Spotify is playing
- [`cava`](https://github.com/karlstav/cava) *(optional)* — for a real audio visualizer
- A terminal with truecolor support (GNOME Terminal, Konsole, Kitty, Alacritty, WezTerm, …)
- The Spotify desktop app (native or Flatpak)

### Fedora

```bash
sudo dnf install playerctl cava
```

### Debian / Ubuntu

```bash
sudo apt install playerctl cava
```

### Arch

```bash
sudo pacman -S playerctl cava
```

## Usage

```bash
git clone https://github.com/<your-username>/spotify-lyrics-tui.git
cd spotify-lyrics-tui
python3 spotify_lyrics.py
```

Start playing something in Spotify. Press **Ctrl+C** to quit.

### Options

| Option | What it does |
|---|---|
| `--small-text` | Show the current line at normal size instead of big block letters |
| `--no-visualizer` | Turn off the background audio visualizer |

Want everything bigger? Zoom your terminal (`Ctrl+Shift++` in GNOME Terminal / Kitty, `Ctrl++` in Konsole) — the layout adapts automatically.

## How it works

1. `playerctl` reads the current track, position and play state from Spotify over MPRIS (D-Bus).
2. Lyrics are fetched from the LRCLIB API in a background thread and parsed from LRC format.
3. Between polls, the playback position is interpolated so animations stay smooth at 30 FPS.
4. `cava` captures system audio through PipeWire (or PulseAudio) and streams bar heights to the script.
5. Everything is composited on a cell canvas (visualizer underneath, lyrics on top) and drawn with 24-bit ANSI colors in the terminal's alternate screen.

## Troubleshooting

- **"Spotify is not running or nothing is playing"** — check that `playerctl -p spotify metadata` prints something.
- **Visualizer doesn't react to music** — make sure `cava` works on its own by running `cava` in a terminal.
- **No lyrics found** — LRCLIB is community-driven; you can [contribute lyrics](https://lrclib.net) for missing songs.
- **Colors look wrong** — your terminal probably doesn't support truecolor.

## Contributing

Issues and pull requests are welcome! Ideas: other players (any MPRIS player works by changing `PLAYER`), themes, a GUI overlay mode.

## Credits

- Lyrics by [LRCLIB](https://lrclib.net)
- Audio analysis by [cava](https://github.com/karlstav/cava)

This project is not affiliated with, endorsed by, or sponsored by Spotify.

## License

[MIT](LICENSE)
