"""The score of the lost-water reel (tehranwater_fa, 26 s): «آبی که ایران از دست داد، روی تهران چقدر بالا می‌آید؟»
An original track in Segah, built from the Persian sound kit (onebit_persian) and timed to the film's own clock
(data/tehranwater/timeline.json, read through src/onebit_tehranwater.py, and the 3D frames' water thickness in
data/tehranwater/frames/frames.json). Everything in the music is synthesized here: no samples. The one voice is the
narration: seven Persian segments, synthesized offline (the fa_IR ganji medium voice) and placed on the film's clock;
the music is ducked under them (see NARRATION).

The mode is Segah on E (E, F-koron, G-sori, A, B, C-koron, D): the dastgah of lament (Mouyeh is a gusheh of
Segah). Its neutral third, G-sori, is neither major nor minor, so the music grieves without drama: the right
colour for a loss nobody sees, water that left the ground. The motif is a water drop and an open santur strike on
E, then the Segah triad down, E4 B3 G-sori3; it opens the reel at 0.00 s and returns at 23.40 s, and a reversed
strike swells into the loop point at 26.00 s, so the loop lands on the first frame's strike.

The water is the music's data. A low drone (E2 to E3, one octave) follows the water on screen, the 3D layer's
thickness over its final value (it meets the counter over 380 at the end of every year's step): at E3 while the layer stands
full, falling an octave as it drains, climbing with the counter, and stepping back down about 150 cents at the wet
year 1398. The santur tremolo plays the year shown, its pitch the year's km3 on the fourteen Segah steps from E3 to
E5, so it climbs two octaves and drops two steps at 1398. The daf roll's loudness follows the counter (-24 dB at
0 km3 to 0 dB at 380, as (km3/380)^1.5), and it thins to two strokes for the step down to 1398. A soft tick marks
each year when its label changes on the chip (the middle of each step); the last step, to 1402-1404, falls in the
silence and is marked by the landing.

    0.00 s         the hook: a water drop (B5 to E6, the bubble's rising pitch) and an open santur strike, E4 over E3;
                   B3 at 0.50 s, G-sori3 at 1.00 s; the drone holds E3 (the water at its full height)
    1.60-2.40 s    the water drains: a reversed whoosh whose band falls from 2.4 kHz to 200 Hz; the santur's ring
                   slows to a stop (a tape stop, its pitch falling); the drone falls an octave with the water
    2.40 s         the rise begins: a soft daf bam
    2.40-8.00 s    the riser: the daf roll (2 strokes a step, 4 from 1390-1391, 8 from 1399-1400, 2 for the step down
                   to 1398), the santur tremolo climbing (11.3 strokes a second), a soft tick at each year's label, a
                   noise swell; everything stops at 8.00 s
    8.00-8.40 s    silence: only the reverb's tail
    8.40 s         the number lands: an impact on E1, a tombak tom, a daf slap (tak) and bam, a santur chord E3 B3 E4
                   E5; the calm bed begins (pad E3 B3 E4, a quiet sub on E1)
    10.0-14.0 s    the bed: sparse setar, the Segah descent B3 A3 G-sori3, and the neighbour B3 C-koron4 B3
    15.00 s        beat 2: one soft thud (tombak tom and daf bam); the pad moves to E3 A3 E4
    19.00 s        beat 3: a quiet kamancheh phrase, the Segah cadence A4 G-sori4 F-koron4 E4; the pad back on E
    23.40 s        beat 4: the motif returns, drop and santur E4 over E3, then B3 and G-sori3; the drone comes back on
                   E3; the pad fades out by 25.4 s
    25.00-26.00 s  a reversed santur strike on E4 swells into 26.00 s; a 30 ms fade, no long fade-out: on the loop
                   the first frame's strike lands on it

Narration (seven segments on the film's clock, each one's speech starting at its start; the music is ducked DUCK_DB
under it with an attack of DUCK_ATTACK before the speech, none before s3, so the landing's impact sounds in full, and
a release of DUCK_RELEASE after it):

    0.15 s   s1  the satellites weighed Iran's water
    3.40 s   s2  from the year 1382 to 1404, Iran lost water:
    8.45 s   s3  about 380 billion m3 (right after the landing at 8.40 s; «سیصد» from about 8.85 s)
    11.35 s  s4  over Tehran it comes to about 600 m, taller than Milad Tower
    s4 + 0.3 s5  about three years of Iran's renewable water (0.30 s after s4's speech, not before 16.0 s)
    s5 + 0.3 s6  by the studies' estimate, most of it was groundwater (at 19.10 s, or 0.30 s after s5 if s5 ends
                 later; its speech ends before 23.5 s)
    23.60 s  s7  where does your city's water come from?
(every segment at length scale 0.85, duration noise 0, so a fresh synthesis has the same timing; no two overlap; a
start set by a rule is rounded up to 0.05 s; the script prints every start and end)

Mix: -14 LUFS integrated, true peak -1.5 dBTP in the WAV (the decoded AAC stays at -1 dBTP or below). The top octave
(above 12 kHz) is taken out before the master, the strings and drums are low-passed warm, and the bass below 120 Hz
is one channel in the spectrum (mono), as in the Latyan and air scores.

    python -I src/onebit_score_tehranwater.py                both cuts (the default)
    python -I src/onebit_score_tehranwater.py --only music   tehranwater_fa_music.wav, muxed under
                                                             tehranwater_fa_reel.mp4 into tehranwater_fa_music_reel.mp4
    python -I src/onebit_score_tehranwater.py --only voice   tehranwater_fa_voice.wav, muxed under
                                                             tehranwater_fa_voice_reel.mp4 into
                                                             tehranwater_fa_voice_music_reel.mp4

The narration needs the offline voice the first time: ONEBIT_TTS_BIN (the piper executable) and ONEBIT_TTS_MODEL
(the fa_IR-ganji-medium .onnx, its .onnx.json beside it); the rendered segments are cached in
data/tehranwater/narration/ (manifest.json) and reused. The silent reels must be newer than
src/onebit_tehranwater.py (--accept-stale-video skips that); the script waits for a reel that is still being
written (--wait seconds, default 1200). The silent reels are not rewritten. The script prints the loudness and the
true peak of each WAV and of each MP4's decoded audio, the RMS per second, the onsets of every event against its
cue, the drone and the tremolo against the counter, the silence before the landing, the ending, the bass in mono,
the narration on the clock with the voice over the ducked music, and the video streams against the silent reels.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from fractions import Fraction
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.ndimage import uniform_filter1d
from scipy.signal import butter, resample_poly, sosfilt, sosfiltfilt

sys.path.insert(0, str(Path(__file__).resolve().parent))


def block_geo_stack() -> None:
    """Keep the geo stack out of this process (the repo's rule, see onebit_score_latyan): the film reads JSON only."""
    for name in ("shapely", "cartopy", "fiona", "geopandas"):
        if name not in sys.modules:
            sys.modules[name] = None


block_geo_stack()

import onebit  # noqa: E402
import onebit_persian as kit  # noqa: E402
import onebit_tehranwater  # noqa: E402

SR = kit.SR
MODE = "segah"                                  # E, F-koron, G-sori, A, B, C-koron, D: the lament
TONIC = kit.note_hz("E3")                       # step 0 of the strings
DRONE_LO = kit.note_hz("E2")                    # the drone at no water; an octave up (E3) at the full layer
SUB_E, SUB_A = kit.note_hz("E1"), kit.note_hz("A1")
TAIL = 3.0                                      # s of room past the end, for the reverb
AIR = 12000.0                                   # Hz: above this the mix has no content (the AAC overshoot)
BASS = 120.0                                    # Hz: below this the two channels are one
MAX_OFFSET = 0.030                              # s: a hit may sit at most this far from its event
LUFS, TP = -14.0, -1.5                          # -1.5 dBTP in the WAV: the decoded AAC stays at -1 or below
END_FADE = 0.03                                 # s: the master's fade at 26.0 s (the loop lands on the strike)
SEED = 53
BASE = "tehranwater_fa"
SILENCE = 0.40                                  # s of silence before the landing (8.0-8.4 s)
TREM_STEPS = 14                                 # the santur tremolo: the counter on 14 Segah steps, E3 to E5
DAF_DB = (-24.0, 0.0)                           # the daf roll's level at 0 km3 and at the final km3 ...
DAF_SHAPE = 1.5                                 # ... as (km3 / final)^1.5: the build steepens towards the landing
DENSE = {6: 4, 14: 8}                           # the daf roll's strokes per step from step k on (2 before)
HOOK = ((0, 1, 0.0, 0.30), (0, 0, 0.0, 0.16), (4, 0, 0.5, 0.28), (2, 0, 1.0, 0.25))   # (step, octave, s, peak)
MOTIF_RETURN = HOOK                                       # beat 4: the same strike and the same notes
BED_NOTES = (("setar", 4, 0, 10.0), ("setar", 3, 0, 10.5), ("setar", 2, 0, 11.0),      # (instrument, step, octave, s)
             ("setar", 4, 0, 13.0), ("setar", 5, 0, 13.5), ("setar", 4, 0, 14.0),
             ("santur", 3, 0, 16.0), ("santur", 0, 1, 17.0), ("santur", 2, 0, 18.0))
KAM_PHRASE = ((3, 1, 0.0, 1.05), (2, 1, 1.0, 0.55), (1, 1, 1.5, 0.55), (0, 1, 2.0, 1.6))  # (step, octave, +s, dur)
PADS = ((((0, 0), (4, 0), (0, 1)), "land", 15.0, SUB_E),          # (chord, start, end, sub): E3 B3 E4 from the land
        (((0, 0), (3, 0), (0, 1)), 15.0, 19.0, SUB_A),            # E3 A3 E4 at beat 2
        (((0, 0), (4, 0), (0, 1)), 19.0, 25.4, SUB_E))            # E3 B3 E4 at beat 3, fading out from beat 4

# ── narration ───────────────────────────────────────────────────────────────
TTS_ENV_BIN, TTS_ENV_MODEL = "ONEBIT_TTS_BIN", "ONEBIT_TTS_MODEL"   # the offline engine and the voice file, from the
                                                                  # environment (no local paths in the repo)
NARR_DIR = onebit.ROOT / "data" / "tehranwater" / "narration"     # the rendered segments (the cache)
VOICE = "fa_IR-ganji-medium"
LENGTH = 0.85                                   # the voice's length scale (faster than its natural 1.0)
NOISE_W = 0.0                                   # no duration noise: the timing of a fresh synthesis is the same
PAD_S = 0.03                                    # s of silence kept before each speech
DUCK_DB = 9.5                                   # dB: the music under the speech
DUCK_ATTACK = 0.15                              # s: the music goes down over this time, ahead of the speech
DUCK_RELEASE = 0.40                             # s: the music comes back over this time after it
RATIO_TARGET = 14.0                             # dB: the voice over the ducked music, over all the speech, pre-master
RATIO_MIN = 10.0                                # dB: the least segment, measured after the master
GAP = 0.03                                      # s: a segment's speech ends at least this long before the next start
STEP = 0.05                                     # s: a start set by a rule is rounded up to this grid (the subtitles)
# start: a fixed time; or after (s after the previous speech's end) and earliest; latest_end: where the speech must end
NARRATION = (
    dict(name="s1", start=0.15, text="ماهواره‌ها آبِ ایران را وزن کردند."),
    dict(name="s2", start=3.40, text="از سالِ هشتاد و دو تا چهارصد و چهار، ایران آب از دست داد:"),
    dict(name="s3", start=8.45, duck_lead=0.0, text="حدودِ سیصد و هشتاد میلیارد متر مکعب."),
    dict(name="s4", start=11.35, text="روی تهران، حدودِ ششصد متر می‌شود؛ بلندتر از برجِ میلاد."),
    dict(name="s5", after=0.30, earliest=16.0, text="تقریباً سه سال آبِ تجدیدپذیرِ ایران."),
    dict(name="s6", after=0.30, earliest=19.10, latest_end=23.5, text="به برآوردِ پژوهش‌ها، بیشترش آبِ زیرزمینی بود."),
    dict(name="s7", start=23.60, text="آبِ شهرِ شما از کجا می‌آید؟"),
)
# «سیصد و هشتاد» in s3: the frication of the /s/ of «سیصد» starts S_ONSET s after the speech's onset, measured in the
# rendered WAV (the 4-9 kHz band; Piper's phoneme alignments run about 60 ms behind the frication). check_voice()
# measures it again.
WORD_380 = dict(segment="s3", s_onset=0.385)


def freq_of(step: int, octave: int = 0) -> float:
    return kit.degree(MODE, step, octave, tonic_hz=TONIC)


# ── the film's clock and the water on screen ────────────────────────────────

def timing(film) -> dict:
    """The film's own times: the drain, the rise, the landing, the beats, the step length, the years. A year's step
    k moves the counter from steps[k] to steps[k + 1] over [rise + k T, rise + (k + 1) T]; its label changes on the
    chip at the middle (film.step_at shows steps[k + 1] from u = 0.5). The dip is the one step whose km3 falls."""
    tl = film.tl
    steps = tl["steps"]
    T = float(tl["t_step"])
    rise, land = float(tl["rise"]), float(tl["land"])
    n = len(steps) - 1
    flips = [rise + (k + 0.5) * T for k in range(n)]
    dips = [k for k in range(n) if steps[k + 1]["km3"] < steps[k]["km3"]]
    tm = dict(drain=float(tl["drain"]), rise=rise, land=land, beats=[float(b) for b in tl["beats"]], T=T,
              end=float(tl["duration"]), fps=int(tl["fps"]), steps=steps, n_steps=n, flips=flips, dips=dips,
              cut=land - SILENCE, km3_end=float(steps[-1]["km3"]))
    assert abs(rise + n * T - land) < 1e-6, (rise, n, T, land)
    assert tm["beats"][0] == land and tm["end"] == 26.0 and tm["fps"] == 30, tm["beats"]
    assert len(dips) == 1 and steps[dips[0] + 1]["label"] == "1398", dips          # the wet year
    assert flips[-1] > tm["cut"] > flips[-2], (flips[-2:], tm["cut"])              # only the last label is in the silence
    for k in range(n):                                                             # the film shows this label from the flip
        st, _ = film.step_at(flips[k] + 1e-4)
        assert st is steps[k + 1], (k, st["label"])
    return tm


def water(film, tm, t: np.ndarray) -> np.ndarray:
    """The water on screen, 0 (none) to 1 (the full layer), per sample: the 3D frames' thickness (h_m) over its final
    value, linear between frames. It eases from year to year and meets the counter at the end of each year's step
    (checked in counter_check); the counter itself jumps to the next year's value at the chip's change."""
    ft = np.array([m["t"] for m in film.meta])
    h = np.array([m["h_m"] for m in film.meta])
    return np.clip(np.interp(t, ft, h / h[-1]), 0.0, 1.0)


def counter_check(film, tm) -> tuple:
    """(the largest gap between the water on screen and the year's km3 over its final value at the end of each year's
    step; the largest jump of the counter away from the label changes). The counter shows the chip's own value, so it
    changes only at the flips; the water eases between the years."""
    ends = [tm["rise"] + (k + 1) * tm["T"] for k in range(tm["n_steps"])]
    want = np.array([tm["steps"][k + 1]["km3"] for k in range(tm["n_steps"])]) / tm["km3_end"]
    gap = float(np.abs(water(film, tm, np.array(ends)) - want).max())
    ts = np.arange(tm["rise"], tm["land"] - 1e-6, 0.001)
    km3 = np.array([film.step_at(t)[1] for t in ts])
    moves = ts[1:][np.diff(km3) != 0]
    off = max(min(abs(t - f) for f in tm["flips"]) for t in moves) if len(moves) else 0.0
    return gap, float(off)


def counter_at(film, tm, t: float) -> float:
    """The counter's km3 over its final value at t (0 before the rise)."""
    v = film.step_at(t)[1]
    return 0.0 if v is None else float(v) / tm["km3_end"]


def shown_index(tm, t: float) -> int:
    """The index of the year shown on the chip at t (0 is 1382-1384)."""
    return int(sum(1 for f in tm["flips"] if f <= t + 1e-9))


def trem_step(tm, idx: int) -> int:
    """The tremolo's Segah step for the year idx: its km3 on TREM_STEPS steps."""
    return int(round(TREM_STEPS * tm["steps"][idx]["km3"] / tm["km3_end"]))


# ── sounds ──────────────────────────────────────────────────────────────────

def _tick() -> np.ndarray:
    """A soft tick: a band-passed click of 3 ms (the Latyan score's)."""
    n = int(0.02 * SR)
    t = np.arange(n) / SR
    noise = np.random.default_rng(31).standard_normal(n)
    x = sosfilt(butter(2, (1500.0, 5000.0), "bandpass", fs=SR, output="sos"), noise) * np.exp(-t / 0.003)
    x = x * np.minimum(1.0, t / 0.0005)
    return x / np.abs(x).max()


def drop(f0: float = None, f1: float = None) -> np.ndarray:
    """A water drop, mono: the bubble's ring, a sine whose pitch rises from f0 (B5) to f1 (E6, two octaves above the
    tonic E4) within about 30 ms and dies in about 0.1 s, a second smaller bubble 45 ms later a fourth lower, and a
    soft low plip at the surface. Peak 1."""
    f0 = f0 or kit.note_hz("B5")
    f1 = f1 or kit.note_hz("E6")
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    f = f1 - (f1 - f0) * np.exp(-t / 0.010)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * (1 - np.exp(-t / 0.0008)) * np.exp(-t / 0.032)
    t2 = np.clip(t - 0.045, 0.0, None)
    f2 = 0.75 * f
    x2 = np.sin(2 * np.pi * np.cumsum(f2) / SR) * (1 - np.exp(-t2 / 0.0008)) * np.exp(-t2 / 0.022) * (t >= 0.045)
    plip = np.sin(2 * np.pi * 260.0 * t) * (1 - np.exp(-t / 0.0005)) * np.exp(-t / 0.008)
    y = x + 0.3 * x2 + 0.25 * plip
    return kit._fade(y / np.abs(y).max(), 0.0003, 0.02)


def santur_note(step: int, octave: int, peak: float, dur: float = 3.0, t60: float = 2.6, bright: float = 0.5):
    """A santur note in Segah (stereo), set to `peak`."""
    x = np.asarray(kit.santur(freq_of(step, octave), dur=dur, vel=1.0, t60=t60, bright=bright), float)
    return x * (peak / np.abs(x).max())


def setar_note(step: int, octave: int, peak: float):
    x = np.asarray(kit.setar(freq_of(step, octave), dur=1.8, vel=1.0, t60=1.7, bright=0.3, buzz=0.05), float)
    return x * (peak / np.abs(x).max())


def whoosh(dur: float, rng) -> np.ndarray:
    """The drain, stereo: noise in a band whose centre falls from 2.4 kHz to 200 Hz (log), swelling like a reversed
    sound (as u^2.5) to its peak 80 ms before the end, then a raised-cosine release to zero at the end. Peak 1."""
    n = int(round(dur * SR))
    t = np.arange(n) / SR
    u = t / dur
    centres = np.geomspace(150.0, 3200.0, 12)
    fc = 2400.0 * (200.0 / 2400.0) ** u
    out = np.zeros((n, 2))
    wsum = np.zeros(n)
    for c in centres:
        w = np.exp(-((np.log(c) - np.log(fc)) / 0.35) ** 2)
        sos = butter(2, (c / 1.25, c * 1.25), "bandpass", fs=SR, output="sos")
        out += w[:, None] * sosfilt(sos, rng.standard_normal((n, 2)), axis=0)
        wsum += w
    out /= np.maximum(wsum, 1e-9)[:, None]
    rel = 0.08
    env = np.where(t < dur - rel, (t / (dur - rel)) ** 2.5,
                   np.cos(0.5 * np.pi * np.clip((t - (dur - rel)) / rel, 0, 1)) ** 2)
    out *= env[:, None]
    return out / np.abs(out).max()


def drone(film, tm, t: np.ndarray, spans) -> np.ndarray:
    """The drone, mono: harmonics 1-6 of a pitch that follows the water on screen, E2 at none and E3 at the full
    layer (DRONE_LO * 2^water); a low-pass at 300 Hz to 1.5 kHz (with the water) and a level of half to full (with the
    water). It sounds over `spans` ((start, end, fade-in, fade-out) in s) and is silent elsewhere."""
    u = water(film, tm, t)
    f = DRONE_LO * 2.0 ** u
    phase = 2 * np.pi * np.cumsum(f) / SR
    fc = 300.0 * 5.0 ** u
    x = np.zeros(len(t))
    for h in range(1, 7):
        x += h ** -1.3 * np.sin(h * phase) / np.sqrt(1.0 + (h * f / fc) ** 4)
    x *= 0.5 + 0.5 * u
    gate = np.zeros(len(t))
    for a, b, fin, fout in spans:
        g = np.clip((t - a) / fin, 0, 1) * np.clip((b - t) / fout, 0, 1)
        gate = np.maximum(gate, np.sin(0.5 * np.pi * g) ** 2)
    return x * gate


# ── the composition ─────────────────────────────────────────────────────────

SENDS = {"drop": 0.6, "santur": 0.35, "setar": 0.35, "kam": 0.35, "daf": 0.2}   # the sends to the room
SEND_HOOK = 0.35
BUSES = ("hook", "drop", "santur", "setar", "kam", "daf", "tick", "drone", "noise", "whoosh", "fx", "pad", "sub",
         "rev", "send")


def compose(film, rec: list):
    """Lay the score on its buses. rec receives one entry per checked event: (label, cue time, hit time, the sounds
    placed for it as (sound, gain, pan)). Returns (buses, the number of samples, the riser's strokes (time, year
    index, tremolo step, daf level dB) for the report)."""
    kit.reseed(SEED)
    rng = np.random.default_rng(SEED)
    tm = timing(film)
    end, rise, land, cut, T = tm["end"], tm["rise"], tm["land"], tm["cut"], tm["T"]
    bus = {k: kit.new_track(end, TAIL) for k in BUSES}
    n = len(bus["fx"])
    t_all = np.arange(n) / SR
    tick = _tick()
    strokes = []

    def put(name, sound, t, gain, pan):
        """A sound on its bus, and its send to the room (the hook is sent after its tape stop, below)."""
        kit.place(bus[name], sound, t, gain, pan)
        if name in SENDS:
            kit.place(bus["send"], sound, t, gain * SENDS[name], pan)

    def event(label, t, items, cue=None):
        for name, sound, gain, pan in items:
            put(name, sound, t, gain, pan)
        rec.append((label, t if cue is None else cue, t, [(s, g, p) for _, s, g, p in items]))

    # the hook at the first frame: the drop, the open strike (E4 over E3), then B3 and G-sori3 on the half-time grid
    d0 = drop()
    items = [("drop", d0, 0.28, 0.0)]
    items += [("hook", santur_note(s, o, pk, dur=4.0, t60=3.2), 1.0, 0.0) for s, o, dt, pk in HOOK if dt == 0.0]
    event("0.00 hook: water drop + open santur strike E4/E3", 0.0, items)
    for s, o, dt, pk in HOOK:
        if dt > 0:
            event(f"{dt:.2f} hook: santur {s}", dt, [("hook", santur_note(s, o, pk, dur=3.0, t60=2.6), 1.0, 0.0)])

    # the drain: the hook's ring slows to a stop from 1.6 to 2.4 s (its pitch falls), and a reversed whoosh falls
    i0, i1 = round(tm["drain"] * SR), round(rise * SR)
    src = bus["hook"][i0:].copy()
    stopped = kit.tape_stop(src, seconds=rise - tm["drain"], shape=2.0)
    m = len(stopped)
    stopped *= (np.cos(0.5 * np.pi * np.clip((np.arange(m) - (m - 0.25 * SR)) / (0.25 * SR), 0, 1)) ** 2)[:, None]
    bus["hook"][i0:] = 0.0
    bus["hook"][i0:i0 + m] = stopped
    bus["send"] += bus["hook"] * SEND_HOOK
    kit.place(bus["whoosh"], whoosh(rise - tm["drain"], rng), tm["drain"], 0.30)

    # the drone: the water on screen, from the first frame to the cut, and again from beat 4 to the end
    bus["drone"] += 0.07 * drone(film, tm, t_all, ((0.0, cut, 0.02, 0.03), (tm["beats"][3], end + 1.0, 1.0, 0.01)))[:, None]

    # the riser: a grid of T/4 from the rise to the cut; the daf follows the counter, the santur the year shown
    tak = kit.daf("tak", pitch=freq_of(0, 1))
    bam = kit.daf("bam", pitch=kit.note_hz("E2"))
    zang = kit.daf("zang")
    G = T / 4
    j = 0
    while rise + j * G < cut - 1e-9:
        for half in (0, 1):
            t = rise + (j + 0.5 * half) * G
            if t >= cut - 1e-9:
                break
            k, p = divmod(j, 4)
            dens = 2
            for k0, d in sorted(DENSE.items()):
                if k >= k0:
                    dens = d
            if k in tm["dips"]:
                dens = 2                                               # the step back down: the roll thins
            if half and dens < 8:
                continue
            u = counter_at(film, tm, t)
            lvl_db = DAF_DB[0] + (DAF_DB[1] - DAF_DB[0]) * u ** DAF_SHAPE
            g = 10 ** (lvl_db / 20)
            idx = shown_index(tm, t)
            items = []
            if (dens == 2 and p in (0, 2)) or dens >= 4:
                kind = "bam" if (p == 0 and not half) else "tak"
                pan = 0.0 if kind == "bam" else (0.3 if (j + half) % 2 else -0.3)
                items.append(("daf", bam if kind == "bam" else tak, (0.55 if kind == "bam" else 0.42) * g, pan))
                if kind == "tak":
                    items.append(("daf", zang, 0.07 * g, -pan))
            if not half:                                               # the santur tremolo, on the T/4 grid
                stp = trem_step(tm, idx)
                pk = (0.30 if j % 2 else 0.26) * (0.2 + 0.8 * 10 ** (lvl_db / 20))
                items.append(("santur", santur_note(stp, 0, pk, dur=0.9, t60=0.9, bright=0.55), 1.0,
                              0.22 if j % 2 else -0.22))
                strokes.append((t, idx, stp, lvl_db))
            is_flip = (not half) and p == 2
            if is_flip:
                items.append(("tick", tick, 0.30, 0.0))
            if items:
                if is_flip:
                    lab = tm["steps"][k + 1]["label"]
                    event(f"year {lab}: tick, daf, santur step {trem_step(tm, idx)}", t, items)
                elif t == rise:
                    event(f"{rise:.2f} the rise begins: daf bam, first santur stroke", t, items)
                else:
                    for name, sound, gain, pan in items:
                        put(name, sound, t, gain, pan)
        j += 1
    # the noise swell under the riser: a band rising from 400 Hz to 2.5 kHz as the counter climbs, cut at the cut
    a, b = round(rise * SR), round(cut * SR)
    tt = t_all[a:b]
    u_r = water(film, tm, tt)
    lo = sosfilt(butter(2, (300.0, 700.0), "bandpass", fs=SR, output="sos"), rng.standard_normal((b - a, 2)), axis=0)
    hi = sosfilt(butter(2, (1500.0, 3500.0), "bandpass", fs=SR, output="sos"), rng.standard_normal((b - a, 2)), axis=0)
    ramp = ((tt - rise) / (cut - rise)) ** 2
    sw = ((1 - u_r)[:, None] * lo + u_r[:, None] * hi) * (ramp * (0.4 + 0.6 * u_r))[:, None]
    sw *= np.clip((cut - tt) / 0.015, 0, 1)[:, None]
    bus["noise"][a:b] += 0.05 * sw / np.abs(sw).max()
    bus["send"][a:b] += 0.03 * sw / np.abs(sw).max()
    # nothing of the riser sounds after the cut: the strokes' rings are faded out over 20 ms at the cut
    c = round(cut * SR)
    fade = np.clip((c + round(0.02 * SR) - np.arange(n)) / (0.02 * SR), 0, 1)[:, None]
    for name in ("santur", "daf", "tick", "noise", "send"):     # the room keeps only what was sent before the cut
        bus[name][c:] *= fade[c:]

    # the landing: an impact on E1, a tombak tom, a daf slap and bam, a santur chord E3 B3 E4 E5
    chord = sum(santur_note(s, o, pk, dur=5.0, t60=3.6) for s, o, pk in ((0, 0, 0.13), (4, 0, 0.10), (0, 1, 0.12),
                                                                           (0, 2, 0.05)))
    items = [("fx", kit.impact(2.4, vel=1.0, pitch=SUB_E), 0.26, 0.0),
             ("fx", kit.tombak("tom", pitch=kit.note_hz("E2")), 0.20, 0.0),
             ("fx", kit.daf("bam", pitch=kit.note_hz("E2")), 0.18, 0.0),
             ("fx", kit.daf("tak", pitch=freq_of(0, 1)), 0.20, 0.0),
             ("santur", chord, 1.0, 0.0)]
    event(f"{land:.2f} the number lands: impact, tom, daf slap, santur chord", land, items)
    kit.place(bus["send"], kit.daf("tak", pitch=freq_of(0, 1)), land, 0.2)

    # the bed: the pads (with a quiet sub), the sparse setar and santur notes
    for chord_steps, a0, b0, sub_f in PADS:
        a0 = land if a0 == "land" else a0
        last = b0 == PADS[-1][2]
        dur = (b0 - a0) + (0.0 if last else 0.6)
        attack = 0.8 if a0 == land else 0.6
        p = kit.pad([freq_of(s, o) for s, o in chord_steps], dur=dur, vel=1.0, width=0.8, detune=5.0, cutoff=1100.0,
                    attack=attack, release=2.0 if last else 0.6)
        kit.place(bus["pad"], p, a0, 0.12)
        kit.place(bus["send"], p, a0, 0.04)
        s_dur = (b0 - a0) + (0.0 if last else 0.03)
        sb = kit.sub(sub_f, s_dur, vel=1.0)
        if last:
            sb = sb * np.clip((tm["beats"][3] + 1.0 - (a0 + np.arange(len(sb)) / SR)) / 1.0, 0, 1)
        kit.place(bus["sub"], sb * np.minimum(1.0, np.arange(len(sb)) / (0.6 * SR)), a0, 0.065)
    for inst, s, o, t in BED_NOTES:
        if inst == "setar":
            event(f"{t:.2f} bed: setar {s}/{o}", t, [("setar", setar_note(s, o, 0.34), 1.0, -0.15)])
        else:
            event(f"{t:.2f} bed: santur {s}/{o}", t, [("santur", santur_note(s, o, 0.22, dur=3.0, t60=2.4), 1.0, 0.15)])

    # beat 2: one soft thud
    b2 = tm["beats"][1]
    event(f"{b2:.2f} beat 2: soft thud (tom, daf bam)", b2,
          [("fx", kit.tombak("tom", pitch=kit.note_hz("E2")), 0.28, 0.0),
           ("fx", kit.daf("bam", pitch=kit.note_hz("E2")), 0.18, 0.0)])

    # beat 3: the kamancheh, the Segah cadence A4 G-sori4 F-koron4 E4
    b3 = tm["beats"][2]
    for s, o, dt, dur in KAM_PHRASE:
        x = kit.kamancheh(freq_of(s, o), dur=dur, vel=1.0, vib_hz=5.0, vib_cents=18.0, bow=0.10)
        event(f"{b3 + dt:.2f} beat 3: kamancheh {s}/{o}", b3 + dt, [("kam", x, 0.28, 0.1)])

    # beat 4: the motif returns: the drop, the open strike, B3, G-sori3; then the reversed strike into the loop point
    b4 = tm["beats"][3]
    items = [("drop", d0, 0.28, 0.0)]
    items += [("santur", santur_note(s, o, pk, dur=4.0, t60=3.2), 1.0, 0.0) for s, o, dt, pk in MOTIF_RETURN if dt == 0.0]
    event(f"{b4:.2f} beat 4: the motif returns (drop + santur E4/E3)", b4, items)
    for s, o, dt, pk in MOTIF_RETURN:
        if dt > 0:
            event(f"{b4 + dt:.2f} motif: santur {s}", b4 + dt, [("santur", santur_note(s, o, pk, dur=3.0, t60=2.6), 1.0, 0.0)])
    rev = kit.reverse(np.asarray(kit.santur(freq_of(0, 1), dur=1.0, vel=1.0, t60=3.2, bright=0.5), float))
    rev = rev * (0.30 / np.abs(rev).max())
    kit.place(bus["rev"], rev, end - len(rev) / SR, 1.0)

    # warm filters: the strings and the drums low-passed (no harsh highs)
    for name, fc, order in (("santur", 6000.0, 2), ("hook", 6000.0, 2), ("rev", 6000.0, 2), ("setar", 4000.0, 2),
                            ("kam", 3500.0, 4), ("daf", 8000.0, 2), ("fx", 7000.0, 2), ("whoosh", 4000.0, 2)):
        bus[name] = sosfilt(butter(order, fc, "lowpass", fs=SR, output="sos"), bus[name], axis=0)
    return bus, n, strokes, tm


def _fit(x, n: int):
    return x[:n] if len(x) >= n else np.concatenate([x, np.zeros((n - len(x),) + x.shape[1:])])


def _air_cut(x, fc: float = AIR) -> np.ndarray:
    """The top octave removed, exactly, in the spectrum. Zero-padded, so the wrap of the FFT does not reach the sound."""
    n = len(x)
    m = n + 2 * SR
    spec = np.fft.rfft(np.asarray(x, float), n=m, axis=0)
    spec[np.fft.rfftfreq(m, 1.0 / SR) > fc] = 0.0
    return np.fft.irfft(spec, n=m, axis=0)[:n]


def _bass_mono(x, fc: float = BASS) -> np.ndarray:
    """The low end in mono, exactly: below fc the two channels are averaged in the spectrum."""
    n = len(x)
    m = n + 2 * SR
    spec = np.fft.rfft(np.asarray(x, float), n=m, axis=0)
    low = np.fft.rfftfreq(m, 1.0 / SR) < fc
    mid = 0.5 * (spec[low, 0] + spec[low, 1])
    spec[low, 0] = mid
    spec[low, 1] = mid
    return np.fft.irfft(spec, n=m, axis=0)[:n]


def music_bus(bus: dict, n: int, tm) -> np.ndarray:
    """The buses summed with the room (one reverb on the send bus), before the top octave is cut. The room's return
    is held 6 dB lower through the silence, so only a breath of it is left."""
    room = _fit(kit.reverb(bus["send"], t60=2.4, predelay=0.02), n) * 0.55
    t = np.arange(n) / SR
    a, b = tm["cut"], tm["land"]
    dip = 1.0 - 0.5 * np.clip((t - a) / 0.05, 0, 1) * np.clip((b - t) / 0.02, 0, 1)
    room *= dip[:, None]
    dry = sum(bus[k] for k in BUSES if k != "send")
    return dry + room


# ── narration ───────────────────────────────────────────────────────────────

def _cached(seg: dict):
    """The segment as rendered before (same text, voice, length scale and duration noise), or None."""
    try:
        man = {m["name"]: m for m in json.loads((NARR_DIR / "manifest.json").read_text(encoding="utf-8"))}
        m = man[seg["name"]]
        if (m["text"] != seg["text"] or m["length_scale"] != LENGTH or m.get("voice") != VOICE
                or m.get("noise_w_scale") != NOISE_W):
            return None
        rate, pcm = wavfile.read(str(NARR_DIR / f"{seg['name']}.wav"))
        assert rate == SR
        return pcm.astype(float) / 32767.0, m["lead"], m["speech"]
    except (OSError, KeyError, ValueError, AssertionError):
        return None


def synth_segment(seg: dict) -> tuple:
    """One segment: the offline voice at LENGTH, cut to its speech (PAD_S of silence kept before and after it, the
    rest of Piper's leading and trailing silence trimmed), resampled to SR, mono, peak 0.9. Returns (samples, lead: s
    kept before the speech, speech: s of speech). A cached segment is reused."""
    hit = _cached(seg)
    if hit is not None:
        return hit
    binary, model = os.environ.get(TTS_ENV_BIN), os.environ.get(TTS_ENV_MODEL)
    if not binary or not model:
        sys.exit(f"the narration needs the offline voice: set {TTS_ENV_BIN} (the engine's executable) and "
                 f"{TTS_ENV_MODEL} (the {VOICE} voice file), or keep the segments rendered in {NARR_DIR}")
    assert Path(model).name.startswith(VOICE), (model, VOICE)
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "raw.wav"
        subprocess.run([binary, "-m", model, "--length-scale", str(LENGTH), "--noise-w-scale", str(NOISE_W),
                        "-f", str(raw)], input=(seg["text"] + "\n").encode("utf-8"), check=True, capture_output=True)
        rate, pcm = wavfile.read(str(raw))
    x = pcm.astype(float) / 32768.0
    if x.ndim > 1:
        x = x[:, 0]
    a = np.flatnonzero(np.abs(x) > 0.01 * np.abs(x).max())
    on, off = int(a[0]), int(a[-1]) + 1
    pad = int(round(PAD_S * rate))
    x = x[max(on - pad, 0): min(off + pad, len(x))]
    lead = (on - max(on - pad, 0)) / rate
    speech = (off - on) / rate
    f = Fraction(SR, rate)
    y = resample_poly(x, f.numerator, f.denominator)
    edge = int(0.01 * SR)
    y[:edge] *= np.linspace(0.0, 1.0, edge)
    y[-edge:] *= np.linspace(1.0, 0.0, edge)
    y = 0.9 * y / np.abs(y).max()
    NARR_DIR.mkdir(parents=True, exist_ok=True)
    wavfile.write(str(NARR_DIR / f"{seg['name']}.wav"), SR, (np.clip(y, -1, 1) * 32767).astype(np.int16))
    return y, lead, speech


def duck_gain(mask: np.ndarray) -> np.ndarray:
    """The music's gain per sample: DUCK_DB down while the mask is on; the attack and the release one-pole in dB."""
    from scipy.signal import lfilter
    a = math.exp(-1.0 / (SR * DUCK_ATTACK))
    r = math.exp(-1.0 / (SR * DUCK_RELEASE))
    target = np.where(mask, -DUCK_DB, 0.0)
    g = np.empty(len(target))
    cur = 0.0
    # piecewise: each run of a constant target is a one-pole filter from the current value
    edges = np.flatnonzero(np.diff(target)) + 1
    starts = np.concatenate([[0], edges])
    stops = np.concatenate([edges, [len(target)]])
    for s0, s1 in zip(starts, stops):
        tgt = target[s0]
        k = a if tgt < cur else r
        seg = lfilter([1 - k], [1, -k], np.full(s1 - s0, tgt), zi=[k * cur])[0]
        g[s0:s1] = seg
        cur = seg[-1]
    return 10.0 ** (g / 20.0)


def narrate(music: np.ndarray, n: int, end: float) -> dict:
    """The voice on the film's clock, and the music ducked under it. Returns the mix before the master (total), the
    music as it sounds (ducked), the voice (centred), the speech spans (name, start, end) in s and the duck gain."""
    v = np.zeros(n)
    spans, manifest, leads = [], [], []
    prev_end = 0.0
    for seg in NARRATION:
        y, lead, speech = synth_segment(seg)
        if "start" in seg:
            start = seg["start"]
        else:                                   # the rule: `after` s after the previous speech, not before `earliest`
            start = max(seg["earliest"], math.ceil((prev_end + seg["after"]) / STEP - 1e-6) * STEP)
        start = round(start, 3)
        assert start >= prev_end + GAP, (seg["name"], start, prev_end)            # no two segments overlap
        assert start + speech <= seg.get("latest_end", end - 0.3), (seg["name"], start + speech)
        i0 = round((start - lead) * SR)
        v[i0:i0 + len(y)] += y[:max(0, n - i0)]
        spans.append((seg["name"], start, start + speech))
        leads.append(seg.get("duck_lead", DUCK_ATTACK))
        prev_end = start + speech
        manifest.append(dict(name=seg["name"], start=start, speech=round(speech, 4), lead=round(lead, 4),
                             length_scale=LENGTH, noise_w_scale=NOISE_W, voice=VOICE, text=seg["text"]))
    NARR_DIR.mkdir(parents=True, exist_ok=True)
    (NARR_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    mask = np.zeros(n, bool)
    core = np.zeros(n, bool)
    for (_, a, b), dl in zip(spans, leads):
        mask[max(0, round((a - dl) * SR)):round(b * SR)] = True
        core[round(a * SR):round(b * SR)] = True
    gain = duck_gain(mask)
    music_d = music * gain[:, None]
    rms = lambda z: float(np.sqrt(np.mean(np.square(z))))  # noqa: E731
    v = sosfiltfilt(butter(2, 60.0, "highpass", fs=SR, output="sos"), v)   # the voice's rumble out (below 60 Hz)
    v *= rms(music_d[core]) * 10 ** (RATIO_TARGET / 20.0) / rms(v[core])
    voice = np.stack([v, v], axis=1)
    total = sosfiltfilt(butter(2, 20.0, "highpass", fs=SR, output="sos"), _air_cut(music_d + voice), axis=0)
    return dict(total=total, music=music_d, voice=voice, spans=spans, gain=gain)


# ── render ──────────────────────────────────────────────────────────────────

def render(film, log: list):
    """The composition, once, and both mixes: (music track, voice track, parts)."""
    bus, n, strokes, tm = compose(film, log)
    music = music_bus(bus, n, tm)
    stem = _air_cut(music)
    # 0.5 dB more headroom in the master: the bass made mono after it moves the peaks a little
    track_m = _bass_mono(kit.master(stem, lufs=LUFS, tp=TP - 0.5, seconds=tm["end"], fade_out=END_FADE))
    parts = narrate(music, n, tm["end"])
    track_v = _bass_mono(kit.master(parts["total"], lufs=LUFS, tp=TP - 0.5, seconds=tm["end"], fade_out=END_FADE))
    parts.update(stem=stem, bus=bus, strokes=strokes, tm=tm)
    return track_m, track_v, parts


def write_wav(path, x) -> Path:
    """48 kHz, 16-bit, stereo, with one TPDF dither for both channels (the bass stays mono, as in the air score)."""
    x = np.clip(np.asarray(x, float), -1, 1)
    rng = np.random.default_rng(3)
    dither = (rng.random(len(x)) - rng.random(len(x))) / 32768
    pcm = np.clip(np.round((x + dither[:, None]) * 32767), -32768, 32767).astype("<i2")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(str(path), SR, pcm)
    return path


# ── checks ──────────────────────────────────────────────────────────────────

def _read_wav(path) -> np.ndarray:
    rate, pcm = wavfile.read(str(path))
    assert rate == SR and pcm.ndim == 2 and pcm.shape[1] == 2, (rate, pcm.shape)
    return pcm.astype(float) / 32768.0


def _decode(media) -> np.ndarray:
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
    return subprocess.run(["ffmpeg", "-v", "error", "-i", str(media), "-map", stream, "-c", "copy", "-f", "md5", "-"],
                          check=True, capture_output=True, text=True).stdout.strip()


def _db(seg) -> float:
    return float(20 * np.log10(np.sqrt(np.mean(np.square(seg))) + 1e-12))


def _side_db(x, fc: float) -> float:
    spec = np.fft.rfft(np.asarray(x, float), axis=0)
    low = np.fft.rfftfreq(len(x), 1.0 / SR) < fc
    side = 0.5 * (spec[low, 0] - spec[low, 1])
    mid = 0.5 * (spec[low, 0] + spec[low, 1])
    return float(10 * np.log10(np.sum(np.abs(side) ** 2) / max(np.sum(np.abs(mid) ** 2), 1e-30)))


def _share_above(x, fc: float) -> float:
    x = np.asarray(x, float)
    x = x.mean(axis=1) if x.ndim == 2 else x
    p = np.abs(np.fft.rfft(x)) ** 2
    f = np.fft.rfftfreq(len(x), 1.0 / SR)
    return float(10 * np.log10(max(p[f > fc].sum(), 1e-30) / max(p.sum(), 1e-30)))


def _flux(x, hop: int = 48, nfft: int = 256):
    """Spectral flux of a mono signal, frames 1 ms apart and 5.3 ms long: (frame centre times, flux)."""
    y = np.concatenate([np.zeros(nfft), x])
    starts = np.arange(0, len(y) - nfft + 1, hop)
    frames = y[starts[:, None] + np.arange(nfft)[None, :]] * np.hanning(nfft)
    logm = np.log10(np.abs(np.fft.rfft(frames, axis=1)) + 1e-5)
    rise = np.maximum(np.diff(logm, axis=0, prepend=logm[:1]), 0.0).sum(axis=1)
    return (starts - nfft / 2) / SR, rise


def _flux_onset(times, rise, t: float, w: float = MAX_OFFSET, first: bool = True):
    """The offset (s) of the onset within w of t, or None: the earliest local flux peak reaching half the strongest
    in the window (first=False: the strongest)."""
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


def _event_offsets(events, mx: np.ndarray, mm: np.ndarray) -> list:
    """Each event's strongest onset in mx (mono), with the rest of the mix mm (before the master) taken away: mm is
    high-passed and fitted to mx locally (the master as a gain curve), so only the event's own sound is measured."""
    hp = butter(2, 12.0, "highpass", fs=SR, output="sos")
    u = sosfilt(hp, mm[:len(mx)])
    w1 = round(0.001 * SR) | 1
    gain = (uniform_filter1d(mx * u, w1, mode="nearest")
            / np.maximum(uniform_filter1d(u * u, w1, mode="nearest"), 1e-12))
    offs = []
    for label, cue, hit_t, items in events:
        lead = min(0.1, hit_t)
        a = round((hit_t - lead) * SR)
        b = a + round(0.4 * SR)
        ev = kit.new_track(0.4)
        for sound, g, pan in items:
            kit.place(ev, sound, (round(hit_t * SR) - a) / SR, g, pan)
        evm = _air_cut(ev.mean(axis=1))
        cleared = mx[a:b] - gain[a:b] * (u[a:b] - sosfilt(hp, evm))
        lt, lr = _flux(cleared)
        offs.append(_flux_onset(lt, lr, lead, first=False))
    return offs


def _own_offsets(events) -> list:
    out = []
    for label, cue, hit_t, items in events:
        lead = min(0.1, hit_t)
        a = round((hit_t - lead) * SR)
        ev = kit.new_track(0.4)
        for sound, g, pan in items:
            kit.place(ev, sound, (round(hit_t * SR) - a) / SR, g, pan)
        lt, lr = _flux(_air_cut(ev.mean(axis=1)))
        out.append(_flux_onset(lt, lr, lead))
    return out


def _pitch(x: np.ndarray, t0: float, t1: float, lo: float = 70.0, hi: float = 200.0) -> float:
    """The fundamental (Hz) of x between t0 and t1 by autocorrelation, with a parabolic peak."""
    seg = x[round(t0 * SR):round(t1 * SR)]
    seg = seg - seg.mean()
    ac = np.correlate(seg, seg, "full")[len(seg) - 1:]
    a, b = int(SR / hi), int(SR / lo)
    k = a + int(np.argmax(ac[a:b]))
    y0, y1, y2 = ac[k - 1], ac[k], ac[k + 1]
    shift = 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2)
    return SR / (k + shift)


def check_mix(name: str, x: np.ndarray, out: Path, log: list, mix: np.ndarray, parts: dict, voice: bool) -> dict:
    """Loudness, true peak, the first 0.1 s, the ending, the bass, the RMS per second, the onsets. Returns the cue
    onsets for the table."""
    tm = parts["tm"]
    lufs, tp = kit.integrated_lufs(x), kit.true_peak_dbtp(x)
    dec = _decode(out)
    aac_lufs, aac_tp = kit.integrated_lufs(dec), kit.aac_true_peak(out)
    a_dur = [float(s["duration"]) for s in _probe(out)["streams"] if s["codec_type"] == "audio"][0]
    print(f"\n======== {name} ========")
    print(f"durations: WAV {len(x) / SR:.3f} s; muxed MP4 audio {a_dur:.3f} s")
    print("(1) loudness and true peak")
    print(f"    WAV            {lufs:+.2f} LUFS   {tp:+.2f} dBTP   (limit -1.5 dBTP)")
    print(f"    MP4 (decoded)  {aac_lufs:+.2f} LUFS   {aac_tp:+.2f} dBTP   (limit -1 dBTP)")
    assert -14.5 <= lufs <= -13.5 and -14.5 <= aac_lufs <= -13.5, (lufs, aac_lufs)
    assert tp <= -1.5 and aac_tp <= -1.0, (tp, aac_tp)
    clip = int(np.sum(np.abs(x) >= 32766 / 32768))
    print(f"    samples at full scale: {clip}; the top octave (above {AIR / 1000:.0f} kHz) of the mix before the "
          f"master {_share_above(mix, AIR):+.1f} dB; above 6 kHz {_share_above(x, 6000.0):+.1f} dB of the WAV's energy")
    assert clip == 0

    print("(2) the first 0.1 s")
    head = x[:int(0.1 * SR)]
    loud = np.flatnonzero(np.abs(x).max(axis=1) > 0.1)
    first_ms = 1000 * loud[0] / SR
    peak_db = 20 * np.log10(np.abs(head).max())
    print(f"    RMS {_db(head):.1f} dBFS, peak {peak_db:.1f} dBFS, first sample above -20 dBFS at {first_ms:.2f} ms")
    assert peak_db > -20 and first_ms < 20, "no sound in the first frame"

    print("(3) the ending (the loop point at 26.0 s): RMS per 0.1 s over the last second (dBFS)")
    win = int(0.1 * SR)
    ends = [_db(x[len(x) - (k + 1) * win:len(x) - k * win]) for k in range(10)][::-1]
    last_step = np.abs(np.diff(x[-int(0.005 * SR):], axis=0)).max()
    print("    " + " ".join(f"{v:.1f}" for v in ends))
    print(f"    last sample {np.abs(x[-1]).max():.2e}, largest step in the last 5 ms {last_step:.2e}; the master's fade "
          f"{END_FADE * 1000:.0f} ms; the first 0.1 s {_db(head):.1f} dBFS against the last 0.1 s {ends[-1]:.1f}")
    assert np.abs(x[-1]).max() < 2e-3 and last_step < 2e-2, "a click at the end"

    print("(4) the bass in mono: the side against the mid below each frequency")
    marks = {f: _side_db(x, f) for f in (60.0, 90.0, 120.0)}
    print("    " + "   ".join(f"below {f:.0f} Hz {v:+.1f} dB" for f, v in marks.items()))
    assert marks[120.0] < -60, "the bass is not mono"

    print("(5) RMS per second (dBFS)")
    rms = [_db(x[k * SR:(k + 1) * SR]) for k in range(int(len(x) / SR))]
    print("    s    " + " ".join(f"{k:>5d}" for k in range(len(rms))))
    print("    dB   " + " ".join(f"{v:>5.1f}" for v in rms))

    print("(6) the silence before the landing")
    pre, sil = _db(x[round((tm["cut"] - 0.4) * SR):round(tm["cut"] * SR)]), \
        _db(x[round((tm["cut"] + 0.05) * SR):round((tm["land"] - 0.02) * SR)])
    print(f"    {tm['cut'] - 0.4:.2f}-{tm['cut']:.2f} s {pre:.1f} dBFS; {tm['cut'] + 0.05:.2f}-{tm['land'] - 0.02:.2f} s "
          f"{sil:.1f} dBFS ({sil - pre:+.1f} dB)" + ("  (the voice speaks here; the music alone below)" if voice else ""))
    if not voice:
        assert sil <= pre - 18.0, (pre, sil)

    print("(7) the events' onsets: each event's own sound, and in the WAV and the decoded MP4 with the rest of the mix "
          "taken away")
    events = [e for e in log if e[3]]
    own = _own_offsets(events)
    wav_off = _event_offsets(events, x.mean(axis=1), mix.mean(axis=1))
    dec_off = _event_offsets(events, dec[:len(x)].mean(axis=1), mix.mean(axis=1))
    for arr, what in ((own, "own"), (wav_off, "WAV"), (dec_off, "decoded")):
        assert all(v is not None for v in arr), what
        worst = max(abs(v) for v in arr)
        print(f"    {what:<8} {len(arr)} events, largest offset {worst * 1000:.2f} ms (limit {MAX_OFFSET * 1000:.0f} ms)")
        assert worst <= MAX_OFFSET, (what, worst)
    # the cues in the plain WAV (nothing taken away): the strongest flux peak within 30 ms
    lt, lr = _flux(x.mean(axis=1))
    rows = {}
    for (label, cue, hit_t, _i), o, wv, dv in zip(events, own, wav_off, dec_off):
        plain = _flux_onset(lt, lr, hit_t, first=False)
        rows[label] = (cue, hit_t, o, wv, dv, plain)
    years = [k for k in rows if k.startswith("year")]
    print(f"    {'event':<62}{'cue s':>7}{'own':>8}{'WAV':>8}{'dec':>8}{'plain':>8}  (ms)")
    for label, (cue, hit_t, o, wv, dv, plain) in rows.items():
        if label in years[1:-1]:
            continue
        print(f"    {label:<62}{cue:7.3f}{o * 1000:+8.2f}{wv * 1000:+8.2f}{dv * 1000:+8.2f}"
              f"{(plain or 0) * 1000:+8.2f}")
    yo = np.array([[rows[k][2], rows[k][3], rows[k][4]] for k in years]) * 1000
    print(f"    the {len(years)} year ticks ({rows[years[0]][0]:.3f}-{rows[years[-1]][0]:.3f} s): largest |own| "
          f"{np.abs(yo[:, 0]).max():.2f} ms, |WAV| {np.abs(yo[:, 1]).max():.2f} ms, |decoded| {np.abs(yo[:, 2]).max():.2f} ms")
    return dict(lufs=lufs, tp=tp, aac_lufs=aac_lufs, aac_tp=aac_tp, rows=rows, rms=rms)


def check_design(film, parts: dict, x_music: np.ndarray) -> None:
    """The score against the film: the water against the counter, the drone's pitch, the tremolo's steps and the
    daf's level against the years (the dip at 1398), the drain, the cut and the reversed strike at the end."""
    tm, bus = parts["tm"], parts["bus"]
    print("\n======== the score against the film ========")
    gap = counter_check(film, tm)
    gap, off = gap
    print(f"(a) the 3D water (h_m over its final value) against each year's km3 (over {tm['km3_end']:.1f}) at the end of "
          f"its step: largest gap {gap:.4f}; the counter changes only at the label changes (largest distance "
          f"{off * 1000:.1f} ms), where the ticks, the tremolo's pitch and the daf's level change")
    assert gap < 0.01 and off <= 0.0015, (gap, off)
    dr = bus["drone"].mean(axis=1)
    print("(b) the drone's pitch (autocorrelation on the drone bus) against the water on screen")
    for t0, t1, what in ((0.4, 1.4, "the full layer, before the drain"), (2.36, 2.44, "drained (the rise begins)"),
                         (6.55, 6.65, "1397 (the top before the dip)"), (6.95, 7.05, "1398 (the wet year)"),
                         (7.75, 7.95, "1401")):
        f = _pitch(dr, t0, t1)
        u = float(water(film, tm, np.array([0.5 * (t0 + t1)]))[0])
        want = DRONE_LO * 2 ** u
        print(f"    {t0:5.2f}-{t1:5.2f} s {what:<34} {f:7.2f} Hz  (water {u:.3f}: {want:7.2f} Hz, "
              f"{1200 * math.log2(f / want):+5.1f} cents)")
    f_top, f_dip = _pitch(dr, 6.55, 6.65), _pitch(dr, 6.95, 7.05)
    print(f"    the step down to 1398: {1200 * math.log2(f_dip / f_top):+.0f} cents")
    assert f_dip < f_top * 2 ** (-100 / 1200)
    print("(c) the riser per year (the label shown): the santur tremolo's Segah step and the daf's level")
    by = {}
    for t, idx, stp, lvl in parts["strokes"]:
        by.setdefault(idx, []).append((stp, lvl))
    line = []
    for idx in sorted(by):
        stp = by[idx][0][0]
        lab = tm["steps"][idx]["label"]
        lab = "1382-84" if idx == 0 else lab
        line.append(f"{lab}:{stp}/{np.mean([v for _, v in by[idx]]):.0f}dB")
    print("    " + "  ".join(line))
    k_dip = tm["dips"][0]
    print(f"    the dip: {tm['steps'][k_dip]['label']} step {trem_step(tm, k_dip)} -> {tm['steps'][k_dip + 1]['label']} "
          f"step {trem_step(tm, k_dip + 1)} (km3 {tm['steps'][k_dip]['km3']:.0f} -> {tm['steps'][k_dip + 1]['km3']:.0f})")
    assert trem_step(tm, k_dip + 1) < trem_step(tm, k_dip)
    riser = (bus["daf"] + bus["santur"]).mean(axis=1)
    seg_db = []
    for k in range(tm["n_steps"]):
        a, b = tm["rise"] + k * tm["T"], min(tm["rise"] + (k + 1) * tm["T"], tm["cut"])
        if b > a:
            seg_db.append((tm["steps"][k + 1]["label"], _db(riser[round(a * SR):round(b * SR)])))
    print("    the daf and santur RMS per step (dBFS, before the master): "
          + " ".join(f"{lab}:{v:.0f}" for lab, v in seg_db))

    print("(d) the drain (1.6-2.4 s): the whoosh and the santur's tape stop")
    w = np.abs(bus["whoosh"]).max(axis=1)
    env = uniform_filter1d(w, round(0.005 * SR))
    pk = int(np.argmax(env))
    on = int(np.flatnonzero(env > env[pk] * 10 ** (-40 / 20))[0])
    off = int(np.flatnonzero(env > env[pk] * 10 ** (-60 / 20))[-1])
    print(f"    the whoosh: above -40 dB of its peak from {on / SR:.3f} s, its peak at {pk / SR:.3f} s, silent "
          f"(below -60 dB) after {off / SR:.3f} s")
    hk = bus["hook"].mean(axis=1)
    print(f"    the hook's ring: {_db(hk[round(1.3 * SR):round(1.6 * SR)]):.1f} dBFS at 1.3-1.6 s, "
          f"{_db(hk[round(2.4 * SR):round(2.6 * SR)]):.1f} at 2.4-2.6 s (stopped)")

    print("(e) the cut at 8.0 s: the riser's dry buses, RMS per 20 ms around it (dBFS, before the master)")
    dry = sum(bus[k] for k in ("daf", "santur", "tick", "noise", "drone")).mean(axis=1)
    print("    " + " ".join(f"{t:.2f}:{_db(dry[round(t * SR):round((t + 0.02) * SR)]):.0f}"
                            for t in np.arange(tm["cut"] - 0.06, tm["cut"] + 0.08, 0.02)))
    print("(f) the end: the reversed strike")
    rv = np.abs(bus["rev"][:round(tm["end"] * SR)]).max(axis=1)
    env = uniform_filter1d(rv, round(0.003 * SR))
    print(f"    the reversed strike's envelope peaks at {np.argmax(env) / SR:.3f} s (the loop point {tm['end']:.2f} s); "
          f"in the music WAV the last 30 ms {_db(x_music[-round(0.03 * SR):]):.1f} dBFS, the 30 ms before "
          f"{_db(x_music[-round(0.06 * SR):-round(0.03 * SR)]):.1f} dBFS")


def _sibilant(y: np.ndarray, t_expect: float, w: float = 0.12) -> float:
    """The onset (s) of the /s/ nearest t_expect in a segment's audio: the first 5 ms frame within +-w where the
    4-9 kHz band (against the whole) rises above half its largest share in the window."""
    hp = sosfilt(butter(4, (4000.0, 9000.0), "bandpass", fs=SR, output="sos"), y)
    h = round(0.005 * SR)
    nf = len(y) // h
    e_hi = np.array([np.mean(hp[i * h:(i + 1) * h] ** 2) for i in range(nf)])
    e_all = np.array([np.mean(y[i * h:(i + 1) * h] ** 2) for i in range(nf)]) + 1e-12
    share = e_hi / e_all
    t = (np.arange(nf) + 0.5) * h / SR
    sel = np.flatnonzero(np.abs(t - t_expect) <= w)
    top = share[sel].max()
    k = sel[np.flatnonzero(share[sel] >= 0.5 * top)[0]]
    return float(t[k] - 0.5 * h / SR)


def _pauses(y: np.ndarray, lead: float, floor_db: float = -40.0, least: float = 0.12) -> list:
    """The pauses inside a segment's speech: runs of 10 ms frames below floor_db under its loudest frame, at least
    `least` s long, as (start, end) in s after the speech's onset."""
    h = round(0.01 * SR)
    e = np.array([np.sqrt(np.mean(y[i:i + h] ** 2)) for i in range(0, len(y) - h, h)])
    quiet = 20 * np.log10(e + 1e-9) < 20 * np.log10(e.max()) + floor_db
    out, k = [], 0
    while k < len(quiet):
        if quiet[k]:
            j = k
            while j < len(quiet) and quiet[j]:
                j += 1
            if (j - k) * 0.01 >= least:
                out.append((k * 0.01 - lead, j * 0.01 - lead))
            k = j
        else:
            k += 1
    return out


def check_voice(x: np.ndarray, parts: dict) -> list:
    """The narration on the clock, the word «سیصد», the voice over the ducked music after the master, the duck."""
    print("(8) the narration: each segment's speech on the film's clock, and the voice over the ducked music")
    xm = x.mean(axis=1)
    ref = parts["total"].mean(axis=1)
    m = min(len(xm), len(ref)) - SR
    g = float(np.dot(xm[:m], ref[:m]) / np.dot(ref[:m], ref[:m]))
    v_m, m_m = parts["voice"].mean(axis=1), parts["music"].mean(axis=1)
    ratios, table = [], []
    for k, (name, a, b) in enumerate(parts["spans"]):
        i0, i1 = round(a * SR), round(b * SR)
        ratio = 10 * np.log10(np.mean(v_m[i0:i1] ** 2) / np.mean(m_m[i0:i1] ** 2))
        ratios.append(ratio)
        nxt = parts["spans"][k + 1][1] if k + 1 < len(parts["spans"]) else parts["tm"]["end"]
        duck = 20 * np.log10(parts["gain"][i0:i1].mean())
        print(f"    {name}  speech {a:6.2f}-{b:6.2f} s ({b - a:.2f} s; next start {nxt:.2f} s)  voice over music "
              f"{ratio:+.1f} dB  music ducked {duck:.1f} dB")
        table.append((name, a, b))
    print(f"    the least segment: voice {min(ratios):+.1f} dB over the music (limit {RATIO_MIN:.0f} dB); the master's "
          f"gain on the mix {20 * np.log10(g):+.1f} dB")
    assert min(ratios) >= RATIO_MIN, ratios
    seg = next(s for s in NARRATION if s["name"] == WORD_380["segment"])
    start = next(a for name, a, _ in parts["spans"] if name == seg["name"])
    y, lead, speech = synth_segment(seg)
    s_meas = _sibilant(y, lead + WORD_380["s_onset"]) - lead
    t_word = start + s_meas
    print(f"    «سیصد و هشتاد» in {seg['name']}: the /s/ of «سیصد» measured {s_meas:.3f} s after the speech's onset "
          f"(expected {WORD_380['s_onset']:.3f} s), at {t_word:.2f} s on the clock; the landing (impact) is at "
          f"{parts['tm']['land']:.2f} s ({t_word - parts['tm']['land']:+.2f} s)")
    assert abs(s_meas - WORD_380["s_onset"]) < 0.03, s_meas
    print("    the subtitles in the picture (onebit_tehranwater.SUBTITLES) against the speech (each line belongs to the "
          "last segment that starts at most 0.5 s after it; pauses of 120 ms or more inside the speech, for the splits):")
    starts = [a for _, a, _ in table]
    own = {name: [] for name, _, _ in table}
    for sa, sb, _ in onebit_tehranwater.SUBTITLES:
        k = max((i for i, a in enumerate(starts) if a - 0.5 <= sa), default=0)
        own[table[k][0]].append((sa, sb))
    for (name, a, b), seg in zip(table, NARRATION):
        y, lead, _ = synth_segment(seg)
        pauses = [(a + p0, a + p1) for p0, p1 in _pauses(y, lead) if 0.1 < p0 < b - a - 0.1]
        subs = own[name]
        if not subs:
            print(f"      {name}: speech {a:.2f}-{b:.2f} s: no subtitle line")
            continue
        sa, sb = subs[0][0], subs[-1][1]
        note = "ok" if abs(sa - a) <= 0.1 and sb >= b - 0.05 else f"move to start {a:.2f} s, end at or after {b:.2f} s"
        split = ""
        if len(subs) > 1:
            split = "; its split at " + ", ".join(f"{x[1]:.2f}" for x in subs[:-1]) + " s"
        ps = ", ".join(f"{p0:.2f}-{p1:.2f}" for p0, p1 in pauses) or "none"
        print(f"      {name}: speech {a:.2f}-{b:.2f} s; subtitle {sa:.2f}-{sb:.2f} s{split}: {note}; pauses {ps}")
    return table


def check_video(video, out, untouched: bool) -> None:
    vid, mux_p = _probe(video), _probe(out)
    print(f"(9) the video stream: silent reel {float(vid['format']['duration']):.3f} s; muxed "
          f"{float(mux_p['format']['duration']):.3f} s")
    v_md5, m_md5 = _md5(video, "0:v:0"), _md5(out, "0:v:0")
    print(f"    silent reel {v_md5}")
    print(f"    muxed reel  {m_md5}")
    assert v_md5 == m_md5, "the video stream changed"
    assert untouched, "the silent reel was rewritten"
    print("    the same packets; the silent reel was not rewritten")


def wait_for(video: Path, frames: int, timeout: float, film_src: Path, accept_stale: bool,
             newer_than: float | None = None) -> None:
    """Wait until the silent reel is complete: ffprobe reads `frames` video frames, and its size holds still between
    two looks 15 s apart (ffmpeg writes the file in place and moves its index at the end). With newer_than (epoch s),
    also wait until the reel was written after that time (a re-render under way)."""
    t0, last = time.time(), None
    while True:
        ok = False
        if video.exists() and (newer_than is None or video.stat().st_mtime > newer_than):
            try:
                vs = [s for s in _probe(video)["streams"] if s["codec_type"] == "video"][0]
                ok = int(vs.get("nb_frames", 0)) == frames
            except (subprocess.CalledProcessError, IndexError, ValueError, KeyError):
                ok = False
        size = video.stat().st_size if video.exists() else None
        if ok and size == last:
            break
        last = size if ok else None
        if time.time() - t0 > timeout:
            sys.exit(f"{video} is not complete after {timeout:.0f} s")
        print(f"waiting for {video.name} ({'complete, checking it holds' if ok else 'not ready'}) "
              f"{time.strftime('%H:%M:%S')} ...", flush=True)
        time.sleep(15)
    if not accept_stale and video.stat().st_mtime < film_src.stat().st_mtime:
        sys.exit(f"{video.name} is older than {film_src.name}: render the film first, then run this score again")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", choices=("music", "voice"), default=None, help="one cut only (default: both)")
    ap.add_argument("--wait", type=float, default=1200.0, help="s to wait for a silent reel still being written")
    ap.add_argument("--accept-stale-video", action="store_true",
                    help="skip the check that the silent reel is newer than src/onebit_tehranwater.py")
    ap.add_argument("--newer-than", default=None,
                    help="wait for silent reels written after this local time (ISO, e.g. 2026-11-06T17:28)")
    args = ap.parse_args()
    newer = None
    if args.newer_than:
        from datetime import datetime
        newer = datetime.fromisoformat(args.newer_than).timestamp()
    film = onebit_tehranwater.TehranWaterFilm(False)
    social = onebit.OUT / "social"
    film_src = Path(onebit_tehranwater.__file__)
    log: list = []
    track_m, track_v, parts = render(film, log)
    tm = parts["tm"]
    frames = round(tm["end"] * tm["fps"])
    results = {}
    cuts = [("music", f"{BASE}_reel.mp4", f"{BASE}_music.wav", f"{BASE}_music_reel.mp4", track_m, parts["stem"]),
            ("voice", f"{BASE}_voice_reel.mp4", f"{BASE}_voice.wav", f"{BASE}_voice_music_reel.mp4", track_v,
             parts["total"])]
    x_music = None
    for name, vid, wav, out, track, mix in cuts:
        if args.only and args.only != name:
            continue
        video, wav, out = social / vid, social / wav, social / out
        write_wav(wav, track)
        print("saved", wav)
        wait_for(video, frames, args.wait, film_src, args.accept_stale_video, newer)
        st = os.stat(video)
        print(f"the silent reel {video.name}: written {time.strftime('%H:%M:%S', time.localtime(st.st_mtime))}")
        before = (st.st_size, st.st_mtime_ns)
        kit.mux(video, wav, out)
        print("saved", out)
        x = _read_wav(wav)
        results[name] = check_mix(name, x, out, log, mix, parts, voice=(name == "voice"))
        if name == "music":
            x_music = x
        else:
            results["spans"] = check_voice(x, parts)
        st2 = os.stat(video)
        check_video(video, out, untouched=before == (st2.st_size, st2.st_mtime_ns))
    check_design(film, parts, x_music if x_music is not None else track_m)
    print("\nall checks pass")


if __name__ == "__main__":
    main()
