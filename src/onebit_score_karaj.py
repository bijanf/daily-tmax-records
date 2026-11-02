"""The score of the Karaj dam reel (karaj_abi_fa, 20 s): an original track in Mahur, built from the Persian
sound kit (onebit_persian) and timed to the film's own clock. Everything is synthesized here: no samples,
no voices.

The lake is the music's data. The film shows, for each autumn, the open water of the Amir Kabir (Karaj)
reservoir in km2 (film.area). Every forward year (film.at) sounds twice: a soft tick, and a setar pluck. The
pluck's pitch is the area on a log scale between the smallest and the largest year of the film, quantized to the
seven steps of Mahur from C3 to C4 (equal steps are equal ratios). Its velocity and its ring grow with the water:
a small lake plucks soft and short, a big one rings. The jump from 1405 to 1404 sounds the pluck of 1404, which
sits on the lowest step. The rewind (from 1404 back to 1366) is one soft tick per year and a reversed sting; the
sting lands on C4 together with the first year's own pluck.

The groove follows the water. At every bar line from the hook on, the mean area on screen over the two seconds
around that line is set against the usual area, the film's 40-year median (film.med): full at 90 % of it or more
(kick, snare, eighth-note hats, a daf stroke), mid at half of it (kick, quarter-note hats, a pad and the sub),
thin at a quarter (the kick on the bar line alone), and off below a quarter (nothing). The 90 % is the film's own
"about the usual" band (karaj.NEAR: 32 of the 40 autumns lie in it). A strict median would put seven of the eight
bar lines at mid, because most autumns sit a little under it, and 1405 (99.7 % of the median) would not come back
full. The hook, five notes in two bars on santur (C, E, G, E, D), is the same every time and sits above the groove.

    0.00 s           the cover: one setar note, C4, the pitch of 1405's area
    1.00 s           the jump: the lake drops to 1404, and its pluck sounds on the lowest step, C3
    2.00-4.00 s      the rewind: the sting read backwards (E4, G4, C4), one soft tick per year from 1404 back
                     to 1366 (33 ticks), its last attack on C4 at 4.00 s (1366) with that year's pluck
    4.00-8.00 s      the hook, two bars: C E G E D
    6.00-9.80 s      the forward years, 1367 to 1404 (film.at): a tick and a pluck each, 0.10 s apart up to
                     1394 (8.10 s), 0.17 s apart after
    7.60 s           scene 2's number lands: an impact, a daf stroke and a santur chord on C, E and G
    9.80-12.00 s     1404 holds: the lake at its low, its pluck at C3; the groove is mid at 10 s and 12 s
    12.00 s          1405 (film.at): its pluck, a tick and a soft daf stroke; the lift D, E, G rises over a pad
                     on G and D
    13.60 s          scene 3's number lands, quieter: a santur chord on G and D, a daf rim
    18.00 s          the last chord, G and D again, with no tonic; the master's fade takes the tails to 20 s
(the times are the film's, read by timing(); the numbers are those of the cut the score was last run on)

Mix: -14 LUFS integrated, true peak -1.5 dBTP in the WAV. The top octave (above 12 kHz) is taken out before the
master: the AAC encoding of the drums' transients adds an error above 6 kHz that lifted the decoded peaks by about
2 dB, and the decoded audio must stay at -1 dBTP or below. After the master the bass below 120 Hz is averaged to
one channel in the spectrum, so the sub is mono (the limiter's gain changes would leave stereo in the bass). The
plucks have a ping-pong echo; the hook and the pad have a room, and are ducked under the kick.

    python -I src/onebit_score_karaj.py

writes outputs/onebit/social/karaj_abi_fa_music.wav and muxes it under the silent reel into
karaj_abi_fa_music_reel.mp4 (the silent reel is not rewritten). The silent reel must be newer than
src/onebit_karaj.py: render the film first with python -I src/onebit_karaj.py. The script prints the loudness and
the true peak of the WAV and of the MP4's decoded audio, the times taken from the film, the groove's levels, the
RMS per second against the area on screen, the side against the mid below each frequency, the onsets of every
event (in the WAV, cleared of the rest of the mix; the accents also in the decoded MP4), and the video stream
against the silent reel.
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
from scipy.signal import butter, sosfilt

sys.path.insert(0, str(Path(__file__).resolve().parent))

import karaj  # noqa: E402
import onebit  # noqa: E402
import onebit_karaj  # noqa: E402
import onebit_persian as kit  # noqa: E402
from onebit_slides import COLOURS  # noqa: E402

SR = kit.SR
BEAT, BAR = kit.BEAT, kit.BAR                  # 0.5 s and 2 s at 120 BPM: the film's 60 BPM grid, half-time
MODE = "mahur"                                 # C, D, E, F, G, A, B: the dastgah nearest to the major scale
STEPS = 7                                      # the lake's area is quantized to the seven steps (C3 to C4)
PLUCK_TONIC = kit.note_hz("C3")                # step 0 of the forward years' plucks
HOOK_TONIC = kit.note_hz("C4")                 # the sting, the hook, the chords: C4 and up, G3 and below
KICK, SUB = kit.note_hz("C1"), kit.note_hz("C2")
TAIL = 3.0                                     # s of room past the end, for the reverb and the echo
LUFS, TP = -14.0, -1.5                         # -1.5 dBTP: the decoded AAC stays under -1 once the top octave is cut
AIR = 12000.0                                  # Hz: above this the mix has no content (the AAC overshoot)
BASS = 120.0                                   # Hz: below this the two channels are one
MAX_OFFSET = 0.030                             # s: a hit may sit at most this far from its event
BASE = "karaj_abi_fa"
BUSES = ("intro", "wind", "ticks", "pluck", "drum", "kick", "pad", "hook", "sub", "fx")
SEED = 37
HOOK = ((0, 0.0, 1.0), (2, 1.0, 1.0), (4, 2.0, 2.0), (2, 4.0, 1.0), (1, 5.0, 3.0))  # (step, beat, length in beats)
LIFT = ((1, 0.0), (2, 1.0), (4, 1.5))          # 1405: the hook's last three notes backwards, rising: D, E, G (beats)
PAD_CHORD = ((0, -1), (4, -1))                 # C3 and G3, the open fifth under the groove until 1405 returns
END_CHORD = ((4, -1), (1, 0))                  # G3 and D4: no tonic and no third, so the last sound does not resolve
FULL = 1.0 - karaj.NEAR                        # the groove's full level: the film's own "about the usual" band
GAIN_WIND = 0.06                               # the dry wind at its loudest: the lake at its lowest
ECHO = dict(delay=0.375, feedback=0.4, taps=6)  # the plucks' ping-pong: a dotted eighth at 120 BPM


def block_geo_stack() -> None:
    """Keep the geo stack out of this process: the film reads only CSV and npz, and the repo's rule is that no
    process holding netCDF readers imports shapely or cartopy (see onebit_score_zayandeh)."""
    for name in ("shapely", "cartopy", "fiona", "geopandas"):
        if name not in sys.modules:
            sys.modules[name] = None


# ── the film's clock and the lake on screen ─────────────────────────────────

def timing(film) -> dict:
    """The film's own times, read every time: the cover (its first key), the jump (the keys between the cover and
    the rewind: 1405 gives way to 1404), the rewind (from the last keyframe of 1404 before 1366's arrival back to
    1366, one step per shown year), the forward years (film.at, every year but the first and the last), the
    keyframe of the last year (film.at: 1405 arrives there, wherever the film puts it), the two lines the music
    answers (the scene start plus film.later), and the end (the last scene start). The hook starts on the first bar
    line after the rewind."""
    years = [int(y) for y in film.years]
    keys = [(float(t), int(y)) for t, y in film.keys]
    st = [float(s) for s in film.starts]
    forward = [(float(film.at[y]), y) for y in years[1:-1]]
    t_first = min(t for t, y in keys if y == years[0])
    back = [(t, y) for t, y in keys if 0.0 < t < forward[0][0]]               # the jump and the rewind
    t_back = max(t for t, y in back if y == years[-2] and t < t_first)        # the rewind starts at the last 1404 key
    tm = dict(years=years, starts=st, end=st[-1], cover=keys[0][0], t_back=t_back, t_first=t_first,
              jump=[(t, y) for t, y in back if t < t_back],
              rewind=[(t, y) for t, y in back if t >= t_back],
              forward=forward, ret=float(film.at[years[-1]]),
              accent1=st[1] + float(film.later(1)), accent2=st[2] + float(film.later(2)),
              hook_start=BAR * math.ceil(t_first / BAR))
    assert tm["cover"] == 0.0 and tm["t_back"] < tm["t_first"] < forward[0][0], tm
    assert len(tm["jump"]) == 1 and tm["jump"][0][1] == years[-2], tm                 # the jump: 1405 to 1404, once
    assert len(tm["rewind"]) == len(years) - 1 and len(forward) == len(years) - 2, tm   # every year but the last
    assert forward[-1][0] < tm["ret"] < tm["end"] - 4.0, tm     # the forward years, then 1405 with room for the lift
    assert tm["hook_start"] < tm["accent1"] < tm["accent2"] < tm["end"] - 3.0, tm
    return tm


def area_curve(film, end: float) -> np.ndarray:
    """The open water on screen (km2) once per millisecond from 0 to end: the two years' areas, blended as the
    film blends them (film.state)."""
    out = np.empty(int(round(end * 1000)) + 1)
    for i in range(len(out)):
        a, b, w = film.state(i / 1000.0)
        out[i] = (1.0 - w) * film.area[a] + w * film.area[b]
    return out


def mean_over(curve: np.ndarray, t0: float, t1: float) -> float:
    i0, i1 = max(0, round(t0 * 1000)), min(len(curve), round(t1 * 1000))
    return float(curve[i0:i1].mean())


def level_of(mean: float, usual: float) -> str:
    """The groove's layers against the usual area: full at FULL (90 %) of it or more, mid at half, thin at a quarter."""
    return "full" if mean >= FULL * usual else "mid" if mean >= usual / 2 else "thin" if mean >= usual / 4 else "off"


