"""The score of the Zayandeh Rud reel (zayandeh_naqsh_fa, 20 s): an original track in Avaz-e Esfahan, built from
the Persian sound kit (onebit_persian) and timed to the film's own clock. Everything is synthesized here: no
samples, no voices.

The river's pulse. The film shows, for each picture year, the Persian months in which Landsat saw the river
flowing (film.cal: 'full', 'low', 'dry' or 'none'). The music counts the same months: the flow is the full months
plus half the low ones, of the picture on screen (blended as the film blends). A layer is on when the flow
averaged over its window reaches its threshold: the thin groove at 3 months, the groove with its santur figure
at 5, the full groove at 7. The window is the bar (two seconds) for the groove and one second for a year's plucks.

In the years below the groove each year sounds its own months. Its tick is always there. Spring (months 1 to 6,
Farvardin to Shahrivar) plays one pluck on the hook's note of its first flowing month (note i of the hook is
month i + 1), its strength and its ring growing with the year's flowing months. Autumn and winter flow (months 7
to 12) plays that note an octave down 0.09 s later. A thin year (low months only) plays a quiet note. A dry year
has only its tick. In 1405 the hook returns with one note for each of months 3 to 6.

    0.00 s         the dry riverbed: the wind (filtered noise) and one low setar note, from the first frame
    0.30-2.25 s    the rewind: a setar sting reversed, its last attack on 1370; one soft tick per rewound year
    2.80-11.52 s   the forward years, one tick each (film.at); plucks in the years below the groove
    4.00-7.60 s    the groove on the bar lines, and the two-bar santur hook (G, A-koron, B, G, E-flat, C)
    7.60 s         '1370s: about 10 months of 12': an impact and a santur chord; the groove stops
    8.00-12.00 s   the groove thins as the flow does, then the rare plucks and the dry 1404 (the wind only)
    13.60 s        '1400-1404: only about 2 months of 12': a santur chord and a daf rim
    15.20 s        1405: the hook returns gently, four notes for the four flowing months (Khordad to Shahrivar)
    18.00 s        the last chord on C; the tails fade over the last second to 20 s
(the times are the film's: timing() reads them from it, these are the values of the current cut)

Mix: -14 LUFS integrated, true peak -1.5 dBTP (the AAC encoding of the reel stays under -1 dBTP), the sub in
mono, the width on the santur and the pad. Synthesized only, no vocals.

    python -I src/onebit_score_zayandeh.py

writes outputs/onebit/social/zayandeh_naqsh_fa_music.wav and muxes it under the silent reel into
zayandeh_naqsh_fa_music_reel.mp4 (the silent reel is not rewritten). It prints the loudness and the true peak
of the WAV and of the MP4's decoded audio, the first 0.1 s, the last second, the RMS per second against the flow,
the onsets of the accents and of the per-year ticks, the durations, and the video stream against the silent reel.
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
import onebit_zayandeh  # noqa: E402
from onebit_slides import COLOURS  # noqa: E402

SR = kit.SR
BEAT, BAR = kit.BEAT, kit.BAR                  # 0.5 s and 2 s at 120 BPM
MODE = "esfahan"
LOW = kit.note_hz("C3")                        # the tonic: the first setar note, the pad, the autumn plucks
HIGH = kit.note_hz("C4")                       # the tonic an octave up: the hook and the spring plucks
SUB = kit.note_hz("C2")
KICK = kit.note_hz("G1")
SEED = 23
TAIL = 3.0                                     # s of room past the end, for the reverb and the echo
LUFS, TP = -14.0, -1.5                         # -1.5 dBTP: the AAC encoding of this track stays under -1
MAX_OFFSET = 0.030                             # s: a hit may sit at most this far from its event
BASE = "zayandeh_naqsh_fa"
BUSES = ("wind", "intro", "ticks", "pluck", "drum", "kick", "pad", "hook", "sub", "fx")
GEO_STACK = ("shapely", "cartopy", "fiona", "geopandas", "pyproj")
# a layer is on at or above its threshold, in flowing months (full + low / 2) averaged over its window
THIN, MID, FULL = 3.0, 5.0, 7.0
HOOK_START = 4.0                               # s: the bar line after 1370 (3.68 s); the hook runs two bars
FINAL = 18.0                                   # s: the last chord, on a bar line
# the two-bar santur hook: (mode step, beat from HOOK_START, length in beats); note i is Persian month i + 1
HOOK = ((4, 0.0, 1.5), (5, 2.0, 1.0), (6, 3.0, 1.0), (4, 4.0, 1.5), (2, 6.0, 1.0), (0, 7.0, 1.0))
HOOK_STEP = tuple(step for step, _, _ in HOOK)
CHORD = (0, 2, 4)                              # the tonic triad: C, E-flat, G
ARP = (0, 1, 2, 1, 0, 1, 2, 1)                 # the santur figure: eighths over the triad


def block_geo_stack() -> None:
    """Keep the geo stack out of this process. The film reads npz and csv only; its data module imports
    rasterio, which does not load any of these names, so the film still builds."""
    for name in GEO_STACK:
        if name not in sys.modules:
            sys.modules[name] = None


def deg(step: int, base: float) -> float:
    return kit.degree(MODE, step, 0, tonic_hz=base)


def pan_of(y: int) -> float:
    """Right to left across the years, as the picture reads: 1991 on the right, 2025 on the left."""
    return 0.35 - 0.7 * (y - 1991) / (2025 - 1991)


# ── the film's clock and the calendar ───────────────────────────────────────

def timing(film) -> dict:
    """The film's own times: the rewound years (2024 down to the first year), the forward years (the second up to
    2026), the rewind's ends, the accent of '1370s', the accent of '1400-1404' and the keyframe of 1405 after it."""
    keys = [(float(t), int(y)) for t, y in film.keys]
    st = [float(s) for s in film.starts]
    forward = sorted((float(t), int(y)) for y, t in film.at.items())
    tm = dict(starts=st, end=st[-1],
              rewind=[(t, y) for t, y in keys if 0.0 < t < forward[0][0]],
              forward=forward,
              t_back=min(t for t, y in keys if y == 2024),
              t_first=min(t for t, y in keys if y == film.years[0]),
              stop=st[1] + float(film.later(1)),
              ret=float(film.at[2026]),
              accent2=st[2] + float(film.later(2)))
    assert tm["t_back"] < tm["t_first"] < forward[0][0] < tm["stop"] < tm["accent2"] < tm["ret"], tm
    assert tm["ret"] + 2.0 < FINAL < tm["end"] - 1.5, tm     # the four notes of 1405 end before the last chord
    return tm


