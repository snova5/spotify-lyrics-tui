import bisect
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata
import urllib.parse
import urllib.request

PLAYER = "spotify"
API = "https://lrclib.net/api"
USER_AGENT = "spotify-lyrics-fedora/3.0"
FPS = 30
SYNC_INTERVAL = 0.5
CAVA_BARS = 80
VIS_HEIGHT = 0.7

ESC = "\033["
RESET = ESC + "0m"
ALT_ON = ESC + "?1049h"
ALT_OFF = ESC + "?1049l"
HIDE_CURSOR = ESC + "?25l"
SHOW_CURSOR = ESC + "?25h"

GREEN = (29, 185, 84)
CYAN = (40, 210, 230)
PINK = (230, 90, 200)
WHITE = (235, 235, 235)
GRAY = (130, 130, 130)
DARK = (55, 55, 55)
BG = (25, 25, 25)
TITLE = (130, 215, 255)
YELLOW = (240, 200, 90)

VIS_LOW = (10, 62, 36)
VIS_MID = (14, 62, 84)
VIS_HIGH = (70, 26, 82)
VIS_PEAK = (90, 170, 140)


def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def wave(x):
    return (math.sin(x) + 1) / 2


def shimmer(k, now):
    t = wave(k * 0.22 - now * 3.0)
    return mix(GREEN, CYAN, t) if t < 0.7 else mix(CYAN, PINK, (t - 0.7) / 0.3)


def vis_color(f):
    if f < 0.5:
        return mix(VIS_LOW, VIS_MID, f * 2)
    return mix(VIS_MID, VIS_HIGH, (f - 0.5) * 2)


def cwidth(ch):
    if unicodedata.combining(ch):
        return 0
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


def swidth(s):
    return sum(cwidth(c) for c in s)


def truncate(s, maxw):
    if swidth(s) <= maxw:
        return s
    out, w = "", 0
    for ch in s:
        if w + cwidth(ch) > maxw - 1:
            break
        out += ch
        w += cwidth(ch)
    return out + "…"


FONT_SRC = {
    "A": ".X./X.X/XXX/X.X/X.X", "B": "XX./X.X/XX./X.X/XX.", "C": ".XX/X../X../X../.XX",
    "D": "XX./X.X/X.X/X.X/XX.", "E": "XXX/X../XX./X../XXX", "F": "XXX/X../XX./X../X..",
    "G": ".XX/X../X.X/X.X/.XX", "H": "X.X/X.X/XXX/X.X/X.X", "I": "XXX/.X./.X./.X./XXX",
    "J": "..X/..X/..X/X.X/.X.", "K": "X.X/X.X/XX./X.X/X.X", "L": "X../X../X../X../XXX",
    "M": "X.X/XXX/XXX/X.X/X.X", "N": "XX./X.X/X.X/X.X/X.X", "O": ".X./X.X/X.X/X.X/.X.",
    "P": "XX./X.X/XX./X../X..", "Q": ".X./X.X/X.X/XX./.XX", "R": "XX./X.X/XX./X.X/X.X",
    "S": ".XX/X../.X./..X/XX.", "T": "XXX/.X./.X./.X./.X.", "U": "X.X/X.X/X.X/X.X/XXX",
    "V": "X.X/X.X/X.X/X.X/.X.", "W": "X.X/X.X/XXX/XXX/X.X", "X": "X.X/X.X/.X./X.X/X.X",
    "Y": "X.X/X.X/.X./.X./.X.", "Z": "XXX/..X/.X./X../XXX",
    "0": "XXX/X.X/X.X/X.X/XXX", "1": ".X./XX./.X./.X./XXX", "2": "XX./..X/.X./X../XXX",
    "3": "XX./..X/.X./..X/XX.", "4": "X.X/X.X/XXX/..X/..X", "5": "XXX/X../XX./..X/XX.",
    "6": ".XX/X../XXX/X.X/XXX", "7": "XXX/..X/.X./.X./.X.", "8": "XXX/X.X/XXX/X.X/XXX",
    "9": "XXX/X.X/XXX/..X/XX.",
    " ": ".../.../.../.../...", ".": ".../.../.../.../.X.", ",": ".../.../.../.X./X..",
    "!": ".X./.X./.X./.../.X.", "?": "XX./..X/.X./.../.X.", "'": ".X./.X./.../.../...",
    '"': "X.X/X.X/.../.../...", "-": ".../.../XXX/.../...", "(": "..X/.X./.X./.X./..X",
    ")": "X../.X./.X./.X./X..", ":": ".../.X./.../.X./...", ";": ".../.X./.../.X./X..",
    "&": ".X./X.X/.X./X.X/.XX", "/": "..X/..X/.X./X../X..", "+": ".../.X./XXX/.X./...",
    "*": ".../X.X/.X./X.X/...", "=": ".../XXX/.../XXX/...",
}
FONT = {k: v.split("/") for k, v in FONT_SRC.items()}
FONT_ALIASES = {
    "’": "'", "‘": "'", "´": "'", "`": "'", "“": '"', "”": '"', "„": '"',
    "–": "-", "—": "-", "…": ".", "¿": "?", "¡": "!",
}


