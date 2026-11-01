"""The score of the Gorgan Bay reel (gorgan_khazar_fa, 20 s): an original track in Segah, built from the Persian
sound kit (onebit_persian) and timed to the film's own clock. Everything is synthesized here: no samples, no voices.

The data are audible, and every number the music uses is a number on the screen. The film shows the bay's area per
year (km2, to the nearest 10) and the Caspian's level against 1374 (m, from 1372). A year the film marks 'uncertain'
has no number on the screen, so the music bridges it in time between the nearest readings and never sounds an
unshown number. Every event time is read from the film (film.keys, film.at, film.starts, film.later), so a change of
the film's pace or text moves the music with it.

    0.00 s         the first sound: a setar sting (E4, G-sori 4, B4), on the first frame
    0.30-2.30 s    the rewind: the sting read backwards, the tape speeding up; one soft tick per rewound year
    2.30 s         1365 (1986, the bay on screen at 420 km2): the sting's last attack lands on the tonic; a kamancheh
                   line starts on E3
    2.80-11.48 s   the forward years, one tick each (film.at), panned as the picture reads (right to left)
                   1365-1372 (to 3.58 s): the line rises with the bay, its pitch proportional to the bay's area
                   1372-1388 (to 5.66 s): the line holds on the plateau
    3.58 s         1372 (1993): the first sea level; the drone enters and follows the level
    4.00 s         the groove on the bar line, full while the bay is at 85 % of 1374 or more; the hook of six notes
                   (G-sori, B, A, F-koron, G-sori, E), two bars, the first time with every note
    5.66 s         1389 (2010): the decline; the line is released; the groove thins with the bay's share of 1374
    7.60 s         'about half' (scene 2): the number lands: a santur chord, a daf bam, a clap, a sub
    8.00 s         the hook again: its last notes drop out as the bay shrinks, so it stops unresolved (G-sori, B, A)
    13.60 s        '2.5 to 2.7 m lower' (scene 3): a lower accent: a one-second drop of the drone to E1, a tom, a
                   kick, a low santur chord
    15.20 s        1405 arrives: a quiet, unresolved close: one setar note on G-sori, a daf rim; the groove at 35 %,
                   the drone at half
    19.00 s        the groove stops; the drone holds on B1, the fifth and not the tonic, to the last second's fade

The drone's pitch is E2 at 0 m with two semitones per metre of the level: the 2.5 m fall since 1374 is a fall of a
fourth, from E2 (82 Hz) to B1 (62 Hz). The kamancheh's pitch is E3 times the bay's area over its area in 1365; the
rise of the bay from 1365 to 1372 is about four and a half semitones. The groove's layers follow the bay's share of
its 1374 area, smoothed over a second: full at 0.85 or more (the santur figure, the clap, the hats on the eighths),
mid at 0.70 (the second kick, the bam on the three, the tak, the eighth hats), thin at 0.50 (the kick and the bam on
the one, quarter-note hats), and sparse below 0.50 (the kick on the bar line only).

Mix: -14 LUFS integrated, true peak -1.5 dBTP (the AAC encoding of the reel stays under -1), the sub in mono.

    python -I src/onebit_score_gorgan.py

writes outputs/onebit/social/gorgan_khazar_fa_music.wav and muxes it under the silent reel into
gorgan_khazar_fa_music_reel.mp4 (the silent reel is not rewritten). It prints the loudness and the true peak of the
WAV and of the MP4's decoded audio, the RMS per second against the bay on screen, the event table with the onset
offsets, the pitch of the drone and of the line against the level and the area, and the video stream against the
silent reel.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.ndimage import uniform_filter1d
from scipy.signal import butter, sawtooth, sosfilt

sys.path.insert(0, str(Path(__file__).resolve().parent))

import onebit  # noqa: E402
import onebit_gorgan as film_mod  # noqa: E402
import onebit_persian as kit  # noqa: E402
from onebit_slides import COLOURS  # noqa: E402

SR = kit.SR
BEAT, BAR = kit.BEAT, kit.BAR              # 0.5 s and 2 s at 120 BPM: a beat is half a film second
MODE = "segah"                             # E, F-koron, G-sori, A, B, C-koron, D
TAIL = 3.0                                 # s of room past the end, for the reverb and the echo
LUFS, TP = -14.0, -1.5                     # -1.5 dBTP: the AAC encoding of this track stays under -1
MAX_OFFSET = 0.030                         # s: a hit may sit at most this far from its event
SEED = 29
THEME = "khazar"
BASE = "gorgan_khazar_fa"
BUSES = ("intro", "ticks", "line", "drone", "drum", "santur", "hook", "fx")
GROOVE_END = 19.0                          # s: the groove stops; the drone holds to the fade
CLOSE_GAIN = 0.35                          # the groove's gain from 1405 on: quiet and unresolved
CLOSE_DRONE = 0.5                          # the drone's level from 1405 on (it fades in over 0.8 s)
LINE_RELEASE = 0.3                         # s: the kamancheh is released as the decline begins
DRONE_ST_PER_M = 2.0                       # semitones of the drone per metre of the sea level (a fall of a fourth)
DRONE_FADE = 0.4                           # s: the drone enters over this long, at the first reading
FULL_SHARE, MID_SHARE, THIN_SHARE = 0.85, 0.70, 0.50     # the groove's layers: the bay's share of 1374
HOOK_TH = (0.0, 0.60, 0.62, 0.66, 0.70, 0.74)            # the share below which each hook note drops out
GATE_WIDTH = 0.05
CHORD = (0, 2, 4)                          # E, G-sori, B: the triad of the santur figure
ARP = (0, 1, 2, 1, 0, 1, 2, 1)             # the santur figure: eighths over the triad
# the hook, two bars: (onset in s from the hook's start, mode step, length in s); note 0 is G-sori
HOOK = ((0.00, 2, 0.75), (0.75, 4, 0.50), (1.25, 3, 0.50), (1.75, 1, 0.75), (2.50, 2, 0.50), (3.00, 0, 1.00))
# the groove: (offset in s from the bar line, lowest layer, voice, gain, pan); the hats are below
GROOVE = ((0.00, 0, "kick", 0.90, 0.0), (1.25, 2, "kick", 0.60, 0.0), (0.00, 1, "bam", 0.50, 0.0),
          (1.00, 2, "bam", 0.40, 0.0), (0.50, 2, "tak", 0.30, -0.3), (1.50, 2, "tak", 0.30, 0.3),
          (1.00, 3, "clap", 0.30, 0.0))


def block_geo_stack() -> None:
    """Keep the geo stack out of this process. The film reads npz and csv only; its data module imports rasterio,
    which does not load any of these names, so the film still builds."""
    for name in ("shapely", "cartopy", "fiona", "geopandas", "pyproj"):
        if name not in sys.modules:
            sys.modules[name] = None


def deg(step: int, octave: int = 0) -> float:
    """A step of the mode, in Hz: octave 0 is E4 (the tonic of Segah, 330 Hz), -1 is E3, -2 is E2, -3 is E1."""
    return kit.degree(MODE, step, octave)


def drone_hz(level_m):
    """The drone's pitch for a sea level (m against 1374): E2 at 0 m, two semitones per metre lower."""
    return deg(0, -2) * 2.0 ** (DRONE_ST_PER_M * np.asarray(level_m, float) / 12.0)


