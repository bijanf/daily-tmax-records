"""The score of the land-subsidence reel (subsidence_fa, 26 s): «زیرِ پایِ کدام شهرها زمین پایین می‌رود؟»
An original track in Homayoun, built from the Persian sound kit (onebit_persian) and timed to the film's own clock
(data/subsidence/timeline.json: the count, the landing, the dive, the beats and the camera path; the brief's numbers
are the fallback). Everything in the music is synthesized here: no samples. The one voice is the narration: seven
Persian sentences, synthesized offline (the fa_IR ganji medium voice) and placed on the film's clock; the music is
ducked under them (see NARRATION).

The mode is Homayoun on D (D, Eb, F#, G, A, Bb, C; the kit's set, in 12-tone pitches): solemn, with the augmented
second Eb-F# that gives the cadence its weight. Segah (the lost-water reel) and Shur/Dashti (the Hamoun reel) are
left to the sister reels. Every pitch in the score is checked to lie in the mode.

The data in the music. The camera's height (the log of its distance, the same closed Hermite path as
src/subsidence3d.py through the timeline's keys) drives an air layer: noise in a band whose centre follows the height
(about 2.6 kHz from space, 140 Hz over the plain) at a level that follows the camera's speed, so the dive (7.8-13 s)
is a falling rush of air and the flight back out (20.5-26 s) a rising one; the drone's upper partials (A3, D4, Eb4)
also open with the height. The area counter (smoothstep from the count to the landing, as in the film) sets the
daf's level (-16 dB at 0 to -2 dB at 56,000 km2). The nine city labels (at 1.6 + 0.6 k s, k = 0..8, fixed in the
film) each sink the ground a step: a setar pluck per label walks down the mode, A4 G4 F#4 Eb4 D4 C4 Bb3 A3 G3; the
dive's bass walks down the same way (D2 C2 Bb1 A1), the flight out climbs back (A1 Bb1 C2 D2) under an ascending
santur line.

    0.00 s         the hook (the end state): a soft low santur strike D2 D3 A3 and a tombak over the drone
                   (D1 D2 A2 with a slow 0.5 Hz beating; exactly periodic over 26 s, so it runs through the loop);
                   0.60 s a soft setar Eb4 (the b2: tension)
    1.20 s         the count begins: a tombak stroke, a quiet santur D4
    1.60-6.40 s    the nine labels (every 0.6 s): a setar pluck a step lower each time and a daf bam at the counter's
                   level; a daf tak between them; a pad D3 A3 D4 swelling with the counter
    6.55-7.45 s    the roll: daf taks every 0.15 s, rising; a riser from 5.8 s; everything stops at 7.50 s
    7.50-7.80 s    the hush: only the drone (14 dB down), the air (15 dB down) and a breath of the room
    7.80 s         the number lands: an impact on D1, a tombak, a daf bam and tak, a santur chord D3 A3 D4 F#4
    8.60-13.0 s    the dive: the bass walks down D2 C2 Bb1 A1 under pads C-Eb-G, Bb-D-G, A-Eb-G-C, swelling; the
                   air falls with the camera
    13.0 s         the second number lands: a softer impact, a tombak, a daf, a santur D2 D3 A3; the pad on D F# A;
                   a slow heartbeat (daf, every 1.15 s) and a sparse setar figure A3 Bb3 A3 G3 F#3
    17.6 s         the cause, in the low register: a deep tombak on G1, the pad on G Bb D, the sub on G1; the
                   kamancheh's Homayoun cadence G3 F#3 Eb3 D3 (through the augmented second)
    20.5-23.4 s    the flight out: the bass climbs A1 Bb1 C2 D2 (pads A-C-Eb, Bb-D-F#, C-Eb-G), an ascending santur
                   line D3 to G4, the air rising with the camera
    23.4 s         the question: a daf, a santur D3 A3 and the labels' motif again, A4 G4 F#4 Eb4, stopping on the
                   open Eb4; the hook's strike, reversed, swells into 26.0 s, where the loop lands on the strike

The loop: the music is rendered with 3 s of tail and the tail is added back onto the start (the reverb and the last
notes ring into the first bar, as they do on Instagram's loop); the drone is exactly periodic and the camera is at
rest at the seam, so the last bar flows into the first. A 5 ms fade in and a 10 ms fade out keep the file's edges
clean on the first play.

Narration (seven sentences, each with a target window on the film's clock; the TTS input spells the numbers as
words, the display text stays for the subtitles). Every sentence is synthesized at LENGTH (0.85); with FALLBACK on,
one that does not fit its window is synthesized again at LENGTH_FLOOR (0.80, the fastest allowed); it is off (the
wording was shortened instead, 6 Nov). The spoken number of s2 must end before the counter lands (7.8 s): the
check asserts that s2's whole speech ends by then. The music is ducked DUCK_ATTACK ahead of each sentence, only
S3_LEAD (0.06 s) ahead of s3, which starts on the landing, so the impact still hits. The duck is DUCK_DB (9.5 dB)
deep, S6_DUCK_DB (13.5 dB) under s6, the softest sentence over the busiest bed. A sentence starts at its window's
start, or GAP after the previous speech if that ran late (rounded up to 0.01 s); the run prints and the manifest
records each sentence's speech on and off (by energy, the template's 1% of the peak), its window, and the overrun.
Segments are cached in data/subsidence/narration/ as <hash>.wav, the hash of (voice, length scale, duration noise,
TTS text): a changed sentence is the only one synthesized again; stale files are removed.

Mix: -14 LUFS integrated, true peak -1.5 dBTP in the WAV (so an AAC encode stays at -1 dBTP or below; the check
encodes one in a temporary directory). The top octave (above 12 kHz) is cut, the strings and drums are low-passed
warm, the bass below 120 Hz is mono. 48 kHz, 16 bit, exactly 26.000 s.

    python -I src/onebit_score_subsidence.py               both WAVs (subsidence_fa_music.wav, subsidence_fa_voice.wav)
    python -I src/onebit_score_subsidence.py --only music  the music WAV only
    python -I src/onebit_score_subsidence.py --narration   the narration only: synthesize what changed, print the fit
                                                           table, write the manifest (seconds; no music)

The narration needs the offline voice for any sentence not in the cache: ONEBIT_TTS_BIN (the piper executable) and
ONEBIT_TTS_MODEL (the fa_IR-ganji-medium .onnx, its .onnx.json beside it). No video is muxed (the silent reel is
another module's); the checks print the loudness and true peak of each WAV (the kit's BS.1770 meter and ffmpeg's
ebur128), the decoded AAC's, the RMS per second, the longest quiet run, the loop seam, the bass in mono, the events'
onsets against their cues, the narration on the clock and the voice over the ducked music.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.ndimage import uniform_filter1d
from scipy.signal import butter, lfilter, resample_poly, sosfilt, sosfiltfilt

sys.path.insert(0, str(Path(__file__).resolve().parent))

import onebit_persian as kit  # noqa: E402

SR = kit.SR
ROOT = kit.ROOT
SOCIAL = ROOT / "outputs" / "onebit" / "social"
TIMELINE = ROOT / "data" / "subsidence" / "timeline.json"
BASE = "subsidence_fa"
MODE = "homayoun"                               # D, Eb, F#, G, A, Bb, C
TONIC = kit.note_hz("D3")                       # step 0 of the strings
DUR = 26.0
N = int(round(DUR * SR))                        # 1,248,000 samples: exactly 26.000 s
TAIL = 3.0                                      # s rendered past the end, then wrapped onto the start (the loop)
AIR = 12000.0                                   # Hz: above this the mix has no content
BASS = 120.0                                    # Hz: below this the two channels are one
MAX_OFFSET = 0.030                              # s: a hit may sit at most this far from its cue
LUFS, TP = -14.0, -1.5                          # -1.5 dBTP in the WAV: an AAC encode stays at -1 or below
FADE_IN, FADE_OUT = 0.005, 0.010                # s: the file's edges (the loop's seam is continuous inside them)
SEAM_DB = 3.0                                   # dB: the largest level step allowed across the loop point
QUIET_DB, QUIET_MAX = -45.0, 1.0                # dBFS over 50 ms, s: no quiet run in the music longer than this
SEED = 71

# the film's clock: the brief's numbers; timeline.json overrides them (and adds the camera path)
CLOCK = dict(duration=26.0, fps=30, count=1.2, land=7.8, dive=8.6, close=13.0, back=20.5,
             beats=[7.8, 13.0, 17.6, 23.4])
LABEL_T0, LABEL_DT, N_LABELS = 1.6, 0.6, 9      # the labels' pop-in: 1.6 + 0.6 k s, k = 0..8 (fixed in the film)
HUSH = 0.30                                     # s of hush before the landing (7.5-7.8 s)
REV_S, REV_GAIN = 1.2, 1.25                     # the reversed strike into the loop point: its length (s) and gain
ROLL_DT = 0.15                                  # s: the roll's grid before the hush
DAF_DB = (-16.0, -2.0)                          # the daf's level at the counter's 0 and its final value ...
DAF_SHAPE = 1.5                                 # ... as counter^1.5

LABEL_NOTES = ("A4", "G4", "F#4", "Eb4", "D4", "C4", "Bb3", "A3", "G3")   # one step down per label
QUESTION_NOTES = ("A4", "G4", "F#4", "Eb4")                                # the motif again, ending open on Eb4
ASCENT = ("D3", "Eb3", "F#3", "G3", "A3", "Bb3", "C4", "D4", "Eb4", "F#4", "G4")   # the flight out, into the A4
BED_SETAR = (("A3", 14.15), ("Bb3", 14.73), ("A3", 15.30), ("G3", 16.45), ("F#3", 17.03))
HEART = (14.15, 15.30, 16.45)                   # the slow pulse after the second number (13.0 + k * 1.15 s)
CAUSE_PULSE = (18.325, 19.05, 19.775)           # the cause's pulse (17.6 + k * 0.725 s)
KAM_PHRASE = (("G3", 18.00, 0.95), ("F#3", 18.90, 0.55), ("Eb3", 19.40, 0.60), ("D3", 19.95, 1.50))
# (notes, start, end, sub note, pad gain): the harmony from the landing on
PADS = ((("D3", "A3", "D4"), "land", "dive", "D2", 0.10),
        (("C3", "G3", "Eb4"), "dive", 10.067, "C2", 0.11),
        (("Bb2", "G3", "D4"), 10.067, 11.533, "Bb1", 0.125),
        (("A2", "Eb3", "G3", "C4"), 11.533, "close", "A1", 0.14),
        (("D3", "F#3", "A3"), "close", 17.6, "D2", 0.11),
        (("G2", "Bb2", "D3"), 17.6, "back", "G1", 0.12),
        (("A2", "C3", "Eb3"), "back", 21.467, "A1", 0.10),
        (("Bb2", "D3", "F#3"), 21.467, 22.433, "Bb1", 0.11),
        (("C3", "Eb3", "G3"), 22.433, 23.4, "C2", 0.12),
        (("D3", "A3", "D4"), 23.4, 26.0, "D2", 0.10))
# the drone: (note, Hz offset, amplitude, pan, opens with the camera's height); every frequency is rounded to a
# multiple of 1/26 Hz, so the drone is exactly periodic over the reel and the loop has no seam in it
DRONE = (("D1", 0.0, 0.45, 0.0, False), ("D2", 0.0, 1.0, -0.25, False), ("D2", 0.5, 0.6, 0.25, False),
         ("A2", 0.0, 0.45, 0.2, False), ("D3", 0.0, 0.25, -0.2, False), ("A3", 0.0, 0.16, 0.3, True),
         ("D4", 0.0, 0.10, -0.3, True), ("Eb4", 0.0, 0.035, 0.35, True))
# the drone's level (dB) over the reel; the first and last values match (the loop)
DRONE_DB = ((0.0, -4.0), (1.2, -4.0), (7.3, 0.0), (7.5, -14.0), (7.78, -14.0), (7.8, -3.0), (8.6, -1.0), (12.8, 1.0),
            (13.0, -1.0), (17.6, 0.0), (20.5, -2.0), (23.4, -3.0), (26.0, -4.0))

# ── narration ───────────────────────────────────────────────────────────────
TTS_ENV_BIN, TTS_ENV_MODEL = "ONEBIT_TTS_BIN", "ONEBIT_TTS_MODEL"   # the offline engine and the voice file, from the
                                                                  # environment (no local paths in the repo)
NARR_DIR = ROOT / "data" / "subsidence" / "narration"            # the rendered segments (the cache) and manifest.json
VOICE = "fa_IR-ganji-medium"
LENGTH = 0.85                                   # the voice's length scale (faster than its natural 1.0)
LENGTH_FLOOR = 0.80                             # the fastest allowed, for a sentence that overruns its window at LENGTH
FALLBACK = False                                # off: every sentence at LENGTH (the coordinator's call, 6 Nov)
# s2's spoken number «پنجاه و شش هزار» must end before the counter lands. word_end: the end of «هزار» after the
# speech's onset, from Piper's phoneme alignments (model patched in memory, length scale 0.85, duration noise 0; the
# /r/ ends at 1.438 s, the /k/ of «کیلومتر» starts at 1.508 s); the check also asserts the whole sentence ends by then
NUMBER_BY = dict(segment="s2", by="land", word_end=1.438)
NOISE_W = 0.0                                   # no duration noise: a fresh synthesis has the same timing
PAD_S = 0.03                                    # s of silence kept before and after each speech
ON_OFF = 0.01                                   # speech on and off: the first and last sample above 1% of the peak
DUCK_DB = 9.5                                   # dB: the music under the speech
DUCK_ATTACK = 0.15                              # s: the music goes down over this time, ahead of the speech
DUCK_RELEASE = 0.40                             # s: the music comes back over this time after it
RATIO_TARGET = 14.0                             # dB: the voice over the ducked music, over all the speech, pre-master
RATIO_MIN = 10.0                                # dB: the least segment, measured after the master
S3_LEAD = 0.06                                  # s: s3 starts on the landing: a short duck ahead of it, so the impact
                                                # still hits but the voice stays RATIO_MIN over the music
S6_DUCK_DB = 13.5                               # dB: s6 is the softest sentence (two pauses, a quiet «است») over a
                                                # busy bed (the cause, then the flight out): a deeper duck under it
GAP = 0.12                                      # s: the least pause after a sentence that ran past the next start
STEP = 0.01                                     # s: a pushed start is rounded up to this grid
END_ROOM = 0.30                                 # s: the last speech ends at least this long before the loop point
# window: (start, end) on the clock; the speech starts at the start and must end by the end. text: the display (the
# subtitles); say: what the voice reads (numbers spelled as words), when it differs
NARRATION = (
    dict(name="s1", window=(0.15, 3.0), text="ماهواره‌ها فرونشستِ زمین را سنجیدند."),
    dict(name="s2", window=(3.6, 7.6), text="حدودِ ۵۶ هزار کیلومتر مربع از ایران پایین می‌رفت؛",
         say="حدودِ پنجاه و شش هزار کیلومتر مربع از ایران پایین می‌رفت؛"),
    dict(name="s3", window=(7.8, 10.2), duck_lead=S3_LEAD, text="بیش از چهار برابرِ استانِ تهران."),
    dict(name="s4", window=(10.35, 15.40), text="در کرج و جنوب‌غربِ تهران، تندترین نقاط سالی ۱۵ تا ۲۰ سانتی‌متر؛",
         say="در کرج و جنوب‌غربِ تهران، تندترین نقاط سالی پانزده تا بیست سانتی‌متر؛"),
    dict(name="s5", window=(15.55, 17.40), text="نزدیکِ یک وجب در سال."),
    dict(name="s6", window=(17.6, 23.2), duck_db=S6_DUCK_DB,
         text="علتِ اصلی: برداشتِ آبِ زیرزمینی؛ و بیشترِ این فرونشست برگشت‌ناپذیر است."),
    dict(name="s7", window=(23.4, 25.7), text="شهرِ شما روی این نقشه هست؟"),
)


def freq_of(step: int, octave: int = 0) -> float:
    return kit.degree(MODE, step, octave, tonic_hz=TONIC)


def hz(name: str) -> float:
    """A note of the score, checked to lie in Homayoun on D."""
    f = kit.note_hz(name)
    cents = round(1200 * math.log2(f / TONIC)) % 1200
    assert cents in kit.mode_cents(MODE), (name, cents)
    return f


# ── the film's clock ────────────────────────────────────────────────────────

def clock() -> dict:
    """The film's times: the brief's, overridden by data/subsidence/timeline.json where it has them (a difference is
    printed); the camera keys and the label times from the timeline if present."""
    c = dict(CLOCK)
    tl = json.loads(TIMELINE.read_text(encoding="utf-8")) if TIMELINE.exists() else {}
    for k in CLOCK:
        if k in tl and tl[k] != CLOCK[k]:
            print(f"note: the timeline's {k} = {tl[k]} (the brief: {CLOCK[k]}); the score follows the timeline")
        c[k] = tl.get(k, CLOCK[k])
    c["camera"] = tl.get("camera")
    c["labels"] = [float(v) for v in tl["label_times"]] if "label_times" in tl else \
        [round(LABEL_T0 + k * LABEL_DT, 3) for k in range(N_LABELS)]
    assert len(c["labels"]) == len(LABEL_NOTES), c["labels"]
    assert c["duration"] == DUR and c["fps"] == 30, c
    c["cut"] = c["land"] - HUSH
    c["named"] = dict(land=c["land"], dive=c["dive"], close=c["close"], back=c["back"])
    return c


def at(c: dict, v) -> float:
    return float(c["named"][v]) if isinstance(v, str) else float(v)


def ease(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def counter(c: dict, t):
    """The counter's value over its final value at t: smoothstep from the count to the landing (as in the film)."""
    return ease((np.asarray(t, float) - c["count"]) / (c["land"] - c["count"]))