def voice(area: float, lo: float, hi: float) -> tuple:
    """(step, u, velocity, ring) of a year's pluck. u is the area on a log scale between the film's smallest (lo)
    and its largest (hi) year: 0 at lo, 1 at hi. The step is u on the seven steps; the velocity and the ring (t60,
    the seconds to fall 60 dB) grow with u, so a big lake rings and a small one is dry. (A setar's peak is 0.6 of
    its velocity and its energy sits in the first 50 ms, so the velocity runs high to be heard among the groove.)"""
    u = (math.log(area) - math.log(lo)) / (math.log(hi) - math.log(lo))
    return int(round(STEPS * u)), u, 0.60 + 0.30 * u, 0.22 + 0.55 * u


def pan_of(y: int, years: list) -> float:
    """Right to left across the years, as the picture reads: the first year on the right, the last on the left."""
    return 0.35 - 0.7 * (y - years[0]) / (years[-1] - years[0])


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
    """The rewind's sting: three setar notes, C4, G4 and E4, 0.12 s apart, ringing; its last 30 ms faded, so that
    played backwards the rewind swells out of silence and lands on C4."""
    x = kit.new_track(1.3)
    for k, step in enumerate((0, 4, 2)):
        s = kit.setar(kit.degree(MODE, step, 0, tonic_hz=HOOK_TONIC), dur=1.2, vel=0.9, t60=1.5, bright=0.6, buzz=0.15)
        kit.place(x, s, 0.12 * k, 0.8, pan=(-0.2, 0.0, 0.2)[k])
    m = int(0.03 * SR)
    x[-m:] *= np.linspace(1.0, 0.0, m)[:, None]
    return x