def pan_of(y: int, y0: int, y1: int) -> float:
    """Right to left across the years, as the picture reads: the first year on the right, the last on the left."""
    return 0.35 - 0.7 * (y - y0) / (y1 - y0)


def level_of(share: float) -> int:
    """The groove's layers from the bay's share of 1374: 3 full, 2 mid, 1 thin, 0 sparse."""
    return 3 if share >= FULL_SHARE else 2 if share >= MID_SHARE else 1 if share >= THIN_SHARE else 0


def _gate(x: float, th: float, width: float = GATE_WIDTH) -> float:
    """0 below th, 1 above th + width, smooth between: a hook note is on while the bay is above its threshold."""
    u = min(1.0, max(0.0, (x - th) / width))
    return u * u * (3.0 - 2.0 * u)


# ── the film's clock and the data on the screen ────────────────────────────

def timing(film) -> dict:
    """The film's own times: the rewind's keys (2025 back to 1986, one tick each), the forward years (1987 to 2026,
    one tick each; 2026 is the close), the rewind's last attack (1986), the first sea level (1993), the decline
    (2010), and the two lines the music answers (scene 2 at starts[1] + later(1), scene 3 at starts[2] + later(2))."""
    keys = [(float(t), int(y)) for t, y in film.keys]
    st = [float(s) for s in film.starts]
    fwd = sorted((float(t), int(y)) for y, t in film.at.items())
    at = {y: t for t, y in fwd}
    y0, y1 = int(film.years[0]), int(film.years[-1])
    tm = dict(starts=st, end=st[-1], y0=y0, y1=y1, fwd=fwd,
              rewind=[(t, y) for t, y in keys if 0.0 < t < fwd[0][0]],
              forward=[(t, y) for t, y in fwd if y != y1],
              t_first=min(t for t, y in keys if y == y0),
              t_level=at[film_mod.FIRST_READING],
              t_decline=at[film_mod.SLOW_FROM],
              t_now=at[y1],
              stop=st[1] + float(film.later(1)),
              accent2=st[2] + float(film.later(2)))
    tm["groove0"] = math.ceil(tm["t_level"] / BAR - 1e-9) * BAR          # the first bar line after the first reading
    assert (tm["t_first"] < tm["t_level"] < tm["groove0"] < tm["t_decline"] < tm["stop"] < tm["accent2"]
            < tm["t_now"]), tm
    assert tm["t_decline"] < tm["groove0"] + 2 * BAR, "the second hook must come in the decline"
    assert tm["t_now"] + 2.0 < GROOVE_END < tm["end"] - 0.5, tm
    return tm