def altitude(c: dict, t: np.ndarray) -> np.ndarray:
    """The camera's height, 0 (the lowest) to 1 (the highest), per time: the log of its distance on the closed cubic
    Hermite path of src/subsidence3d.py through the timeline's keys (at rest at the seam). Without keys: 1 over Iran,
    smoothstep down to 0 over the dive, 0 over the plain, smoothstep back up over the flight out."""
    t = np.asarray(t, float) % DUR
    keys = c.get("camera")
    if keys:
        ts = np.array([k["t"] for k in keys], float)
        v = np.array([math.log(k["dist"]) for k in keys])
        n = len(ts) - 1
        tan = np.zeros(n + 1)
        tan[1:n] = (v[2:] - v[:-2]) / (ts[2:] - ts[:-2])
        i = np.clip(np.searchsorted(ts, t, side="right") - 1, 0, n - 1)
        h = ts[i + 1] - ts[i]
        u = (t - ts[i]) / h
        y = ((2 * u ** 3 - 3 * u ** 2 + 1) * v[i] + (u ** 3 - 2 * u ** 2 + u) * h * tan[i]
             + (-2 * u ** 3 + 3 * u ** 2) * v[i + 1] + (u ** 3 - u ** 2) * h * tan[i + 1])
        tg = np.linspace(0, DUR, 2601)                  # the range is taken over the whole period
        ig = np.clip(np.searchsorted(ts, tg, side="right") - 1, 0, n - 1)
        hg = ts[ig + 1] - ts[ig]
        ug = (tg - ts[ig]) / hg
        yg = ((2 * ug ** 3 - 3 * ug ** 2 + 1) * v[ig] + (ug ** 3 - 2 * ug ** 2 + ug) * hg * tan[ig]
              + (-2 * ug ** 3 + 3 * ug ** 2) * v[ig + 1] + (ug ** 3 - ug ** 2) * hg * tan[ig + 1])
        return np.clip((y - yg.min()) / (yg.max() - yg.min()), 0.0, 1.0)
    down = 1 - ease((t - c["land"]) / (c["close"] - c["land"]))
    up = ease((t - c["back"]) / (DUR - c["back"]))
    return np.where(t < c["back"], down, up)