def big_normalize(text):
    out = []
    for ch in " ".join(text.split()):
        ch = FONT_ALIASES.get(ch, ch)
        base = "".join(c for c in unicodedata.normalize("NFD", ch) if not unicodedata.combining(c)).upper()
        if len(base) != 1 or base not in FONT:
            return None
        out.append(base)
    return "".join(out)


def wrap_words(text, maxc):
    words, pos = [], 0
    for word in text.split(" "):
        words.append((pos, word))
        pos += len(word) + 1
    out, cur, cur_start = [], "", 0
    for start, word in words:
        while len(word) > maxc:
            if cur:
                out.append((cur_start, cur))
                cur = ""
            out.append((start, word[:maxc]))
            start += maxc
            word = word[maxc:]
        if not word:
            continue
        if not cur:
            cur_start, cur = start, word
        elif len(cur) + 1 + len(word) <= maxc:
            cur += " " + word
        else:
            out.append((cur_start, cur))
            cur_start, cur = start, word
    if cur:
        out.append((cur_start, cur))
    return out


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.ch = [[" "] * w for _ in range(h)]
        self.fg = [[None] * w for _ in range(h)]
        self.bg = [[None] * w for _ in range(h)]
        self.bold = [[False] * w for _ in range(h)]
        self.vis = [[False] * w for _ in range(h)]

    def cell(self, x, y, ch, color, bold=False):
        if not (0 <= y < self.h and 0 <= x < self.w):
            return x
        wid = cwidth(ch)
        if wid == 0:
            if x > 0 and self.ch[y][x - 1]:
                self.ch[y][x - 1] += ch
            return x
        if ch == " ":
            if self.vis[y][x]:
                self.ch[y][x] = " "
                self.vis[y][x] = False
            return x + 1
        if x + wid > self.w:
            return self.w
        self.ch[y][x] = ch
        self.fg[y][x] = color
        self.bold[y][x] = bold
        if wid == 2:
            self.ch[y][x + 1] = ""
        return x + wid

    def put(self, x, y, text, color, bold=False):
        for ch in text:
            x = self.cell(x, y, ch, color, bold)
        return x

    def put_centered(self, y, text, color, bold=False):
        text = truncate(text, self.w)
        return self.put(max(0, (self.w - swidth(text)) // 2), y, text, color, bold)

    def render(self):
        out = []
        for y in range(self.h):
            out.append(f"{ESC}{y + 1};1H")
            state = None
            for x in range(self.w):
                ch = self.ch[y][x]
                if ch == "":
                    continue
                st = (self.fg[y][x], self.bg[y][x], self.bold[y][x])
                if st != state:
                    code = "0"
                    if st[2]:
                        code += ";1"
                    if st[0]:
                        code += ";38;2;%d;%d;%d" % st[0]
                    if st[1]:
                        code += ";48;2;%d;%d;%d" % st[1]
                    out.append(ESC + code + "m")
                    state = st
                out.append(ch)
            out.append(RESET)
        return "".join(out)


def read_player():
    fmt = "{{status}}\t{{position}}\t{{mpris:length}}\t{{artist}}\t{{title}}\t{{album}}"
    try:
        out = subprocess.run(
            ["playerctl", "-p", PLAYER, "metadata", "--format", fmt],
            capture_output=True, text=True, timeout=2,
        )
    except subprocess.TimeoutExpired:
        return None
    if out.returncode != 0:
        return None
    parts = out.stdout.rstrip("\n").split("\t", 5)
    if len(parts) < 6 or not parts[4]:
        return None
    status, position, length, artist, title, album = parts

    def num(x):
        try:
            return int(x) / 1_000_000
        except ValueError:
            return 0.0

    return {
        "status": status,
        "position": num(position),
        "duration": num(length),
        "artist": artist,
        "title": title,
        "album": album,
    }


class Player:
    def __init__(self):
        self.track = None
        self.status = "Stopped"
        self._pos = 0.0
        self._pos_time = 0.0
        self._last_sync = 0.0

    def sync(self):
        now = time.monotonic()
        if now - self._last_sync < SYNC_INTERVAL:
            return
        self._last_sync = now
        info = read_player()
        if not info:
            self.track = None
            self.status = "Stopped"
            return
        self.track = {k: info[k] for k in ("artist", "title", "album", "duration")}
        self.status = info["status"]
        self._pos = info["position"]
        self._pos_time = time.monotonic()

    @property
    def position(self):
        if self.status == "Playing":
            return self._pos + (time.monotonic() - self._pos_time)
        return self._pos


IS_WINDOWS = sys.platform == "win32"


def setup_windows_console():
    try:
        import ctypes
        kernel = ctypes.windll.kernel32
        handle = kernel.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if kernel.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel.SetConsoleMode(handle, mode.value | 0x0004)
        kernel.SetConsoleOutputCP(65001)
    except Exception:
        pass
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def load_media_control():
    try:
        from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as manager
        return manager
    except ImportError:
        pass
    try:
        from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as manager
        return manager
    except ImportError:
        return None


def win_seconds(value):
    if value is None:
        return 0.0
    if hasattr(value, "total_seconds"):
        return value.total_seconds()
    if hasattr(value, "duration"):
        return value.duration / 10_000_000
    return float(value)


class WindowsPlayer:
    def __init__(self, manager_cls):
        self.track = None
        self.status = "Stopped"
        self._pos = 0.0
        self._pos_time = 0.0
        self._lock = threading.Lock()
        self._cls = manager_cls
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        import asyncio
        try:
            asyncio.run(self._loop())
        except Exception:
            pass

    async def _loop(self):
        import asyncio
        manager = await self._cls.request_async()
        while True:
            try:
                info = await self._read(manager)
            except Exception:
                info = None
            with self._lock:
                if info:
                    self.track = info["track"]
                    self.status = info["status"]
                    self._pos = info["position"]
                    self._pos_time = time.monotonic()
                else:
                    self.track = None
                    self.status = "Stopped"
            await asyncio.sleep(SYNC_INTERVAL)

    async def _read(self, manager):
        from datetime import datetime, timezone
        session = None
        for s in manager.get_sessions():
            if PLAYER in (s.source_app_user_model_id or "").lower():
                session = s
                break
        if session is None:
            return None
        props = await session.try_get_media_properties_async()
        if not props or not props.title:
            return None
        timeline = session.get_timeline_properties()
        playing = int(session.get_playback_info().playback_status) == 4
        pos = win_seconds(timeline.position)
        if playing:
            try:
                updated = timeline.last_updated_time
                if updated.tzinfo is None:
                    updated = updated.replace(tzinfo=timezone.utc)
                age = (datetime.now(timezone.utc) - updated).total_seconds()
                if 0 < age < 3600:
                    pos += age
            except Exception:
                pass
        duration = win_seconds(timeline.end_time) - win_seconds(timeline.start_time)
        return {
            "track": {
                "artist": props.artist or "",
                "title": props.title,
                "album": props.album_title or "",
                "duration": max(0.0, duration),
            },
            "status": "Playing" if playing else "Paused",
            "position": pos,
        }

    def sync(self):
        pass

    @property
    def position(self):
        with self._lock:
            if self.status == "Playing":
                return self._pos + (time.monotonic() - self._pos_time)
            return self._pos


CAVA_CONFIG = """[general]
bars = {bars}
framerate = 60
autosens = 1

[input]
method = {method}
source = auto

[output]
method = raw
raw_target = /dev/stdout
data_format = ascii
ascii_max_range = 1000
bar_delimiter = 59
frame_delimiter = 10
channels = mono
mono_option = average

[smoothing]
noise_reduction = 70
"""


class AudioSource:
    def __init__(self, bars=CAVA_BARS):
        self.n = bars
        self.values = [0.0] * bars
        self.lock = threading.Lock()
        self.proc = None
        self.cfg = None
        self.live = False
        self._start()

    def _start(self):
        if not shutil.which("cava"):
            return
        for method in ("pipewire", "pulse"):
            fd, path = tempfile.mkstemp(prefix="spotify-lyrics-cava-", suffix=".conf")
            with os.fdopen(fd, "w") as f:
                f.write(CAVA_CONFIG.format(bars=self.n, method=method))
            try:
                proc = subprocess.Popen(
                    ["cava", "-p", path],
                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL, text=True, bufsize=1,
                )
            except OSError:
                os.remove(path)
                continue
            time.sleep(0.5)
            if proc.poll() is None:
                self.proc, self.cfg, self.live = proc, path, True
                threading.Thread(target=self._reader, daemon=True).start()
                return
            os.remove(path)

    def _reader(self):
        try:
            for line in self.proc.stdout:
                parts = line.strip().strip(";").split(";")
                try:
                    vals = [int(x) / 1000 for x in parts if x]
                except ValueError:
                    continue
                if len(vals) == self.n:
                    with self.lock:
                        self.values = vals
        except Exception:
            pass
        self.live = False

    def _fake(self, playing, now):
        if not playing:
            return [0.0] * self.n
        beat = wave(now * math.pi * 4 - math.pi / 2) ** 6
        out = []
        for i in range(self.n):
            x = i / (self.n - 1)
            bass = (1 - x) ** 2 * beat * 0.7
            body = 0.2 + 0.4 * wave(now * (1.9 + x * 3.1) + i * 0.9) * wave(now * (2.7 - x) + i * 0.37)
            out.append(min(1.0, (bass + body * (1 - 0.5 * x)) * (0.85 + 0.15 * random.random())))
        return out

    def read(self, playing, now):
        if self.live:
            with self.lock:
                return list(self.values)
        return self._fake(playing, now)

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        if self.cfg and os.path.exists(self.cfg):
            os.remove(self.cfg)


class WindowsAudio(AudioSource):
    def _start(self):
        self._stopped = False
        self._updated = 0.0
        try:
            import numpy
            import soundcard
        except ImportError:
            return
        self._ready = threading.Event()
        threading.Thread(target=self._capture, daemon=True).start()
        self._ready.wait(2.0)

    def _capture(self):
        try:
            import warnings
            import numpy as np
            import soundcard as sc
            warnings.filterwarnings("ignore", category=getattr(sc, "SoundcardRuntimeWarning", RuntimeWarning))
            rate, size, hop = 48000, 2048, 1024
            speaker = sc.default_speaker()
            mic = sc.get_microphone(id=str(speaker.name), include_loopback=True)
            freqs = np.fft.rfftfreq(size, 1 / rate)
            edges = np.searchsorted(freqs, np.geomspace(40, 14000, self.n + 1))
            tilt = 1 + np.linspace(0, 3, self.n)
            window = np.hanning(size)
            buf = np.zeros(size)
            peak = 4.0
            with mic.recorder(samplerate=rate, blocksize=hop) as rec:
                self.live = True
                self._ready.set()
                while not self._stopped:
                    data = rec.record(numframes=hop)
                    mono = data.mean(axis=1) if data.ndim > 1 else data
                    if len(mono) >= size:
                        buf = mono[-size:]
                    else:
                        buf = np.concatenate([buf[len(mono):], mono])
                    spec = np.abs(np.fft.rfft(buf * window))
                    bands = np.array([spec[a:max(a + 1, b)].max() for a, b in zip(edges[:-1], edges[1:])])
                    bands = np.sqrt(bands * tilt)
                    peak = max(peak * 0.997, float(bands.max()), 4.0)
                    with self.lock:
                        self.values = np.clip(bands / peak, 0, 1).tolist()
                        self._updated = time.monotonic()
        except Exception:
            pass
        self.live = False
        self._ready.set()

    def read(self, playing, now):
        if self.live:
            with self.lock:
                if time.monotonic() - self._updated > 0.25:
                    return [0.0] * self.n
                return list(self.values)
        return self._fake(playing, now)

    def stop(self):
        self._stopped = True


def resample(vals, n):
    m = len(vals)
    if m == 0:
        return [0.0] * n
    if n == 1 or m == 1:
        return [max(vals)] * n
    out = []
    for k in range(n):
        p = k * (m - 1) / (n - 1)
        i = int(p)
        j = min(i + 1, m - 1)
        f = p - i
        out.append(vals[i] * (1 - f) + vals[j] * f)
    return out


class Visualizer:
    BAR_W = 2
    GAP = 1

    def __init__(self):
        self.levels = []
        self.peaks = []
        self.peak_vel = []

    def draw(self, cv, values, dt):
        step = self.BAR_W + self.GAP
        nb = max(1, (cv.w + self.GAP) // step)
        vals = resample(values, nb)
        if len(self.levels) != nb:
            self.levels = [0.0] * nb
            self.peaks = [0.0] * nb
            self.peak_vel = [0.0] * nb

        max_rows = max(1, int(cv.h * VIS_HEIGHT))
        halves = max_rows * 2
        bottom = cv.h - 1
        x0 = max(0, (cv.w - (nb * step - self.GAP)) // 2)

        for k in range(nb):
            target = max(0.0, min(1.0, vals[k]))
            level = self.levels[k]
            level = target if target > level else max(target, level - dt * 1.8)
            self.levels[k] = level

            if level >= self.peaks[k]:
                self.peaks[k] = level
                self.peak_vel[k] = 0.0
            else:
                self.peak_vel[k] += dt * 1.2
                self.peaks[k] = max(0.0, self.peaks[k] - self.peak_vel[k] * dt)

            hh = int(level * halves)
            full, half = hh // 2, hh % 2
            x = x0 + k * step
            for r in range(full):
                y = bottom - r
                color = vis_color(r / max_rows)
                for dx in range(self.BAR_W):
                    if 0 <= y < cv.h and x + dx < cv.w:
                        cv.bg[y][x + dx] = color
            if half:
                y = bottom - full
                color = vis_color(full / max_rows)
                for dx in range(self.BAR_W):
                    if 0 <= y < cv.h and x + dx < cv.w:
                        cv.ch[y][x + dx] = "▄"
                        cv.fg[y][x + dx] = color
                        cv.vis[y][x + dx] = True

            ph = int(self.peaks[k] * halves)
            py = bottom - ph // 2
            if ph > hh + 1 and 0 <= py < cv.h:
                for dx in range(self.BAR_W):
                    if x + dx < cv.w and cv.ch[py][x + dx] == " " and cv.bg[py][x + dx] is None:
                        cv.ch[py][x + dx] = "▔" if ph % 2 == 0 else "▁"
                        cv.fg[py][x + dx] = VIS_PEAK
                        cv.vis[py][x + dx] = True


def http_get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def clean_title(title):
    title = re.sub(r"\s*-\s*.*(remaster|version|edit|live|mix).*$", "", title, flags=re.I)
    title = re.sub(r"\s*[\(\[].*?(feat|ft\.|with).*?[\)\]]", "", title, flags=re.I)
    return title.strip()


def fetch_lyrics(track):
    params = {
        "artist_name": track["artist"],
        "track_name": track["title"],
        "album_name": track["album"],
    }
    if track["duration"]:
        params["duration"] = round(track["duration"])
    data = http_get_json(f"{API}/get?" + urllib.parse.urlencode(params))
    if data and (data.get("syncedLyrics") or data.get("plainLyrics") or data.get("instrumental")):
        return data

    q = f"{track['artist']} {clean_title(track['title'])}"
    results = http_get_json(f"{API}/search?" + urllib.parse.urlencode({"q": q}))
    if not results:
        return None

    def score(item):
        s = 10 if item.get("syncedLyrics") else 0
        if track["duration"] and item.get("duration"):
            s -= abs(item["duration"] - track["duration"])
        return s

    results = [r for r in results if r.get("syncedLyrics") or r.get("plainLyrics")]
    return max(results, key=score) if results else None


LRC_STAMP = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\]")


def parse_lrc(lrc):
    lines = []
    for raw in lrc.splitlines():
        stamps = LRC_STAMP.findall(raw)
        text = LRC_STAMP.sub("", raw).strip()
        for m, s in stamps:
            lines.append((int(m) * 60 + float(s), text))
    lines.sort(key=lambda x: x[0])
    return [t for t, _ in lines], [x for _, x in lines]


class LyricsStore:
    def __init__(self):
        self.cache = {}
        self.pending = set()
        self.lock = threading.Lock()

    def get(self, track):
        key = (track["artist"], track["title"])
        with self.lock:
            if key in self.cache:
                return self.cache[key]
            if key in self.pending:
                return None
            self.pending.add(key)
        threading.Thread(target=self._load, args=(track, key), daemon=True).start()
        return None

    def _load(self, track, key):
        data = fetch_lyrics(track)
        if data and data.get("instrumental"):
            result = ("instrumental", None)
        elif data and data.get("syncedLyrics"):
            result = ("synced", parse_lrc(data["syncedLyrics"]))
        elif data and data.get("plainLyrics"):
            result = ("plain", data["plainLyrics"].splitlines())
        else:
            result = ("none", None)
        with self.lock:
            self.cache[key] = result
            self.pending.discard(key)


BARS = "▁▂▃▄▅▆▇█"
SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


class Renderer:
    def __init__(self, visualizer=True, big=True):
        self.big = big
        self.shift = 0.0
        self.key = None
        self.key_time = 0.0
        self.index = -1
        self.prev_index = -1
        self.index_time = 0.0
        self.scroll = 0.0
        self.fresh = True
        self.last_frame = time.monotonic()
        self.vis = Visualizer() if visualizer else None

    def header(self, cv, track, status, now):
        age = now - self.key_time
        title = truncate(track["title"], max(5, cv.w - 16))
        n = int(len(title) * ease(age / 0.7))
        shown = title[:n]

        eq_n = 5
        total = swidth(title) + 2 * (eq_n + 2)
        x = max(0, (cv.w - total) // 2)
        playing = status == "Playing"
        eq = []
        for i in range(eq_n):
            if playing:
                v = 0.6 * wave(now * (5 + i * 1.3) + i * 2.1) + 0.4 * wave(now * (3.1 + i * 0.7) + i)
            else:
                v = 0.0
            eq.append((BARS[int(v * (len(BARS) - 1))], mix(GREEN, CYAN, i / (eq_n - 1))))

        for ch, color in eq:
            x = cv.cell(x, 0, ch, color)
        x += 2
        title_x = x
        x = cv.put(x, 0, shown, TITLE, bold=True)
        if n < len(title):
            cv.cell(x, 0, "▌", CYAN)
        x = title_x + swidth(title) + 2
        for ch, color in reversed(eq):
            x = cv.cell(x, 0, ch, color)

        info = f"{track['artist']} — {track['album']}"
        cv.put_centered(1, info, mix(BG, (170, 170, 170), ease((age - 0.3) / 0.7)))

    def progress_bar(self, cv, y, pos, duration, playing, now):
        def fmt(s):
            s = max(0, int(s))
            return f"{s // 60}:{s % 60:02d}"

        left, right = fmt(pos), fmt(duration)
        bw = max(10, min(cv.w - len(left) - len(right) - 6, 70))
        frac = max(0.0, min(1.0, pos / duration)) if duration else 0.0
        filled = int(frac * bw)

        total = len(left) + len(right) + bw + 2
        x = max(0, (cv.w - total) // 2)
        x = cv.put(x, y, left, GRAY) + 1
        for k in range(bw):
            if k < filled:
                x = cv.cell(x, y, "━", shimmer(k, now))
            elif k == filled:
                if playing or int(now * 2) % 2 == 0:
                    x = cv.cell(x, y, "●", WHITE)
                else:
                    x = cv.cell(x, y, "─", DARK)
            else:
                x = cv.cell(x, y, "─", DARK)
        x = cv.put(x + 1, y, right, GRAY)
        if not playing:
            cv.cell(x + 2, y, "⏸", YELLOW)

    def breathing_dots(self, cv, y, now, progress):
        x = max(0, (cv.w - 7) // 2)
        for k in range(3):
            b = wave(now * 4 - k * 0.9)
            lit = progress >= (k + 1) / 3
            cv.cell(x + k * 3, y, "●", mix(DARK, GREEN if lit else GRAY, 0.4 + 0.6 * b))

    def ease_scroll(self, target, dt):
        if self.fresh:
            self.scroll = target - 6
            self.fresh = False
        self.scroll += (target - self.scroll) * (1 - math.exp(-dt * 9))
        if abs(target - self.scroll) < 0.01:
            self.scroll = target

    def plan_big(self, text, w, max_h):
        if not self.big or not text:
            return None
        norm = big_normalize(text)
        if not norm:
            return None
        for scale, rows, max_lines in ((2, 5, 2), (1, 3, 3)):
            maxc = (w - 2 + scale) // (4 * scale)
            if maxc < 4:
                continue
            wrapped = wrap_words(norm, maxc)
            height = len(wrapped) * rows + len(wrapped) - 1
            if len(wrapped) <= max_lines and height <= max_h:
                return norm, scale, rows, wrapped, height
        return None

    def karaoke_colors(self, n, times, i, pos, appear, now):
        nxt = times[i + 1] if i + 1 < len(times) else times[i] + 5
        dur = max(0.5, min(nxt - times[i], 1.0 + n * 0.06))
        p = max(0.0, min(1.0, (pos - times[i]) / dur))
        exact = p * n
        nfill = int(exact)
        base = mix(GRAY, WHITE, appear)

        def color(k):
            if k < nfill:
                return shimmer(k, now)
            if k == nfill:
                return mix(base, shimmer(k, now), exact - nfill)
            return base

        return color

    def draw_big(self, cv, y, plan, color_fn, slide):
        norm, scale, rows, wrapped, _ = plan
        for li, (start, line) in enumerate(wrapped):
            width = len(line) * 4 * scale - scale
            x = max(0, (cv.w - width) // 2)
            if x + slide + width <= cv.w:
                x += slide
            ly = y + li * (rows + 1)
            for j, ch in enumerate(line):
                glyph = FONT[ch]
                color = color_fn(start + j)
                cx = x + j * 4 * scale
                if scale == 2:
                    for r in range(5):
                        for c in range(3):
                            if glyph[r][c] == "X":
                                cv.cell(cx + 2 * c, ly + r, "█", color)
                                cv.cell(cx + 2 * c + 1, ly + r, "█", color)
                else:
                    for tr in range(3):
                        for c in range(3):
                            top = glyph[2 * tr][c] == "X"
                            bot = 2 * tr + 1 < 5 and glyph[2 * tr + 1][c] == "X"
                            if top and bot:
                                cv.cell(cx + c, ly + tr, "█", color)
                            elif top:
                                cv.cell(cx + c, ly + tr, "▀", color)
                            elif bot:
                                cv.cell(cx + c, ly + tr, "▄", color)

    def synced_body(self, cv, y0, body_h, times, texts, pos, now, dt):
        cur = bisect.bisect_right(times, pos) - 1
        if self.fresh:
            self.shift = body_h // 2
            self.fresh = False
        if cur != self.index:
            self.prev_index, self.index, self.index_time = self.index, cur, now
            self.shift = max(self.shift, 3.0)
        self.shift *= math.exp(-dt * 9)
        if self.shift < 0.05:
            self.shift = 0.0
        off = round(self.shift)
        appear = ease((now - self.index_time) / 0.35)
        slide = int((1 - appear) * 4)

        text = texts[cur] if 0 <= cur < len(texts) else ""
        plan = self.plan_big(text, cv.w, body_h - 4) if text else None
        height = plan[4] if plan else 1
        center = y0 + body_h // 2
        top = center - height // 2 + off

        def visible(y):
            return y0 <= y < y0 + body_h

        if cur == -1:
            first = times[0] if times else 1
            if visible(top):
                self.breathing_dots(cv, top, now, pos / first if first else 1)
        elif not text:
            nxt = times[cur + 1] if cur + 1 < len(times) else times[cur] + 5
            if visible(top):
                self.breathing_dots(cv, top, now, (pos - times[cur]) / max(0.1, nxt - times[cur]))
        elif plan:
            colors = self.karaoke_colors(len(plan[0]), times, cur, pos, appear, now)
            self.draw_big(cv, top, plan, colors, slide)
        else:
            self.karaoke_line(cv, top, text, times, cur, pos, appear, slide, now)

        half = max(1, body_h // 2)

        def neighbor(i, y):
            if not visible(y) or not (0 <= i < len(texts)):
                return
            depth = 1 - min(1.0, abs(y - center) / (half + 1)) * 0.8
            shown = texts[i] or "♪"
            if i < cur:
                past = mix(BG, (115, 115, 115), depth)
                if i == self.prev_index:
                    color = mix(GREEN, past, ease((now - self.index_time) / 0.6))
                else:
                    color = past
            else:
                color = mix(BG, (210, 210, 210), depth)
            cv.put_centered(y, shown, color)

        gap = 1 if plan else 0
        for k in range(1, body_h + 1):
            neighbor(cur - k, top - gap - k)
            neighbor(cur + k, top + height - 1 + gap + k)

    def karaoke_line(self, cv, y, text, times, i, pos, appear, slide, now):
        text = truncate(text, cv.w - 4)
        color = self.karaoke_colors(len(text), times, i, pos, appear, now)
        tw = swidth(text)
        x = max(0, (cv.w - tw) // 2)
        if x + slide + tw <= cv.w:
            x += slide
        for k, ch in enumerate(text):
            x = cv.cell(x, y, ch, color(k), bold=True)

    def plain_body(self, cv, y0, body_h, lines, pos, duration, dt):
        cv.put_centered(y0, "(unsynced lyrics)", YELLOW)
        view = body_h - 2
        frac = max(0.0, min(1.0, pos / duration)) if duration else 0.0
        self.ease_scroll(frac * max(0, len(lines) - view), dt)
        start = max(0, round(self.scroll))
        for row in range(max(0, view)):
            i = start + row
            if i >= len(lines):
                break
            edge = min(row, view - 1 - row)
            color = mix(BG, (215, 215, 215), 0.35 + 0.65 * min(1.0, edge / 2))
            cv.put_centered(y0 + 2 + row, lines[i], color)

    def message_body(self, cv, y0, body_h, text, now, color=YELLOW):
        cv.put_centered(y0 + body_h // 2, text, mix(GRAY, color, wave(now * 2)))

    def instrumental_body(self, cv, y0, body_h, now):
        mid = y0 + body_h // 2
        x = max(0, (cv.w - 9) // 2)
        for k in range(5):
            b = wave(now * 3 - k * 0.8)
            sym = "♪" if (int(now * 2) + k) % 2 else "♫"
            cv.cell(x + k * 2, mid - 1, sym, mix(DARK, mix(GREEN, CYAN, k / 4), b))
        cv.put_centered(mid + 1, "Instrumental", GRAY)

    def loading_body(self, cv, y0, body_h, now):
        spin = SPINNER[int(now * 12) % len(SPINNER)]
        dots = "." * (int(now * 3) % 4)
        x = max(0, (cv.w - swidth("X  Searching for lyrics...")) // 2)
        cv.put(x, y0 + body_h // 2, f"{spin}  Searching for lyrics{dots}", shimmer(0, now))

    def frame(self, player, store, audio):
        w, h = shutil.get_terminal_size((80, 24))
        now = time.monotonic()
        dt = min(0.2, now - self.last_frame)
        self.last_frame = now
        cv = Canvas(w, h)

        track = player.track
        playing = bool(track) and player.status == "Playing"
        if self.vis:
            self.vis.draw(cv, audio.read(playing, now) if audio else [], dt)

        if not track:
            mid = h // 2
            cv.put_centered(mid - 1, "♫", mix(DARK, GREEN, wave(now * 2)), bold=True)
            cv.put_centered(mid + 1, "Spotify is not running or nothing is playing…", GRAY)
            self.key = None
            return cv

        key = (track["artist"], track["title"])
        if key != self.key:
            self.key, self.key_time = key, now
            self.index = self.prev_index = -1
            self.index_time = now
            self.fresh = True

        pos = player.position
        self.header(cv, track, player.status, now)
        self.progress_bar(cv, h - 1, pos, track["duration"], playing, now)

        y0 = 3
        body_h = max(1, h - 5)
        result = store.get(track)
        if result is None:
            self.loading_body(cv, y0, body_h, now)
        else:
            kind, content = result
            if kind == "synced":
                self.synced_body(cv, y0, body_h, content[0], content[1], pos, now, dt)
            elif kind == "plain":
                self.plain_body(cv, y0, body_h, content, pos, track["duration"], dt)
            elif kind == "instrumental":
                self.instrumental_body(cv, y0, body_h, now)
            else:
                self.message_body(cv, y0, body_h, "No lyrics found for this song.", now)
        return cv


def main():
    if IS_WINDOWS:
        setup_windows_console()
        manager = load_media_control()
        if manager is None:
            print("The Windows media packages are missing. Install them with:")
            print("  python -m pip install winrt-Windows.Media.Control winrt-Windows.Foundation winrt-Windows.Foundation.Collections")
            sys.exit(1)
        player = WindowsPlayer(manager)
    else:
        if not shutil.which("playerctl"):
            print("playerctl is missing. Install it with: sudo dnf install playerctl")
            sys.exit(1)
        player = Player()

    use_vis = "--no-visualizer" not in sys.argv
    audio = None
    if use_vis:
        audio = WindowsAudio() if IS_WINDOWS else AudioSource()
    if use_vis and not audio.live:
        if IS_WINDOWS:
            print("Could not capture system audio, using a simulated visualizer.")
            print("For a real one: python -m pip install soundcard numpy")
        else:
            print("cava not found or could not start, using a simulated visualizer.")
            print("For a real one: sudo dnf install cava")
        time.sleep(1.5)

    store = LyricsStore()
    renderer = Renderer(visualizer=use_vis, big="--small-text" not in sys.argv)
    frame_time = 1 / FPS

    sys.stdout.write(ALT_ON + HIDE_CURSOR)
    try:
        while True:
            t0 = time.monotonic()
            player.sync()
            sys.stdout.write(renderer.frame(player, store, audio).render())
            sys.stdout.flush()
            time.sleep(max(0.0, frame_time - (time.monotonic() - t0)))
    except KeyboardInterrupt:
        pass
    finally:
        if audio:
            audio.stop()
        sys.stdout.write(RESET + SHOW_CURSOR + ALT_OFF)
        sys.stdout.flush()


if __name__ == "__main__":
    main()