def bay_areas(film) -> tuple:
    """The bay's area per year as the film shows it (km2). A year the film marks 'uncertain' has no number on the
    screen: it is bridged in time between the nearest readings, so that no unshown number is sounded."""
    yrs = sorted(int(y) for y in film.years)
    known = [y for y in yrs if film.label[y] != "uncertain"]
    val = {y: float(film.label[y]) for y in known}
    areas = {y: val[y] if y in val else float(np.interp(y, known, [val[k] for k in known])) for y in yrs}
    return areas, [y for y in yrs if y not in val]


def curves(film, tm: dict, grid: np.ndarray) -> dict:
    """Per millisecond of the reel: the bay's area (km2, the on-screen values, bridged), the share of the 1374 area
    and the same share smoothed over a second; and the level on the screen from 1372 on."""
    areas, bridged = bay_areas(film)
    pt = np.array([tm["t_first"]] + [t for t, _ in tm["fwd"]])
    pa = np.array([areas[tm["y0"]]] + [areas[y] for _, y in tm["fwd"]])
    A = np.interp(grid, pt, pa)
    share = A / areas[film_mod.BASE_YEAR]
    share_s = uniform_filter1d(share, 1000, mode="nearest")
    rd = [(t, y) for t, y in tm["fwd"] if y >= film_mod.FIRST_READING]
    lt = np.array([t for t, _ in rd])
    lv = np.array([float(film.level[y]) for _, y in rd])
    return dict(pt=pt, pa=pa, areas=areas, bridged=bridged, A=A, share=share, share_s=share_s, lt=lt, lv=lv)


# ── sounds ──────────────────────────────────────────────────────────────────

def _tick() -> np.ndarray:
    """A soft tick: a band-passed click of 3 ms, with its own noise seed."""
    n = int(0.02 * SR)
    t = np.arange(n) / SR
    noise = np.random.default_rng(31).standard_normal(n)
    x = sosfilt(butter(2, (1500.0, 5000.0), "bandpass", fs=SR, output="sos"), noise) * np.exp(-t / 0.003)
    x = x * np.minimum(1.0, t / 0.0005)
    return x / np.abs(x).max()


def _sting() -> np.ndarray:
    """The sting: three setar notes, E4, G-sori 4 and B4, 0.15 s apart, ringing; its last 30 ms faded."""
    x = kit.new_track(1.3)
    for k, step in enumerate(CHORD):
        s = kit.setar(deg(step, 0), dur=1.2, vel=0.9, t60=1.5, bright=0.6, buzz=0.15)
        kit.place(x, s, 0.15 * k, 0.8, pan=(-0.2, 0.0, 0.2)[k])
    m = int(0.03 * SR)
    x[-m:] *= np.linspace(1.0, 0.0, m)[:, None]
    return x


def _rewind_rise(x: np.ndarray, n_out: int, v0: float = 0.5) -> np.ndarray:
    """The sting read backwards from its end to its start in n_out samples, the tape speeding up as it goes: the read
    speed rises linearly from v0 to v1, with v1 set so that the whole sting is read. Its first attack arrives on the
    last sample, so the rewind ends on that attack."""
    x = np.asarray(x, float)
    avg = (len(x) - 1) / n_out
    v1 = 2.0 * avg - v0
    v = v0 + (v1 - v0) * np.arange(n_out) / max(n_out - 1, 1)
    pos = (len(x) - 1) - np.concatenate([[0.0], np.cumsum(v)[:-1]])
    pos = np.clip(pos, 0.0, len(x) - 1)
    idx = np.arange(len(x))
    return np.stack([np.interp(pos, idx, x[:, c]) for c in range(x.shape[1])], axis=1)


def _kamancheh(f: np.ndarray, vel: float, release: float) -> np.ndarray:
    """A bowed lead on a pitch curve f (Hz per sample), mono: the kit's kamancheh voice (a sawtooth with its body
    formants and a little bow hiss, vibrato once the bow holds), attack 30 ms, released over the last `release` s."""
    n = len(f)
    t = np.arange(n) / SR
    rng = np.random.default_rng(41)
    vib = 30.0 * np.sin(2 * np.pi * 5.5 * t) * np.clip((t - 0.3) / 0.6, 0.0, 1.0)
    x = sawtooth(2 * np.pi * np.cumsum(f * 2.0 ** (vib / 1200.0)) / SR)
    x = 0.5 * x + 0.5 * sosfilt(butter(2, (900.0, 3000.0), "bandpass", fs=SR, output="sos"), x)
    x = x + 0.02 * sosfilt(butter(2, (2000.0, 6000.0), "bandpass", fs=SR, output="sos"), rng.standard_normal(n))
    env = np.minimum(1.0, t / 0.03) * np.clip((t[-1] - t) / release, 0.0, 1.0)
    x = x * env
    return vel * 0.5 * x / np.abs(x).max()