def _rewind_rise(x: np.ndarray, n_out: int, v0: float = 0.5) -> np.ndarray:
    """The sting read backwards from its end to its start in n_out samples, the tape speeding up as it goes: the read
    speed rises linearly from v0 to v1, with v1 set so that the whole sting is read. Its first attack arrives on
    the last sample, so the rewind ends on that attack."""
    x = np.asarray(x, float)
    avg = (len(x) - 1) / n_out
    v1 = 2.0 * avg - v0
    v = v0 + (v1 - v0) * np.arange(n_out) / max(n_out - 1, 1)
    pos = (len(x) - 1) - np.concatenate([[0.0], np.cumsum(v)[:-1]])
    pos = np.clip(pos, 0.0, len(x) - 1)
    idx = np.arange(len(x))
    return np.stack([np.interp(pos, idx, x[:, c]) for c in range(x.shape[1])], axis=1)


def _air_cut(x, fc: float = AIR) -> np.ndarray:
    """The top octave removed, exactly, in the spectrum: nothing above fc. Zero-padded, so the wrap of the FFT does
    not reach the sound. (Without it the AAC encoding of the drums' transients overshoots the WAV by about 2 dB.)"""
    n = len(x)
    m = n + 2 * SR
    spec = np.fft.rfft(np.asarray(x, float), n=m, axis=0)
    spec[np.fft.rfftfreq(m, 1.0 / SR) > fc] = 0.0
    return np.fft.irfft(spec, n=m, axis=0)[:n]


def _bass_mono(x, fc: float = BASS) -> np.ndarray:
    """The low end in mono, exactly: below fc the two channels are averaged in the spectrum, above fc they are left
    as they are. A filter-based crossover would leave stereo below fc, because its low and high parts do not add
    back to the input in phase. Zero-padded, so the wrap of the FFT does not reach the sound."""
    n = len(x)
    m = n + 2 * SR
    spec = np.fft.rfft(np.asarray(x, float), n=m, axis=0)
    low = np.fft.rfftfreq(m, 1.0 / SR) < fc
    mid = 0.5 * (spec[low, 0] + spec[low, 1])
    spec[low, 0] = mid
    spec[low, 1] = mid
    return np.fft.irfft(spec, n=m, axis=0)[:n]


# ── the composition ─────────────────────────────────────────────────────────