# ── sounds ──────────────────────────────────────────────────────────────────

def santur_note(name: str, peak: float, dur: float = 3.0, t60: float = 2.6, bright: float = 0.5):
    x = np.asarray(kit.santur(hz(name), dur=dur, vel=1.0, t60=t60, bright=bright), float)
    return x * (peak / np.abs(x).max())


def setar_note(name: str, peak: float, t60: float = 1.7):
    x = np.asarray(kit.setar(hz(name), dur=1.8, vel=1.0, t60=t60, bright=0.3, buzz=0.05), float)
    return x * (peak / np.abs(x).max())


def drone(c: dict) -> np.ndarray:
    """The drone, stereo, N samples: the DRONE partials (each exactly periodic over 26 s), the upper ones weighted by
    the camera's height, at the DRONE_DB level curve."""
    t = np.arange(N) / SR
    alt = altitude(c, t)
    lvl = 10 ** (np.interp(t, [p[0] for p in DRONE_DB], [p[1] for p in DRONE_DB]) / 20)
    out = np.zeros((N, 2))
    rng = np.random.default_rng(SEED + 1)
    for name, off, amp, pan, opens in DRONE:
        f = round((hz(name) + off) * DUR) / DUR
        x = amp * np.sin(2 * np.pi * f * t + rng.uniform(0, 2 * np.pi))
        if opens:
            x = x * (0.15 + 0.85 * alt)
        gl, gr = kit.pan_gains(pan)
        out[:, 0] += gl * x
        out[:, 1] += gr * x
    return out * lvl[:, None] / np.abs(out).max()


def air(c: dict, rng) -> tuple:
    """The camera's air, stereo, N samples, peak 1: noise in a band whose centre follows the height (140 Hz low, 2.6
    kHz high, log), at a level that follows the camera's speed (|d height / dt|, smoothed over 0.2 s). Returns (air,
    centre Hz per sample, level per sample)."""
    t = np.arange(N) / SR
    alt = altitude(c, t)
    speed = np.abs(np.gradient(alt, 1.0 / SR))
    speed = uniform_filter1d(speed, round(0.2 * SR), mode="wrap")
    lvl = (speed / speed.max()) ** 0.8
    fc = 140.0 * (2600.0 / 140.0) ** alt
    centres = np.geomspace(100.0, 3600.0, 12)
    out = np.zeros((N, 2))
    wsum = np.zeros(N)
    for cc in centres:
        w = np.exp(-((np.log(cc) - np.log(fc)) / 0.35) ** 2)
        sos = butter(2, (cc / 1.25, cc * 1.25), "bandpass", fs=SR, output="sos")
        out += w[:, None] * sosfilt(sos, rng.standard_normal((N, 2)), axis=0)
        wsum += w
    out /= np.maximum(wsum, 1e-9)[:, None]
    out *= lvl[:, None]
    return out / np.abs(out).max(), fc, lvl


# ── the composition ─────────────────────────────────────────────────────────

SENDS = {"hook": 0.35, "count": 0.25, "pluck": 0.35, "santur": 0.35, "setar": 0.35, "kam": 0.35, "perc": 0.15}
BUSES = ("hook", "count", "pluck", "santur", "setar", "kam", "perc", "fx", "pad", "sub", "drone", "air", "rev",
         "send")