def _drone(f: np.ndarray, env: np.ndarray, vel: float) -> np.ndarray:
    """The sea's drone, mono: a sine on the pitch curve f (Hz per sample) with the kit's soft saturation, and a soft
    octave above it on the same curve, so that a small speaker shows the fall of the low note; times env."""
    phase = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(phase)
    x = 0.7 * s + 0.3 * np.tanh(3.0 * s) / np.tanh(3.0) + 0.22 * np.sin(2.0 * phase)
    return vel * x * env


def _bass_mono(x, fc: float = 120.0) -> np.ndarray:
    """The low end in mono: everything below fc is averaged to one channel, and the rest stays wide."""
    low = sosfilt(butter(4, fc, "lowpass", fs=SR, output="sos"), x, axis=0)
    mid = 0.5 * (low[:, 0] + low[:, 1])
    out = x - low
    out[:, 0] += mid
    out[:, 1] += mid
    return out


def _fit(x, n: int):
    """Crop or zero-pad x along time to n rows."""
    return x[:n] if len(x) >= n else np.concatenate([x, np.zeros((n - len(x),) + x.shape[1:])])


# ── the composition ─────────────────────────────────────────────────────────

def _compose(film, rec: list):
    """Lay the score on its buses. Returns (buses, the kick times, the curves, the timing). rec receives one entry per
    checked event: (label, visual time, time of the hit) for a sound that is isolated in the WAV, and a fourth item,
    the sounds placed for it as (sound, gain, pan), when the others must be cleared for the check."""
    kit.reseed(SEED)
    tm = timing(film)
    end, y0, y1 = tm["end"], tm["y0"], tm["y1"]
    grid = np.arange(int(round(end * 1000)) + 1) / 1000.0
    cv = curves(film, tm, grid)
    fs = cv["share_s"]
    bus = {k: kit.new_track(end, TAIL) for k in BUSES}
    n = len(bus["fx"])
    t_all = np.arange(n) / SR
    tick = _tick()
    S = dict(kick=kit.kick808(kit.note_hz("E1"), vel=1.0, decay=0.9, drive=1.3),
             bam=kit.daf("bam", pitch=deg(0, -2)), tak=kit.daf("tak", pitch=deg(0, 0)),
             tom=kit.tombak("tom", pitch=deg(0, -2)), clap=kit.clap(), hat=kit.hat(False))
    kicks: list = []
    g0, t_now, t_dec = tm["groove0"], tm["t_now"], tm["t_decline"]
    nb = int(round((GROOVE_END - g0) / BEAT))
    beat_level = [level_of(float(np.mean(fs[round((g0 + k * BEAT) * 1000):round((g0 + (k + 1) * BEAT) * 1000)])))
                  for k in range(nb)]

    def lvl_at(t: float) -> int:
        k = int(math.floor((t - g0) / BEAT + 1e-9))
        return beat_level[min(max(k, 0), nb - 1)]

    def cg(t: float) -> float:
        return CLOSE_GAIN if t >= t_now else 1.0

    def hit(name, sound, t, gain, pan=0.0):
        kit.place(bus[name], sound, t, gain, pan)

    def event(label, t, items):
        for name, sound, gain, pan in items:
            hit(name, sound, t, gain, pan)
        rec.append((label, t, t, [(s, g, p) for _, s, g, p in items]))

    # 0.00 s: the first sound, the sting's head; 0.30 to 2.30 s: the sting read backwards, its last attack on 1986
    sting = _sting()
    head = sting[:int(0.3 * SR)].copy()
    head[-int(0.02 * SR):] *= np.linspace(1.0, 0.0, int(0.02 * SR))[:, None]
    hit("intro", head, 0.0, 1.0)
    rec.append(("0 s: the first sound, a setar sting", 0.0, 0.0))
    hit("intro", _rewind_rise(sting, round((tm["t_first"] - 0.3) * SR)), 0.3, 1.0)
    rec.append(("1986: the sting ends on the tonic", tm["t_first"], tm["t_first"]))

    # the years, one tick each: the rewind, then the forward years (2026 is the close, at the end)
    for t, y in tm["rewind"]:
        event(f"rewind {y}", t, [("ticks", tick, 0.16, pan_of(y, y0, y1))])
    for t, y in tm["forward"]:
        event(f"forward {y}", t, [("ticks", tick, 0.13, pan_of(y, y0, y1))])

    # the line, a kamancheh from 1365 on E3: its pitch proportional to the bay's area; released as the decline starts
    tl = np.arange(int(round((t_dec + LINE_RELEASE - tm["t_first"]) * SR))) / SR
    area_t = np.interp(tm["t_first"] + tl, cv["pt"], cv["pa"])
    line = _kamancheh(deg(0, -1) * area_t / cv["areas"][y0], vel=0.8, release=LINE_RELEASE)
    hit("line", line, tm["t_first"], 0.9, -0.15)

    # the drone, from the first sea level (1372) on: its pitch follows the level on the screen
    f_drone = drone_hz(np.interp(t_all, cv["lt"], cv["lv"]))
    env = np.clip((t_all - tm["t_level"]) / DRONE_FADE, 0.0, 1.0)
    env = env * (1.0 - (1.0 - CLOSE_DRONE) * np.clip((t_all - t_now) / 0.8, 0.0, 1.0))   # quiet from 1405 on
    hit("drone", _drone(f_drone, env, vel=0.7), 0.0, 1.0)

    # the groove, bar by bar from the bar line after 1372; each sound sounds while its layer is on
    for b in np.arange(g0, GROOVE_END, BAR):
        for off, need, voice, g, pan in GROOVE:
            t = b + off
            if t >= GROOVE_END or lvl_at(t) < need:
                continue
            if voice == "kick":
                kicks.append(t)
            hit("drum", S[voice], t, g * cg(t), pan)
        for k8 in range(8):
            t = b + 0.25 * k8
            if t >= GROOVE_END:
                break
            lv = lvl_at(t)
            pan = 0.25 if k8 % 2 else -0.25
            if lv >= 2:
                hit("drum", S["hat"], t, (0.12 if k8 % 2 == 0 else 0.07) * cg(t), pan)
            elif lv == 1 and k8 % 2 == 0:
                hit("drum", S["hat"], t, 0.10 * cg(t), pan)
            if lv >= 3:
                hit("santur", kit.santur(deg(CHORD[ARP[k8]], 0), dur=1.2, vel=0.3, t60=1.5), t, 0.9 * cg(t))

    # the hook, two bars, at the bar line of the plateau and again in the decline; its notes drop out as the bay shrinks
    for h in (g0, g0 + 2 * BAR):
        for i, (dt, step, length) in enumerate(HOOK):
            t = h + dt
            gate = _gate(float(np.interp(t, grid, fs)), HOOK_TH[i])
            if gate <= 0.0 or t >= GROOVE_END:
                continue
            s = kit.setar(deg(step, 0), dur=length + 0.6, vel=0.9, t60=1.6, bright=0.5, buzz=0.1)
            hit("hook", s, t, 0.75 * gate, pan=0.25 if i % 2 == 0 else -0.25)

    # 7.60 s, scene 2's line, 'about half': the number lands
    items = [("santur", kit.santur(deg(s, 0), dur=3.0, vel=0.6, t60=2.6), 0.9, 0.0) for s in CHORD]
    items += [("drum", S["bam"], 0.9, 0.0), ("drum", S["clap"], 0.35, 0.0),
              ("drone", kit.sub(kit.note_hz("E1"), dur=0.6, vel=0.8), 0.8, 0.0)]
    event('7.60 s, scene 2 "about half": the chord, the bam, the clap', tm["stop"], items)

    # 13.60 s, scene 3's line, '2.5 to 2.7 m lower': the drone drops an octave, a tom, a kick, a low chord
    f_drop = float(drone_hz(np.interp(tm["accent2"], cv["lt"], cv["lv"])))
    items = [("drum", S["kick"], 0.9, 0.0), ("drum", S["tom"], 1.0, 0.0),
             ("drone", kit.sub(kit.note_hz("E1"), dur=1.0, vel=0.9, glide_from=f_drop, glide_s=0.15), 0.9, 0.0)]
    items += [("santur", kit.santur(deg(s, -1), dur=4.0, vel=0.6, t60=3.0), 0.9, 0.0) for s in CHORD]
    kicks.append(tm["accent2"])
    event('13.60 s, scene 3 "2.5 to 2.7 m lower": the drop, the tom, the low chord', tm["accent2"], items)

    # 15.20 s, 1405 arrives: a quiet, unresolved close (a tick, a setar note on G-sori, a daf rim)
    items = [("ticks", tick, 0.14, pan_of(y1, y0, y1)),
             ("hook", kit.setar(deg(2, 0), dur=2.4, vel=0.7, t60=2.2, bright=0.4, buzz=0.05), 0.8, -0.15),
             ("drum", S["tak"], 0.5, 0.0)]
    event("15.20 s, 1405 arrives: a quiet, unresolved close", t_now, items)
    return bus, kicks, cv, tm