def _compose(film, curve: np.ndarray, rec: list):
    """Lay the score on its buses. Returns (buses, the kick times, the groove's levels). rec receives one entry per
    checked event: (label, visual time, time of the hit, the sounds placed for it as (sound, gain, pan))."""
    kit.reseed(SEED)
    tm = timing(film)
    end, years, hs, ret = tm["end"], tm["years"], tm["hook_start"], tm["ret"]
    lo, hi = min(film.area[y] for y in years), max(film.area[y] for y in years)   # the film's smallest and largest year
    usual = float(film.med)                                                        # the usual area: the 40-year median
    bus = {k: kit.new_track(end, TAIL) for k in BUSES}
    n = len(bus["fx"])
    t_all = np.arange(n) / SR
    kicks: list = []
    levels: list = []
    tick = _tick()
    kick = kit.kick808(KICK, vel=1.0, decay=0.9, drive=1.3)
    snare, hat = kit.snare(), kit.hat(False)
    bam = kit.daf("bam", pitch=kit.note_hz("C2"))
    tak = kit.daf("tak", pitch=kit.note_hz("G3"))

    def hit(name, sound, t, gain, pan=0.0):
        kit.place(bus[name], sound, t, gain, pan)

    def event(label, t, items):
        """items: (bus name, sound, gain, pan). Placed at t, and logged for the check."""
        for name, sound, gain, pan in items:
            kit.place(bus[name], sound, t, gain, pan)
        rec.append((label, t, t, [(s, g, p) for _, s, g, p in items]))

    def pluck(y: int):
        step, _, vel, t60 = voice(film.area[y], lo, hi)
        return kit.setar(kit.degree(MODE, step, 0, tonic_hz=PLUCK_TONIC), dur=1.2, vel=vel, t60=t60, bright=0.6,
                         buzz=0.0)

    def tone(step: int, octave: int, **kw):
        return kit.santur(kit.degree(MODE, step, octave, tonic_hz=HOOK_TONIC), **kw)

    def pad_of(pairs, **kw):
        return kit.pad([kit.degree(MODE, s, o, tonic_hz=HOOK_TONIC) for s, o in pairs], **kw)

    # the dry wind: a bandpassed noise, louder where the lake is small and silent at the usual area or above
    on_screen = np.interp(t_all, np.arange(len(curve)) / 1000.0, curve)
    on_screen = uniform_filter1d(on_screen, int(0.5 * SR) | 1, mode="nearest")
    rng = np.random.default_rng(29)
    sos = butter(2, (120.0, 1000.0), "bandpass", fs=SR, output="sos")
    w = np.stack([sosfilt(sos, rng.standard_normal(n)), sosfilt(sos, rng.standard_normal(n))], axis=1)
    w = w / np.abs(w).max()
    dry = GAIN_WIND * (1.0 - np.clip(on_screen / usual, 0.0, 1.0)) * np.minimum(1.0, t_all / 0.05)
    bus["wind"] += w * dry[:, None]

    # the cover: one setar note, the pitch of the last year's area (its pluck comes back at the lift)
    step_last = voice(film.area[years[-1]], lo, hi)[0]
    hit("intro", kit.setar(kit.degree(MODE, step_last, 0, tonic_hz=PLUCK_TONIC), dur=2.6, vel=0.95, t60=2.4,
                           bright=0.5, buzz=0.1), tm["cover"], 0.9)

    # the jump: 1405 gives way to 1404 (the lake drops to half its usual area): its pluck, on the lowest step
    for t, y in tm["jump"]:
        pan = pan_of(y, years)
        event(f"jump to {y}: its pluck", t, [("ticks", tick, 0.36, pan), ("pluck", pluck(y), 1.0, pan)])

    # the rewind: the sting read backwards, its last attack on C4 at the first year; one soft tick per year
    n_out = round((tm["t_first"] - tm["t_back"]) * SR)
    hit("intro", _rewind_rise(_sting(), n_out), tm["t_back"], 0.7)
    for t, y in tm["rewind"]:
        items = [("ticks", tick, 0.36, -pan_of(y, years))]
        if y == years[0]:                                     # the arrival: the first year's own pluck with the sting
            items.append(("pluck", pluck(y), 1.0, -pan_of(y, years)))
        event(f"rewind {y}", t, items)

    # the forward years: a tick and a pluck each, at film.at
    for t, y in tm["forward"]:
        pan = pan_of(y, years)
        event(f"forward {y}", t, [("ticks", tick, 0.32, pan), ("pluck", pluck(y), 1.0, pan)])

    # the hook: five notes in two bars on santur, C E G E D; the last note rings on
    for step, beat, length in HOOK:
        s = tone(step, 0, dur=length * BEAT + 1.6, vel=0.7, t60=2.2)
        event(f"hook step {step}", hs + beat * BEAT, [("hook", s, 0.75, 0.0)])

    # the groove on each bar line from the hook on, its level from the lake on screen around that line
    for b0 in np.arange(hs, end - 1e-9, BAR):
        mean = mean_over(curve, b0 - 1.0, b0 + 1.0)
        lvl = level_of(mean, usual)
        levels.append((float(b0), mean, lvl))
        if lvl == "off":
            continue
        for t in ([b0] if lvl == "thin" else [b0, b0 + 1.25]):
            event(f"groove {b0:.0f} s: kick", t, [("kick", kick, 0.9, 0.0)])
            kicks.append(t)
        if lvl == "full":
            for k in range(8):
                hit("drum", hat, b0 + 0.25 * k, 0.12 if k % 2 == 0 else 0.07, pan=0.25 if k % 2 else -0.25)
            hit("drum", snare, b0 + 1.0, 0.5)
            hit("drum", bam, b0, 0.5)
        if lvl == "mid":
            for k in range(4):
                hit("drum", hat, b0 + 0.5 * k, 0.10, pan=0.25 if k % 2 else -0.25)
        if lvl in ("mid", "full"):
            hit("sub", kit.sub(SUB, dur=BAR + 0.03, vel=0.8), b0, 0.35)
            chord = PAD_CHORD if b0 < ret else END_CHORD            # the open fifth until 1405, then G and D
            hit("pad", pad_of(chord, dur=BAR + 0.25, vel=0.3, width=0.9, cutoff=1800.0, attack=0.3, release=0.25),
                b0, 1.0)

    # the first accent: scene 2's number lands. An impact, a daf stroke, a chord on C E G
    items = [("fx", kit.impact(2.2, vel=0.8, pitch=kit.note_hz("C1")), 1.0, 0.0), ("fx", bam, 0.7, 0.0)]
    items += [("fx", tone(s, 0, dur=3.0, vel=0.55, t60=2.6), 0.9, 0.0) for s in (0, 2, 4)]
    event("scene 2's number lands: impact, daf, chord", tm["accent1"], items)

    # 1405 at its keyframe: its pluck, a tick and a soft daf stroke; the lift is the hook's last three notes backwards
    pan26 = pan_of(years[-1], years)
    items = [("ticks", tick, 0.32, pan26), ("pluck", pluck(years[-1]), 1.0, pan26), ("fx", bam, 0.4, 0.0),
             ("hook", tone(LIFT[0][0], 0, dur=3.2, vel=0.42, t60=2.4), 1.0, 0.0)]
    event(f"{ret:.2f} s: 1405, its pluck, the lift begins (D)", ret, items)
    for step, beat in LIFT[1:]:
        event(f"lift step {step}", ret + beat * BEAT, [("hook", tone(step, 0, dur=3.2, vel=0.42, t60=2.4), 1.0, 0.0)])
    hit("pad", pad_of(END_CHORD, dur=end - ret + 1.0, vel=0.22, width=0.9, cutoff=1500.0, attack=1.2, release=1.5),
        ret, 1.0)

    # the second accent, quieter: scene 3's number lands. A chord on G and D, a daf rim
    items = [("fx", tone(s, o, dur=3.5, vel=0.4, t60=2.4), 0.9, 0.0) for s, o in END_CHORD]
    items.append(("fx", tak, 0.5, 0.0))
    event("scene 3's number lands: G and D, a daf rim", tm["accent2"], items)

    # the last bar line: a chord on G and D, with no tonic; the master's fade takes the tails to the end
    event(f"{end - BAR:.0f} s: the last chord, G and D, no tonic", end - BAR,
          [("fx", tone(s, o, dur=4.0, vel=0.45, t60=3.2), 0.9, 0.0) for s, o in END_CHORD])
    return bus, kicks, levels