def months_curve(film, end: float) -> np.ndarray:
    """The flowing months (full + half the low) of the picture on screen, once per millisecond, blended as the
    film blends its years."""
    cache: dict = {}

    def flow(y: int) -> float:
        if y not in cache:
            m = film.cal[onebit_zayandeh.persian(y)]
            cache[y] = m.count("full") + 0.5 * m.count("low")
        return cache[y]

    out = np.empty(int(round(end * 1000)) + 1)
    for i in range(len(out)):
        a, b, w = film.state(i / 1000.0)
        out[i] = (1.0 - w) * flow(a) + w * flow(b)
    return out


def mean_over(curve: np.ndarray, t0: float, t1: float) -> float:
    i0, i1 = max(0, round(t0 * 1000)), min(len(curve), round(t1 * 1000))
    return float(curve[i0:i1].mean())


def layer_level(months: float) -> str:
    return "full" if months >= FULL else "mid" if months >= MID else "thin" if months >= THIN else "off"


def year_plucks(film, y: int) -> list:
    """The plucks of one forward year from its own months, as (mode step, base, vel, t60, offset in s).
    Spring: the hook's note of the first flowing month of months 1 to 6, louder and longer with more flowing
    months. Autumn and winter: the same note of the hook an octave down, 0.09 s later. Low months only: a quiet
    note of the first low month. Nothing else: a dry year, which keeps only its tick."""
    m = film.cal[onebit_zayandeh.persian(y)]
    n_full = m.count("full")
    out = []
    spring = [i for i in range(6) if m[i] == "full"]
    if spring:
        out.append((HOOK_STEP[spring[0]], HIGH, 0.35 + 0.03 * n_full, 0.5 + 0.06 * n_full, 0.0))
    autumn = [i for i in range(6, 12) if m[i] == "full"]
    if autumn:
        out.append((HOOK_STEP[autumn[0] - 6], LOW, 0.30, 0.6, 0.09))
    if not spring and not autumn:
        low = [i for i in range(6) if m[i] == "low"]
        if low:
            out.append((HOOK_STEP[low[0]], HIGH, 0.16, 0.3, 0.0))
    return out