def mix_bus(bus: dict, kicks: list, n: int) -> np.ndarray:
    """The buses summed. The harmony (the santur, the hook and the line) ducks under the kick and has a room; the hook
    has an echo; the drone is mono; the sting, the ticks, the accents and the drums are dry."""
    harm = kit.duck(kit.widen(bus["santur"], 0.3) + bus["hook"] + bus["line"], kicks, depth_db=3.0, release=0.15)
    wet = kit.reverb(harm, t60=1.8) * 0.25
    echo = kit.pingpong(bus["hook"] * 0.5, delay=0.375, feedback=0.35, taps=4) * 0.5
    mix = (bus["drum"] + harm + _fit(wet, n) + _fit(echo, n) + bus["drone"] + bus["intro"] + bus["ticks"]
           + bus["fx"])
    return _bass_mono(mix)


def render(film, log: list | None = None):
    """The mastered track, the mix before the master (for the verification), the curves and the buses."""
    rec = [] if log is None else log
    bus, kicks, cv, tm = _compose(film, rec)
    mix = mix_bus(bus, kicks, len(bus["fx"]))
    track = kit.master(mix, lufs=LUFS, tp=TP, seconds=tm["end"], fade_out=1.0)
    return track, mix, cv, bus


# ── checks ──────────────────────────────────────────────────────────────────