# ── the mix ─────────────────────────────────────────────────────────────────

def _fit(x, n: int):
    """Crop or zero-pad x along time to n rows."""
    return x[:n] if len(x) >= n else np.concatenate([x, np.zeros((n - len(x),) + x.shape[1:])])


def mix_bus(bus: dict, kicks: list, n: int) -> np.ndarray:
    """The buses summed, the top octave cut. The hook and the pad are ducked under the kick and have a room; the
    plucks have a ping-pong echo; the sting, the wind, the ticks, the plucks and the accents are dry."""
    harm = kit.duck(kit.widen(bus["hook"], 0.3) + kit.widen(bus["pad"], 0.3), kicks, depth_db=3.0, release=0.15)
    wet = kit.reverb(harm, t60=1.8) * 0.25
    echo = kit.pingpong(bus["pluck"] * 0.5, delay=ECHO["delay"], feedback=ECHO["feedback"], taps=ECHO["taps"]) * 0.5
    mix = (bus["drum"] + bus["kick"] + harm + _fit(wet, n) + bus["sub"] + bus["fx"] + bus["ticks"]
           + bus["pluck"] + _fit(echo, n) + bus["intro"] + bus["wind"])
    return _air_cut(mix)


def render(film, curve: np.ndarray, log: list | None = None):
    """The mastered track (bass in mono), the mix before the master (for the verification), the groove's levels.
    The bass is made mono after the master: the limiter's gain changes would otherwise leave stereo below 120 Hz."""
    rec = [] if log is None else log
    bus, kicks, levels = _compose(film, curve, rec)
    mix = mix_bus(bus, kicks, len(bus["fx"]))
    track = kit.master(mix, lufs=LUFS, tp=TP, seconds=float(film.starts[-1]), fade_out=1.0)
    return _bass_mono(track), mix, levels


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