def return_notes(film) -> list:
    """1405: the hook's notes for the flowing months among months 3 to 6, as (step, offset in s from the
    note of month 3). Khordad to Shahrivar flowed in 1405, so these are the hook's second half."""
    m = film.cal[onebit_zayandeh.persian(2026)]
    return [(HOOK[i][0], (HOOK[i][1] - HOOK[2][1]) * BEAT) for i in range(2, 6) if m[i] == "full"]


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
    """The rewind's sting: three setar notes, C4, G4 and E-flat4, 0.12 s apart, ringing; its last 30 ms faded,
    so that played backwards the rewind swells out of silence."""
    x = kit.new_track(1.3)
    for k, step in enumerate((0, 4, 2)):
        s = kit.setar(deg(step, HIGH), dur=1.2, vel=0.9, t60=1.5, bright=0.6, buzz=0.15)
        kit.place(x, s, 0.12 * k, 0.8, pan=(-0.2, 0.0, 0.2)[k])
    m = int(0.03 * SR)
    x[-m:] *= np.linspace(1.0, 0.0, m)[:, None]
    return x


def _rewind_rise(x: np.ndarray, n_out: int, v0: float = 0.5) -> np.ndarray:
    """The sting read backwards from its end to its start in n_out samples, the tape speeding up as it goes:
    the read speed rises linearly from v0 to v1, with v1 set so that the whole sting is read. Its first attack
    arrives on the last sample, so the rewind ends on that attack."""
    x = np.asarray(x, float)
    avg = (len(x) - 1) / n_out
    v1 = 2.0 * avg - v0
    v = v0 + (v1 - v0) * np.arange(n_out) / max(n_out - 1, 1)
    pos = (len(x) - 1) - np.concatenate([[0.0], np.cumsum(v)[:-1]])
    pos = np.clip(pos, 0.0, len(x) - 1)
    idx = np.arange(len(x))
    return np.stack([np.interp(pos, idx, x[:, c]) for c in range(x.shape[1])], axis=1)


def _bass_mono(x, fc: float = 120.0) -> np.ndarray:
    """The low end in mono: everything below fc is averaged to one channel, and the rest stays wide."""
    low = sosfilt(butter(4, fc, "lowpass", fs=SR, output="sos"), x, axis=0)
    mid = 0.5 * (low[:, 0] + low[:, 1])
    out = x - low
    out[:, 0] += mid
    out[:, 1] += mid
    return out