def _read_wav(path) -> np.ndarray:
    rate, pcm = wavfile.read(str(path))
    assert rate == SR and pcm.ndim == 2 and pcm.shape[1] == 2, (rate, pcm.shape)
    return pcm.astype(float) / 32768.0


def _decode(media) -> np.ndarray:
    """The audio of a media file as a player decodes it, stereo at 48 kHz."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(media), "-vn", "-f", "f32le", "-ac", "2",
                          "-ar", str(SR), "-"], check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype="<f4").reshape(-1, 2).astype(float)


def _probe(media) -> dict:
    raw = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "format=duration:stream=index,codec_type,codec_name,width,height,r_frame_rate,"
                          "nb_frames,duration,sample_rate,channels", "-of", "json", str(media)],
                         check=True, capture_output=True, text=True).stdout
    return json.loads(raw)


def _md5(media, stream: str) -> str:
    """The MD5 of one stream's packets, copied without re-encoding: equal digests mean the same video."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(media), "-map", stream, "-c", "copy", "-f", "md5", "-"],
                         check=True, capture_output=True, text=True).stdout
    return raw.strip()


def _frame(media, t: float, shape=(1920, 1080)) -> np.ndarray:
    """The RGB frame of a video at time t (s), as integers."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(media), "-ss", f"{t:.4f}", "-frames:v", "1",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], check=True, capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(shape[0], shape[1], 3).astype(int)


def _db(seg) -> float:
    return float(20 * np.log10(np.sqrt(np.mean(np.square(seg))) + 1e-12))


def _flux(x, hop: int = 48, nfft: int = 256):
    """Spectral flux of a mono signal, frames 1 ms apart and 5.3 ms long: the rise of the log magnitude from one frame
    to the next, summed over the bins. Returns each frame's centre time (s) and the flux."""
    y = np.concatenate([np.zeros(nfft), x])
    starts = np.arange(0, len(y) - nfft + 1, hop)
    frames = y[starts[:, None] + np.arange(nfft)[None, :]] * np.hanning(nfft)
    logm = np.log10(np.abs(np.fft.rfft(frames, axis=1)) + 1e-5)
    rise = np.maximum(np.diff(logm, axis=0, prepend=logm[:1]), 0.0).sum(axis=1)
    return (starts - nfft / 2) / SR, rise


def _flux_onset(times, rise, t: float, w: float = MAX_OFFSET):
    """The offset (s) of the strongest flux peak within w of t, or None if there is none."""
    sel = np.flatnonzero(np.abs(times - t) <= w)
    return None if len(sel) == 0 else float(times[sel[np.argmax(rise[sel])]] - t)


def _pitch(x, t0: float, t1: float, lo: float, hi: float) -> float:
    """The strongest partial of x between t0 and t1 (s) within lo to hi Hz: a Hann window, zero-padded, and a
    parabolic fit on the log magnitude."""
    seg = np.asarray(x[round(t0 * SR):round(t1 * SR)], float)
    seg = seg * np.hanning(len(seg))
    N = 1 << 20
    spec = np.abs(np.fft.rfft(seg, N))
    fr = np.fft.rfftfreq(N, 1.0 / SR)
    band = np.flatnonzero((fr >= lo) & (fr <= hi))
    k = int(band[np.argmax(spec[band])])
    a, b, c = np.log(spec[k - 1:k + 2] + 1e-12)
    d = 0.5 * (a - c) / (a - 2 * b + c)
    return float((k + d) * SR / N)