def _side_db(x, fc: float) -> float:
    """The side (L minus R) against the mid (L plus R), in power, over the spectrum below fc (Hz), dB."""
    spec = np.fft.rfft(np.asarray(x, float), axis=0)
    low = np.fft.rfftfreq(len(x), 1.0 / SR) < fc
    side = 0.5 * (spec[low, 0] - spec[low, 1])
    mid = 0.5 * (spec[low, 0] + spec[low, 1])
    return float(10 * np.log10(np.sum(np.abs(side) ** 2) / max(np.sum(np.abs(mid) ** 2), 1e-30)))


def _share_above(x, fc: float) -> float:
    """The share of the signal's energy above fc (Hz), dB: the top octave's content against the whole."""
    x = np.asarray(x, float)
    x = x.mean(axis=1) if x.ndim == 2 else x
    p = np.abs(np.fft.rfft(x)) ** 2
    f = np.fft.rfftfreq(len(x), 1.0 / SR)
    return float(10 * np.log10(max(p[f > fc].sum(), 1e-30) / max(p.sum(), 1e-30)))


def _flux(x, hop: int = 48, nfft: int = 256):
    """Spectral flux of a mono signal, frames 1 ms apart and 5.3 ms long. Returns each frame's centre time (s)
    and its flux: the rise of the log magnitude from one frame to the next, summed over the bins."""
    y = np.concatenate([np.zeros(nfft), x])
    starts = np.arange(0, len(y) - nfft + 1, hop)
    frames = y[starts[:, None] + np.arange(nfft)[None, :]] * np.hanning(nfft)
    logm = np.log10(np.abs(np.fft.rfft(frames, axis=1)) + 1e-5)
    rise = np.maximum(np.diff(logm, axis=0, prepend=logm[:1]), 0.0).sum(axis=1)
    return (starts - nfft / 2) / SR, rise


def _flux_onset(times, rise, t: float, w: float = MAX_OFFSET, first: bool = True):
    """The offset (s) of the onset within w of t, or None if there is none. The onset is the earliest local peak of
    the flux that reaches half the strongest one in the window: a pluck can bloom again a few tens of milliseconds
    after its attack, so the strongest peak is not always the attack. first=False gives the strongest peak."""
    sel = np.flatnonzero(np.abs(times - t) <= w)
    if len(sel) == 0:
        return None
    if not first:
        return float(times[sel[np.argmax(rise[sel])]] - t)
    top = rise[sel].max()
    peaks = [k for k in sel if 0 < k < len(rise) - 1 and rise[k] >= rise[k - 1] and rise[k] >= rise[k + 1]
             and rise[k] >= 0.5 * top]
    k = peaks[0] if peaks else sel[np.argmax(rise[sel])]
    return float(times[k] - t)