def compose(c: dict, rec: list) -> tuple:
    """Lay the score on its buses (each N + TAIL long). rec receives one entry per checked event: (label, cue time,
    hit time, the sounds placed for it as (sound, gain, pan)). Returns (buses, extra: the air's centre and level, the
    counter strokes)."""
    kit.reseed(SEED)
    rng = np.random.default_rng(SEED)
    bus = {k: kit.new_track(DUR, TAIL) for k in BUSES}
    land, cut, close = c["land"], c["cut"], c["close"]
    strokes = []

    def put(name, sound, t, gain, pan):
        kit.place(bus[name], sound, t, gain, pan)
        if name in SENDS:
            kit.place(bus["send"], sound, t, gain * SENDS[name], pan)

    def event(label, t, items):
        for name, sound, gain, pan in items:
            put(name, sound, t, gain, pan)
        rec.append((label, t, t, [(s, g, p) for _, s, g, p in items]))

    # the drone and the air: the whole reel
    bus["drone"][:N] += 0.10 * drone(c)
    a_x, a_fc, a_lvl = air(c, rng)
    tt = np.arange(N) / SR
    hush = 1.0 - (1 - 10 ** (-15 / 20)) * np.clip((tt - c["cut"]) / 0.02, 0, 1) * np.clip((c["land"] - tt) / 0.02, 0, 1)
    bus["air"][:N] += 0.055 * a_x * hush[:, None]          # the air holds its breath through the hush too

    # the hook (the end state): a low santur strike over the drone, a soft tombak; the b2 at 0.6 s
    strike = santur_note("D3", 0.13, dur=4.0, t60=3.2) + santur_note("A3", 0.08, dur=4.0, t60=3.0) \
        + santur_note("D2", 0.08, dur=4.0, t60=3.4)
    event("0.00 hook: santur D2 D3 A3, tombak", 0.0,
          [("hook", strike, 1.0, 0.0), ("perc", kit.tombak("tom", pitch=hz("D2")), 0.12, 0.0)])
    event("0.60 hook: setar Eb4 (the b2)", 0.6, [("hook", setar_note("Eb4", 0.16), 1.0, 0.2)])
    event(f"{c['count']:.2f} the count begins: tombak, santur D4", c["count"],
          [("count", kit.tombak("tom", pitch=hz("D2")), 0.16, 0.0),
           ("count", santur_note("D4", 0.10, dur=2.5, t60=2.0), 1.0, -0.1)])

    # the labels: a setar a step lower each time, a daf bam at the counter's level, a tak between them
    bam = kit.daf("bam", pitch=hz("D2"))
    tak = kit.daf("tak", pitch=hz("D4"))
    zang = kit.daf("zang")
    for k, (tl, note) in enumerate(zip(c["labels"], LABEL_NOTES)):
        u = float(counter(c, tl))
        g = 10 ** ((DAF_DB[0] + (DAF_DB[1] - DAF_DB[0]) * u ** DAF_SHAPE) / 20)
        pan = 0.25 if k % 2 else -0.25
        event(f"label {k + 1} at {tl:.2f}: setar {note}, daf bam", tl,
              [("count", setar_note(note, 0.32), 1.0, pan), ("count", bam, 0.50 * g, 0.0)])
        strokes.append((tl, note, 20 * math.log10(g)))
        t2 = tl + LABEL_DT / 2
        if k >= 1 and t2 < cut:
            u2 = float(counter(c, t2))
            g2 = 10 ** ((DAF_DB[0] + (DAF_DB[1] - DAF_DB[0]) * u2 ** DAF_SHAPE) / 20)
            put("count", tak, t2, 0.34 * g2, -pan)
            put("count", zang, t2, 0.06 * g2, pan)
    # the roll into the hush, and a riser under it
    t = c["labels"][-1] + ROLL_DT
    j = 0
    while t < cut - 1e-6:
        u = float(counter(c, t))
        g = 10 ** ((DAF_DB[0] + (DAF_DB[1] - DAF_DB[0]) * u ** DAF_SHAPE) / 20) * (0.7 + 0.3 * j / 6)
        put("count", tak, t, 0.36 * g, 0.3 if j % 2 else -0.3)
        put("count", zang, t, 0.05 * g, -0.3 if j % 2 else 0.3)
        j += 1
        t = round(t + ROLL_DT, 6)
    r0 = 5.8
    rz = kit.riser(dur=cut - r0 + 0.05, vel=1.0, f0=hz("D3"), f1=hz("D5"))
    put("count", rz, r0, 0.07, 0.0)
    # under the count: a pad on D A D that swells with the counter
    cp = kit.pad([hz("D3"), hz("A3"), hz("D4")], dur=cut - c["count"] + 0.05, vel=1.0, width=0.8, detune=5.0,
                 cutoff=900.0, attack=0.5, release=0.05)
    cp = cp * (0.35 + 0.65 * counter(c, c["count"] + np.arange(len(cp)) / SR))[:, None]
    kit.place(bus["count"], cp, c["count"], 0.09)
    kit.place(bus["send"], cp, c["count"], 0.03)
    # the hush: nothing of the count sounds after the cut (a 20 ms fade); the room keeps only what was sent before
    ci = round(cut * SR)
    fade = np.clip((ci + round(0.02 * SR) - np.arange(len(bus["count"]))) / (0.02 * SR), 0, 1)[:, None]
    for name in ("count", "send"):
        bus[name][ci:] *= fade[ci:]

    # the landing: an impact on D1, a tombak, a daf bam and tak, a santur chord D3 A3 D4 F#4
    chord = santur_note("D3", 0.13, 5.0, 3.6) + santur_note("A3", 0.10, 5.0, 3.6) \
        + santur_note("D4", 0.11, 5.0, 3.6) + santur_note("F#4", 0.05, 5.0, 3.2)
    event(f"{land:.2f} the number lands: impact, tombak, daf, santur chord", land,
          [("fx", kit.impact(2.4, vel=1.0, pitch=hz("D1")), 0.26, 0.0),
           ("fx", kit.tombak("tom", pitch=hz("D2")), 0.20, 0.0),
           ("fx", kit.daf("bam", pitch=hz("D2")), 0.18, 0.0),
           ("fx", kit.daf("tak", pitch=hz("D4")), 0.20, 0.0),
           ("santur", chord, 1.0, 0.0)])
    kit.place(bus["send"], kit.daf("tak", pitch=hz("D4")), land, 0.2)

    # the harmony: pads with a quiet sub under each; the dive's bass walks down, the flight's climbs back
    for k, (notes, a0, b0, sub_note, pg) in enumerate(PADS):
        a0, b0 = at(c, a0), at(c, b0)
        last = k == len(PADS) - 1
        dur = (b0 - a0) + (0.0 if last else 0.5)
        attack = 0.6 if a0 == land else 0.35
        p = kit.pad([hz(nm) for nm in notes], dur=dur, vel=1.0, width=0.8, detune=5.0, cutoff=1000.0,
                    attack=attack, release=1.4 if last else 0.5)
        kit.place(bus["pad"], p, a0, pg)
        kit.place(bus["send"], p, a0, 0.35 * pg)
        s_dur = (b0 - a0) + (0.0 if last else 0.03)
        sb = kit.sub(hz(sub_note), s_dur, vel=1.0)
        if last:
            sb = sb * np.clip((b0 - 0.4 - (a0 + np.arange(len(sb)) / SR)) / 1.6, 0, 1)
        swell = 1.0 + (0.35 * (a0 - c["dive"]) / (close - c["dive"]) if c["dive"] <= a0 < close else 0.0)
        kit.place(bus["sub"], sb * np.minimum(1.0, np.arange(len(sb)) / (0.3 * SR)), a0, 0.06 * swell)

    # the second number: a softer impact, tombak, daf, a santur D2 D3 A3; then the heartbeat and the setar figure
    hit = santur_note("D2", 0.12, 4.0, 3.4) + santur_note("D3", 0.14, 4.0, 3.2) + santur_note("A3", 0.09, 4.0, 3.0)
    event(f"{close:.2f} the second number lands: impact, tombak, daf, santur", close,
          [("fx", kit.impact(2.0, vel=1.0, pitch=hz("D1")), 0.16, 0.0),
           ("fx", kit.tombak("tom", pitch=hz("D2")), 0.24, 0.0),
           ("fx", kit.daf("bam", pitch=hz("D2")), 0.16, 0.0),
           ("santur", hit, 1.0, 0.0)])
    for t in HEART:
        event(f"{t:.2f} heartbeat: daf bam", t, [("perc", kit.daf("bam", pitch=hz("D2")), 0.13, 0.0)])
    for note, t in BED_SETAR:
        event(f"{t:.2f} bed: setar {note}", t, [("setar", setar_note(note, 0.28), 1.0, -0.15)])

    # the cause: low register
    b3 = c["beats"][2]
    event(f"{b3:.2f} the cause: tombak G1, daf", b3,
          [("fx", kit.tombak("tom", pitch=hz("G1")), 0.28, 0.0),
           ("fx", kit.daf("bam", pitch=hz("G2")), 0.12, 0.0)])
    for t in CAUSE_PULSE:
        event(f"{t:.2f} cause pulse: tombak", t, [("perc", kit.tombak("tom", pitch=hz("G1")), 0.12, 0.0)])
    for note, t, dur in KAM_PHRASE:
        x = kit.kamancheh(hz(note), dur=dur, vel=1.0, vib_hz=5.0, vib_cents=16.0, bow=0.10)
        event(f"{t:.2f} the cause: kamancheh {note}", t, [("kam", x, 0.30, 0.1)])

    # the flight out: an ascending santur line from D3 into the question's A4
    back = c["back"]
    dt = (c["beats"][3] - back) / (len(ASCENT) + 1)
    for k, note in enumerate(ASCENT):
        t = round(back + k * dt, 4)
        pk = 0.10 + 0.10 * k / (len(ASCENT) - 1)
        event(f"{t:.2f} flight out: santur {note}", t,
              [("santur", santur_note(note, pk, dur=2.0, t60=1.8, bright=0.55), 1.0, -0.2 if k % 2 else 0.2)])

    # the question: daf, santur D3 A3, the labels' motif again, stopping on the open Eb4
    b4 = c["beats"][3]
    event(f"{b4:.2f} the question: daf, santur D3 A3, setar A4", b4,
          [("perc", kit.daf("bam", pitch=hz("D2")), 0.16, 0.0),
           ("santur", santur_note("D3", 0.14, 4.0, 3.0) + santur_note("A3", 0.10, 4.0, 3.0), 1.0, 0.0),
           ("pluck", setar_note(QUESTION_NOTES[0], 0.26), 1.0, -0.25)])
    for k, note in enumerate(QUESTION_NOTES[1:], start=1):
        t = round(b4 + k * LABEL_DT, 4)
        t60 = 2.6 if k == len(QUESTION_NOTES) - 1 else 1.7
        event(f"{t:.2f} the question: setar {note}", t,
              [("pluck", setar_note(note, 0.26, t60=t60), 1.0, 0.25 if k % 2 else -0.25)])
    # the hook's own strike, reversed, swells into the loop point (the seam is its mirror)
    rev = kit.reverse(strike[:round(REV_S * SR)]) * REV_GAIN
    kit.place(bus["rev"], rev, DUR - len(rev) / SR, 1.0)

    # warm filters: the strings and the drums low-passed
    for name, fc, order in (("santur", 6000.0, 2), ("hook", 6000.0, 2), ("rev", 6000.0, 2), ("setar", 4000.0, 2),
                            ("pluck", 4500.0, 2), ("count", 6500.0, 2), ("kam", 3500.0, 4), ("perc", 8000.0, 2),
                            ("fx", 7000.0, 2), ("air", 4000.0, 2)):
        bus[name] = sosfilt(butter(order, fc, "lowpass", fs=SR, output="sos"), bus[name], axis=0)
    return bus, dict(air_fc=a_fc, air_lvl=a_lvl, strokes=strokes)


