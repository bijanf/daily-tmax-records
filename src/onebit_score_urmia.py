"""The score of the Lake Urmia reel (urmia_namak_fa, 20 s): an original track in Bayat-e Tork, built from
the Persian sound kit (onebit_persian) and timed to the film's own clock. Everything is synthesized here:
no samples, no voices.

The music dries up with the lake. The film's gauge gives an intensity I: 0 at 1269.5 m (the lowest reading)
and 1 at 1278 m, read from the water level on the screen (film.state, film.level, film.measured). Each layer
is on while I is above its threshold: the drums, the pad and the santur drop out one by one as the lake falls,
the hook loses its last notes, the whole ensemble follows I in level (16 dB down at 0), and a low-pass closes
as I falls (300 Hz at 0, 16 kHz at 1).

    0.00 s   the sting on the first frame: a dark chord on E and a rising setar figure
    0.30 s   the rewind: the sting played backwards, the tape speeding up, its pitch rising
    2.24 s   1365 (1986): the blue lake: a warm chord on A, a santur strike and a daf stroke; the rewind's
             last attack (E) lands on it
    2.80 s   the years run forward: a tick per year, its pitch the lake's level (E4 at the lowest reading,
             E5 at the highest); the full ensemble on the bar line at 3.0 s: half-time beat, sub, santur
             arpeggio, pad, a six-note setar hook
    7.60 s   'about 8 m': an impact, and the beat stops; a lone kamancheh line (from 6.0 s) carries on
    10.87 s  1404 (2025): the white lake: wind (filtered noise) and one setar note on D
    12.30 s  1405: the beat returns gently (intensity 0.62, about half the layers); the hook comes back an
             octave up and brighter
    13.60 s  'about 7 m below 1374': a santur chord on A and a daf rim
    19.00 s  the last hit on E; the tails fade over the last second to 20 s

The grid is 120 BPM (a beat 0.5 s, a bar 2 s), with its bar lines on the odd seconds (3, 5, 7, 13, 15, 17, 19 s).
The events that are not on it (2.24, 7.6, 12.3, 13.6 s) sit on their own film times. The per-year ticks are
soft plucks with a click, one for each rewound year and each forward year, at the film's own keyframe times;
their pitch follows the level of the year on the screen (gap years hold the last reading, as the gauge does).

    python -inten src/onebit_score_urmia.py

writes outputs/onebit/social/urmia_namak_fa_music.wav and muxes it under the silent reel into
urmia_namak_fa_music_reel.mp4 (the silent reel is not rewritten). It prints the loudness and the true peak
of the WAV and of the MP4's decoded audio, the RMS per second with the intensity, the onsets of the events
(in the WAV, and in the decoded MP4), the tick offsets, the durations, and the video stream against the
silent reel.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.ndimage import uniform_filter1d
from scipy.signal import butter, sosfilt

sys.path.insert(0, str(Path(__file__).resolve().parent))

import onebit  # noqa: E402
import onebit_persian as kit  # noqa: E402
import onebit_urmia  # noqa: E402
from onebit_slides import COLOURS  # noqa: E402

SR = kit.SR
BAR = kit.BAR                              # 2 s at 120 BPM
MODE = "bayat_tork"                        # E, F#, G-koron, A, B, C, D
TONIC = "E4"
TAIL = 3.0                                 # s of room past the end, for the reverb
LUFS, TP = -14.0, -2.0                     # -2 dBTP: the AAC encoding of this track overshoots by a few tenths
MAX_OFFSET = 0.030                         # s: a hit may sit at most this far from its event
BASE = "urmia_namak_fa"
GROOVE0 = 3.0                              # s: the first bar line of the groove
LAST_HIT = 19.0                            # s: the last bar line, where the last hit falls
LEVEL_LOW, LEVEL_HIGH = 1269.5, 1278.0     # m: intensity 0 (the lowest reading) and 1 (almost full)
I_RET = 0.62                               # the intensity of 1405: about half the layers
F_LO = 0.15                                # the ensemble's level at intensity 0, against its level at 1 (about -16 dB)
GATE_WIDTH = 0.10                          # a layer's gate opens over this much intensity
CUT_LO, CUT_HI, N_CUT = 300.0, 16000.0, 8  # the closing low-pass: its range, and the fixed filters it morphs between
BUSES = ("intro", "fx", "lead", "data", "kick", "drum", "pad", "santur", "hook", "sub")
CHORD = (0, 2, 4)                          # the tonic triad's steps; the arpeggio walks over it in eighths
ARP = (0, 1, 2, 1, 0, 1, 2, 1)
# the hook: (time from its start in s, mode step, length in s); two bars
HOOK = ((0.0, 4, 0.5), (0.5, 2, 0.5), (1.0, 0, 1.0), (2.0, 3, 0.5), (2.5, 4, 0.5), (3.0, 6, 1.0))
HOOK_TH = (0.10, 0.25, 0.40, 0.50, 0.60, 0.70)    # the intensity below which each hook note drops out
KAM = ((6.0, 4, 0.9), (7.0, 2, 0.5), (7.6, 1, 0.9), (8.6, 2, 0.6), (9.3, 0, 1.3))   # the kamancheh line


def block_geo_stack() -> None:
    """Keep the geo stack out of this process: the film reads only CSV and npz, and the repo's rule is
    that no process holding netCDF readers imports shapely or cartopy (see onebit_score_wateryear)."""
    for name in ("shapely", "cartopy", "fiona", "rasterio", "pyproj", "geopandas"):
        if name not in sys.modules:
            sys.modules[name] = None


def deg(step: int, octave: int = 0) -> float:
    return kit.degree(MODE, step, octave)


# ── the film's clock and the lake's level ───────────────────────────────────

def timing(film) -> dict:
    """The film's own times: the keyframes of 1365, 1404 and 1405, the two lines the music answers, and the
    years' keyframes (the rewind's keys, and the forward pass's film.at)."""
    keys = [(float(t), int(y)) for t, y in film.keys]
    st = [float(s) for s in film.starts]
    assert len(st) == 4 and st == sorted(st), st
    t_blue = min(t for t, y in keys if y == 1986)
    tm = dict(starts=st, end=st[-1], t1365=t_blue,
              t1404=float(film.at[2025]), t1405=float(film.at[2026]),
              collapse=st[1] + float(film.later(1)), accent=st[2] + float(film.later(2)),
              rew=[(t, y) for t, y in keys if 0.0 < t <= t_blue + 1e-9],
              fwd=[(float(film.at[y]), int(y)) for y in sorted(film.at) if 1987 <= y <= 2025])
    assert tm["t1365"] < tm["collapse"] < tm["t1404"] < tm["t1405"] < tm["accent"] < LAST_HIT, tm
    return tm