def check_audio(film, wav, out, log: list, mix, curve: np.ndarray, levels: list) -> None:
    """Print the numbers and assert the audio checks: loudness, the true peaks (WAV and decoded), the top octave
    cut before the master, the first and the last 0.1 s, the groove and the pitch against the lake, the bass in
    mono, and the events' onsets."""
    x = _read_wav(wav)
    lufs, tp = kit.integrated_lufs(x), kit.true_peak_dbtp(x)
    dec = _decode(out)
    aac_lufs, aac_tp = kit.integrated_lufs(dec), kit.aac_true_peak(out)
    a_dur = [float(s["duration"]) for s in _probe(out)["streams"] if s["codec_type"] == "audio"][0]
    tm = timing(film)
    print(f"times from the film: cover {tm['cover']:.2f} s, jump {tm['jump'][0][0]:.2f} s, rewind "
          f"{tm['t_back']:.2f}-{tm['t_first']:.2f} s, forward years {tm['forward'][0][0]:.2f}-"
          f"{tm['forward'][-1][0]:.2f} s, hook {tm['hook_start']:.2f} s, accent {tm['accent1']:.2f} s, "
          f"1405 {tm['ret']:.2f} s, accent {tm['accent2']:.2f} s, end {tm['end']:.2f} s")
    print(f"durations: WAV {len(x) / SR:.3f} s; muxed MP4 audio {a_dur:.3f} s")

    print("\n(1) loudness and true peak")
    print(f"    WAV            {lufs:+.2f} LUFS   {tp:+.2f} dBTP   (limit -1.5 dBTP)")
    print(f"    MP4 (decoded)  {aac_lufs:+.2f} LUFS   {aac_tp:+.2f} dBTP   (limit -1 dBTP)")
    assert -14.5 <= lufs <= -13.5 and -14.5 <= aac_lufs <= -13.5, (lufs, aac_lufs)
    assert tp <= -1.5 and aac_tp <= -1.0, (tp, aac_tp)
    air_mix, air_wav = _share_above(mix, AIR), _share_above(x, AIR)
    print(f"    the top octave (above {AIR / 1000:.0f} kHz): the mix before the master {air_mix:+.1f} dB of its energy, "
          f"the WAV {air_wav:+.1f} dB (its dither and the limiter's gain)")
    assert air_mix < -60.0, air_mix

    print("\n(2) the first 0.1 s: sound from the first frame")
    head = x[:int(0.1 * SR)]
    loud = np.flatnonzero(np.abs(x).max(axis=1) > 0.1)           # the first sample above -20 dBFS
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

    print("\n(4) the groove against the lake on screen: the mean area over the 2 s around each bar line")
    usual = float(film.med)
    print(f"    the usual area (film.med, the 40-year median) {usual:.4f} km2; full from {FULL * usual:.4f} km2 "
          f"(within {100 * karaj.NEAR:.0f} % of it: the film's own 'about the usual' band), mid from {usual / 2:.4f}, "
          f"thin from {usual / 4:.4f}")
    for b0, mean, lvl in levels:
        print(f"    {b0:5.1f} s   {mean:6.3f} km2 = {mean / usual:5.2f} x the usual   {lvl}")

    print("\n(5) RMS per 1 s of the WAV (dBFS) against the area on screen (mean over the second, km2)")
    rms = [_db(x[k * SR:(k + 1) * SR]) for k in range(int(len(x) / SR))]
    area = [float(curve[k * 1000:(k + 1) * 1000].mean()) for k in range(len(rms))]
    print("    s     " + " ".join(f"{k:>5d}" for k in range(len(rms))))
    print("    dB    " + " ".join(f"{v:>5.0f}" for v in rms))
    print("    km2   " + " ".join(f"{v:>5.2f}" for v in area))
    lo, hi = min(film.area[y] for y in tm["years"]), max(film.area[y] for y in tm["years"])
    areas = np.array([film.area[y] for _, y in tm["forward"]])
    steps = np.array([voice(film.area[y], lo, hi)[0] for _, y in tm["forward"]])
    rings = np.array([voice(film.area[y], lo, hi)[3] for _, y in tm["forward"]])
    r_step = float(np.corrcoef(np.log(areas), steps)[0, 1])
    r_ring = float(np.corrcoef(np.log(areas), rings)[0, 1])
    print(f"    the forward years: the pluck's pitch against log(area) r = {r_step:.3f}; "
          f"its ring against log(area) r = {r_ring:.3f}")
    assert r_step >= 0.9 and r_ring >= 0.9, (r_step, r_ring)

    print("\n(6) the bass in mono: the side against the mid in the spectrum of the WAV, below each frequency")
    marks = {f: _side_db(x, f) for f in (60.0, 90.0, 120.0)}
    print("    " + "   ".join(f"below {f:.0f} Hz {v:+.1f} dB" for f, v in marks.items()))
    assert marks[120.0] < -60, "the bass is not mono"

    print("\n(7) the events' onsets: each event's own sound (its first significant flux rise), and the same in the WAV")
    # (a) each event's own sound, through the same top-octave cut: its attack must sit at its event
    own = []
    for label, visual, hit_t, items in log:
        a = round((hit_t - 0.1) * SR)
        ev = kit.new_track(0.4)
        for sound, g, pan in items:
            kit.place(ev, sound, (round(hit_t * SR) - a) / SR, g, pan)
        lt, lr = _flux(_air_cut(ev.mean(axis=1)))
        own.append(_flux_onset(lt, lr, 0.1))
    assert all(v is not None for v in own), "an event with no onset"
    worst_own = max(abs(v) for v in own)
    print(f"    the sounds on their own, {len(own)} events: largest first-rise offset {worst_own * 1000:.2f} ms "
          f"(a click at a known time reads -1.67 ms here)")
    assert worst_own <= MAX_OFFSET, worst_own
    mm = mix.mean(axis=1)

    # (b) the same events in the WAV, after the master: the strongest flux peak within 30 ms of each event, with the
    #     rest of the mix taken out. The master's gain is estimated from the WAV and the mix; its residual is small.
    hp = butter(2, 12.0, "highpass", fs=SR, output="sos")          # the master's DC blocker
    mx = x.mean(axis=1)
    u = sosfilt(hp, mm[:len(mx)])
    w1 = round(0.001 * SR) | 1
    gain = (uniform_filter1d(mx * u, w1, mode="nearest")
            / np.maximum(uniform_filter1d(u * u, w1, mode="nearest"), 1e-12))   # the master as a gain curve
    wav_off = []
    for label, visual, hit_t, items in log:
        a = round((hit_t - 0.1) * SR)
        b = a + round(0.4 * SR)
        ev = kit.new_track(0.4)
        for sound, g, pan in items:
            kit.place(ev, sound, (round(hit_t * SR) - a) / SR, g, pan)
        evm = _air_cut(ev.mean(axis=1))
        cleared = mx[a:b] - gain[a:b] * (u[a:b] - sosfilt(hp, evm))  # hp(mix - event) = hp(mix) - hp(event)
        lt, lr = _flux(cleared)
        wav_off.append(_flux_onset(lt, lr, 0.1, first=False))
    assert all(v is not None for v in wav_off), "an event with no onset in the WAV"
    k_worst = int(np.argmax(np.abs(wav_off)))
    worst_wav = abs(wav_off[k_worst])
    print(f"    the WAV: largest strongest-peak offset {worst_wav * 1000:.2f} ms at {log[k_worst][0]} "
          f"(limit {MAX_OFFSET * 1000:.0f} ms)")
    assert worst_wav <= MAX_OFFSET, (log[k_worst][0], worst_wav)
    print(f"    {'event':<60}{'visual s':>10}{'own ms':>10}{'WAV ms':>10}")
    for (label, visual, _h, _i), o, wv in zip(log, own, wav_off):
        if not label.startswith(("rewind", "forward", "groove", "hook", "lift")):
            print(f"    {label:<60}{visual:10.3f}{o * 1000:+10.2f}{wv * 1000:+10.2f}")
    for group in ("rewind", "forward", "groove", "hook", "lift"):
        idx = [i for i, e in enumerate(log) if e[0].startswith(group)]
        if idx:
            o_arr = np.array([own[i] for i in idx]) * 1000
            w_arr = np.array([wav_off[i] for i in idx]) * 1000
            print(f"    {group + ' events, n=' + str(len(idx)):<60} own sound: largest |{np.abs(o_arr).max():.2f}| ms; "
                  f"WAV: largest |{np.abs(w_arr).max():.2f}| ms")
    for (label, _v, _h, _i), o, wv in zip(log, own, wav_off):
        if abs(wv - o) > 0.005:
            print(f"    note: {label}: the WAV's strongest flux peak is {wv * 1000:+.2f} ms from the event, while its own "
                  f"sound rises at {o * 1000:+.2f} ms (a later bump of the WAV within the window)")
    print(f"    all {len(log)} events: the sounds within {worst_own * 1000:.2f} ms, the WAV within "
          f"{worst_wav * 1000:.2f} ms (limit {MAX_OFFSET * 1000:.0f} ms): pass")

    print("\n    through the MP4's AAC audio, decoded (the accents: the strongest flux peak, offset in ms):")
    dtimes, drise = _flux(dec.mean(axis=1))
    worst_dec = 0.0
    for label, visual, hit_t, _items in log:
        if not label.startswith(("rewind", "forward", "groove", "hook", "lift")) and visual > 0.1:
            off = _flux_onset(dtimes, drise, hit_t, first=False)
            assert off is not None and abs(off) <= MAX_OFFSET, (label, off)
            worst_dec = max(worst_dec, abs(off))
            print(f"      {label:<60} {off * 1000:+7.2f}")
    print(f"    the decoded accents are within the limit (largest {worst_dec * 1000:.2f} ms)")