def _fit(x, n: int):
    return x[:n] if len(x) >= n else np.concatenate([x, np.zeros((n - len(x),) + x.shape[1:])])


def _air_cut(x, fc: float = AIR) -> np.ndarray:
    """The top octave removed in the spectrum (zero-padded, so the FFT's wrap does not reach the sound)."""
    n = len(x)
    m = n + 2 * SR
    spec = np.fft.rfft(np.asarray(x, float), n=m, axis=0)
    spec[np.fft.rfftfreq(m, 1.0 / SR) > fc] = 0.0
    return np.fft.irfft(spec, n=m, axis=0)[:n]


def _bass_mono(x, fc: float = BASS) -> np.ndarray:
    """The low end in mono: below fc the two channels are averaged in the spectrum."""
    n = len(x)
    m = n + 2 * SR
    spec = np.fft.rfft(np.asarray(x, float), n=m, axis=0)
    low = np.fft.rfftfreq(m, 1.0 / SR) < fc
    mid = 0.5 * (spec[low, 0] + spec[low, 1])
    spec[low, 0] = mid
    spec[low, 1] = mid
    return np.fft.irfft(spec, n=m, axis=0)[:n]


def music_bus(bus: dict, c: dict) -> np.ndarray:
    """The buses summed with the room (one reverb on the send bus; its return held 6 dB lower through the hush),
    then the tail past 26 s added back onto the start: N samples."""
    n = len(bus["fx"])
    room = _fit(kit.reverb(bus["send"], t60=2.6, predelay=0.02), n) * 0.55
    t = np.arange(n) / SR
    dip = 1.0 - 0.5 * np.clip((t - c["cut"]) / 0.05, 0, 1) * np.clip((c["land"] - t) / 0.02, 0, 1)
    room *= dip[:, None]
    x = sum(bus[k] for k in BUSES if k != "send") + room
    out = x[:N].copy()
    tail = x[N:]
    out[:len(tail)] += tail
    return out


def edges(x: np.ndarray) -> np.ndarray:
    """The file's edges: a raised-cosine fade in over FADE_IN and out over FADE_OUT."""
    x = np.array(x, float)
    a, b = round(FADE_IN * SR), round(FADE_OUT * SR)
    x[:a] *= (np.sin(0.5 * np.pi * np.arange(a) / a) ** 2)[:, None]
    x[-b:] *= (np.cos(0.5 * np.pi * (np.arange(b) + 1) / b) ** 2)[:, None]
    return x


def finish(mix: np.ndarray) -> np.ndarray:
    """The master: -14 LUFS, the true peak 0.5 dB under TP (the bass made mono after it moves the peaks a little),
    the bass in mono, the edges; exactly N samples."""
    y = kit.master(mix, lufs=LUFS, tp=TP - 0.5, seconds=DUR, fade_out=0.0)
    y = edges(_bass_mono(edges(y)))                 # faded again after the mono bass, which spreads a fade's edge
    assert len(y) == N, len(y)
    return y


# ── narration ───────────────────────────────────────────────────────────────

def _key(say: str, ls: float) -> str:
    return hashlib.sha1(f"{VOICE}|{ls:.3f}|{NOISE_W:.3f}|{say}".encode("utf-8")).hexdigest()[:12]


def on_off(y: np.ndarray) -> tuple:
    """(on, off) in s: the first and last sample above ON_OFF of the peak (the template's measure)."""
    a = np.flatnonzero(np.abs(y) > ON_OFF * np.abs(y).max())
    return a[0] / SR, (a[-1] + 1) / SR


def synth(say: str, ls: float) -> tuple:
    """One sentence at length scale ls: from the cache (<hash>.wav) or the offline voice, cut to its speech with
    PAD_S of silence either side, resampled to SR, mono, peak 0.9. Returns (samples, lead: s before the speech,
    speech: s, hash). The lead and the speech are measured on the cached file, so a cache hit and a fresh
    synthesis give the same numbers."""
    h = _key(say, ls)
    path = NARR_DIR / f"{h}.wav"
    if not path.exists():
        binary, model = os.environ.get(TTS_ENV_BIN), os.environ.get(TTS_ENV_MODEL)
        if not binary or not model:
            sys.exit(f"the narration needs the offline voice: set {TTS_ENV_BIN} (the engine's executable) and "
                     f"{TTS_ENV_MODEL} (the {VOICE} voice file), or keep the segments rendered in {NARR_DIR}")
        assert Path(model).name.startswith(VOICE), (model, VOICE)
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "raw.wav"
            subprocess.run([binary, "-m", model, "--length-scale", str(ls), "--noise-w-scale", str(NOISE_W),
                            "-f", str(raw)], input=(say + "\n").encode("utf-8"), check=True, capture_output=True)
            rate, pcm = wavfile.read(str(raw))
        x = pcm.astype(float) / 32768.0
        if x.ndim > 1:
            x = x[:, 0]
        a = np.flatnonzero(np.abs(x) > ON_OFF * np.abs(x).max())
        on, off = int(a[0]), int(a[-1]) + 1
        pad = int(round(PAD_S * rate))
        x = x[max(on - pad, 0): min(off + pad, len(x))]
        f = Fraction(SR, rate)
        y = resample_poly(x, f.numerator, f.denominator)
        edge = int(0.01 * SR)
        y[:edge] *= np.linspace(0.0, 1.0, edge)
        y[-edge:] *= np.linspace(1.0, 0.0, edge)
        y = 0.9 * y / np.abs(y).max()
        NARR_DIR.mkdir(parents=True, exist_ok=True)
        wavfile.write(str(path), SR, (np.clip(y, -1, 1) * 32767).astype(np.int16))
        print(f"synthesized {path.name} (length scale {ls}): {say}")
    rate, pcm = wavfile.read(str(path))
    assert rate == SR
    y = pcm.astype(float) / 32767.0
    on, off = on_off(y)
    return y, on, off - on, h