def _compose(film, rec: list):
    """Lay the score on its buses. Returns (buses, kick times, the flow in months per millisecond). rec receives one
    entry per checked event: (label, visual time, time of the hit, the sounds placed for it as (sound, gain, pan))."""
    kit.reseed(SEED)
    tm = timing(film)
    end = tm["end"]
    months = months_curve(film, end)
    grid = np.arange(len(months)) / 1000.0
    m1 = uniform_filter1d(months, 1000, mode="nearest")      # the flow, a centred 1-s mean, per millisecond
    bus = {k: kit.new_track(end, TAIL) for k in BUSES}
    n = len(bus["fx"])
    t_all = np.arange(n) / SR
    kicks: list = []
    tick = _tick()
    kick = kit.kick808(KICK, vel=1.0, decay=0.9, drive=1.3)
    snare, hat = kit.snare(), kit.hat(False)
    bam, tak = kit.daf("bam"), kit.daf("tak")
    stop = tm["stop"]

    def hit(name, sound, t, gain, pan=0.0, until=None):
        if until is None or t < until:
            kit.place(bus[name], sound, t, gain, pan)

    def event(label, t, items):
        """items: (bus name, sound, gain, pan). Placed at t, and logged for the check."""
        for name, sound, gain, pan in items:
            kit.place(bus[name], sound, t, gain, pan)
        rec.append((label, t, t, [(s, g, p) for _, s, g, p in items]))

    # 0.00 s: the dry riverbed. The wind is filtered noise, louder where the flow is low; one low setar note.
    gain_w = 0.10 * (1.0 - np.clip(np.interp(t_all, grid, m1) / FULL, 0.0, 1.0))
    rng = np.random.default_rng(29)
    sos = butter(2, (120.0, 1000.0), "bandpass", fs=SR, output="sos")
    w = np.stack([sosfilt(sos, rng.standard_normal(n)), sosfilt(sos, rng.standard_normal(n))], axis=1)
    w = w / np.abs(w).max()
    bus["wind"] += w * (gain_w * np.minimum(1.0, t_all / 0.005))[:, None]
    hit("intro", kit.setar(LOW, dur=2.6, vel=0.9, t60=2.4, bright=0.5, buzz=0.1), 0.0, 0.9)

    # 0.30 to 2.25 s: the rewind. The sting read backwards, its last attack on 1370; one soft tick per year.
    n_out = round((tm["t_first"] - tm["t_back"]) * SR)
    hit("intro", _rewind_rise(_sting(), n_out), tm["t_back"], 0.7)
    for t, y in tm["rewind"]:
        event(f"rewind {y}", t, [("ticks", tick, 0.2, -pan_of(y))])

    # 2.80 s on: the forward years, one tick each. Below the groove, each year also sounds its own months.
    late = []
    for t, y in tm["forward"]:
        if y == 2026:
            continue                                         # 1405 has its own event, at its keyframe
        pan = pan_of(y)
        items = [("ticks", tick, 0.16, pan)]
        if float(m1[round(t * 1000)]) < MID:
            for step, base, vel, t60, off in year_plucks(film, y):
                pl = kit.setar(deg(step, base), dur=1.6, vel=vel, t60=t60, bright=0.7, buzz=0.0)
                if off == 0.0:
                    items.append(("pluck", pl, 1.0, pan))
                else:
                    late.append((t + off, pl, pan))
        event(f"forward {y}", t, items)
    for t, pl, pan in late:
        kit.place(bus["pluck"], pl, t, 1.0, pan)

    # 4.00 to 7.60 s: the groove on the bar lines, each bar at the level of its own flow. It stops at 7.60 s.
    for b0 in np.arange(HOOK_START, tm["starts"][2], BAR):   # bars 4, 6, 8 and 10 s; 1405 has its own section
        lvl = layer_level(mean_over(months, b0, b0 + BAR))
        if lvl == "off":
            continue
        until = stop if b0 < stop else None
        for t in ([b0] if lvl == "thin" else [b0, b0 + 1.25]):
            hit("kick", kick, t, 0.9, until=until)
            if until is None or t < until:
                kicks.append(t)
        if lvl == "thin":
            for k in range(4):
                hit("drum", hat, b0 + 0.5 * k, 0.10, pan=0.25 if k % 2 else -0.25, until=until)
        else:
            for k in range(8):
                hit("drum", hat, b0 + 0.25 * k, 0.12 if k % 2 == 0 else 0.07,
                    pan=0.25 if k % 2 else -0.25, until=until)
        if lvl in ("mid", "full"):                           # the santur figure: eighths over the triad
            for k in range(8):
                hit("hook", kit.santur(deg(CHORD[ARP[k]], HIGH), dur=1.2, vel=0.3, t60=1.5),
                    b0 + 0.25 * k, 0.9, until=until)
        if lvl == "full":
            hit("drum", snare, b0 + 1.0, 0.5, until=until)
            hit("drum", bam, b0, 0.5, until=until)
    if layer_level(mean_over(months, HOOK_START, stop)) in ("mid", "full"):
        hit("pad", kit.pad([deg(s, LOW) for s in CHORD], dur=stop - HOOK_START, vel=0.3, width=0.9,
                           cutoff=1800.0, attack=0.4, release=0.25), HOOK_START, 1.0)
        hit("sub", kit.sub(SUB, dur=stop - HOOK_START, vel=0.8), HOOK_START, 0.9)

    # 4.00 to 7.50 s: the two-bar santur hook, six notes; its notes are the months, Farvardin to Shahrivar.
    for step, beat, length in HOOK:
        hit("hook", kit.santur(deg(step, HIGH), dur=length * BEAT + 1.6, vel=0.6, t60=2.2),
            HOOK_START + beat * BEAT, 0.75)

    # 7.60 s, '1370s: about 10 months a year': an impact and a santur chord on C, E-flat and A-koron.
    items = [("fx", kit.impact(2.2, vel=0.9, pitch=SUB), 1.0, 0.0),
             ("fx", kit.sub(SUB, dur=1.4, vel=0.8), 0.9, 0.0)]
    items += [("fx", kit.santur(deg(s, HIGH), dur=3.0, vel=0.6, t60=2.6), 0.9, 0.0) for s in (0, 2, 5)]
    event('"1370s: about 10 months a year": the impact, the groove stops', stop, items)

    # 15.20 s, 1405 (after the last line): the hook returns gently. A daf stroke and the sub on the same beat; its
    # other notes follow, the last 2 s later, before the last chord.
    ret = tm["ret"]
    rn = return_notes(film)
    items = [("ticks", tick, 0.16, pan_of(2026)), ("fx", bam, 0.5, 0.0),
             ("fx", kit.sub(SUB, dur=1.3, vel=0.6), 0.6, 0.0)]
    items += [("fx", kit.santur(deg(s, HIGH), dur=2.2, vel=0.42, t60=2.0), 1.0, 0.0) for s, off in rn if off == 0.0]
    event("1405: the hook returns gently", ret, items)
    for step, off in rn:
        if off > 0.0:
            hit("fx", kit.santur(deg(step, HIGH), dur=2.2, vel=0.42, t60=2.0), ret + off, 1.0)
    hit("pad", kit.pad([deg(s, LOW) for s in CHORD], dur=FINAL + 1.5 - ret, vel=0.25, width=0.9,
                       cutoff=1600.0, attack=0.8, release=1.2), ret, 1.0)

    # 13.60 s, '1400-1404: only about 2 months': a santur chord on C, E-flat and G, and a daf rim.
    items = [("fx", kit.santur(deg(s, HIGH), dur=4.0, vel=0.55, t60=3.0), 0.9, 0.0) for s in CHORD]
    items.append(("fx", tak, 0.7, 0.0))
    event('"1400-1404: only about 2 months": the santur chord, a daf rim', tm["accent2"], items)

    # 18.00 s: the last chord on C. Its tails fade over the last second (the master's fade) to 20 s.
    for s in CHORD:
        hit("fx", kit.santur(deg(s, HIGH), dur=5.0, vel=0.55, t60=3.2), FINAL, 0.9)
    hit("fx", kit.daf("bam", vel=0.7), FINAL, 0.6)
    hit("sub", kit.sub(SUB, dur=2.4, vel=0.9), FINAL, 0.9)
    return bus, kicks, months