def check_video(video, out, untouched: bool) -> None:
    """The muxed MP4's video stream against the silent reel: the same packets, and the silent reel not rewritten."""
    vid, mux_p = _probe(video), _probe(out)
    print(f"\ndurations: silent reel video {float(vid['format']['duration']):.3f} s; "
          f"muxed MP4 {float(mux_p['format']['duration']):.3f} s")
    print("\n(8) the video stream of the muxed MP4 against the silent reel")
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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.parse_args()
    block_geo_stack()
    film = onebit_karaj.KarajFilm(onebit.THEMES["abi"], COLOURS["abi"])
    base = onebit.OUT / "social" / BASE
    video = Path(f"{base}_reel.mp4")
    wav = Path(f"{base}_music.wav")
    out = Path(f"{base}_music_reel.mp4")
    if video.stat().st_mtime < Path(onebit_karaj.__file__).stat().st_mtime:
        sys.exit(f"{video.name} is older than src/onebit_karaj.py: render the film first "
                 f"(python -I src/onebit_karaj.py), then run this score again")
    st = os.stat(video)
    before = (st.st_size, st.st_mtime_ns)
    end = float(film.starts[-1])
    curve = area_curve(film, end)
    log: list = []
    track, mix, levels = render(film, curve, log)
    kit.write_wav(wav, track)
    print("saved", wav)
    kit.mux(video, wav, out)
    print("saved", out)
    check_audio(film, wav, out, log, mix, curve, levels)
    st2 = os.stat(video)
    check_video(video, out, untouched=before == (st2.st_size, st2.st_mtime_ns))
    print("\nall checks pass")


if __name__ == "__main__":
    main()