def layout() -> list:
    """Each sentence at LENGTH (with FALLBACK, at LENGTH_FLOOR if it overruns its window); placed at its window's
    start or GAP after the previous speech (rounded up to STEP) if that ran late. Rows: the placement and the fit."""
    rows, prev_end, keep = [], None, set()
    for seg in NARRATION:
        a, b = seg["window"]
        say = seg.get("say", seg["text"])
        assert not re.search(r"[0-9۰-۹٠-٩]", say), (seg["name"], "spell the numbers as words in `say`")
        y, lead, speech, h = synth(say, LENGTH)
        keep.add(h)
        ls, sp_hi, sp_lo = LENGTH, speech, None
        if FALLBACK and speech > (b - a) + 1e-9:
            y, lead, speech, h = synth(say, LENGTH_FLOOR)
            keep.add(h)
            ls, sp_lo = LENGTH_FLOOR, speech
        start = a
        if prev_end is not None and prev_end + GAP > a:
            start = math.ceil((prev_end + GAP) / STEP - 1e-6) * STEP
        start = round(start, 3)
        end = start + speech
        rows.append(dict(name=seg["name"], window=[a, b], start=start, end=round(end, 4), speech=round(speech, 4),
                         lead=round(lead, 4), length_scale=ls, speech_at_085=round(sp_hi, 4),
                         over_at_085=round(sp_hi - (b - a), 3),
                         over_at_080=None if sp_lo is None else round(sp_lo - (b - a), 3),
                         late=round(start - a, 3), over=round(end - b, 3), fits=bool(start == a and end <= b + 1e-9),
                         hash=h, file=f"{h}.wav", duck_lead=seg.get("duck_lead", DUCK_ATTACK),
                         duck_db=seg.get("duck_db", DUCK_DB),
                         text=seg["text"], say=say, y=y))
        prev_end = end
    for f in NARR_DIR.glob("*.wav"):                     # the cache keeps only the current sentences' renders
        if re.fullmatch(r"[0-9a-f]{12}", f.stem) and f.stem not in keep:
            f.unlink()
            print(f"removed the stale segment {f.name}")
    return rows


