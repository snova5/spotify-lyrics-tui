# Installing on Gentoo

Everything spotify-lyrics-tui needs is in the main Gentoo repository. Python is already on every Gentoo system, because Portage depends on it.

## 1. Choose the audio backend for cava

cava needs one audio backend to read your system sound. Enable the one your desktop uses.

For PipeWire (the default on most current desktops):

```bash
echo "media-sound/cava pipewire" | sudo tee /etc/portage/package.use/cava
```

For PulseAudio:

```bash
echo "media-sound/cava pulseaudio" | sudo tee /etc/portage/package.use/cava
```

If `/etc/portage/package.use` is a file instead of a folder on your system, append the line to that file instead.

## 2. Install the dependencies

```bash
sudo emerge --ask media-sound/playerctl media-sound/cava dev-vcs/git
```

cava is optional. Without it the visualizer is simulated and does not follow the music.

## 3. Install Spotify (if you don't have it yet)

The Spotify client is in the repository as `media-sound/spotify`. It has its own license, which Portage asks you to accept:

```bash
echo "media-sound/spotify Spotify" | sudo tee /etc/portage/package.license/spotify
sudo emerge --ask media-sound/spotify
```

If `/etc/portage/package.license` is a file, append the line to it instead.

## 4. Install spotify-lyrics-tui

```bash
git clone https://github.com/snova5/spotify-lyrics-tui.git
cd spotify-lyrics-tui
./install.sh
```

Then open it with:

```bash
spotifylyr
```

## Checking that it works

- `playerctl -p spotify metadata` should print the current song while Spotify is playing.
- `cava` on its own should show bars that move with the music.

If `playerctl` says "No players found", make sure Spotify is running in the same desktop session as your terminal. playerctl talks to Spotify over the D-Bus session bus, which your desktop session starts for you.

## Init system

Nothing here runs as a service, so it works the same on OpenRC and systemd.
