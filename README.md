# spotify-lyrics-tui

Animated, synced lyrics for whatever you're playing on Spotify — right in your terminal, with a live audio visualizer in the background.

Works on Linux (built on Fedora, also Debian/Ubuntu, Arch, Gentoo and LFS) and on Windows 10 and 11.

## Features

- **Synced lyrics** fetched automatically from [LRCLIB](https://lrclib.net) — free, no account or API key
- **Karaoke fill** on the current line with a shimmering green → cyan → pink gradient
- **Big text**: the current line is drawn in large block letters, as big as your terminal allows
- **Audio visualizer** in the background, reacting to the real system audio via [cava](https://github.com/karlstav/cava) (falls back to a simulated one if cava isn't installed)
- Smooth scrolling, fading past lines, typewriter title, animated equalizer, breathing dots during instrumental breaks
- Progress bar, pause indicator, unsynced-lyrics fallback, instrumental detection
- Handles diacritics, CJK and emoji widths correctly
- Single file, pure Python standard library on Linux — no pip packages

## Requirements (Linux)

Using Windows? Skip to [Windows 10 / 11](#windows-10--11).

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

### Gentoo

```bash
echo "media-sound/cava pipewire" | sudo tee /etc/portage/package.use/cava
sudo emerge --ask media-sound/playerctl media-sound/cava
```

Full guide, including Spotify and the PulseAudio option: [docs/gentoo.md](docs/gentoo.md)

### Linux From Scratch

Build playerctl and cava from source with their BLFS dependencies. Step-by-step guide: [docs/lfs.md](docs/lfs.md)

## Usage

```bash
git clone https://github.com/snova5/spotify-lyrics-tui.git
cd spotify-lyrics-tui
./install.sh
```

Then open it from any terminal with:

```bash
spotifylyr
```

Start playing something in Spotify. Press **Ctrl+C** to quit.

The installer copies the script to `~/.local/share/spotifylyr` and adds the `spotifylyr` command to `~/.local/bin`. No root needed. To update, `git pull` and run `./install.sh` again. To remove it:

```bash
./install.sh --uninstall
```

You can also run it without installing: `python3 spotify_lyrics.py`.

### Options

| Option | What it does |
|---|---|
| `--small-text` | Show the current line at normal size instead of big block letters |
| `--no-visualizer` | Turn off the background audio visualizer |

Example: `spotifylyr --small-text`

Want everything bigger? Zoom your terminal (`Ctrl+Shift++` in GNOME Terminal / Kitty, `Ctrl++` in Konsole) — the layout adapts automatically.

## Windows 10 / 11

### What you need

- **Python 3.9 or newer** from [python.org](https://www.python.org/downloads/). In the installer, check **"Add python.exe to PATH"**.
- **Windows Terminal**. It comes with Windows 11; on Windows 10 install it from the Microsoft Store. The old console window can't show some of the characters the app uses.
- **The Spotify desktop app**, either from spotify.com or from the Microsoft Store. The web player in a browser is not detected.

You don't need playerctl or cava on Windows.

### Install

Download the repo with `git clone https://github.com/snova5/spotify-lyrics-tui.git`, or with **Code → Download ZIP** on GitHub and extract it.

Then double-click **`install.cmd`** in the folder, or run it from a terminal:

```bat
cd spotify-lyrics-tui
install.cmd
```

The installer:

1. finds your Python
2. installs the Python packages from `requirements-windows.txt`
3. copies the app to `%LOCALAPPDATA%\spotifylyr`
4. adds the `spotifylyr` command to your user PATH. No administrator rights needed.

Open a **new** terminal window and run:

```bat
spotifylyr
```

The same options work: `spotifylyr --small-text`, `spotifylyr --no-visualizer`.

To update, download the new version and run `install.cmd` again. To remove it:

```bat
install.cmd -Uninstall
```

### Python packages used on Windows

| Package | Why |
|---|---|
| `winrt-Windows.Media.Control` (+ `Foundation`, `Foundation.Collections`) | Reads what Spotify is playing from Windows' media controls |
| `soundcard`, `numpy` | Capture the sound going to your speakers for the visualizer |

Without `soundcard` and `numpy` the visualizer is simulated. The visualizer shows whatever plays on your default output device.

## How it works

1. **Linux:** `playerctl` reads the current track, position and play state from Spotify over MPRIS (D-Bus). **Windows:** the same information comes from the Global System Media Transport Controls, the media controls Windows shows in the volume popup.
2. Lyrics are fetched from the LRCLIB API in a background thread and parsed from LRC format.
3. Between polls, the playback position is interpolated so animations stay smooth at 30 FPS.
4. **Linux:** `cava` captures system audio through PipeWire (or PulseAudio) and streams bar heights to the script. **Windows:** `soundcard` records the speaker output through WASAPI loopback, and the script turns it into bars with an FFT.
5. Everything is composited on a cell canvas (visualizer underneath, lyrics on top) and drawn with 24-bit ANSI colors in the terminal's alternate screen.

## Troubleshooting

- **"Spotify is not running or nothing is playing"** — check that `playerctl -p spotify metadata` prints something.
- **Visualizer doesn't react to music** — make sure `cava` works on its own by running `cava` in a terminal.
- **No lyrics found** — LRCLIB is community-driven; you can [contribute lyrics](https://lrclib.net) for missing songs.
- **Colors look wrong** — your terminal probably doesn't support truecolor.
- **Windows: `spotifylyr` is not recognized** — open a new terminal window after installing, so it picks up the new PATH.
- **Windows: boxes instead of some symbols** — use Windows Terminal instead of the old console window.
- **Windows: install.cmd says Python was not found** — install Python from python.org with "Add python.exe to PATH" checked, then run install.cmd again.

## Contributing

Issues and pull requests are welcome! Ideas: other players (any MPRIS player works by changing `PLAYER`), themes, a GUI overlay mode.

## Credits

- Lyrics by [LRCLIB](https://lrclib.net)
- Audio analysis by [cava](https://github.com/karlstav/cava)

This project is not affiliated with, endorsed by, or sponsored by Spotify.

## License

[MIT](LICENSE)