def check(film, wav, video, out, log: list, mix, cv: dict, bus: dict, untouched: bool) -> None:
    """Print the numbers and assert the checks."""
    x = _read_wav(wav)
    lufs, tp = kit.integrated_lufs(x), kit.true_peak_dbtp(x)
    dec = _decode(out)
    aac_lufs, aac_tp = kit.integrated_lufs(dec), kit.aac_true_peak(out)
    vid, mux_p = _probe(video), _probe(out)
    a_dur = [float(s["duration"]) for s in mux_p["streams"] if s["codec_type"] == "audio"][0]
    print(f"durations: WAV {len(x) / SR:.3f} s; silent reel video {float(vid['format']['duration']):.3f} s; "
          f"muxed MP4 {float(mux_p['format']['duration']):.3f} s (its audio stream {a_dur:.3f} s)")

    print("\n(1) loudness and true peak")
    print(f"    WAV            {lufs:+.2f} LUFS   {tp:+.2f} dBTP")
    print(f"    MP4 (decoded)  {aac_lufs:+.2f} LUFS   {aac_tp:+.2f} dBTP")
    assert -14.5 <= lufs <= -13.5 and -14.5 <= aac_lufs <= -13.5, (lufs, aac_lufs)
    assert tp <= -1 and aac_tp <= -1, (tp, aac_tp)

    print("\n(2) the first 0.1 s: sound from the first frame")
    head = x[:int(0.1 * SR)]
    loud = np.flatnonzero(np.abs(x).max(axis=1) > 0.1)                 # the first sample above -20 dBFS
    assert loud.size, "no sound above -20 dBFS"
    first_ms = 1000 * loud[0] / SR
    peak_db = 20 * np.log10(np.abs(head).max())
    print(f"    RMS {_db(head):.1f} dBFS, peak {peak_db:.1f} dBFS, first sample above -20 dBFS at {first_ms:.2f} ms")
    assert peak_db > -20 and first_ms < 20, "no sound in the first frame"

    print("\n(3) the last second, RMS per 0.1 s (dBFS)")
    win = int(0.1 * SR)
    ends = [_db(x[len(x) - (k + 1) * win:len(x) - k * win]) for k in range(10)][::-1]
    last_step = np.abs(np.diff(x[-int(0.005 * SR):], axis=0)).max()
    print("    " + " ".join(f"{v:.1f}" for v in ends))
    print(f"    last sample {abs(x[-1, 0]):.2e}, largest step in the last 5 ms {last_step:.2e}")
    assert ends[-1] < ends[0] - 10 and abs(x[-1, 0]) < 1e-3 and last_step < 2e-3, "the ending is not a clean fade"

    print("\n(4) per second: the film's bay and level on screen, the groove's layer, the drone and the line (Hz)")
    tm = timing(film)
    grid = np.arange(int(round(tm["end"] * 1000)) + 1) / 1000.0
    rms = [_db(x[k * SR:(k + 1) * SR]) for k in range(20)]
    print("    s   year shown  km2 on screen  share  groove  level m  drone Hz  line Hz    RMS dB")
    for k in range(20):
        t = k + 0.5
        a, b, w = film.state(t)
        shown = b if w >= 0.5 else a
        share = float(np.interp(t, grid, cv["share_s"]))
        lv = float(np.interp(t, cv["lt"], cv["lv"])) if t >= tm["t_level"] else float("nan")
        dr = f"{float(drone_hz(lv)):7.1f}" if np.isfinite(lv) else "      -"
        ln = "      -"
        if tm["t_first"] <= t < tm["t_decline"] + LINE_RELEASE:
            ln = f"{deg(0, -1) * float(np.interp(t, cv['pt'], cv['pa'])) / cv['areas'][tm['y0']]:7.1f}"
        print(f"    {k:>2d}  {shown:>10d}  {film.label[shown]:>13s}  {share:6.3f}  {level_of(share):>6d} {lv:8.2f}"
              f"  {dr}  {ln}  {rms[k]:7.1f}")
    print(f"    the film shows {film.label[tm['y1']]} km2 for {tm['y1']} and {film.label[tm['y0']]} for {tm['y0']}; "
          f"bridged (no number on screen): {cv['bridged']}")
    dry = np.mean(rms[10:12])
    full = np.mean(rms[4:6])
    print(f"    groove and line at 4-6 s {full:.1f} dB; decline at 10-12 s {dry:.1f} dB: {full - dry:+.1f} dB")
    for h in (tm["groove0"], tm["groove0"] + 2 * BAR):
        gates = [_gate(float(np.interp(h + dt, grid, cv["share_s"])), HOOK_TH[i]) for i, (dt, _, _) in enumerate(HOOK)]
        names = "G-sori B A F-koron G-sori E".split()
        print(f"    hook at {h:.1f} s, note gates: " + "  ".join(f"{nm} {g:.2f}" for nm, g in zip(names, gates)))
    assert full > dry, "the decline is not quieter than the plateau"

    print("\n(5) the events: onsets in the WAV (isolated sounds) and in the cleared WAV (the ticks and accents)")
    hp = butter(2, 12.0, "highpass", fs=SR, output="sos")             # the master's DC blocker
    u = sosfilt(hp, mix[:len(x)], axis=0)
    w1 = round(0.001 * SR) | 1
    num = uniform_filter1d((x * u).sum(axis=1), w1, mode="nearest")
    den = uniform_filter1d((u * u).sum(axis=1), w1, mode="nearest")
    gain = num / np.maximum(den, 1e-12)                               # the master as a gain curve, per sample
    print(f"    the master as a gain curve on the mix: median {20 * np.log10(np.median(gain)):+.2f} dB")
    times, rise = _flux(x.mean(axis=1))
    rows = []
    for entry in log:
        label, visual, hit_t = entry[0], entry[1], entry[2]
        if len(entry) == 3:
            off, how = _flux_onset(times, rise, hit_t), "WAV"
        else:
            a = round((hit_t - 0.1) * SR)
            b = a + round(0.4 * SR)
            ev = kit.new_track(0.4)
            for sound, g, pan in entry[3]:
                kit.place(ev, sound, (round(hit_t * SR) - a) / SR, g, pan)
            cleared = x[a:b] - gain[a:b, None] * sosfilt(hp, mix[a:b] - _bass_mono(ev), axis=0)
            lt, lr = _flux(cleared.mean(axis=1))
            off, how = _flux_onset(lt, lr, 0.1), "cleared"
        rows.append((label, visual, hit_t, off, how))
    assert all(r[3] is not None for r in rows), "an event with no onset"
    print(f"    {'event':<66}{'visual s':>10}{'found s':>10}{'offset ms':>11}  method")
    for label, visual, hit_t, off, how in rows:
        if not label.startswith(("rewind", "forward")):
            print(f"    {label:<66}{visual:10.4f}{hit_t + off:10.4f}{off * 1000:+11.2f}  {how}")
    for group in ("rewind", "forward"):
        offs = np.array([r[3] for r in rows if r[0].startswith(group)]) * 1000
        print(f"    {group + ' ticks, n=' + str(len(offs)):<66} median offset {np.median(offs):+.2f} ms,"
              f" largest |offset| {np.abs(offs).max():.2f} ms")
    worst = max(abs(r[3]) for r in rows)
    assert worst <= MAX_OFFSET, worst
    print(f"    all {len(rows)} events: largest offset {worst * 1000:.2f} ms (limit {MAX_OFFSET * 1000:.0f} ms): pass")

    print("\n(6) the pitch of the drone against the level on the screen, and of the line against the bay (cents)")
    lt, lv = cv["lt"], cv["lv"]
    for t0, t1 in ((4.2, 5.2), (11.6, 13.4), (16.0, 18.0)):
        meas = _pitch(bus["drone"].mean(axis=1), t0, t1, 40.0, 120.0)
        tt = np.arange(round(t0 * SR), round(t1 * SR)) / SR
        exp = float(np.mean(drone_hz(np.interp(tt, lt, lv))))
        cents = 1200 * np.log2(meas / exp)
        print(f"    drone {t0:5.2f}-{t1:5.2f} s: {meas:7.2f} Hz, expected {exp:7.2f} Hz: {cents:+6.1f} cents")
        assert abs(cents) <= 15, (t0, t1, cents)
    for t0, t1 in ((4.2, 5.2),):
        meas = _pitch(bus["line"].mean(axis=1), t0, t1, 120.0, 400.0)
        tt = np.arange(round(t0 * SR), round(t1 * SR)) / SR
        exp = float(np.mean(deg(0, -1) * np.interp(tt, cv["pt"], cv["pa"]) / cv["areas"][tm["y0"]]))
        cents = 1200 * np.log2(meas / exp)
        print(f"    line  {t0:5.2f}-{t1:5.2f} s: {meas:7.2f} Hz, expected {exp:7.2f} Hz: {cents:+6.1f} cents")
        assert abs(cents) <= 25, (t0, t1, cents)

    print("\n(7) the video stream of the muxed MP4 against the silent reel")
    v_md5, m_md5 = _md5(video, "0:v:0"), _md5(out, "0:v:0")
    print(f"    silent reel {v_md5}")
    print(f"    muxed reel  {m_md5}")
    assert v_md5 == m_md5, "the video stream changed"
    vs = [s for s in mux_p["streams"] if s["codec_type"] == "video"][0]
    vs0 = [s for s in vid["streams"] if s["codec_type"] == "video"][0]
    print(f"    {vs['codec_name']} {vs['width']}x{vs['height']} {vs['r_frame_rate']} nb_frames {vs['nb_frames']}"
          f" (silent {vs0['nb_frames']}): same packets")
    assert untouched, "the silent reel was rewritten"
    print("    the silent reel was not rewritten (size and modification time unchanged)")

    print("\n(8) the silent reel shows the film as it is now (frames against a fresh draw, mean |difference|)")
    fps = float(vs0["r_frame_rate"].split("/")[0]) / float(vs0["r_frame_rate"].split("/")[1])
    for t in (1.3, 8.8, 11.5, 15.7):
        k = round(t * fps) / fps
        ref = np.asarray(film.draw(1, k).convert("RGB")).astype(int)
        d = np.abs(ref - _frame(video, k)).mean()
        print(f"    t={k:6.3f} s: {d:.2f}")
        assert d < 4.0, f"the silent reel differs from the film at {k} s: {d:.2f}"
    print("\nall checks pass")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.parse_args()
    block_geo_stack()
    film = film_mod.GorganFilm(onebit.THEMES[THEME], COLOURS[THEME])
    base = onebit.OUT / "social" / BASE
    video = Path(f"{base}_reel.mp4")
    wav = Path(f"{base}_music.wav")
    out = Path(f"{base}_music_reel.mp4")
    st = os.stat(video)
    before = (st.st_size, st.st_mtime_ns)
    log: list = []
    track, mix, cv, bus = render(film, log)
    kit.write_wav(wav, track)
    print("saved", wav)
    kit.mux(video, wav, out)
    print("saved", out)
    st2 = os.stat(video)
    check(film, wav, video, out, log, mix, cv, bus, untouched=before == (st2.st_size, st2.st_mtime_ns))


if __name__ == "__main__":
    main()