def _fit(x, n: int):
    """Crop or zero-pad x along time to n rows."""
    return x[:n] if len(x) >= n else np.concatenate([x, np.zeros((n - len(x),) + x.shape[1:])])


def mix_bus(bus: dict, kicks: list, n: int) -> np.ndarray:
    """The buses summed. The harmony (the hook and the pad, widened) ducks under the kick and has a room; the
    plucks have an echo; the sub is mono; the sting, the wind, the ticks, the plucks and the accents are dry."""
    harm = kit.duck(kit.widen(bus["hook"], 0.3) + kit.widen(bus["pad"], 0.3), kicks, depth_db=3.0, release=0.15)
    wet = kit.reverb(harm, t60=1.8) * 0.25
    echo = kit.pingpong(bus["pluck"] * 0.5, delay=0.375, feedback=0.4, taps=6) * 0.5
    mix = (bus["drum"] + bus["kick"] + harm + _fit(wet, n) + bus["sub"] + bus["fx"] + bus["ticks"]
           + bus["pluck"] + _fit(echo, n) + bus["wind"] + bus["intro"])
    return _bass_mono(mix)


def render(film, log: list | None = None):
    """The mastered track, the mix before the master (for the verification), and the flow in months per ms."""
    rec = [] if log is None else log
    bus, kicks, months = _compose(film, rec)
    mix = mix_bus(bus, kicks, len(bus["fx"]))
    return kit.master(mix, lufs=LUFS, tp=TP, seconds=float(film.starts[-1]), fade_out=1.0), mix, months


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
    return subprocess.run(["ffmpeg", "-v", "error", "-i", str(media), "-map", stream, "-c", "copy", "-f", "md5", "-"],
                          check=True, capture_output=True, text=True).stdout.strip()


