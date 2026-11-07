"""The score of the El Niño reel (elnino26_fa, 30 s): «النینوی بسیار قوی آمده؛ یعنی طوفانِ نوح؟»
An original track in Mahur, built from the Persian sound kit (onebit_persian) and timed to the film's own clock
(data/elnino26/timeline.json: the landing, the turn, the beats and the two rows of drops with their wet/dry flags;
the brief's numbers are the fallback). Everything in the music is synthesized here: no samples. The one voice is the
narration: eight Persian sentences, synthesized offline (the fa_IR ganji medium voice) and placed on the film's
clock; the music is ducked under them (see NARRATION). The machinery (the cache, the manifest, the ducking, the
master and the checks) is the subsidence reel's (src/onebit_score_subsidence.py).

The mode is Mahur on F (F, G, A, Bb, C, D, E; the kit's set, in 12-tone pitches): the dastgah nearest to the major
scale, so the minor turn (the strong El Niños, on D minor, the relative minor) and the open chords of the winters
(no third) read as departures, and the verdict's F major as a resolution. Segah, Homayoun and Dashti are left to the
sister reels; the Karaj reel's Mahur is on C. Every pitch in the score is checked to lie in the mode.

The data in the music. The ONI counter (smoothstep from the count to the landing, shown to one decimal, as in
src/onebit_elnino26.py) ticks a daf tak each time its shown value changes (at v = 0.05, 0.15, ... 2.45 °C: 25 ticks,
sparse at the ends and quick in the middle, as an odometer), at a level that rises with it (-18 dB to -4 dB), and a
setar climbs the mode as it shows 0.5, 1.0, 1.5 and 2.0 °C (Bb3 C4 D4 E4), the leading tone resolving to the
landing's F. The globe's turn (smoothstep, Pacific to Iran) drives an air layer at its angular speed
and opens or closes the drone's upper partials (bright over the warm Pacific, dark over Iran). The drops: one drop
per El Niño season, in the timeline's order (chronological), 0.06 s apart, each sounding DROP_LAG (0.05 s) into its
0.2 s fade-in (the film's drops). A wetter season is a santur note with a
droplet plip, and each wetter season climbs one step of the mode from F3; a drier season is a muted low setar (C3)
and the climb waits. The 21 wet autumns of 26 climb three octaves and arrive on F6, the tonic; the 11 wet winters
of 22 climb half as far and stop on C5, the open fifth.

    0.00 s         the hook (the end state): a santur strike F2 F3 C4 and a tombak over the drone (F1 F2 C3 F3
                   with a slow 0.5 Hz beating; exactly periodic over 30 s, so it runs through the loop); 0.55 s a
                   soft setar A4 (the warm third: the glowing Pacific)
    1.00-5.75 s    the count: the daf ticks (0.1 °C each), the setar steps (0.5 °C each), a pad F3 C4 F4 swelling
                   with the counter, a riser from 4.4 s; everything stops at 5.75 s
    5.75-6.00 s    the hush: only the drone (14 dB down) and a breath of the room
    6.00 s         the ONI lands (the accent): an impact on F1, a tombak, a daf bam and tak, a santur chord
                   F3 A3 C4 F4; the pad on F A C, a heartbeat (7.0, 8.0 s) and a setar A4 G4
    8.50-12.50 s   the turn (a travelling motion): I vi IV V (F, Dm, Bb, C) a chord per quarter of the turn over a
                   walking bass F2 D2 Bb1 C2; a santur ostinato in eighths and a tombak tom-bak pulse whose level
                   follows the globe's speed; the air rushes with it
    12.50 s        the autumns: a daf bam, a low santur F2 F3, the pad on F A C F; the 26 drops (21 wet) climb
    16.00 s        the strong El Niños (4 of 6): the minor turn, a tombak and a santur D3 F3 A3, the pad on D minor
                   then G minor; the kamancheh descends A4 G4 F4 E4 D4 over a slow tombak pulse
    19.50 s        the winters: an open santur F2 C3, the pads without a third (F C G, then D A E, then C F G and
                   C E G into the verdict); the 22 drops (11 wet) climb half as far; a setar G4 A4 G4 E4
    23.00 s        the verdict (the resolution): a soft impact, a tombak, a daf, the full santur chord F2 F3 A3 C4
                   F4 A4, the pad on F major (the third arrives at last); the setar's cadence C5 A4 G4 F4
    26.50 s        the question: a daf, a santur Bb2 F3, the setar C5 A4 G4, stopping on the open G4; the pad Bb
                   then C (a half cadence) as the globe turns back; the hook's strike, reversed, swells into 30.0 s,
                   where the loop lands on the strike (the F answers the C)

The loop: the music is rendered with 3 s of tail and the tail is added back onto the start (the reverb and the last
notes ring into the first bar, as they do on Instagram's loop); the drone is exactly periodic and the globe is at
rest at the seam, so the last bar flows into the first. A 5 ms fade in and a 10 ms fade out keep the file's edges
clean on the first play. The globe's way back (from the question + BACK_AFTER, 26.8 s, to 30 s, unless the timeline
has "back") follows src/elnino26_3d.py's camera; it moves the air and the drone's colour.

Narration (eight sentences, each with a target window on the film's clock; the TTS input spells the numbers as
words, the display text stays for the subtitles). Every sentence is synthesized at LENGTH (0.85); FALLBACK (a second
synthesis at LENGTH_FLOOR 0.80 for a sentence that overruns) is off: an overrun is reported (the fit table, the
manifest's over_at_085), not sped up. A sentence starts at its window's start; one longer than its window starts
early by its overrun (at most SHIFT, 0.4 s, and at most BEAT_LEAD, 1 s, before its beat), so it still ends in its
window; one that the speech before runs into starts GAP after it (MIN_GAP, 0.03 s, if GAP would push it past SHIFT).
The music is ducked DUCK_ATTACK ahead of each sentence, only ACCENT_LEAD (0.06 s) ahead of a sentence that starts on
its beat (the winters, the verdict, the question), so the accent still hits. The duck is DUCK_DB deep unless a
sentence has its own duck_db. The run prints and the manifest records each sentence's speech on and off (by energy,
1% of the peak), its window, its shift and the overrun. Segments are cached in data/elnino26/narration/ as <hash>.wav, the hash of (voice, length scale,
duration noise, TTS text): a changed sentence is the only one synthesized again; stale files are removed.

Mix: -14 LUFS integrated, true peak -1.5 dBTP in the WAV (so an AAC encode stays at -1 dBTP or below; the check
encodes one in a temporary directory). The top octave (above 12 kHz) is cut, the strings and drums are low-passed
warm, the bass below 120 Hz is mono. 48 kHz, 16 bit, exactly 30.000 s.

    python -I src/onebit_score_elnino26.py               both WAVs (elnino26_fa_music.wav, elnino26_fa_voice.wav)
    python -I src/onebit_score_elnino26.py --only music  the music WAV only
    python -I src/onebit_score_elnino26.py --narration   the narration only: synthesize what changed, print the fit
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
TIMELINE = ROOT / "data" / "elnino26" / "timeline.json"
BASE = "elnino26_fa"
MODE = "mahur"                                  # F, G, A, Bb, C, D, E (the kit's Mahur set on F)
TONIC = kit.note_hz("F3")                       # step 0 of the strings
LETTERS = ("F", "G", "A", "Bb", "C", "D", "E")  # the mode's steps from the tonic, for the names of the drops' notes
DUR = 30.0
N = int(round(DUR * SR))                        # 1,440,000 samples: exactly 30.000 s
TAIL = 3.0                                      # s rendered past the end, then wrapped onto the start (the loop)
AIR = 12000.0                                   # Hz: above this the mix has no content
BASS = 120.0                                    # Hz: below this the two channels are one
MAX_OFFSET = 0.030                              # s: a hit may sit at most this far from its cue
LUFS, TP = -14.0, -1.5                          # -1.5 dBTP in the WAV: an AAC encode stays at -1 or below
FADE_IN, FADE_OUT = 0.005, 0.010                # s: the file's edges (the loop's seam is continuous inside them)
SEAM_DB = 3.0                                   # dB: the largest level step allowed across the loop point
QUIET_DB, QUIET_MAX = -45.0, 1.0                # dBFS over 50 ms, s: no quiet run in the music longer than this
SEED = 83

# the film's clock: the brief's numbers; timeline.json overrides them (and gives the drops)
CLOCK = dict(duration=30.0, fps=30, count=1.0, land=6.0, turn=[8.5, 12.5], autumn_at=12.5, strong_at=16.0,
             winter_at=19.5, verdict_at=23.0, question_at=26.5, oni_shown=2.5)
BACK_AFTER = 0.3                                # s: the globe turns back from the question + this to the loop point
BRIEF = dict(autumn=(26, 21), winter=(22, 11))  # (drops, wet): the brief's counts, checked against the timeline
DROP_DT = 0.06                                  # s between drops (the film's), unless the timeline has drop times
DROP_LAG = 0.05                                 # s: a drop sounds this far into its 0.2 s fade-in (16% opaque)
HUSH = 0.25                                     # s of hush before the landing (5.75-6.0 s)
REV_S, REV_GAIN = 1.2, 1.70                     # the reversed strike into the loop point: its length (s) and gain
TICK = 0.1                                      # °C: a daf tak each time the counter passes a multiple of this
TICK_DB = (-18.0, -4.0)                         # the ticks' level at the counter's 0 and its final value ...
TICK_SHAPE = 1.5                                # ... as counter^1.5
STEP_NOTES = ((0.5, "Bb3"), (1.0, "C4"), (1.5, "D4"), (2.0, "E4"))   # the setar's climb: one step per 0.5 °C
BACK_AIR = 0.6                                  # the air of the way back, against the turn's
RISER_AT = 4.4                                  # s: the riser into the hush

# the turn: a chord per quarter (I vi IV V) and its santur ostinato in eighths
TURN_CHORDS = ((("F3", "A3", "C4"), "F2", ("F4", "C5", "A4", "C5")),
               (("D3", "F3", "A3"), "D2", ("D4", "A4", "F4", "A4")),
               (("Bb2", "D3", "F3"), "Bb1", ("Bb3", "F4", "D4", "F4")),
               (("C3", "E3", "G3"), "C2", ("C4", "G4", "E4", "G4")))
HOLD_SETAR = (("A4", 6.75), ("G4", 7.30))       # after the landing
HEART = (7.0, 8.0)                              # the hot Pacific's slow pulse
KAM_PHRASE = (("A4", 16.30, 0.85), ("G4", 17.15, 0.55), ("F4", 17.70, 0.55), ("E4", 18.25, 0.45),
              ("D4", 18.70, 0.95))              # the minor turn's descent
STRONG_PULSE = (16.75, 17.50, 18.25, 19.00)
WINTER_SETAR = (("G4", 21.40), ("A4", 21.80), ("G4", 22.20), ("E4", 22.60))   # E4: the leading tone into the verdict
VERDICT_SETAR = (("C5", 23.90), ("A4", 24.40), ("G4", 24.90), ("F4", 25.40))
VERDICT_HEART = (24.0, 25.0, 26.0)
QUESTION_NOTES = ("C5", "A4", "G4")             # 0.6 s apart from the question, ending open on G4
DRY_NOTE = "C3"                                 # a drier season: a muted low setar
# (notes, start, end, sub note, pad gain): the harmony from the landing on ("turn1".."turn3": the turn's quarters)
PADS = ((("F3", "A3", "C4"), "land", "turn0", "F1", 0.10),
        (TURN_CHORDS[0][0], "turn0", "turn1", TURN_CHORDS[0][1], 0.10),
        (TURN_CHORDS[1][0], "turn1", "turn2", TURN_CHORDS[1][1], 0.11),
        (TURN_CHORDS[2][0], "turn2", "turn3", TURN_CHORDS[2][1], 0.12),
        (TURN_CHORDS[3][0], "turn3", "autumn", TURN_CHORDS[3][1], 0.13),
        (("F3", "A3", "C4", "F4"), "autumn", "strong", "F2", 0.10),
        (("D3", "F3", "A3"), "strong", 17.75, "D2", 0.11),
        (("G2", "Bb2", "D3"), 17.75, "winter", "G1", 0.12),
        (("F3", "C4", "G4"), "winter", 21.25, "F2", 0.10),
        (("D3", "A3", "E4"), 21.25, 22.25, "D2", 0.10),
        (("C3", "F3", "G3"), 22.25, 22.70, "C2", 0.11),
        (("C3", "E3", "G3"), 22.70, "verdict", "C2", 0.12),
        (("F3", "A3", "C4"), "verdict", "question", "F1", 0.11),
        (("Bb2", "D3", "F3"), "question", 28.0, "Bb1", 0.10),
        (("C3", "G3", "E4"), 28.0, 30.0, "C2", 0.09))
# the drone: (note, Hz offset, amplitude, pan, opens over the Pacific); every frequency is rounded to a multiple of
# 1/30 Hz, so the drone is exactly periodic over the reel and the loop has no seam in it
DRONE = (("F1", 0.0, 0.45, 0.0, False), ("F2", 0.0, 1.0, -0.25, False), ("F2", 0.5, 0.6, 0.25, False),
         ("C3", 0.0, 0.45, 0.2, False), ("F3", 0.0, 0.25, -0.2, False), ("C4", 0.0, 0.16, 0.3, True),
         ("F4", 0.0, 0.10, -0.3, True), ("G4", 0.0, 0.035, 0.35, True))
# the drone's level (dB) over the reel; the first and last values match (the loop)
DRONE_DB = ((0.0, -4.0), (1.0, -4.0), (5.55, 0.0), (5.75, -14.0), (5.98, -14.0), (6.0, -3.0), (8.5, -2.0),
            (12.5, -1.0), (16.0, -2.0), (19.5, -2.0), (23.0, -2.0), (26.5, -3.0), (30.0, -4.0))

# ── narration ───────────────────────────────────────────────────────────────
TTS_ENV_BIN, TTS_ENV_MODEL = "ONEBIT_TTS_BIN", "ONEBIT_TTS_MODEL"   # the offline engine and the voice file, from the
                                                                  # environment (no local paths in the repo)
NARR_DIR = ROOT / "data" / "elnino26" / "narration"              # the rendered segments (the cache) and manifest.json
VOICE = "fa_IR-ganji-medium"
LENGTH = 0.85                                   # the voice's length scale (faster than its natural 1.0)
LENGTH_FLOOR = 0.80                             # the fastest allowed, for a sentence that overruns its window at LENGTH
FALLBACK = False                                # off: every sentence at LENGTH; an overrun is reported, not sped up
NOISE_W = 0.0                                   # no duration noise: a fresh synthesis has the same timing
PAD_S = 0.03                                    # s of silence kept before and after each speech
ON_OFF = 0.01                                   # speech on and off: the first and last sample above 1% of the peak
DUCK_DB = 9.5                                   # dB: the music under the speech
DUCK_ATTACK = 0.15                              # s: the music goes down over this time, ahead of the speech
DUCK_RELEASE = 0.40                             # s: the music comes back over this time after it
RATIO_TARGET = 14.0                             # dB: the voice over the ducked music, over all the speech, pre-master
RATIO_MIN = 10.0                                # dB: the least segment, measured after the master
ACCENT_LEAD = 0.06                              # s: a sentence that starts on a musical accent: a short duck ahead of
                                                # it, so the accent still hits but the voice stays RATIO_MIN over it
GAP = 0.12                                      # s: the pause after a sentence that ran past the next start ...
MIN_GAP = 0.03                                  # ... or this, the least, when GAP would push it past SHIFT
SHIFT = 0.40                                    # s: a sentence may start up to this much off its window's start
BEAT_LEAD = 1.0                                 # s: and at most this much before its beat (the film's picture)
STEP = 0.01                                     # s: a pushed start is rounded up to this grid
END_ROOM = 0.30                                 # s: the last speech ends at least this long before the loop point
# window: (start, end) on the clock; the speech starts at the start and must end by the end (the window may shift
# by up to SHIFT, 7 Nov). beat: the film's beat the sentence speaks to (a start on it gets the short ACCENT_LEAD
# duck). text: the display (the subtitles); say: what the voice reads (numbers spelled as words), when it differs
NARRATION = (
    dict(name="s1", window=(0.15, 2.9), text="النینو برگشته؛ و این بار خیلی قوی."),
    dict(name="s2", window=(3.1, 8.2), text="آبِ مرکزِ اقیانوسِ آرام، دو و نیم درجه گرم‌تر از معمول شد."),
    dict(name="s3", window=(8.5, 11.2), text="برای بارانِ ایران یعنی چه؟"),
    dict(name="s4", window=(11.5, 16.2), beat=12.5,
         text="۲۱ پاییز از ۲۶ پاییزِ النینو، پرباران‌تر از معمول بود.",
         say="بیست و یک پاییز از بیست و شش پاییزِ النینو، پرباران‌تر از معمول بود."),
    dict(name="s5", window=(16.3, 19.4), beat=16.0, text="ولی النینوی قوی‌تر، بارانِ بیشتر نیاورد."),
    dict(name="s6", window=(19.5, 22.9), beat=19.5, text="زمستان‌ها نیمی پرباران‌تر بود، نیمی کم‌باران‌تر."),
    dict(name="s7", window=(23.0, 26.4), beat=23.0, text="شانسِ پاییزِ پرباران بالا می‌رود؛ نه طوفانِ نوح."),
    dict(name="s8", window=(26.5, 29.5), beat=26.5, text="پاییزِ امسال در شهرِ شما چطور بوده؟"),
)


def freq_of(step: int) -> float:
    return kit.degree(MODE, step, 0, tonic_hz=TONIC)


def step_name(step: int) -> str:
    """The note name of a step above F3: F3 G3 A3 Bb3 C4 D4 E4 F4 ..."""
    k = step % 7
    return f"{LETTERS[k]}{3 + step // 7 + (1 if k >= 4 else 0)}"


def hz(name: str) -> float:
    """A note of the score, checked to lie in Mahur on F."""
    f = kit.note_hz(name)
    cents = round(1200 * math.log2(f / TONIC)) % 1200
    assert cents in kit.mode_cents(MODE), (name, cents)
    return f


# ── the film's clock ────────────────────────────────────────────────────────

def clock() -> dict:
    """The film's times: the brief's, overridden by data/elnino26/timeline.json where it has them (a difference is
    printed); the two seasons' drops (years, wet flags, times) from the timeline."""
    c = dict(CLOCK)
    tl = json.loads(TIMELINE.read_text(encoding="utf-8"))
    for k in CLOCK:
        if k in tl and tl[k] != CLOCK[k]:
            print(f"note: the timeline's {k} = {tl[k]} (the brief: {CLOCK[k]}); the score follows the timeline")
        c[k] = tl.get(k, CLOCK[k])
    assert c["duration"] == DUR and c["fps"] == 30, c
    drops = {}
    for season in ("autumn", "winter"):
        d = tl[season]
        years = [int(y) for y in d["years"]]
        wet = [bool(d["wet"][str(y)]) for y in years]
        assert len(years) == d["n"] and sum(wet) == d["wetter"], (season, len(years), sum(wet))
        if (len(years), sum(wet)) != BRIEF[season]:
            print(f"note: the timeline's {season} has {sum(wet)} wet of {len(years)} (the brief: {BRIEF[season]})")
        times = tl.get(f"{season}_drop_times") or [round(c[f"{season}_at"] + k * DROP_DT + DROP_LAG, 4)
                                                   for k in range(len(years))]
        assert len(times) == len(years), (season, len(times))
        drops[season] = list(zip(years, wet, [float(t) for t in times]))
    c["drops"] = drops
    c["strong"] = (tl["autumn"].get("strong_wetter"), len(tl["autumn"].get("strong", [])))
    c["back"] = [float(v) for v in tl.get("back") or (c["question_at"] + BACK_AFTER, DUR)]
    c["cut"] = c["land"] - HUSH
    a, b = c["turn"]
    c["named"] = dict(land=c["land"], autumn=c["autumn_at"], strong=c["strong_at"], winter=c["winter_at"],
                      verdict=c["verdict_at"], question=c["question_at"],
                      **{f"turn{k}": a + k * (b - a) / 4 for k in range(4)})
    return c