def _year_level(film, y: int) -> float:
    """The gauge's reading for a year: its own, or the last measured year's (the gauge's heading names it)."""
    return float(film.level.loc[film.measured[y]])


def level_now(film, t: float) -> float:
    """The water level on the screen at time t (m): the two years' readings, blended as the picture is."""
    a, b, w = film.state(t)
    return (1.0 - w) * _year_level(film, a) + w * _year_level(film, b)


def _ramp(t, a: float, b: float):
    return np.clip((t - a) / (b - a), 0.0, 1.0)


def intensity(film, t_all: np.ndarray, tm: dict) -> np.ndarray:
    """I per sample. From the blue lake to the collapse it follows the lake (0 at 1269.5 m, 1 at 1278 m);
    the collapse takes it to 0 within 40 ms; from 1405 it rises to I_RET over 0.3 s and holds until the last
    hit, where it falls to 0."""
    grid = np.arange(0.0, tm["end"] + 0.5, 0.002)
    lev = np.array([level_now(film, float(t)) for t in grid])
    u = np.clip((np.interp(t_all, grid, lev) - LEVEL_LOW) / (LEVEL_HIGH - LEVEL_LOW), 0.0, 1.0)
    lake = u * (t_all >= tm["t1365"]) * (1.0 - _ramp(t_all, tm["collapse"], tm["collapse"] + 0.04))
    back = I_RET * _ramp(t_all, tm["t1405"], tm["t1405"] + 0.3) * (1.0 - _ramp(t_all, LAST_HIT, LAST_HIT + 0.04))
    return lake + back