def _db(seg) -> float:
    return float(20 * np.log10(np.sqrt(np.mean(np.square(seg))) + 1e-12))


def _flux(x, hop: int = 48, nfft: int = 256):
    """Spectral flux of a mono signal, frames 1 ms apart and 5.3 ms long. Returns each frame's centre time (s)
    and its flux: the rise of the log magnitude from one frame to the next, summed over the bins."""
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


def check(film, wav, video, out, log: list, mix, months, untouched: bool) -> None:
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
    loud = np.flatnonzero(np.abs(x).max(axis=1) > 0.1)                # the first sample above -20 dBFS
    assert loud.size, "no sound above -20 dBFS"
    first_ms = 1000 * loud[0] / SR
    peak_db = 20 * np.log10(np.abs(head).max())
    print(f"    RMS {_db(head):.1f} dBFS (a 0.1 s mean of a plucked note reads well below its peak), "
          f"peak {peak_db:.1f} dBFS, first sample above -20 dBFS at {first_ms:.2f} ms")
    assert peak_db > -20 and first_ms < 20, "no sound in the first frame"

    print("\n(3) the last second, RMS per 0.1 s (dBFS)")
    win = int(0.1 * SR)
    ends = [_db(x[len(x) - (k + 1) * win:len(x) - k * win]) for k in range(10)][::-1]
    last_step = np.abs(np.diff(x[-int(0.005 * SR):], axis=0)).max()
    print("    " + " ".join(f"{v:.1f}" for v in ends))
    print(f"    last sample {abs(x[-1, 0]):.2e}, largest step in the last 5 ms {last_step:.2e}")
    assert ends[-1] < ends[0] - 10 and abs(x[-1, 0]) < 1e-3 and last_step < 2e-3, "the ending is not a clean fade"

    print("\n(4) RMS per 1 s (dBFS) against the flowing months on screen (mean over the second)")
    rms = [_db(x[k * SR:(k + 1) * SR]) for k in range(20)]
    flow = [float(months[k * 1000:(k + 1) * 1000].mean()) for k in range(20)]
    print("    s     " + " ".join(f"{k:>5d}" for k in range(20)))
    print("    dB    " + " ".join(f"{v:>5.0f}" for v in rms))
    print("    months" + " ".join(f"{v:>5.1f}" for v in flow))
    groove, dry = float(np.mean(rms[4:8])), float(np.mean(rms[10:12]))
    print(f"    groove 4-8 s {groove:.1f} dB, dry 1404 at 10-12 s {dry:.1f} dB: {groove - dry:.1f} dB apart")
    assert groove - dry >= 10, "the drying-up is not visible"

    print("\n(5) the events: onsets, each cleared of the rest of the mix (the Urmia score's method)")
    hp = butter(2, 12.0, "highpass", fs=SR, output="sos")          # the master's DC blocker
    u = sosfilt(hp, mix[:len(x)], axis=0)
    w1 = round(0.001 * SR) | 1
    num = uniform_filter1d((x * u).sum(axis=1), w1, mode="nearest")
    den = uniform_filter1d((u * u).sum(axis=1), w1, mode="nearest")
    gain = num / np.maximum(den, 1e-12)                            # the master as a gain curve, per sample
    rows = []
    for label, visual, hit_t, items in log:
        a = round((hit_t - 0.1) * SR)
        b = a + round(0.4 * SR)
        ev = kit.new_track(0.4)
        for sound, g, pan in items:
            kit.place(ev, sound, (round(hit_t * SR) - a) / SR, g, pan)
        cleared = x[a:b] - gain[a:b, None] * sosfilt(hp, mix[a:b] - _bass_mono(ev), axis=0)
        lt, lr = _flux(cleared.mean(axis=1))
        rows.append((label, visual, _flux_onset(lt, lr, 0.1)))
    assert all(r[2] is not None for r in rows), "an event with no onset"
    print(f"    {'event':<62}{'visual s':>10}{'found s':>10}{'offset ms':>11}")
    accents = [r for r in rows if not r[0].startswith(("rewind", "forward"))]
    for label, visual, off in accents:
        print(f"    {label:<62}{visual:10.3f}{visual + off:10.3f}{off * 1000:+11.2f}")
    ticks = np.array([r[2] for r in rows if r[0].startswith(("rewind", "forward"))]) * 1000
    for group in ("rewind", "forward"):
        offs = np.array([r[2] for r in rows if r[0].startswith(group)]) * 1000
        print(f"    {group + ' ticks, n=' + str(len(offs)):<62} median offset {np.median(offs):+.2f} ms,"
              f" largest |offset| {np.abs(offs).max():.2f} ms")
    print(f"    all per-year ticks, n={len(ticks)}: median offset {np.median(ticks):+.2f} ms (limit "
          f"{MAX_OFFSET * 1000:.0f} ms)")
    assert abs(np.median(ticks)) <= MAX_OFFSET * 1000, "the per-year ticks are late"
    assert all(abs(r[2]) <= MAX_OFFSET for r in accents), "an accent is off"

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
    film = onebit_zayandeh.ZayandehFilm(onebit.THEMES["naqsh"], COLOURS["naqsh"])
    base = onebit.OUT / "social" / BASE
    video = Path(f"{base}_reel.mp4")
    wav = Path(f"{base}_music.wav")
    out = Path(f"{base}_music_reel.mp4")
    st = os.stat(video)
    before = (st.st_size, st.st_mtime_ns)
    log: list = []
    track, mix, months = render(film, log)
    kit.write_wav(wav, track)
    print("saved", wav)
    kit.mux(video, wav, out)
    print("saved", out)
    st2 = os.stat(video)
    check(film, wav, video, out, log, mix, months, untouched=before == (st2.st_size, st2.st_mtime_ns))


if __name__ == "__main__":
    main()