def at(c: dict, v) -> float:
    return float(c["named"][v]) if isinstance(v, str) else float(v)


def ease(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def counter(c: dict, t):
    """The counter's value over its final value at t: smoothstep from the count to the landing (as in the film)."""
    return ease((np.asarray(t, float) - c["count"]) / (c["land"] - c["count"]))


def crossings(c: dict, values) -> list:
    """The times at which the counter (in °C, landing on oni_shown) passes each value."""
    tg = np.linspace(c["count"], c["land"], 20001)
    vg = counter(c, tg) * c["oni_shown"]
    return [float(np.interp(v, vg, tg)) for v in values]


def facing(c: dict, t) -> np.ndarray:
    """The globe's turn, 0 (the Pacific) to 1 (Iran), per time: smoothstep over the turn, 1 over Iran, smoothstep
    back over the way back (at rest at the seam)."""
    t = np.asarray(t, float) % DUR
    a, b = c["turn"]
    r0, r1 = c["back"]
    return np.where(t < r0, ease((t - a) / (b - a)), 1.0 - ease((t - r0) / (r1 - r0)))


# ── sounds ──────────────────────────────────────────────────────────────────

def santur_note(name: str, peak: float, dur: float = 3.0, t60: float = 2.6, bright: float = 0.5):
    x = np.asarray(kit.santur(hz(name), dur=dur, vel=1.0, t60=t60, bright=bright), float)
    return x * (peak / np.abs(x).max())


def setar_note(name: str, peak: float, t60: float = 1.7, bright: float = 0.3, buzz: float = 0.05, dur: float = 1.8):
    x = np.asarray(kit.setar(hz(name), dur=dur, vel=1.0, t60=t60, bright=bright, buzz=buzz), float)
    return x * (peak / np.abs(x).max())


def plip(f0: float, peak: float) -> np.ndarray:
    """A water drop, mono: a sine that rises by 0.6 of its pitch within about 20 ms (the bubble's resonance) and
    dies in about 30 ms, with a 1 ms attack."""
    n = round(0.15 * SR)
    t = np.arange(n) / SR
    f = f0 * (1 + 0.6 * (1 - np.exp(-t / 0.012)))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * (1 - np.exp(-t / 0.001)) * np.exp(-t / 0.03)
    return x * (peak / np.abs(x).max())


def drone(c: dict) -> np.ndarray:
    """The drone, stereo, N samples: the DRONE partials (each exactly periodic over 30 s), the upper ones open over
    the warm Pacific and closed over Iran, at the DRONE_DB level curve."""
    t = np.arange(N) / SR
    glow = 1.0 - facing(c, t)
    lvl = 10 ** (np.interp(t, [p[0] for p in DRONE_DB], [p[1] for p in DRONE_DB]) / 20)
    out = np.zeros((N, 2))
    rng = np.random.default_rng(SEED + 1)
    for name, off, amp, pan, opens in DRONE:
        f = round((hz(name) + off) * DUR) / DUR
        x = amp * np.sin(2 * np.pi * f * t + rng.uniform(0, 2 * np.pi))
        if opens:
            x = x * (0.2 + 0.8 * glow)
        gl, gr = kit.pan_gains(pan)
        out[:, 0] += gl * x
        out[:, 1] += gr * x
    return out * lvl[:, None] / np.abs(out).max()


def air(c: dict, rng) -> tuple:
    """The globe's air, stereo, N samples, peak 1: noise in a band whose centre and level follow the globe's angular
    speed (|d facing / dt|, smoothed over 0.2 s; 180 Hz at rest to 2.4 kHz at full speed, log); the way back at
    BACK_AIR of the turn's level. Returns (air, centre Hz per sample, level per sample)."""
    t = np.arange(N) / SR
    speed = np.abs(np.gradient(facing(c, t), 1.0 / SR))
    speed = uniform_filter1d(speed, round(0.2 * SR), mode="wrap")
    s = np.clip(speed / speed.max(), 0.0, 1.0)     # the moving average can dip a hair below 0 at rest
    lvl = s ** 0.8 * np.where(t >= c["back"][0], BACK_AIR, 1.0)
    fc = 180.0 * (2400.0 / 180.0) ** s
    centres = np.geomspace(120.0, 3600.0, 12)
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

SENDS = {"hook": 0.35, "count": 0.25, "pluck": 0.35, "santur": 0.35, "setar": 0.35, "kam": 0.35, "perc": 0.15,
         "drops": 0.40, "ost": 0.25}
BUSES = ("hook", "count", "pluck", "santur", "setar", "kam", "perc", "fx", "pad", "sub", "drone", "air", "rev",
         "drops", "ost", "send")


def compose(c: dict, rec: list) -> tuple:
    """Lay the score on its buses (each N + TAIL long). rec receives one entry per checked event: (label, cue time,
    hit time, the sounds placed for it as (sound, gain, pan)). Returns (buses, extra: the air's centre and level, the
    counter's ticks and steps, the drops)."""
    kit.reseed(SEED)
    rng = np.random.default_rng(SEED)
    bus = {k: kit.new_track(DUR, TAIL) for k in BUSES}
    land, cut = c["land"], c["cut"]
    ticks, drops_log = [], []

    def put(name, sound, t, gain, pan):
        kit.place(bus[name], sound, t, gain, pan)
        if name in SENDS:
            kit.place(bus["send"], sound, t, gain * SENDS[name], pan)

    def event(label, t, items):
        for name, sound, gain, pan in items:
            put(name, sound, t, gain, pan)
        rec.append((label, t, t, [(s, g, p) for _, s, g, p in items]))

    def tick_gain(t):
        u = float(counter(c, t))
        return 10 ** ((TICK_DB[0] + (TICK_DB[1] - TICK_DB[0]) * u ** TICK_SHAPE) / 20)

    # the drone and the air: the whole reel
    bus["drone"][:N] += 0.10 * drone(c)
    a_x, a_fc, a_lvl = air(c, rng)
    bus["air"][:N] += 0.055 * a_x

    # the hook (the end state): a santur strike over the drone, a soft tombak; the warm third at 0.55 s
    strike = santur_note("F3", 0.13, dur=4.0, t60=3.2) + santur_note("C4", 0.08, dur=4.0, t60=3.0) \
        + santur_note("F2", 0.08, dur=4.0, t60=3.4)
    event("0.00 hook: santur F2 F3 C4, tombak", 0.0,
          [("hook", strike, 1.0, 0.0), ("perc", kit.tombak("tom", pitch=hz("F2")), 0.12, 0.0)])
    event("0.55 hook: setar A4 (the warm third)", 0.55, [("hook", setar_note("A4", 0.16), 1.0, 0.2)])
    event(f"{c['count']:.2f} the count begins: tombak, santur F4", c["count"],
          [("count", kit.tombak("tom", pitch=hz("F2")), 0.14, 0.0),
           ("count", santur_note("F4", 0.09, dur=2.5, t60=2.0), 1.0, -0.1)])

    # the counter: a daf tak per 0.1 °C, a setar step per 0.5 °C (with a daf bam)
    tak = kit.daf("tak", pitch=hz("F4"))
    zang = kit.daf("zang")
    bam = kit.daf("bam", pitch=hz("F2"))
    n_ticks = int(round(c["oni_shown"] / TICK))
    vals = [round(TICK * k, 3) for k in range(1, n_ticks + 1)]          # the shown values, 0.1 ... 2.5
    steps = dict(STEP_NOTES)
    for v, t in zip(vals, crossings(c, [v - TICK / 2 for v in vals])):  # shown when the value rounds up to it
        if t >= cut - 0.02:
            continue
        t = round(t, 4)
        g = tick_gain(t)
        k = len(ticks)
        if v in steps:
            pan = 0.25 if k % 2 else -0.25
            event(f"{t:.2f} the counter at {v:.1f} °C: setar {steps[v]}, daf bam", t,
                  [("count", setar_note(steps[v], 0.30), 1.0, pan), ("count", bam, 0.5 * g, 0.0)])
            ticks.append((t, v, steps[v], 20 * math.log10(g)))
        else:
            put("count", tak, t, 0.34 * g, 0.3 if k % 2 else -0.3)
            put("count", zang, t, 0.05 * g, -0.3 if k % 2 else 0.3)
            ticks.append((t, v, "tak", 20 * math.log10(g)))
    rz = kit.riser(dur=cut - RISER_AT + 0.05, vel=1.0, f0=hz("F3"), f1=hz("F5"))
    put("count", rz, RISER_AT, 0.07, 0.0)
    # under the count: a pad on F C F (open: the heat building) that swells with the counter
    cp = kit.pad([hz("F3"), hz("C4"), hz("F4")], dur=cut - c["count"] + 0.05, vel=1.0, width=0.8, detune=5.0,
                 cutoff=900.0, attack=0.5, release=0.05)
    cp = cp * (0.35 + 0.65 * counter(c, c["count"] + np.arange(len(cp)) / SR))[:, None]
    kit.place(bus["count"], cp, c["count"], 0.09)
    kit.place(bus["send"], cp, c["count"], 0.03)
    # the hush: nothing of the count sounds after the cut (a 20 ms fade); the room keeps only what was sent before
    ci = round(cut * SR)
    fade = np.clip((ci + round(0.02 * SR) - np.arange(len(bus["count"]))) / (0.02 * SR), 0, 1)[:, None]
    for name in ("count", "send"):
        bus[name][ci:] *= fade[ci:]

    # the landing: an impact on F1, a tombak, a daf bam and tak, a santur chord F3 A3 C4 F4
    chord = santur_note("F3", 0.13, 5.0, 3.6) + santur_note("A3", 0.10, 5.0, 3.6) \
        + santur_note("C4", 0.11, 5.0, 3.6) + santur_note("F4", 0.06, 5.0, 3.2)
    event(f"{land:.2f} the ONI lands: impact, tombak, daf, santur chord", land,
          [("fx", kit.impact(2.4, vel=1.0, pitch=hz("F1")), 0.26, 0.0),
           ("fx", kit.tombak("tom", pitch=hz("F2")), 0.20, 0.0),
           ("fx", kit.daf("bam", pitch=hz("F2")), 0.18, 0.0),
           ("fx", kit.daf("tak", pitch=hz("F4")), 0.20, 0.0),
           ("santur", chord, 1.0, 0.0)])
    kit.place(bus["send"], kit.daf("tak", pitch=hz("F4")), land, 0.2)
    for t in HEART:
        event(f"{t:.2f} heartbeat: daf bam", t, [("perc", kit.daf("bam", pitch=hz("F2")), 0.12, 0.0)])
    for note, t in HOLD_SETAR:
        event(f"{t:.2f} the hot Pacific: setar {note}", t, [("setar", setar_note(note, 0.22), 1.0, -0.15)])

    # the harmony: pads with a quiet sub under each
    for k, (notes, a0, b0, sub_note, pg) in enumerate(PADS):
        a0, b0 = at(c, a0), at(c, b0)
        last = k == len(PADS) - 1
        dur = (b0 - a0) + (0.0 if last else 0.5)
        attack = 0.6 if a0 == land else 0.35
        p = kit.pad([hz(nm) for nm in notes], dur=dur, vel=1.0, width=0.8, detune=5.0, cutoff=1000.0,
                    attack=attack, release=1.0 if last else 0.5)
        kit.place(bus["pad"], p, a0, pg)
        kit.place(bus["send"], p, a0, 0.35 * pg)
        s_dur = (b0 - a0) + (0.0 if last else 0.03)
        sb = kit.sub(hz(sub_note), s_dur, vel=1.0)
        if last:
            sb = sb * np.clip((b0 - 0.4 - (a0 + np.arange(len(sb)) / SR)) / 1.6, 0, 1)
        kit.place(bus["sub"], sb * np.minimum(1.0, np.arange(len(sb)) / (0.3 * SR)), a0, 0.06)

    # the turn: a santur ostinato in eighths and a tombak tom-bak pulse, both at the globe's speed
    a, b = c["turn"]
    q = (b - a) / 4
    spd = lambda t: float(4 * (t - a) / (b - a) * (1 - (t - a) / (b - a)))  # noqa: E731  (0 at rest, 1 mid-turn)
    # the figure twice per chord: eight eighths per quarter of the turn
    for k, (_, _, figure) in enumerate(TURN_CHORDS):
        for j in range(8):
            t = round(a + k * q + j * q / 8, 4)
            note = figure[j % 4]
            pk = 0.05 + 0.06 * spd(t)
            event(f"{t:.2f} the turn: santur {note}", t,
                  [("ost", santur_note(note, pk, dur=1.6, t60=1.4, bright=0.5), 1.0, -0.2 if j % 2 else 0.2)])
    for j in range(8):
        t = round(a + j * q / 2, 4)
        put("perc", kit.tombak("tom", pitch=hz("F2")), t, 0.07 + 0.06 * spd(t), 0.0)
        put("perc", kit.tombak("bak", pitch=hz("C5")), t + q / 4, 0.03 + 0.04 * spd(t + q / 4), 0.15)

    # the drops: a wet season a santur note one step up the mode with a plip; a dry one a muted low setar
    def reveal(season: str, t0: float):
        climb = 0
        for k, (year, wet, t) in enumerate(c["drops"][season]):
            pan = 0.3 * math.sin(1.7 * k)
            if wet:
                climb += 1
                note = step_name(climb)
                x = santur_note(note, 0.085, dur=1.6, t60=1.1, bright=0.45)
                event(f"{t:.2f} {season} {year}: wet, santur {note}", t,
                      [("drops", x, 1.0, pan), ("drops", plip(950.0 + 40.0 * (k % 7), 0.03), 1.0, -pan)])
                drops_log.append((season, year, t, "wet", note))
            else:
                x = setar_note(DRY_NOTE, 0.12, t60=0.15, bright=0.0, buzz=0.0, dur=0.6)
                event(f"{t:.2f} {season} {year}: dry, muted setar {DRY_NOTE}", t, [("drops", x, 1.0, pan)])
                drops_log.append((season, year, t, "dry", DRY_NOTE))
        return climb

    t0 = c["autumn_at"]
    event(f"{t0:.2f} the autumns: daf bam, santur F2 F3", t0,
          [("perc", kit.daf("bam", pitch=hz("F2")), 0.14, 0.0),
           ("santur", santur_note("F2", 0.10, 4.0, 3.2) + santur_note("F3", 0.08, 4.0, 3.0), 1.0, 0.0)])
    top_autumn = reveal("autumn", t0)

    # the strong El Niños: the minor turn
    t0 = c["strong_at"]
    event(f"{t0:.2f} the strong ones: tombak D2, daf, santur D3 F3 A3", t0,
          [("fx", kit.tombak("tom", pitch=hz("D2")), 0.22, 0.0),
           ("fx", kit.daf("bam", pitch=hz("D2")), 0.12, 0.0),
           ("santur", santur_note("D3", 0.12, 4.0, 3.2) + santur_note("F3", 0.08, 4.0, 3.0)
            + santur_note("A3", 0.08, 4.0, 3.0), 1.0, 0.0)])
    for t in STRONG_PULSE:
        event(f"{t:.2f} the minor turn's pulse: tombak", t, [("perc", kit.tombak("tom", pitch=hz("D2")), 0.10, 0.0)])
    for note, t, dur in KAM_PHRASE:
        x = kit.kamancheh(hz(note), dur=dur, vel=1.0, vib_hz=5.0, vib_cents=16.0, bow=0.10)
        event(f"{t:.2f} the minor turn: kamancheh {note}", t, [("kam", x, 0.28, 0.1)])

    # the winters: open chords, the drops half-half
    t0 = c["winter_at"]
    event(f"{t0:.2f} the winters: daf bam, santur F2 C3 (open)", t0,
          [("perc", kit.daf("bam", pitch=hz("F2")), 0.13, 0.0),
           ("santur", santur_note("F2", 0.10, 4.0, 3.2) + santur_note("C3", 0.08, 4.0, 3.0), 1.0, 0.0)])
    top_winter = reveal("winter", t0)
    for note, t in WINTER_SETAR:
        event(f"{t:.2f} the winters: setar {note}", t, [("setar", setar_note(note, 0.22), 1.0, 0.15)])

    # the verdict: the resolution on F major
    t0 = c["verdict_at"]
    full = santur_note("F2", 0.09, 5.0, 3.6) + santur_note("F3", 0.12, 5.0, 3.6) + santur_note("A3", 0.10, 5.0, 3.6) \
        + santur_note("C4", 0.10, 5.0, 3.4) + santur_note("F4", 0.06, 5.0, 3.2) + santur_note("A4", 0.04, 5.0, 3.0)
    event(f"{t0:.2f} the verdict: impact, tombak, daf, santur F2 F3 A3 C4 F4 A4", t0,
          [("fx", kit.impact(2.0, vel=1.0, pitch=hz("F1")), 0.14, 0.0),
           ("fx", kit.tombak("tom", pitch=hz("F2")), 0.20, 0.0),
           ("fx", kit.daf("bam", pitch=hz("F2")), 0.14, 0.0),
           ("santur", full, 1.0, 0.0)])
    for note, t in VERDICT_SETAR:
        event(f"{t:.2f} the verdict: setar {note}", t,
              [("setar", setar_note(note, 0.24, t60=2.4 if note == "F4" else 1.7), 1.0, -0.15)])
    for t in VERDICT_HEART:
        event(f"{t:.2f} the verdict's pulse: daf bam", t, [("perc", kit.daf("bam", pitch=hz("F2")), 0.10, 0.0)])

    # the question: daf, santur Bb2 F3, the setar C5 A4 G4, ending open on G4
    t0 = c["question_at"]
    event(f"{t0:.2f} the question: daf, santur Bb2 F3, setar {QUESTION_NOTES[0]}", t0,
          [("perc", kit.daf("bam", pitch=hz("Bb1")), 0.13, 0.0),
           ("santur", santur_note("Bb2", 0.12, 4.0, 3.0) + santur_note("F3", 0.08, 4.0, 3.0), 1.0, 0.0),
           ("pluck", setar_note(QUESTION_NOTES[0], 0.24), 1.0, -0.25)])
    for k, note in enumerate(QUESTION_NOTES[1:], start=1):
        t = round(t0 + 0.6 * k, 4)
        t60 = 2.6 if k == len(QUESTION_NOTES) - 1 else 1.7
        event(f"{t:.2f} the question: setar {note}", t,
              [("pluck", setar_note(note, 0.24, t60=t60), 1.0, 0.25 if k % 2 else -0.25)])
    # the hook's own strike, reversed, swells into the loop point (the seam is its mirror)
    rev = kit.reverse(strike[:round(REV_S * SR)]) * REV_GAIN
    kit.place(bus["rev"], rev, DUR - len(rev) / SR, 1.0)

    # warm filters: the strings and the drums low-passed
    for name, fc, order in (("santur", 6000.0, 2), ("hook", 6000.0, 2), ("rev", 6000.0, 2), ("setar", 4000.0, 2),
                            ("pluck", 4500.0, 2), ("count", 6500.0, 2), ("kam", 3500.0, 4), ("perc", 8000.0, 2),
                            ("fx", 7000.0, 2), ("air", 4000.0, 2), ("drops", 7000.0, 2), ("ost", 6000.0, 2)):
        bus[name] = sosfilt(butter(order, fc, "lowpass", fs=SR, output="sos"), bus[name], axis=0)
    return bus, dict(air_fc=a_fc, air_lvl=a_lvl, ticks=ticks, drops=drops_log,
                     tops=dict(autumn=step_name(top_autumn), winter=step_name(top_winter)))


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
    then the tail past 30 s added back onto the start: N samples."""
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
    """Each sentence at LENGTH (with FALLBACK, at LENGTH_FLOOR if it overruns its window), placed at its window's
    start; one longer than its window starts earlier, within SHIFT and BEAT_LEAD of its beat; one that the previous
    speech runs into starts GAP after it (MIN_GAP if GAP would push it past SHIFT), rounded up to STEP. Rows: the
    placement and the fit (fits: the speech no longer than the window and the start within SHIFT, so the speech
    lies inside the shifted window)."""
    rows, prev_end, keep = [], None, set()
    for seg in NARRATION:
        a, b = seg["window"]
        beat = seg.get("beat")
        say = seg.get("say", seg["text"])
        assert not re.search(r"[0-9۰-۹٠-٩]", say), (seg["name"], "spell the numbers as words in `say`")
        y, lead, speech, h = synth(say, LENGTH)
        keep.add(h)
        ls, sp_hi, sp_lo = LENGTH, speech, None
        if FALLBACK and speech > (b - a) + 1e-9:
            y, lead, speech, h = synth(say, LENGTH_FLOOR)
            keep.add(h)
            ls, sp_lo = LENGTH_FLOOR, speech
        earliest = max(a - SHIFT, -math.inf if beat is None else beat - BEAT_LEAD, 0.0)
        if prev_end is not None:
            earliest = max(earliest, prev_end + MIN_GAP)
        early = math.floor((b - speech) / STEP + 1e-6) * STEP        # a long sentence starts early, if it may
        start = max(min(a, early), math.ceil(earliest / STEP - 1e-6) * STEP)
        if prev_end is not None and prev_end + MIN_GAP > a:         # the speech before runs into this window: a
            start = max(start, min(prev_end + GAP, max(a + SHIFT, prev_end + MIN_GAP)))   # pause of GAP if the
            start = math.ceil(start / STEP - 1e-6) * STEP                                 # shift allows
        start = round(start, 3)
        end = start + speech
        shift = round(start - a, 3)
        on_beat = beat is not None and abs(start - beat) < 1e-6
        rows.append(dict(name=seg["name"], window=[a, b], beat=beat, start=start, end=round(end, 4),
                         speech=round(speech, 4), lead=round(lead, 4), length_scale=ls, speech_at_085=round(sp_hi, 4),
                         over_at_085=round(sp_hi - (b - a), 3),
                         over_at_080=None if sp_lo is None else round(sp_lo - (b - a), 3),
                         shift=shift, shift_excess=round(max(0.0, abs(shift) - SHIFT), 3),
                         gap_before=None if prev_end is None else round(start - prev_end, 3),
                         over=round(end - b, 3),
                         fits=bool(speech <= (b - a) + 1e-9 and abs(shift) <= SHIFT + 1e-9),
                         hash=h, file=f"{h}.wav",
                         duck_lead=seg.get("duck_lead", ACCENT_LEAD if on_beat else DUCK_ATTACK),
                         duck_db=seg.get("duck_db", DUCK_DB),
                         text=seg["text"], say=say, y=y))
        prev_end = end
    for f in NARR_DIR.glob("*.wav"):                     # the cache keeps only the current sentences' renders
        if re.fullmatch(r"[0-9a-f]{12}", f.stem) and f.stem not in keep:
            f.unlink()
            print(f"removed the stale segment {f.name}")
    return rows


def write_manifest(rows: list) -> None:
    man = [dict(name=r["name"], window=r["window"], beat=r["beat"], start=r["start"], end=r["end"],
                speech=r["speech"], lead=r["lead"], length_scale=r["length_scale"], noise_w_scale=NOISE_W, voice=VOICE,
                file=r["file"], fits=r["fits"], shift=r["shift"], shift_excess=r["shift_excess"],
                gap_before=r["gap_before"], over=r["over"], over_at_085=r["over_at_085"],
                over_at_080=r["over_at_080"], duck_lead=r["duck_lead"], duck_db=r["duck_db"],
                text=r["text"], say=r["say"]) for r in rows]
    NARR_DIR.mkdir(parents=True, exist_ok=True)
    (NARR_DIR / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")


def fit_table(rows: list) -> None:
    print(f"the narration against its windows (s; shift: the start off the window's start, allowed +-{SHIFT}; excess: "
          f"past that; over: the end past the window's end; at 0.85: the speech's length against the window's, "
          f"alone; gap: the pause before it)")
    print(f"    {'':4}{'window':>14}{'speech on-off':>17}{'len':>7}{'ls':>6}{'shift':>7}{'excess':>7}{'over':>7}"
          f"{'at 0.85':>9}{'gap':>6}  fits")
    for r in rows:
        gap = "-" if r["gap_before"] is None else f"{r['gap_before']:.2f}"
        print(f"    {r['name']:<4}{r['window'][0]:>6.2f}-{r['window'][1]:<6.2f}{r['start']:>8.3f}-{r['end']:<8.3f}"
              f"{r['speech']:>7.3f}{r['length_scale']:>6.2f}{r['shift']:>+7.2f}{r['shift_excess']:>7.2f}"
              f"{r['over']:>+7.3f}{r['over_at_085']:>+9.3f}{gap:>6}  {'yes' if r['fits'] else 'NO'}")
    long_ = [f"{r['name']} by {r['over_at_085']:.2f} s (placed {r['start']:.2f}-{r['end']:.2f}, "
             f"{'inside' if r['end'] <= r['window'][1] + 1e-9 else 'past'} the window's end)"
             for r in rows if r["over_at_085"] > 1e-9]
    pushed = [f"{r['name']} by {r['shift_excess']:.2f} s" for r in rows if r["shift_excess"] > 1e-9]
    if long_:
        print(f"    WARNING: longer than the window at {LENGTH}: {', '.join(long_)}")
    if pushed:
        print(f"    WARNING: pushed past the +-{SHIFT} s shift by the speech before: {', '.join(pushed)}")


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

    print(f"(3) the loop seam ({DUR:.1f} s -> 0.0 s)")
    s = seam(x)
    for w in (0.25, 0.5):
        e, b = s[w]
        print(f"    last {w:.2f} s {e:.1f} dBFS, first {w:.2f} s {b:.1f} dBFS: {b - e:+.1f} dB")
    print(f"    the step from the last sample to the first {s['step']:.2e}; the last sample "
          f"{np.abs(x[-1]).max():.2e}, the first {np.abs(x[0]).max():.2e}")
    if voice:                                       # the narration enters at s1's start: the step is the voice's; the
        print(f"    (the voice enters at {parts['spans'][0][1]:.2f} s: the bed under it is checked in (8))")   # bed is
    else:                                                                                              # checked in (8)
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
          f"{sil:.1f} dBFS ({sil - pre:+.1f} dB)" + ("  (the voice speaks here)" if voice else ""))
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
        table.append((name, round(on, 3), round(off, 3), round(float(ratio), 1)))
    print(f"    the least sentence: voice {min(ratios):+.1f} dB over the music (limit {RATIO_MIN:.0f} dB)")
    assert min(ratios) >= RATIO_MIN, ratios
    gaps = [round(spans[k + 1][1] - spans[k][2], 3) for k in range(len(spans) - 1)]
    print(f"    the pauses between sentences (s): {', '.join(f'{g:.2f}' for g in gaps)}; the last speech ends at "
          f"{spans[-1][2]:.2f} s ({DUR - spans[-1][2]:.2f} s before the loop point)")
    assert min(gaps) >= 0.03, gaps
    bed = parts["music"]
    e1, b1 = _db(bed[-round(0.25 * SR):]), _db(bed[:round(0.10 * SR)])
    print(f"    the loop seam under the voice: the ducked music's last 0.25 s {e1:.1f} dB, its first 0.10 s "
          f"(before the duck for s1 takes hold) {b1:.1f} dB: {b1 - e1:+.1f} dB (before the master); "
          f"the voice itself enters at {spans[0][1]:.2f} s")
    assert abs(b1 - e1) < SEAM_DB, (e1, b1)
    return table


def check_design(parts: dict) -> None:
    c = parts["clock"]
    print("\n======== the score against the film ========")
    t = np.array([0.0, 6.0, 8.5, 9.5, 10.5, 11.5, 12.5, 16.0, 19.5, 23.0, 26.5, 27.5, 28.5, 29.5])
    fa = facing(c, t)
    idx = np.round(t * SR).astype(int).clip(0, N - 1)
    print("(a) the globe's turn (0 the Pacific, 1 Iran) and the air: the band's centre (Hz) and level (0-1)")
    print("    " + "  ".join(f"{tt:.1f}s:{a:.2f}/{parts['air_fc'][i]:.0f}Hz/{parts['air_lvl'][i]:.2f}"
                             for tt, a, i in zip(t, fa, idx)))
    print("(b) the counter (time, °C, sound, level dB)")
    print("    " + "  ".join(f"{tt:.2f}:{v:.1f}/{nt}/{lv:.0f}" for tt, v, nt, lv in parts["ticks"]))
    for season in ("autumn", "winter"):
        rows = [d for d in parts["drops"] if d[0] == season]
        wet = sum(d[3] == "wet" for d in rows)
        print(f"(c) the {season} drops: {len(rows)}, {wet} wet, {rows[0][2]:.2f}-{rows[-1][2]:.2f} s; the climb tops "
              f"on {parts['tops'][season]}")
        print("    " + "  ".join(f"{y}:{'W' if kind == 'wet' else 'd'}{nt}" for _, y, _, kind, nt in rows))
    print(f"(d) the strong El Niños (autumn): {c['strong'][0]} wet of {c['strong'][1]} (the minor turn at "
          f"{c['strong_at']:.1f} s)")
    print(f"(e) the mode: Mahur on F, every note checked; the drone's partials (Hz, periodic over {DUR:.0f} s): "
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