def _gate(inten, th: float):
    """A layer's gate: 0 below th, 1 above th + GATE_WIDTH, smooth between."""
    x = np.clip((np.asarray(inten, float) - th) / GATE_WIDTH, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def _tone(level: float) -> float:
    """A tick's pitch: E4 at the lowest reading, E5 at the highest, along the mode, continuous in the level."""
    u = float(np.clip((level - LEVEL_LOW) / (LEVEL_HIGH - LEVEL_LOW), 0.0, 1.0))
    cents = np.array(kit.mode_cents(MODE) + (1200,), float)
    return kit.note_hz(TONIC) * 2.0 ** (float(np.interp(7.0 * u, np.arange(8), cents)) / 1200.0)


# ── sounds ──────────────────────────────────────────────────────────────────

def _tick() -> np.ndarray:
    """A soft tick: a band-passed click of 3 ms with its own noise seed."""
    n = int(0.02 * SR)
    t = np.arange(n) / SR
    noise = np.random.default_rng(31).standard_normal(n)
    x = sosfilt(butter(2, (1500.0, 5000.0), "bandpass", fs=SR, output="sos"), noise) * np.exp(-t / 0.003)
    x = x * np.minimum(1.0, t / 0.0005)
    return x / np.abs(x).max()


def _sounds() -> dict:
    return dict(kick=kit.kick808(kit.note_hz("E1"), vel=1.0, decay=0.9, drive=1.3),
                snare=kit.snare(), clap=kit.clap(), hat=kit.hat(False),
                bam=kit.daf("bam", pitch=kit.note_hz("E2")), bamA=kit.daf("bam", pitch=kit.note_hz("A2")),
                tak=kit.daf("tak", pitch=kit.note_hz("E4")), takA=kit.daf("tak", pitch=kit.note_hz("A3")),
                zang=kit.daf("zang"))


def _sting() -> np.ndarray:
    """The sting: three setar notes, E4, G-koron 4 and B4, 0.15 s apart, ringing; its last 30 ms faded."""
    x = kit.new_track(1.3)
    for k, step in enumerate((0, 2, 4)):
        s = kit.setar(deg(step, 0), dur=1.2, vel=0.9, t60=1.5, bright=0.6, buzz=0.15)
        kit.place(x, s, 0.15 * k, 0.8, pan=(-0.2, 0.0, 0.2)[k])
    m = int(0.03 * SR)
    x[-m:] *= np.linspace(1.0, 0.0, m)[:, None]
    return x


def _rewind_rise(x: np.ndarray, n_out: int, v0: float = 0.25) -> np.ndarray:
    """The sting played backwards from its end to its start, the tape speeding up as it goes: the read speed
    rises linearly from v0 to v1 (samples per output sample), with v1 set so that the whole sting is read in
    n_out samples; its first attack arrives on the last sample. The pitch rises with the speed."""
    x = np.asarray(x, float)
    avg = (len(x) - 1) / n_out
    v1 = 2.0 * avg - v0
    v = v0 + (v1 - v0) * np.arange(n_out) / max(n_out - 1, 1)
    pos = (len(x) - 1) - np.concatenate([[0.0], np.cumsum(v)[:-1]])
    pos = np.clip(pos, 0.0, len(x) - 1)
    idx = np.arange(len(x))
    return np.stack([np.interp(pos, idx, x[:, c]) for c in range(x.shape[1])], axis=1)


def _wind(n: int, t_all: np.ndarray, t0: float, t1: float) -> np.ndarray:
    """The wind over the white lake: two channels of band-passed noise, gusting slowly, faded in from t0 and
    out by t1."""
    rng = np.random.default_rng(11)
    sos = butter(2, (120.0, 1000.0), "bandpass", fs=SR, output="sos")
    w = np.stack([sosfilt(sos, rng.standard_normal(n)), sosfilt(sos, rng.standard_normal(n))], axis=1)
    w = w / np.abs(w).max()
    env = (_ramp(t_all, t0, t0 + 0.9) * (1.0 - _ramp(t_all, t1, t1 + 0.4))
           * (0.7 + 0.3 * np.sin(2 * np.pi * 0.21 * t_all)))
    return 0.1 * w * env[:, None]


# ── the composition ─────────────────────────────────────────────────────────

def _groove(hit, S: dict, b: float, stop: float, kicks: list) -> None:
    """One bar of the half-time groove from the bar line b: kicks on the 1, the 'and' of 2 and the 'and' of 3;
    the backbeat (snare and clap) on 3; the daf's centre on 1 and 3 and its rim between; hats on the eighths,
    the quarters alone at the lower level. Each layer opens at its own intensity."""
    for off in (0.0, 0.75, 1.25):
        if hit("kick", S["kick"], b + off, 0.9, th=0.0, until=stop):
            kicks.append(b + off)
    hit("drum", S["snare"], b + 1.0, 0.5, th=0.45, until=stop)
    hit("drum", S["clap"], b + 1.0, 0.3, th=0.45, until=stop)
    for off in (0.0, 1.0):
        hit("drum", S["bam"], b + off, 0.5, th=0.5, until=stop)
    for off in (0.375, 0.75, 1.375, 1.75):
        hit("drum", S["tak"], b + off, 0.34, pan=-0.3 if off < 1.0 else 0.3, th=0.6, until=stop)
    for k in range(8):
        g = 0.12 if k % 4 == 0 else 0.07 if k % 2 == 0 else 0.06
        hit("drum", S["hat"], b + 0.25 * k, g, pan=0.25 if k % 2 else -0.25,
            th=0.5 if k % 2 == 0 else 0.75, until=stop)


def _hook(hit, bus: str, t0: float, octave: int, gain: float, bright: float, th=None) -> None:
    """The six-note setar hook, two bars from t0: the notes alternate sides; with th, each note is gated."""
    for i, (dt, step, length) in enumerate(HOOK):
        s = kit.setar(deg(step, octave), dur=length + 0.6, vel=1.0, t60=1.6, bright=bright, buzz=0.12)
        hit(bus, s, t0 + dt, gain, pan=0.25 if i % 2 == 0 else -0.25, th=None if th is None else th[i])


def _compose(film, rec: list):
    """Lay the score on its buses. Returns (buses, the intensity per sample, the kick times, the length in s).
    `rec` receives one entry per event: (label, visual time, time of the hit placed on it), and for the ticks a
    fourth item, the sounds placed for them as (sound, gain, pan), so that the verification can clear them."""
    kit.reseed(19)
    tm = timing(film)
    seconds = tm["end"]
    bus = {k: kit.new_track(seconds, TAIL) for k in BUSES}
    n = len(bus["fx"])
    t_all = np.arange(n) / SR
    inten = intensity(film, t_all, tm)
    S = _sounds()
    kicks: list = []

    def hit(name, sound, t, gain, pan=0.0, th=None, until=None):
        """Place a sound on a bus at t. th gates it by the intensity at t (its layer is on above th);
        until drops it if t is not before that time. Returns the gain placed, 0 if none."""
        if until is not None and t >= until:
            return 0.0
        g = gain
        if th is not None:
            g *= float(_gate(inten[min(int(round(t * SR)), n - 1)], th))
        if g <= 0.0:
            return 0.0
        kit.place(bus[name], sound, t, g, pan)
        return g

    t_blue, t_white, t_new = tm["t1365"], tm["t1404"], tm["t1405"]
    stop, accent = tm["collapse"], tm["accent"]

    # ── the sting: from the first frame, a dark chord on E and a rising setar figure ──
    hit("intro", kit.pad([deg(s, -2) for s in CHORD], dur=2.25, vel=0.42, width=1.0, detune=9.0,
                         cutoff=600.0, attack=0.5, release=0.3), 0.0, 0.9)
    hit("intro", kit.sub(kit.note_hz("E1"), dur=2.2, vel=0.6), 0.0, 0.8)
    sting = _sting()
    head = sting[:int(0.3 * SR)].copy()
    head[-int(0.02 * SR):] *= np.linspace(1.0, 0.0, int(0.02 * SR))[:, None]
    hit("intro", head, 0.0, 1.0)

    # ── the rewind: the sting backwards, its pitch rising, one tick per rewound year ──
    hit("fx", _rewind_rise(sting, round((t_blue - 0.3) * SR)), 0.3, 0.7)
    for t, y in tm["rew"]:
        pl = kit.setar(_tone(_year_level(film, y)), dur=0.12, vel=0.5, t60=0.08, bright=0.8, buzz=0.0)
        ck = _tick()
        kit.place(bus["data"], pl, t, 0.35, 0.0)
        kit.place(bus["data"], ck, t, 0.14, 0.0)
        rec.append((f"rewind {y}", t, t, [(pl, 0.35, 0.0), (ck, 0.14, 0.0)]))

    # ── 1365, the blue lake: a warm chord on A, a santur strike, a daf stroke ──
    hit("pad", kit.pad([deg(s, -1) for s in (3, 5, 7)], dur=0.76 + 0.4, vel=0.45, width=0.9,
                       cutoff=2400.0, attack=0.06, release=0.4), t_blue, 1.0)
    for f in (deg(3, -1), deg(5, -1), deg(7, -1), deg(3, 0)):
        hit("santur", kit.santur(f, dur=4.0, vel=0.55, t60=3.0), t_blue, 1.0)
    hit("drum", S["bamA"], t_blue, 0.9, th=0.5)
    hit("sub", kit.sub(kit.note_hz("A1"), dur=0.76, vel=0.8, glide_from=kit.note_hz("E1")), t_blue, 0.9)
    rec.append(("1365: the blue lake, a warm chord", t_blue, t_blue))

    # ── the years run forward: the groove, the pad, the sub, the santur arpeggio and the hook ──
    hit("pad", kit.pad([deg(s, -1) for s in CHORD], dur=stop - GROOVE0 + 0.5, vel=0.42, width=0.9,
                       cutoff=2000.0, attack=0.3, release=0.5), GROOVE0, 1.0)
    hit("sub", kit.sub(kit.note_hz("E1"), dur=stop - GROOVE0, vel=0.9, glide_from=kit.note_hz("A1")), GROOVE0, 0.9)
    for b in (GROOVE0, GROOVE0 + BAR, GROOVE0 + 2 * BAR):          # 3, 5 and 7 s; 7 s stops at the collapse
        _groove(hit, S, b, stop, kicks)
    for j in range(int((stop - GROOVE0) / 0.25)):                  # eighths over E, until the collapse
        hit("santur", kit.santur(deg(CHORD[ARP[j % 8]], 1), dur=1.2, vel=0.4, t60=1.5), GROOVE0 + 0.25 * j, 1.0)
    _hook(hit, "hook", GROOVE0, octave=0, gain=0.85, bright=0.5, th=HOOK_TH)
    for t, y in tm["fwd"]:
        pl = kit.setar(_tone(_year_level(film, y)), dur=0.25, vel=0.5, t60=0.2, bright=0.8, buzz=0.0)
        ck = _tick()
        pan = 0.35 - 0.7 * (y - 1987) / (2025 - 1987)              # read from the right, as the picture is
        kit.place(bus["data"], pl, t, 0.45, pan)
        kit.place(bus["data"], ck, t, 0.14, pan)
        rec.append((f"forward {y}", t, t, [(pl, 0.45, pan), (ck, 0.14, pan)]))
    for t, step, length in KAM:                                    # the kamancheh line, carried on below
        kit.place(bus["lead"], kit.kamancheh(deg(step, 0), dur=length, vel=0.6, vib_hz=5.5, vib_cents=30.0,
                                             bow=0.15), t, 0.85, pan=-0.15)

    # ── 7.6 s, 'about 8 m': an impact, the beat stops ──
    hit("fx", kit.impact(2.2, vel=0.9, pitch=kit.note_hz("E1")), stop, 1.0)
    rec.append(('"about 8 m": the impact, the beat stops', stop, stop))

    # ── 10.87 s, 1404: the white lake, wind and one setar note ──
    bus["fx"] += _wind(n, t_all, t_white, t_new)
    kit.place(bus["lead"], kit.setar(deg(6, 0), dur=2.0, vel=0.9, t60=1.8, bright=0.4, buzz=0.05), t_white, 0.8)
    rec.append(("1404: the white lake, one setar note", t_white, t_white))

    # ── 12.3 s, 1405: the beat returns gently, the hook comes back an octave up and brighter ──
    hit("fx", S["kick"], t_new, 0.8)
    kicks.append(t_new)
    hit("fx", S["bam"], t_new, 0.5)
    hit("fx", kit.sub(kit.note_hz("E1"), dur=1.3, vel=0.7), t_new, 0.9)
    for f in (deg(0, 0), deg(2, 0), deg(4, 0)):
        hit("fx", kit.santur(f, dur=2.4, vel=0.35, t60=2.2), t_new, 1.0)
    hit("pad", kit.pad([deg(s, -1) for s in CHORD], dur=accent - t_new + 0.2, vel=0.4, width=0.9,
                       cutoff=2000.0, attack=0.3, release=0.2), t_new, 1.0)
    _hook(hit, "fx", t_new, octave=1, gain=0.8, bright=0.9)
    rec.append(("1405: the beat returns, the hook comes back brighter", t_new, t_new))
    for k in (5, 6, 7):                                            # the bars at 13, 15 and 17 s
        _groove(hit, S, GROOVE0 + k * BAR, LAST_HIT, kicks)

    # ── 13.6 s, 'about 7 m below 1374': a santur chord on A and a daf rim ──
    for f in (deg(3, -1), deg(5, -1), deg(7, -1), deg(3, 0)):
        hit("fx", kit.santur(f, dur=4.0, vel=0.6, t60=2.6), accent, 1.0)
    hit("fx", S["takA"], accent, 0.8)
    hit("pad", kit.pad([deg(s, -1) for s in (3, 5, 7)], dur=1.8, vel=0.4, width=0.9, cutoff=2400.0,
                       attack=0.06, release=0.4), accent, 1.0)
    hit("sub", kit.sub(kit.note_hz("A1"), dur=1.4, vel=0.8, glide_from=kit.note_hz("E1")), accent, 0.9)
    rec.append(('"about 7 m below 1374": the accent', accent, accent))

    # ── back on E from 15 s; the last hit at 19 s, the tails fade over the last second ──
    hit("pad", kit.pad([deg(s, -1) for s in CHORD], dur=LAST_HIT - 15.0 + 0.5, vel=0.42, width=0.9,
                       cutoff=2000.0, attack=0.3, release=0.5), 15.0, 1.0)
    hit("sub", kit.sub(kit.note_hz("E1"), dur=LAST_HIT - 15.0, vel=0.9, glide_from=kit.note_hz("A1")), 15.0, 0.9)
    t = LAST_HIT
    hit("fx", S["kick"], t, 1.0)
    kicks.append(t)
    hit("fx", S["bam"], t, 0.9)
    hit("fx", S["snare"], t, 0.45)
    hit("fx", S["clap"], t, 0.3)
    hit("fx", S["zang"], t, 0.35, pan=-0.2)
    for f in (deg(0, 0), deg(2, 0), deg(4, 0), deg(0, 1)):
        hit("fx", kit.santur(f, dur=3.4, vel=0.6, t60=3.0), t, 1.0)
    hit("fx", kit.pad([deg(s, -1) for s in CHORD], dur=3.2, vel=0.4, width=0.9, cutoff=2000.0,
                      attack=0.02, release=1.0), t, 1.0)
    hit("fx", kit.sub(kit.note_hz("E1"), dur=2.0, vel=0.95), t, 0.9)
    hit("fx", kit.setar(deg(7, 0), dur=2.4, vel=1.0, t60=2.2, bright=0.6, buzz=0.12), t, 0.9)
    rec.append(("19 s: the last hit on E", t, t))
    return bus, inten, kicks, seconds


# ── the mix ─────────────────────────────────────────────────────────────────

def _fit(x, n: int):
    """Crop or zero-pad x along time to n rows."""
    return x[:n] if len(x) >= n else np.concatenate([x, np.zeros((n - len(x),) + x.shape[1:])])


def _bass_mono(x, fc: float = 120.0) -> np.ndarray:
    """The low end in mono: everything below fc is averaged to one channel, and the rest stays wide."""
    low = sosfilt(butter(4, fc, "lowpass", fs=SR, output="sos"), x, axis=0)
    mid = 0.5 * (low[:, 0] + low[:, 1])
    out = x - low
    out[:, 0] += mid
    out[:, 1] += mid
    return out


def _lowpass_morph(x: np.ndarray, inten: np.ndarray) -> np.ndarray:
    """The closing low-pass: its cut-off follows I on a log scale, from CUT_LO at 0 to CUT_HI at 1. It is
    built from N_CUT fixed filters, and each sample takes its two nearest in proportion, so the closing is
    smooth and nothing clicks."""
    cuts = np.geomspace(CUT_LO, CUT_HI, N_CUT)
    pos = np.clip(np.asarray(inten, float), 0.0, 1.0) * (N_CUT - 1)
    i0 = np.minimum(np.floor(pos).astype(int), N_CUT - 2)
    w1 = pos - i0
    w0 = 1.0 - w1
    out = np.zeros_like(x)
    for k, fc in enumerate(cuts):
        wk = np.where(i0 == k, w0, 0.0) + np.where(i0 + 1 == k, w1, 0.0)
        if np.any(wk > 0):
            out += wk[:, None] * sosfilt(butter(4, float(fc), "lowpass", fs=SR, output="sos"), x, axis=0)
    return out


def mix_bus(bus: dict, inten: np.ndarray, kicks: list, n: int) -> np.ndarray:
    """The buses summed. The layers are gated by I and follow it in level (F_LO at 0, 1 at 1); the harmony is
    ducked under the kick and, with the rhythm, closed by the low-pass; the harmony has a room; the sub is
    mono; the sting, the wind, the kamancheh, the impacts and the ticks are dry and ungated."""
    fader = F_LO + (1.0 - F_LO) * inten
    pad = kit.widen(bus["pad"], 0.3) * (_gate(inten, 0.35) * fader)[:, None]
    santur = kit.widen(bus["santur"], 0.3) * (_gate(inten, 0.55) * fader)[:, None]
    sub = bus["sub"] * (_gate(inten, 0.0) * fader)[:, None]
    harm = kit.duck(pad + santur + bus["hook"] * fader[:, None], kicks, depth_db=3.0, release=0.15)
    harm_m = _lowpass_morph(harm, inten)
    rhy_m = _lowpass_morph((bus["kick"] + bus["drum"]) * fader[:, None], inten)
    wet = _fit(kit.reverb(harm_m, t60=1.4) * 0.3, n)
    mix = rhy_m + harm_m + wet + sub + bus["intro"] + bus["lead"] + bus["fx"] + bus["data"]
    return _bass_mono(mix)


def render(film, log: list | None = None):
    """The mastered track, the mix before the master (for the verification), and the intensity per sample."""
    rec = [] if log is None else log
    bus, inten, kicks, seconds = _compose(film, rec)
    mix = mix_bus(bus, inten, kicks, len(bus["fx"]))
    return kit.master(mix, lufs=LUFS, tp=TP, seconds=seconds, fade_out=1.0), mix, inten


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


def _db(seg) -> float:
    return float(20 * np.log10(np.sqrt(np.mean(np.square(seg))) + 1e-12))


def _flux(x, hop: int = 48, nfft: int = 256):
    """Spectral flux of a mono signal, frames 1 ms apart and 5.3 ms long: the rise of the log magnitude from
    one frame to the next, summed over the bins. Returns each frame's centre time (s) and the flux."""
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


def check(film, wav, video, out, log: list, mix, inten, untouched: bool) -> None:
    """Print the numbers and the event table, and assert the checks."""
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

    print("\n(2) the first 0.1 s")
    head = x[:int(0.1 * SR)]
    print(f"    RMS {_db(head):.1f} dBFS, peak {np.abs(head).max():.3f}")
    assert _db(head) > -30, "silent start"

    print("\n(3) the last second, RMS per 0.1 s (dBFS)")
    win = int(0.1 * SR)
    ends = [_db(x[len(x) - (k + 1) * win:len(x) - k * win]) for k in range(10)][::-1]
    last_step = np.abs(np.diff(x[-int(0.005 * SR):], axis=0)).max()
    print("    " + " ".join(f"{v:.1f}" for v in ends))
    print(f"    last sample {abs(x[-1, 0]):.2e}, largest step in the last 5 ms {last_step:.2e}")
    assert ends[-1] < ends[0] - 10 and abs(x[-1, 0]) < 1e-3 and last_step < 2e-3, "the ending is not a clean fade"

    print("\n(4) RMS per 1 s of the WAV (dBFS), and the intensity I at the middle of each second")
    rms = [_db(x[k * SR:(k + 1) * SR]) for k in range(20)]
    print("    s  " + " ".join(f"{k:>4d}" for k in range(20)))
    print("    dB " + " ".join(f"{v:>4.0f}" for v in rms))
    print("    I  " + " ".join(f"{inten[int((k + 0.5) * SR)]:>4.2f}" for k in range(20)))
    mono = x.mean(axis=1)

    print("\n(5) the events: onsets in the WAV (isolated sounds) and in the cleared WAV (the ticks)")
    hp = butter(2, 12.0, "highpass", fs=SR, output="sos")          # the master's DC blocker
    u = sosfilt(hp, mix[:len(x)], axis=0)                           # the mix through it: the master's input
    w1 = round(0.001 * SR) | 1
    num = uniform_filter1d((x * u).sum(axis=1), w1, mode="nearest")
    den = uniform_filter1d((u * u).sum(axis=1), w1, mode="nearest")
    gain = num / np.maximum(den, 1e-12)                             # the master as a gain curve, per sample
    print(f"    the master as a gain curve on the mix: median {20 * np.log10(np.median(gain)):+.2f} dB")
    times, rise = _flux(mono)
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
    print(f"    {'event':<50}{'visual s':>10}{'found s':>10}{'offset ms':>11}  method")
    for label, visual, hit_t, off, how in rows:
        if not label.startswith(("rewind", "forward")):
            print(f"    {label:<50}{visual:10.4f}{hit_t + off:10.4f}{off * 1000:+11.2f}  {how}")
    for group in ("rewind", "forward"):
        offs = np.array([r[3] for r in rows if r[0].startswith(group)]) * 1000
        print(f"    {group + ' ticks, n=' + str(len(offs)):<50} median offset {np.median(offs):+.2f} ms,"
              f" largest |offset| {np.abs(offs).max():.2f} ms")
    worst = max(abs(r[3]) for r in rows)
    assert worst <= MAX_OFFSET, worst
    print(f"    all {len(rows)} events: largest offset {worst * 1000:.2f} ms (limit {MAX_OFFSET * 1000:.0f} ms): pass")

    print("\n    through the MP4's AAC audio, decoded (the isolated events, offset in ms):")
    dtimes, drise = _flux(dec.mean(axis=1))
    for label, visual, hit_t, *placed in log:
        if not placed:
            off = _flux_onset(dtimes, drise, hit_t)
            print(f"      {label:<50} {'-' if off is None else f'{off * 1000:+7.2f}'}")

    print("\n(6) the video stream of the muxed MP4 against the silent reel")
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
    print("\nall checks pass")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.parse_args()
    block_geo_stack()
    film = onebit_urmia.UrmiaFilm(onebit.THEMES["namak"], COLOURS["namak"])
    base = onebit.OUT / "social" / BASE
    video = Path(f"{base}_reel.mp4")
    wav = Path(f"{base}_music.wav")
    out = Path(f"{base}_music_reel.mp4")
    st = os.stat(video)
    before = (st.st_size, st.st_mtime_ns)
    log: list = []
    track, mix, inten = render(film, log)
    kit.write_wav(wav, track)
    print("saved", wav)
    kit.mux(video, wav, out)
    print("saved", out)
    st2 = os.stat(video)
    check(film, wav, video, out, log, mix, inten, untouched=before == (st2.st_size, st2.st_mtime_ns))


if __name__ == "__main__":
    main()
