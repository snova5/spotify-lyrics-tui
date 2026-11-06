# Installing on Linux From Scratch

On LFS you build `playerctl` and `cava` from source. Most of what they need comes from the base LFS book and from [BLFS](https://www.linuxfromscratch.org/blfs/). Run the `make install` and `ninja install` steps as root.

## What you need first

From the LFS book (already on your system after chapter 8):

- Python 3, Meson, Ninja, Autoconf, Automake, Libtool, pkgconf

From BLFS:

| Package | Why |
|---|---|
| make-ca | CA certificates. Without them Python can't connect to the lyrics server over HTTPS, and every song shows "No lyrics found". |
| Git | To download the sources |
| GLib | Needed by playerctl |
| D-Bus | playerctl talks to Spotify over the D-Bus session bus |
| CMake | To build iniparser |
| FFTW | Needed by cava |
| PipeWire or PulseAudio | So cava can read your system audio |

A desktop such as KDE Plasma or Xfce from BLFS already pulls in GLib and D-Bus.

Install PipeWire or PulseAudio before you build cava. cava's configure script only builds the audio backends it finds.

## 1. FFTW

Follow the [BLFS FFTW page](https://www.linuxfromscratch.org/blfs/view/stable/general/fftw.html). cava uses the double precision build, which is the first of the three builds on that page.

## 2. iniparser

cava reads its config with iniparser, which is not in BLFS:

```bash
git clone https://github.com/ndevilla/iniparser.git
cd iniparser
mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Release ..
make
```

As root:

```bash
make install
```

## 3. cava

```bash
git clone https://github.com/karlstav/cava.git
cd cava
./autogen.sh
./configure --prefix=/usr
make
```

As root:

```bash
make install
```

If `configure` says it can't find iniparser, the header was installed in a subfolder. Run it again like this:

```bash
CPPFLAGS="-I/usr/include/iniparser" ./configure --prefix=/usr
```

## 4. playerctl

```bash
git clone https://github.com/altdesktop/playerctl.git
cd playerctl
meson setup build --prefix=/usr --buildtype=release -Dintrospection=false -Dgtk-doc=false
ninja -C build
```

As root:

```bash
ninja -C build install
```

The two options turn off GObject introspection and the documentation, so you don't need gobject-introspection or gtk-doc.

## 5. spotify-lyrics-tui

As your normal user:

```bash
git clone https://github.com/snova5/spotify-lyrics-tui.git
cd spotify-lyrics-tui
./install.sh
```

Then open it with:

```bash
spotifylyr
```

If the installer says `~/.local/bin` is not in your PATH, run the line it prints. On LFS your `~/.bashrc` doesn't add that folder by default.

## Spotify

Spotify is not in BLFS. Install it whatever way you prefer, for example with Flatpak. Both the Flatpak and the native app work, as long as `playerctl -p spotify metadata` shows the current song.

## Checking that it works

- `playerctl -p spotify metadata` should print the current song while Spotify is playing.
- `cava` on its own should show bars that move with the music.
- `python3 -c "import urllib.request; urllib.request.urlopen('https://lrclib.net')"` should print nothing. If it prints an SSL certificate error, install make-ca.

If `playerctl` says "No players found" and you started the terminal outside your desktop session (for example from a TTY), there is no D-Bus session bus. Start Spotify and spotifylyr from inside your desktop session.

## Init system

Nothing here runs as a service, so it works the same on SysVinit, OpenRC and systemd.