def write_manifest(rows: list) -> None:
    man = [dict(name=r["name"], window=r["window"], start=r["start"], end=r["end"], speech=r["speech"],
                lead=r["lead"], length_scale=r["length_scale"], noise_w_scale=NOISE_W, voice=VOICE, file=r["file"],
                fits=r["fits"], late=r["late"], over=r["over"], over_at_085=r["over_at_085"],
                over_at_080=r["over_at_080"], text=r["text"], say=r["say"]) for r in rows]
    NARR_DIR.mkdir(parents=True, exist_ok=True)
    (NARR_DIR / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")


def fit_table(rows: list) -> None:
    print("the narration against its windows (s; over: the speech's end past the window's end; at 0.85 / 0.80: the "
          "speech's length against the window's length, alone)")
    print(f"    {'':4}{'window':>14}{'speech on-off':>17}{'len':>7}{'ls':>6}{'late':>7}{'over':>7}"
          f"{'at 0.85':>9}{'at 0.80':>9}  fits")
    for r in rows:
        lo = "-" if r["over_at_080"] is None else f"{r['over_at_080']:+.3f}"
        print(f"    {r['name']:<4}{r['window'][0]:>6.2f}-{r['window'][1]:<6.2f}{r['start']:>8.3f}-{r['end']:<8.3f}"
              f"{r['speech']:>7.3f}{r['length_scale']:>6.2f}{r['late']:>+7.2f}{r['over']:>+7.3f}"
              f"{r['over_at_085']:>+9.3f}{lo:>9}  {'yes' if r['fits'] else 'NO'}")
    bad = [r["name"] for r in rows if not r["fits"]]
    if bad:
        print(f"    WARNING: {', '.join(bad)} do not fit their windows; the later sentences are pushed (see 'late')")


def duck_gain(target: np.ndarray) -> np.ndarray:
    """The music's gain per sample towards `target` (dB per sample: 0, or a sentence's duck depth below 0); the attack
    and the release one-pole in dB."""
    a = math.exp(-1.0 / (SR * DUCK_ATTACK))
    r = math.exp(-1.0 / (SR * DUCK_RELEASE))
    g = np.empty(len(target))
    cur = 0.0
    edges_ = np.flatnonzero(np.diff(target)) + 1
    starts = np.concatenate([[0], edges_])
    stops = np.concatenate([edges_, [len(target)]])
    for s0, s1 in zip(starts, stops):
        tgt = target[s0]
        k = a if tgt < cur else r
        seg = lfilter([1 - k], [1, -k], np.full(s1 - s0, tgt), zi=[k * cur])[0]
        g[s0:s1] = seg
        cur = seg[-1]
    return 10.0 ** (g / 20.0)


def narrate(music: np.ndarray, rows: list) -> dict:
    """The voice on the clock and the music ducked under it (N samples). Returns the mix before the master (total),
    the ducked music, the voice (centred), the speech spans (name, start, end) and the duck gain."""
    v = np.zeros(N)
    spans = []
    prev = 0.0
    for r in rows:
        assert r["start"] >= prev + 0.03 - 1e-9, (r["name"], r["start"], prev)       # no two sentences overlap
        i0 = round((r["start"] - r["lead"]) * SR)
        y = r["y"]
        v[i0:i0 + len(y)] += y[:max(0, N - i0)]
        spans.append((r["name"], r["start"], r["end"], r["duck_lead"], r["duck_db"]))
        prev = r["end"]
    assert prev <= DUR - END_ROOM, ("the narration runs into the loop point", prev)
    target = np.zeros(N)
    core = np.zeros(N, bool)
    for _, a, b, dl, depth in spans:
        i0, i1 = max(0, round((a - dl) * SR)), round(b * SR)
        target[i0:i1] = np.minimum(target[i0:i1], -depth)
        core[round(a * SR):round(b * SR)] = True
    gain = duck_gain(target)
    music_d = music * gain[:, None]
    rms = lambda z: float(np.sqrt(np.mean(np.square(z))))  # noqa: E731
    v = sosfiltfilt(butter(2, 60.0, "highpass", fs=SR, output="sos"), v)   # the voice's rumble out (below 60 Hz)
    v *= rms(music_d[core]) * 10 ** (RATIO_TARGET / 20.0) / rms(v[core])
    voice = np.stack([v, v], axis=1)
    total = sosfiltfilt(butter(2, 20.0, "highpass", fs=SR, output="sos"), _air_cut(music_d + voice), axis=0)
    return dict(total=total, music=music_d, voice=voice, spans=[s[:3] for s in spans], gain=gain)


# ── render ──────────────────────────────────────────────────────────────────

def render(c: dict, log: list, voice: bool = True) -> tuple:
    """The composition, once, and both mixes: (music track, voice track or None, parts)."""
    bus, extra = compose(c, log)
    music = music_bus(bus, c)
    stem = _air_cut(music)
    track_m = finish(stem)
    parts = dict(stem=stem, bus=bus, clock=c, **extra)
    track_v = None
    if voice:
        rows = layout()
        write_manifest(rows)
        parts.update(narrate(music, rows), rows=rows)
        track_v = finish(parts["total"])
    return track_m, track_v, parts


def write_wav(path, x) -> Path:
    """48 kHz, 16-bit, stereo, with one TPDF dither for both channels (the bass stays mono)."""
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


def _db(seg) -> float:
    return float(20 * np.log10(np.sqrt(np.mean(np.square(seg))) + 1e-12))


def ffmpeg_ebur128(path) -> tuple:
    """(integrated LUFS, true peak dBTP) by ffmpeg's ebur128 filter (BS.1770, 4x oversampled true peak)."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True, check=True)
    summary = r.stderr[r.stderr.rfind("Summary:"):]
    lufs = float(re.search(r"I:\s+(-?[\d.]+) LUFS", summary).group(1))
    tp = float(re.search(r"True peak:\s+Peak:\s+(-?[\d.]+) dBFS", summary).group(1))
    return lufs, tp


def aac_roundtrip(path) -> tuple:
    """(LUFS, true peak) of the WAV encoded as Instagram-like AAC (192 kbps) and decoded, in a temporary directory."""
    with tempfile.TemporaryDirectory() as tmp:
        m4a = Path(tmp) / "a.m4a"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(path), "-c:a", "aac", "-b:a", "192k",
                        str(m4a)], check=True)
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(m4a), "-f", "f32le", "-ac", "2", "-ar", str(SR),
                              "-"], check=True, capture_output=True).stdout
    dec = np.frombuffer(raw, dtype="<f4").reshape(-1, 2).astype(float)
    return kit.integrated_lufs(dec), kit.true_peak_dbtp(dec)


def _side_db(x, fc: float) -> float:
    """The side against the mid below fc (dB), over the whole file with a Hann window (without one, the leakage of
    the wide pads just above the split reads as side below it)."""
    x = np.asarray(x, float) * np.hanning(len(x))[:, None]
    spec = np.fft.rfft(x, axis=0)
    low = np.fft.rfftfreq(len(x), 1.0 / SR) < fc
    side = 0.5 * (spec[low, 0] - spec[low, 1])
    mid = 0.5 * (spec[low, 0] + spec[low, 1])
    return float(10 * np.log10(np.sum(np.abs(side) ** 2) / max(np.sum(np.abs(mid) ** 2), 1e-30)))


def _flux(x, hop: int = 48, nfft: int = 256):
    """Spectral flux of a mono signal, frames 1 ms apart and 5.3 ms long: (frame centre times, flux)."""
    y = np.concatenate([np.zeros(nfft), x])
    starts = np.arange(0, len(y) - nfft + 1, hop)
    frames = y[starts[:, None] + np.arange(nfft)[None, :]] * np.hanning(nfft)
    logm = np.log10(np.abs(np.fft.rfft(frames, axis=1)) + 1e-5)
    rise = np.maximum(np.diff(logm, axis=0, prepend=logm[:1]), 0.0).sum(axis=1)
    return (starts - nfft / 2) / SR, rise


def _flux_onset(times, rise, t: float, w: float = MAX_OFFSET, first: bool = True):
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


def quiet_runs(x: np.ndarray, floor_db: float = QUIET_DB, win: float = 0.05, hop: float = 0.01) -> tuple:
    """(the longest run in s of 50 ms windows below floor_db, its start s, the quietest window dBFS)."""
    m = x.mean(axis=1) if x.ndim == 2 else x
    w, h = round(win * SR), round(hop * SR)
    cs = np.concatenate([[0.0], np.cumsum(m * m)])
    st = np.arange(0, len(m) - w + 1, h)
    db = 10 * np.log10((cs[st + w] - cs[st]) / w + 1e-24)
    q = db < floor_db
    best, best_t, k = 0.0, None, 0
    while k < len(q):
        if q[k]:
            j = k
            while j < len(q) and q[j]:
                j += 1
            length = (j - k - 1) * hop + win
            if length > best:
                best, best_t = length, st[k] / SR
            k = j
        else:
            k += 1
    return best, best_t, float(db.min())


def seam(x: np.ndarray) -> dict:
    """The loop point: RMS of the last and the first 0.25 s and 0.5 s (dB), and the sample step across it."""
    out = {}
    for w in (0.25, 0.5):
        k = round(w * SR)
        out[w] = (_db(x[-k:]), _db(x[:k]))
    out["step"] = float(np.abs(x[0] - x[-1]).max())
    return out


def check_mix(name: str, x: np.ndarray, path: Path, log: list, mix: np.ndarray, parts: dict, voice: bool) -> dict:
    c = parts["clock"]
    lufs, tp = kit.integrated_lufs(x), kit.true_peak_dbtp(x)
    f_lufs, f_tp = ffmpeg_ebur128(path)
    a_lufs, a_tp = aac_roundtrip(path)
    print(f"\n======== {name}: {path.name} ========")
    print(f"duration {len(x) / SR:.6f} s ({len(x)} samples at {SR} Hz)")
    assert len(x) == N
    print("(1) loudness and true peak")
    print(f"    the kit (BS.1770)    {lufs:+.2f} LUFS   {tp:+.2f} dBTP")
    print(f"    ffmpeg ebur128       {f_lufs:+.2f} LUFS   {f_tp:+.2f} dBTP")
    print(f"    AAC 192k, decoded    {a_lufs:+.2f} LUFS   {a_tp:+.2f} dBTP   (limit -1 dBTP)")
    assert -14.5 <= lufs <= -13.5 and -14.5 <= f_lufs <= -13.5, (lufs, f_lufs)
    assert tp <= TP and f_tp <= -1.0 and a_tp <= -1.0, (tp, f_tp, a_tp)
    clip = int(np.sum(np.abs(x) >= 32766 / 32768))
    print(f"    samples at full scale: {clip}")
    assert clip == 0

    print("(2) the first 0.1 s")
    head = x[:int(0.1 * SR)]
    loud = np.flatnonzero(np.abs(x).max(axis=1) > 0.1)
    first_ms = 1000 * loud[0] / SR
    peak_db = 20 * np.log10(np.abs(head).max())
    print(f"    RMS {_db(head):.1f} dBFS, peak {peak_db:.1f} dBFS, first sample above -20 dBFS at {first_ms:.2f} ms")
    assert peak_db > -20 and first_ms < 30, "no sound in the first frame"

    print("(3) the loop seam (26.0 s -> 0.0 s)")
    s = seam(x)
    for w in (0.25, 0.5):
        e, b = s[w]
        print(f"    last {w:.2f} s {e:.1f} dBFS, first {w:.2f} s {b:.1f} dBFS: {b - e:+.1f} dB")
    print(f"    the step from the last sample to the first {s['step']:.2e}; the last sample "
          f"{np.abs(x[-1]).max():.2e}, the first {np.abs(x[0]).max():.2e}")
    if not voice:
        assert abs(s[0.5][1] - s[0.5][0]) < SEAM_DB and abs(s[0.25][1] - s[0.25][0]) < SEAM_DB, s
    assert np.abs(x[-1]).max() < 2e-3 and np.abs(x[0]).max() < 2e-3, "a click at an edge"

    print("(4) the bass in mono: the side against the mid below each frequency (the split is at 120 Hz)")
    marks = {f: _side_db(x, f) for f in (60.0, 90.0, 115.0)}
    print("    " + "   ".join(f"below {f:.0f} Hz {v:+.1f} dB" for f, v in marks.items()))
    assert marks[115.0] < -60, "the bass is not mono"

    print("(5) RMS per second (dBFS) and the longest quiet run")
    rms = [_db(x[k * SR:(k + 1) * SR]) for k in range(int(len(x) / SR))]
    print("    s    " + " ".join(f"{k:>5d}" for k in range(len(rms))))
    print("    dB   " + " ".join(f"{v:>5.1f}" for v in rms))
    q, qt, qmin = quiet_runs(x)
    where = f" from {qt:.2f} s" if qt is not None else ""
    print(f"    the longest run of 50 ms windows under {QUIET_DB:.0f} dBFS: {q:.2f} s{where}; the quietest 50 ms "
          f"{qmin:.1f} dBFS (limit {QUIET_MAX:.1f} s)")
    assert q <= QUIET_MAX, (q, qt)

    print("(6) the hush before the landing")
    pre = _db(x[round((c["cut"] - 0.4) * SR):round(c["cut"] * SR)])
    sil = _db(x[round((c["cut"] + 0.05) * SR):round((c["land"] - 0.02) * SR)])
    print(f"    {c['cut'] - 0.4:.2f}-{c['cut']:.2f} s {pre:.1f} dBFS; {c['cut'] + 0.05:.2f}-{c['land'] - 0.02:.2f} s "
          f"{sil:.1f} dBFS ({sil - pre:+.1f} dB)" + ("  (the voice may speak here)" if voice else ""))
    if not voice:
        assert sil <= pre - 10.0, (pre, sil)

    print("(7) the events' onsets: each event's own sound, and in the WAV with the rest of the mix taken away")
    events = [e for e in log if e[3]]
    own = _own_offsets(events)
    wav_off = _event_offsets(events, x.mean(axis=1), mix.mean(axis=1))
    for arr, what in ((own, "own"), (wav_off, "WAV")):
        assert all(v is not None for v in arr), what
        k = int(np.argmax([abs(v) for v in arr]))
        worst = abs(arr[k])
        print(f"    {what:<5} {len(arr)} events, largest offset {worst * 1000:.2f} ms "
              f"(limit {MAX_OFFSET * 1000:.0f} ms): {events[k][0]}")
        assert worst <= MAX_OFFSET, (what, worst)
    if not voice:
        print(f"    {'event':<58}{'cue s':>7}{'own':>8}{'WAV':>8}  (ms)")
        for (label, cue, _h, _i), o, w in zip(events, own, wav_off):
            print(f"    {label:<58}{cue:7.3f}{o * 1000:+8.2f}{w * 1000:+8.2f}")
    return dict(lufs=lufs, tp=tp, f_lufs=f_lufs, f_tp=f_tp, a_lufs=a_lufs, a_tp=a_tp, seam=s, quiet=q, rms=rms)


def check_voice(x: np.ndarray, parts: dict) -> list:
    """The narration on the clock, measured in the voice track by energy; the voice over the ducked music."""
    print("(8) the narration: each sentence's speech on the clock (measured on the placed voice, 1% of its peak), "
          "and the voice over the ducked music")
    v_m, m_m = parts["voice"].mean(axis=1), parts["music"].mean(axis=1)
    spans = parts["spans"]
    ratios, table = [], []
    for k, (name, a, b) in enumerate(spans):
        lo = round(max(0.0, a - 0.2, spans[k - 1][2] + 0.01 if k else 0.0) * SR)
        hi = round(min(spans[k + 1][1] - 0.01 if k + 1 < len(spans) else DUR, b + 0.25) * SR)
        on, off = on_off(v_m[lo:hi])
        on, off = lo / SR + on, lo / SR + off
        i0, i1 = round(a * SR), round(b * SR)
        ratio = 10 * np.log10(np.mean(v_m[i0:i1] ** 2) / np.mean(m_m[i0:i1] ** 2))
        ratios.append(ratio)
        duck = 20 * np.log10(parts["gain"][i0:i1].mean())
        print(f"    {name}  placed {a:6.3f}-{b:6.3f} s, measured {on:6.3f}-{off:6.3f} s ({off - on:.2f} s)  voice over "
              f"music {ratio:+.1f} dB  music ducked {duck:.1f} dB")
        # the off is measured after the voice's 60 Hz high-pass, which can take a few tens of ms of the faint tail
        assert abs(on - a) < 0.005 and abs(off - b) < 0.06, (name, on, off, a, b)
        table.append((name, round(on, 3), round(off, 3)))
    print(f"    the least sentence: voice {min(ratios):+.1f} dB over the music (limit {RATIO_MIN:.0f} dB)")
    assert min(ratios) >= RATIO_MIN, ratios
    a2, b2 = next((a, b) for nm, a, b in spans if nm == NUMBER_BY["segment"])
    land = at(parts["clock"], NUMBER_BY["by"])
    print(f"    the spoken number in {NUMBER_BY['segment']} ends at about {a2 + NUMBER_BY['word_end']:.2f} s (Piper's "
          f"alignment), the sentence at {b2:.2f} s; the counter lands at {land:.2f} s")
    assert a2 + NUMBER_BY["word_end"] < land and b2 <= land, (a2, b2, land)
    bed = parts["music"]
    e1, b1 = _db(bed[-round(0.25 * SR):]), _db(bed[:round(0.10 * SR)])
    print(f"    the loop seam under the voice: the ducked music's last 0.25 s {e1:.1f} dB, its first 0.10 s "
          f"(before the duck for s1 takes hold) {b1:.1f} dB: {b1 - e1:+.1f} dB (before the master); "
          f"the voice itself enters at "
          f"{spans[0][1]:.2f} s")
    return table


def check_design(parts: dict) -> None:
    c = parts["clock"]
    print("\n======== the score against the film ========")
    t = np.array([0.0, 7.8, 9.0, 10.0, 11.0, 12.0, 13.0, 17.6, 20.5, 21.5, 22.5, 23.4, 24.5, 25.5])
    alt = altitude(c, t)
    idx = np.round(t * SR).astype(int).clip(0, N - 1)
    print("(a) the camera's height and the air: the band's centre (Hz) and level (0-1, the camera's speed)")
    print("    " + "  ".join(f"{tt:.1f}s:{a:.2f}/{parts['air_fc'][i]:.0f}Hz/{parts['air_lvl'][i]:.2f}"
                             for tt, a, i in zip(t, alt, idx)))
    print("(b) the labels (time, setar note, daf level dB at the counter's value)")
    print("    " + "  ".join(f"{tl:.2f}:{nt}/{lv:.0f}dB" for tl, nt, lv in parts["strokes"]))
    print(f"(c) the mode: Homayoun on D, every note checked; the drone's partials (Hz, periodic over {DUR:.0f} s): "
          + ", ".join(f"{round((hz(nm) + off) * DUR) / DUR:.4f}" for nm, off, *_ in DRONE))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", choices=("music", "voice"), default=None, help="one WAV only (default: both)")
    ap.add_argument("--narration", action="store_true", help="the narration only: synthesize, fit table, manifest")
    args = ap.parse_args()
    if args.narration:
        rows = layout()
        write_manifest(rows)
        fit_table(rows)
        print("saved", NARR_DIR / "manifest.json")
        return
    c = clock()
    log: list = []
    track_m, track_v, parts = render(c, log, voice=args.only != "music")
    results = {}
    if args.only != "voice":
        p = write_wav(SOCIAL / f"{BASE}_music.wav", track_m)
        print("saved", p)
        results["music"] = check_mix("music", _read_wav(p), p, log, parts["stem"], parts, voice=False)
    if track_v is not None:
        p = write_wav(SOCIAL / f"{BASE}_voice.wav", track_v)
        print("saved", p)
        print("saved", NARR_DIR / "manifest.json")
        x = _read_wav(p)
        results["voice"] = check_mix("voice", x, p, log, parts["total"], parts, voice=True)
        check_voice(x, parts)
        print()
        fit_table(parts["rows"])
    check_design(parts)
    print("\nsummary")
    for k, r in results.items():
        print(f"    {k:<6} {r['lufs']:+.2f} LUFS {r['tp']:+.2f} dBTP (kit); {r['f_lufs']:+.2f} LUFS {r['f_tp']:+.2f} "
              f"dBTP (ffmpeg); AAC {r['a_tp']:+.2f} dBTP; seam {r['seam'][0.5][1] - r['seam'][0.5][0]:+.1f} dB; "
              f"longest quiet {r['quiet']:.2f} s")
    print("all checks pass")


if __name__ == "__main__":
    main()
