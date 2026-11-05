"""The score of the winter NO2 reel (air_tehran_fa, 24 s): an original track built from the Persian sound kit
(onebit_persian, the Shur set) and timed to the film's own clock. Everything is synthesized here: no samples.
The one voice is the narration: four Persian segments, synthesized offline (the fa_IR ganji medium voice) and
placed on the film's clock; the music is ducked under them (see NARRATION).

The music is calm, warm and quiet, under the narration, and it is not an alarm: no pitch glides, no sustained
voice is above 1 kHz, and every held note keeps one pitch. The counter (film.ratio, the Tehran-Karaj box's NO2 as a
multiple of the summer reference) moves the music through the pad's brightness and level, never through pitch.

    the pad     a warm chord in Shur on D: D3, A3 and D4, each a series of exact harmonics of D2 (the n-th at
                level/n^0.5, up to about 1.5 kHz), with a quiet D2 below. Every partial is an integer multiple of
                D2, so nothing beats. The counter moves only the low-pass cutoff (500 Hz summer to 1.6 kHz winter)
                and a 1.5 dB swell; the pad comes in over 1.5 s.
    the plucks  one very soft, low setar pluck per month, 26 dB under the pad's peak, velocity following the
                counter. The pitch is D3, F3 or A3 and steps only when the counter crosses 1.4 or 2.6.
    the santur  a hook on D3 at the first frame, the chord D3, F3, A3 at the hold, and the open ending
                (A3 and E3-koron, no tonic).

    0.00 s           the hook: one santur strike on D3 with a long ring (the first sound of the reel)
    0.00-1.50 s      the pad comes in
    1.00-9.46 s      the Jalali months Aban 1404 to Mehr 1405 at 1.3 months a second: a pluck per month
                     (1.00, 1.77, ... 9.46 s), the pitch changing only at the counter's thresholds
    9.46-10.06 s     the turn back to the winter
    10.60-19.06 s    the months again, the same plucks (10.60, 11.37, ... 19.06 s)
    19.66 s          the hold: a santur chord, D3, F3, A3, with a long ring
    21.00 s          the open ending: A3 and E3-koron on the santur, no tonic; the pad fades out together by
                     23.2 s; the master's fade takes the tails to 24 s

Narration (the segments at the film's clock; each one's speech starts at its start, the music is ducked
DUCK_DB under it with an attack of DUCK_ATTACK and a release of DUCK_RELEASE, the voice sits centred at
RATIO_TARGET dB above the ducked music):

    0.30-4.40 s   S1  this is Iran, from space; the amber patch is nitrogen dioxide
    4.50-10.40 s  S2  the gas of burning fuel: cars, power plants, factories and heaters
    10.60-17.00 s S3  in winter one reason is that cold air holds the gas near the ground (no number: the counter
                  is still showing the months)
    19.70-23.85 s S4  Tehran, about three times the summer's, the figure the counter holds (x3, from 19.66 s,
                  when the six city labels come on); then, where is your city?
    (the windows are the limits of the speech; each segment is spoken at its natural speed, length scale 1.0,
    and the speech of each one ends inside its window)

Mix: -14 LUFS integrated, true peak -1.5 dBTP in the WAV. The top octave (above 12 kHz) is taken out before the
master (the AAC overshoot), and the bass below 120 Hz is one channel in the spectrum (mono), as in the Karaj score.
The plucks and the santur are low-passed warm at 1.6 kHz (sixth order).

    python -I src/onebit_score_air.py              the narrated track: air_tehran_fa_voice.wav and
                                                   air_tehran_fa_voice_reel.mp4 (under the silent reel)
    python -I src/onebit_score_air.py --no-voice   the music-only track: air_tehran_fa_music.wav and
                                                   air_tehran_fa_music_reel.mp4, as before

The silent reel must be newer than src/onebit_air.py: render the film first with python -I src/onebit_air.py
(--accept-stale-video skips that check, for a preview on the current reel). The silent reel is not rewritten.
The script prints the loudness and the true peak of the WAV and of the MP4's decoded audio, the pad's pitch
against the score, the side against the mid below each frequency, the onsets of every event, the video stream
against the silent reel, and, with the voice, the narration on the clock and the voice-to-music ratio.
It then runs the NOT AN ALARM checks on the music alone: the pitch of every sustained voice, the spectral centroid
in every second, the 2-5 kHz level against 100-800 Hz, the pad's modulation above 4 Hz, and the plucks under the pad.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.ndimage import gaussian_filter1d
from scipy.signal import butter, hilbert, resample_poly, sosfilt, sosfiltfilt

sys.path.insert(0, str(Path(__file__).resolve().parent))

import air  # noqa: E402
import onebit  # noqa: E402
import onebit_air  # noqa: E402
import onebit_persian as kit  # noqa: E402

SR = kit.SR
MODE = "shur"                                   # the dastgah of the score: the Shur set (koron second, minor third)
TONIC = kit.note_hz("D3")                       # step 0 of the pad and of the plucks' lowest note (D3)
TAIL = 3.0                                      # s of room past the end, for the reverb and the echo
AIR = 12000.0                                   # Hz: above this the mix has no content (the AAC overshoot)
BASS = 120.0                                    # Hz: below this the two channels are one
MAX_OFFSET = 0.030                              # s: a hit may sit at most this far from its event
BASE = "air_tehran_fa"
SEED = 41
ACCENTS = {"hold": (onebit_air.HOLD, ((0, 0), (2, 0), (4, 0))),         # santur chord D3, F3, A3, as the Azar-Bahman field returns
           "end": (21.0, ((4, 0), (1, 0)))}                              # santur A3, E3-koron (open, no tonic)
LUFS, TP = -14.0, -1.5                          # -1.5 dBTP: the decoded AAC stays under -1 once the top octave is cut
# The pad: a warm chord in Shur on D. Its three roots are harmonics of PAD_F0 (D2, half of D3): D3 (2), A3 (3) and
# D4 (4). Each root has its own series of harmonics, the n-th at level / n^PAD_ROLLOFF, up to PAD_TOP_HARM (about
# 1.5 kHz). Every partial is an exact integer multiple of PAD_F0, so no two partials beat at a stable pitch: no
# detuned layers and no glides. The partials of a root fade together from 21.0 to 23.2 s.
# The roll-off is 0.5, not the 1/n^1.5 of a natural tone: with 1/n^1.5 no choice of the three levels meets all of
# these at once: no single partial above 40 % of the pad's energy, the centroid of the music at least 300 Hz, and at
# least half the energy above 250 Hz (the cutoff at 500 Hz in summer takes the rest). 0.5 meets them.
PAD_F0 = kit.note_hz("D2")                      # Hz: the fundamental of the pad's harmonic series (D3 / 2)
PAD_ROOTS = ((2, 0.50), (3, 1.50), (4, 1.30))   # (harmonic of PAD_F0, level): D3, A3, D4
PAD_BASS = 0.03                                 # the quiet D2 below the chord (harmonic 1)
PAD_ROLLOFF = 0.5                               # the n-th harmonic of a root is at level / n^PAD_ROLLOFF
PAD_TOP_HARM = 20                               # the highest harmonic of PAD_F0 (20 x D2 = 1.47 kHz)
PAD_FADE_END, PAD_FADE_REL = 23.2, 2.2          # s: the pad's end, and the release before it


def _pad_partials() -> tuple:
    amp = {1: PAD_BASS}
    for root, level in PAD_ROOTS:
        for n in range(1, PAD_TOP_HARM // root + 1):
            amp[root * n] = amp.get(root * n, 0.0) + level * n ** -PAD_ROLLOFF
    return tuple((h, a, 0.0, PAD_FADE_END, PAD_FADE_REL) for h, a in sorted(amp.items()))


PAD_PARTIALS = _pad_partials()                  # (harmonic, amplitude, phase, end s, release s)
PAD_EASE = (14.2, 19.7)                         # s: the 293.66 Hz partial (D4, harmonic 4 of D2) eases down over this span
PAD_EASE_DB, PAD_EASE_HARM = -2.5, 4           # dB, and the harmonic: the strongest steady partial in the reel
PAD_LEVEL = 0.25                                # the pad's peak before the mix; the other sounds are set against it
PAD_ATTACK = 1.5                                # s: the pad comes in from silence over this time
CUT_SUMMER, CUT_WINTER = 500.0, 1600.0          # Hz: the pad's low-pass cutoff in summer and in winter (geometric between)
PLUCK_TIERS = ((1.4, 0), (2.6, 2))              # (the counter below which, scale step): D3 under 1.4, F3 under 2.6
PLUCK_TOP = 4                                   # the scale step above the last threshold: A3
PLUCK_DB = -26.0                                # dB: a pluck's peak under the pad's peak (the rule: at least 24)
HOOK_DB, HOLD_DB, END_DB = -6.0, -6.0, -9.0     # dB: the santur sounds under the pad's peak
SANTUR_SPREAD = 0.0                              # the santur is centred (kit default 0.35): the bass stays mono
HOOK_BRIGHT = 0.9                               # the hook's hammer: harder than the kit's 0.6, so the first second is not all fundamental
HOOK_FADE = 0.008                              # s: the hook's raised-cosine fade-in (no edge for the bass in mono)
WARM = 1600.0                                   # Hz: the plucks and the santur are low-passed here (sixth order)
WARM_SOS = butter(6, WARM, "lowpass", fs=SR, output="sos")
NOTE_OF_STEP = {0: "D3", 2: "F3", 4: "A3"}

# ── narration ───────────────────────────────────────────────────────────────
TTS_ENV_BIN, TTS_ENV_MODEL = "ONEBIT_TTS_BIN", "ONEBIT_TTS_MODEL"   # the offline engine and the voice file, from the
                                                                  # environment (no local paths in the repo)
NARR_DIR = onebit.ROOT / "data" / "air" / "narration"                                   # the rendered segments
PAD = 0.03                                      # s of silence kept before each speech
DUCK_DB = 12.0                                  # dB: the music under the speech (8-12 dB)
DUCK_ATTACK = 0.15                              # s: the music goes down over this time, ahead of the speech
DUCK_RELEASE = 0.40                             # s: the music comes back over this time after it
VOICE = "fa_IR-ganji-medium"                    # the offline voice (its model file stem); the cache is keyed on it
RATIO_TARGET = 13.5                             # dB: the voice over the ducked music, set before the master (the calmer music lets the limiter take more of the voice)
RATIO_MIN = 10.0                                # dB: the measured minimum after the master
NARRATION = (
    dict(name="s1", start=0.3, end=4.4, length=1.0, noise=0.0,
         text="این ایران از فضاست؛ نارنجی، دی‌اکسیدِ نیتروژن است."),
    dict(name="s2", start=4.5, end=10.4, length=1.0, noise=0.0,
         text="گاز از سوزاندنِ سوخت؛ خودرو، نیروگاه، کارخانه و بخاری."),
    dict(name="s3", start=10.6, end=17.0, length=1.0, noise=0.3,
         text="زمستان‌ها یک دلیلش این است که هوای سرد این گاز را نزدیکِ زمین نگه می‌دارد."),
    dict(name="s4", start=19.7, end=23.85, length=1.0, noise=0.0,
         text="تهران، حدودِ سه برابرِ تابستان. شهرِ شما کجاست؟"),
)


def freq_of(step: int, octave: int = 0) -> float:
    return kit.degree(MODE, step, octave, tonic_hz=TONIC)


def timing(film) -> dict:
    """The film's clock, read from the film: the twelve month ticks of each of the two passes, the turns and the hold."""
    sch = film.schedule()
    tm = dict(ticks=[t for t, _ in sch["ticks"]], months=[ym for _, ym in sch["ticks"]], turns=list(sch["turns"]),
              turn=sch["turns"][-1], hold=float(sch["hold"]), end=float(sch["end"]))
    assert len(tm["ticks"]) == 2 * len(onebit_air.MONTHS) and tm["turn"] == onebit_air.DIAL_END, tm
    assert all(a < b for a, b in zip(tm["ticks"], tm["ticks"][1:])), tm["ticks"]
    assert abs(tm["hold"] - (tm["turn"] + onebit_air.TURN)) < 1e-9 and tm["end"] == 24.0, tm
    assert ACCENTS["hold"][0] == onebit_air.HOLD and ACCENTS["end"][0] > ACCENTS["hold"][0], tm
    return tm


def counter_level(film, tm, t: np.ndarray) -> np.ndarray:
    """The counter as a share of the way to winter (0 summer, 1 winter), per sample: the brightness of the pad."""
    pts = [(0.0, film.winter)]
    pts += [(t_k, film.ratio[ym]) for t_k, ym in zip(tm["ticks"], tm["months"])]
    pts += [(t_turn + onebit_air.TURN, film.winter) for t_turn in tm["turns"]]
    pts.sort(key=lambda p: p[0])
    level = np.interp(t, [p[0] for p in pts], [p[1] for p in pts])
    return np.clip((level - 1.0) / (film.winter - 1.0), 0.0, 1.0)


def pluck_step(ratio: float) -> int:
    """The pluck's scale step. The pitch changes only when the counter crosses a threshold; otherwise it is the same note."""
    for limit, step in PLUCK_TIERS:
        if ratio < limit:
            return step
    return PLUCK_TOP


def smooth_level(film, tm, n: int) -> np.ndarray:
    """The counter's share of the way to winter, per sample, smoothed (Gaussian, 0.25 s), so it never steps."""
    grid = np.arange(0.0, tm["end"] + 0.02, 0.001)
    lev = gaussian_filter1d(counter_level(film, tm, grid), 250.0, mode="nearest")
    return np.interp(np.arange(n) / SR, grid, lev)


def pad_bed(t: np.ndarray, lev: np.ndarray, voices: list) -> np.ndarray:
    """The pad, mono: the chord's partials at fixed pitches. Each partial's gain is set by the low-pass
    1/sqrt(1 + (f/fc)^6), with fc following the counter (CUT_SUMMER to CUT_WINTER). The level swells 1.5 dB with the
    counter. The attack is PAD_ATTACK. The voices are the chord's notes (D2, D3, A3, D4), not the partials."""
    fc = CUT_SUMMER * (CUT_WINTER / CUT_SUMMER) ** lev
    swell = 10 ** (1.5 * lev / 20)
    attack = np.sin(0.5 * np.pi * np.minimum(1.0, t / PAD_ATTACK)) ** 2
    out = np.zeros(len(t))
    ease = np.clip((t - PAD_EASE[0]) / (PAD_EASE[1] - PAD_EASE[0]), 0.0, 1.0)
    ease = 10 ** (PAD_EASE_DB * (ease * ease * (3 - 2 * ease)) / 20)     # the 293.66 Hz partial eases down (no held tone)
    for harm, amp, phase, t_off, rel in PAD_PARTIALS:
        f = harm * PAD_F0
        fade = np.sin(0.5 * np.pi * np.clip((t_off - t) / rel, 0.0, 1.0)) ** 2
        gain = ease if harm == PAD_EASE_HARM else 1.0
        out += gain * amp * fade * np.sin(2 * np.pi * f * t + phase) / np.sqrt(1.0 + (f / fc) ** 6)
    for root in [1] + [r for r, _ in PAD_ROOTS]:
        voices.append(dict(kind="pad", f=root * PAD_F0, t0=0.0, t1=PAD_FADE_END, spread=0.0))
    return PAD_LEVEL * out * attack * swell


def put(track: np.ndarray, sound, t: float) -> None:
    """Add a sound to both channels of the track at t. A mono sound goes to the centre (no pan law)."""
    s = np.asarray(sound, float)
    if s.ndim == 1:
        s = np.stack([s, s], axis=1)
    i = round(t * SR)
    m = min(len(s), len(track) - i)
    track[i:i + m] += s[:m]


def scale_to(x: np.ndarray, peak: float) -> np.ndarray:
    """x set so that its peak, over the channels, is `peak`."""
    return x * (peak / np.abs(x).max())


def pluck(freq: float, peak: float) -> np.ndarray:
    """A setar pluck, mono, low-passed warm and set to `peak`. The setar's own fade-in keeps it free of clicks."""
    x = np.asarray(kit.setar(freq, dur=1.6, vel=1.0, t60=1.3, bright=0.15, buzz=0.0), float)
    return scale_to(sosfilt(WARM_SOS, x), peak)


def santur_notes(pairs, dur: float, t60: float, peak: float, bright: float = 0.6) -> np.ndarray:
    """Santur notes (scale step, octave) sounding together, stereo, low-passed warm and set to `peak`. bright is the
    hammer's hardness (the kit's default 0.6)."""
    x = sum(kit.santur(freq_of(s, o), dur=dur, vel=1.0, t60=t60, spread=SANTUR_SPREAD, bright=bright) for s, o in pairs)
    return scale_to(sosfilt(WARM_SOS, x, axis=0), peak)


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


def compose(film, rec: list):
    """Lay the score on its buses. Returns (buses, the number of samples, the voices: each sustained or plucked voice
    with its pitch and its pitch spread in cents, from the synthesis parameters)."""
    kit.reseed(SEED)
    tm = timing(film)
    end = tm["end"]
    bus = {k: kit.new_track(end, TAIL) for k in ("pad", "plucks", "santur")}
    n = len(bus["pad"])
    t = np.arange(n) / SR
    voices: list = []

    def event(label, t_hit, items):
        for name, sound in items:
            put(bus[name], sound, t_hit)
        rec.append((label, t_hit, t_hit, [(s, 1.0, 0.0) for _, s in items]))

    pad = pad_bed(t, smooth_level(film, tm, n), voices)
    pad_peak = float(np.abs(pad).max())
    put(bus["pad"], pad, 0.0)
    rec.append(("pad: attack", 0.0, 0.0, []))

    # the hook: one santur strike on D3 with a long ring, at the first frame
    hook = santur_notes([(0, 0)], 8.0, 4.0, pad_peak * 10 ** (HOOK_DB / 20), bright=HOOK_BRIGHT)
    hook = hook * (np.sin(0.5 * np.pi * np.minimum(1.0, np.arange(len(hook)) / (HOOK_FADE * SR))) ** 2)[:, None]   # no abrupt edge at the first frame
    event("hook: santur D3 at 0.00 s", 0.0, [("santur", hook)])
    voices.append(dict(kind="santur", f=freq_of(0, 0), t0=0.0, t1=8.0, spread=2.5))

    # one very soft pluck per month of the dial: the pitch from the counter's thresholds, the velocity from the counter
    for t_k, ym in zip(tm["ticks"], tm["months"]):
        lv = float(counter_level(film, tm, np.array([t_k]))[0])
        step = pluck_step(film.ratio[ym])
        f = freq_of(step)
        event(f"month {ym}: pluck {NOTE_OF_STEP[step]}", t_k,
              [("plucks", pluck(f, pad_peak * 10 ** (PLUCK_DB / 20) * (0.8 + 0.2 * lv)))])
        voices.append(dict(kind="pluck", f=f, t0=t_k, t1=t_k + 1.6, spread=0.0))

    # the hold: the santur chord D3, F3, A3 with a long ring
    t_h, pairs = ACCENTS["hold"]
    event(f"hold: santur chord D3, F3, A3 at {t_h:.2f} s", t_h,
          [("santur", santur_notes(pairs, 6.0, 4.5, pad_peak * 10 ** (HOLD_DB / 20)))])
    voices += [dict(kind="santur", f=freq_of(s, o), t0=t_h, t1=t_h + 6.0, spread=2.5) for s, o in pairs]

    # the open ending: A3 and E3-koron on the santur, no tonic; the pad's A voices fade by 23.2 s
    t_e, pairs = ACCENTS["end"]
    event(f"end: santur A3, E3-koron at {t_e:.2f} s", t_e,
          [("santur", santur_notes(pairs, end - t_e, 3.0, pad_peak * 10 ** (END_DB / 20)))])
    voices += [dict(kind="santur", f=freq_of(s, o), t0=t_e, t1=end, spread=2.5) for s, o in pairs]
    return bus, n, voices


def music_bus(bus: dict, n: int) -> np.ndarray:
    """The buses summed, before the top octave is cut. The pad has a room; the plucks and the santur are dry."""
    room = kit.reverb(kit.widen(bus["pad"], 0.3), t60=1.8) * 0.25
    return bus["pad"] + _fit(room, n) + bus["plucks"] + bus["santur"]


# ── narration ───────────────────────────────────────────────────────────────

def _cached(seg: dict):
    """The segment as rendered before (same text and length scale), or None. The voice is not seeded, so a fresh
    synthesis differs from run to run; the rendered segments in NARR_DIR are the reproducible source."""
    try:
        man = {m["name"]: m for m in json.loads((NARR_DIR / "manifest.json").read_text(encoding="utf-8"))}
        m = man[seg["name"]]
        if (m["text"] != seg["text"] or m["length_scale"] != seg["length"] or m.get("voice") != VOICE
                or m.get("noise_w_scale", 0.0) != seg.get("noise", 0.0)):
            return None
        rate, pcm = wavfile.read(str(NARR_DIR / f"{seg['name']}.wav"))
        return pcm.astype(float) / 32767.0, m["lead"], m["speech"]
    except (OSError, KeyError, ValueError):
        return None


def synth_segment(seg: dict) -> tuple:
    """One segment: the offline voice at its length scale, cut to its speech (PAD of silence kept before it) and
    resampled to SR, mono, peak 0.9. Returns (samples, lead: s of silence kept before the speech, speech: s of
    speech). The rendered segment is reused when it was made from the same text and length scale. Raises if the
    speech does not end by the segment's end."""
    hit = _cached(seg)
    if hit is not None:
        y, lead, speech = hit
        assert seg["start"] + speech <= seg["end"], (seg["name"], speech)
        return y, lead, speech
    binary, model = os.environ.get(TTS_ENV_BIN), os.environ.get(TTS_ENV_MODEL)
    if not binary or not model:
        sys.exit(f"the narration needs the offline voice: set {TTS_ENV_BIN} (the engine's executable) and "
                 f"{TTS_ENV_MODEL} (the {VOICE} voice file), or render the segments already in {NARR_DIR}")
    assert Path(model).name.startswith(VOICE), (model, VOICE)
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "raw.wav"
        # the duration jitter is set per segment (seg["noise"]); the cache is keyed on it, so each WAV is reproducible
        subprocess.run([binary, "-m", model, "--length-scale", str(seg["length"]),
                        "--noise-w-scale", str(seg.get("noise", 0.0)), "-f", str(raw)],
                       input=(seg["text"] + "\n").encode("utf-8"), check=True, capture_output=True)
        rate, pcm = wavfile.read(str(raw))
    x = pcm.astype(float) / 32768.0
    if x.ndim > 1:
        x = x[:, 0]
    a = np.flatnonzero(np.abs(x) > 0.01 * np.abs(x).max())
    on, off = int(a[0]), int(a[-1]) + 1
    pad = int(round(PAD * rate))
    x = x[max(on - pad, 0): min(off + pad, len(x))]
    lead = (on - max(on - pad, 0)) / rate
    speech = (off - on) / rate
    f = Fraction(SR, rate)
    y = resample_poly(x, f.numerator, f.denominator)
    edge = int(0.01 * SR)
    y[:edge] *= np.linspace(0.0, 1.0, edge)
    y[-edge:] *= np.linspace(1.0, 0.0, edge)
    y = 0.9 * y / np.abs(y).max()
    assert seg["start"] + speech <= seg["end"], (seg["name"], speech, seg["end"] - seg["start"])
    return y, lead, speech


def duck_gain(mask: np.ndarray) -> np.ndarray:
    """The music's gain per sample: DUCK_DB down while the mask is on, the attack and the release one-pole in dB."""
    a = math.exp(-1.0 / (SR * DUCK_ATTACK))
    r = math.exp(-1.0 / (SR * DUCK_RELEASE))
    target = np.where(mask, -DUCK_DB, 0.0)
    g = np.empty(len(target))
    cur = 0.0
    for i, t in enumerate(target):
        k = a if t < cur else r
        cur = k * cur + (1.0 - k) * t
        g[i] = cur
    return 10.0 ** (g / 20.0)


def narrate(music: np.ndarray, n: int) -> dict:
    """The voice on the film's clock, and the music ducked under it. Returns the mix before the master (total), the
    music as it sounds (ducked), the voice (both centred), and the speech spans (name, start, end) in s."""
    NARR_DIR.mkdir(parents=True, exist_ok=True)
    v = np.zeros(n)
    spans, manifest = [], []
    for seg in NARRATION:
        y, lead, speech = synth_segment(seg)
        i0 = round((seg["start"] - lead) * SR)
        v[i0:i0 + len(y)] += y[:max(0, n - i0)]
        spans.append((seg["name"], seg["start"], seg["start"] + speech))
        if _cached(seg) is None:
            wavfile.write(str(NARR_DIR / f"{seg['name']}.wav"), SR, (np.clip(y, -1, 1) * 32767).astype(np.int16))
        manifest.append(dict(name=seg["name"], start=seg["start"], speech=round(speech, 4), lead=round(lead, 4),
                             length_scale=seg["length"], noise_w_scale=seg.get("noise", 0.0), voice=VOICE,
                             text=seg["text"]))
    (NARR_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    mask = np.zeros(n, bool)
    core = np.zeros(n, bool)
    for _, a, b in spans:
        mask[round((a - DUCK_ATTACK) * SR):round(b * SR)] = True
        core[round(a * SR):round(b * SR)] = True
    music_d = music * duck_gain(mask)[:, None]
    rms = lambda z: float(np.sqrt(np.mean(np.square(z))))  # noqa: E731
    v = sosfiltfilt(butter(2, 20.0, "highpass", fs=SR, output="sos"), v)   # the speech's own offset and rumble, out
    v *= rms(music_d[core]) * 10 ** (RATIO_TARGET / 20.0) / rms(v[core])     # the voice sits RATIO_TARGET dB above
    voice = np.stack([v, v], axis=1)
    total = sosfiltfilt(butter(2, 20.0, "highpass", fs=SR, output="sos"), _air_cut(music_d + voice), axis=0)   # nothing below 20 Hz: the gain moves of the ducking leave no offset
    return dict(total=total, music=music_d, voice=voice, spans=spans)


# ── render ──────────────────────────────────────────────────────────────────

def render(film, log: list | None = None, voice: bool = True):
    """The mastered track (bass in mono), the parts of the mix before the master (for the verification), the buses.
    parts["stem"] is the music alone before the master (no voice, no duck): the subject of the NOT AN ALARM checks."""
    rec = [] if log is None else log
    bus, n, voices = compose(film, rec)
    music = music_bus(bus, n)
    stem = _air_cut(music)
    if voice:
        parts = narrate(music, n)
    else:
        parts = dict(total=stem, music=music, voice=None, spans=[])
    parts["stem"], parts["voices"] = stem, voices
    track = kit.master(parts["total"], lufs=LUFS, tp=TP - 0.5, seconds=float(film.L.end), fade_out=1.0)   # the master settles above its ceiling on this track: 0.5 dB more headroom
    return _bass_mono(track), parts, bus


# ── checks ──────────────────────────────────────────────────────────────────

def write_wav(path, x) -> Path:
    """The 48 kHz, 16-bit WAV of kit.write_wav, with one TPDF dither for both channels. The kit's dither is drawn per
    channel, and below 120 Hz the music is quiet and mono: a per-channel dither would be the only side there."""
    x = np.clip(np.asarray(x, float), -1, 1)
    rng = np.random.default_rng(3)
    dither = (rng.random(len(x)) - rng.random(len(x))) / 32768
    pcm = np.clip(np.round((x + dither[:, None]) * 32767), -32768, 32767).astype("<i2")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(str(path), SR, pcm)
    return path


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


def _flux(x, hop: int = 48, nfft: int = 256):
    y = np.concatenate([np.zeros(nfft), x])
    starts = np.arange(0, len(y) - nfft + 1, hop)
    frames = y[starts[:, None] + np.arange(nfft)[None, :]] * np.hanning(nfft)
    logm = np.log10(np.abs(np.fft.rfft(frames, axis=1)) + 1e-5)
    rise = np.maximum(np.diff(logm, axis=0, prepend=logm[:1]), 0.0).sum(axis=1)
    return (starts - nfft / 2) / SR, rise


def _flux_onset(times, rise, t: float, w: float = MAX_OFFSET, first: bool = True):
    """The offset (s) of the onset within w of t, or None. The onset is the earliest local peak of the flux that
    reaches half the strongest one in the window (first=False: the strongest peak)."""
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


def fundamental(x: np.ndarray, t0: float, t1: float, lo: float = 80.0, hi: float = 400.0) -> float:
    """The strongest frequency (Hz) of x between t0 and t1, zero-padded for a fine grid."""
    seg = x[int(t0 * SR):int(t1 * SR)]
    seg = seg * np.hanning(len(seg))
    nfft = 2 ** 20
    spec = np.abs(np.fft.rfft(seg, nfft))
    f = np.fft.rfftfreq(nfft, 1.0 / SR)
    m = np.flatnonzero((f >= lo) & (f <= hi))
    k = m[np.argmax(spec[m])]
    a, b, c = np.log(spec[k - 1]), np.log(spec[k]), np.log(spec[k + 1])
    shift = 0.5 * (a - c) / (a - 2 * b + c)                 # parabolic peak in the log magnitude
    return float(f[k] + shift * (f[1] - f[0]))


def _event_offsets(events, mx: np.ndarray, mm: np.ndarray) -> list:
    """Each event's strongest onset in mx (a mono signal), with the rest of the mix mm (before the master) taken
    away: mm is high-passed and fitted to mx locally, so only the event's own sound is left to measure."""
    from scipy.ndimage import uniform_filter1d
    hp = butter(2, 12.0, "highpass", fs=SR, output="sos")
    u = sosfilt(hp, mm[:len(mx)])
    w1 = round(0.001 * SR) | 1
    gain = (uniform_filter1d(mx * u, w1, mode="nearest")
            / np.maximum(uniform_filter1d(u * u, w1, mode="nearest"), 1e-12))
    offs = []
    for label, visual, hit_t, items in events:
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


def _mastered_gain(x_mean: np.ndarray, ref_mean: np.ndarray) -> float:
    """The one gain that takes the pre-master mix to the WAV (the master's gain, the limiter aside)."""
    m = min(len(x_mean), len(ref_mean)) - SR                 # the last second is the fade
    return float(np.dot(x_mean[:m], ref_mean[:m]) / np.dot(ref_mean[:m], ref_mean[:m]))


def check_audio(film, wav, out, log: list, parts: dict, bus) -> None:
    x = _read_wav(wav)
    mix = parts["total"]
    lufs, tp = kit.integrated_lufs(x), kit.true_peak_dbtp(x)
    dec = _decode(out)
    aac_lufs, aac_tp = kit.integrated_lufs(dec), kit.aac_true_peak(out)
    a_dur = [float(s["duration"]) for s in _probe(out)["streams"] if s["codec_type"] == "audio"][0]
    tm = timing(film)
    print(f"times from the film: months {tm['ticks'][0]:.2f}-{tm['ticks'][11]:.2f} s and "
          f"{tm['ticks'][12]:.2f}-{tm['ticks'][-1]:.2f} s ({len(tm['ticks'])} ticks), turns {tm['turns'][0]:.2f} s and "
          f"{tm['turn']:.2f} s, hold {tm['hold']:.2f} s, end {tm['end']:.2f} s")
    print(f"durations: WAV {len(x) / SR:.3f} s; muxed MP4 audio {a_dur:.3f} s")

    print("\n(1) loudness and true peak")
    print(f"    WAV            {lufs:+.2f} LUFS   {tp:+.2f} dBTP   (limit -1.5 dBTP)")
    print(f"    MP4 (decoded)  {aac_lufs:+.2f} LUFS   {aac_tp:+.2f} dBTP   (limit -1 dBTP)")
    assert -14.5 <= lufs <= -13.5 and -14.5 <= aac_lufs <= -13.5, (lufs, aac_lufs)
    assert tp <= -1.5 and aac_tp <= -1.0, (tp, aac_tp)
    air_mix, air_wav = _share_above(mix, AIR), _share_above(x, AIR)
    print(f"    the top octave (above {AIR / 1000:.0f} kHz): the mix before the master {air_mix:+.1f} dB of its energy, "
          f"the WAV {air_wav:+.1f} dB")
    assert air_mix < -60.0, air_mix

    print("\n(2) the first 0.1 s: sound from the first frame")
    head = x[:int(0.1 * SR)]
    loud = np.flatnonzero(np.abs(x).max(axis=1) > 0.1)
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

    print("\n(4) the pad's pitch: its D3 partial held in two windows, against the score")
    pad_m = bus["pad"].mean(axis=1)
    worst = 0.0
    for a, b in ((4.0, 8.0), (13.0, 17.0)):
        f_meas = fundamental(pad_m, a, b, lo=120.0, hi=170.0)
        cents = 1200 * math.log2(f_meas / freq_of(0, 0))
        worst = max(worst, abs(cents))
        print(f"    {a:6.2f}-{b:6.2f} s  measured {f_meas:8.2f} Hz  score {freq_of(0, 0):8.2f} Hz  ({cents:+5.2f} cents)")
    print(f"    largest error {worst:.2f} cents (limit 5)")
    assert worst <= 5.0, worst

    print("\n(5) the bass in mono: the side against the mid in the spectrum of the WAV, below each frequency")
    marks = {f: _side_db(x, f) for f in (60.0, 90.0, 120.0)}
    print("    " + "   ".join(f"below {f:.0f} Hz {v:+.1f} dB" for f, v in marks.items()))
    assert marks[120.0] < -60, "the bass is not mono"

    check_not_alarm(film, parts, bus, log)

    print("\n(6) the events' onsets: each event's own sound, and the same in the WAV")
    events = [e for e in log if e[3]]
    own = []
    for label, visual, hit_t, items in events:
        a = round((hit_t - 0.1) * SR)
        ev = kit.new_track(0.4)
        for sound, g, pan in items:
            kit.place(ev, sound, (round(hit_t * SR) - a) / SR, g, pan)
        lt, lr = _flux(_air_cut(ev.mean(axis=1)))
        own.append(_flux_onset(lt, lr, 0.1))
    assert all(v is not None for v in own), "an event with no onset"
    worst_own = max(abs(v) for v in own)
    print(f"    the sounds on their own, {len(own)} events: largest first-rise offset {worst_own * 1000:.2f} ms "
          f"(limit {MAX_OFFSET * 1000:.0f} ms)")
    assert worst_own <= MAX_OFFSET, worst_own
    wav_off = _event_offsets(events, x.mean(axis=1), mix.mean(axis=1))
    assert all(v is not None for v in wav_off), "an event with no onset in the WAV"
    worst_wav = max(abs(v) for v in wav_off)
    print(f"    the WAV: largest strongest-peak offset {worst_wav * 1000:.2f} ms (limit {MAX_OFFSET * 1000:.0f} ms)")
    assert worst_wav <= MAX_OFFSET, worst_wav
    for (label, visual, _h, _i), o, wv in zip(events, own, wav_off):
        print(f"    {label:<40}{visual:8.3f} s  own {o * 1000:+7.2f} ms  WAV {wv * 1000:+7.2f} ms")

    print("\n    through the MP4's AAC audio, decoded (the strongest flux peak, offset in ms):")
    if parts["voice"] is None:
        dtimes, drise = _flux(dec.mean(axis=1))
        dec_off = [_flux_onset(dtimes, drise, hit_t, first=False) for _l, _v, hit_t, _i in events]
        note = ""
    else:
        dec_off = _event_offsets(events, dec.mean(axis=1), mix.mean(axis=1))
        note = " (the voice taken away as in the WAV)"
    worst_dec = 0.0
    for (label, visual, hit_t, _items), off in zip(events, dec_off):
        assert off is not None and abs(off) <= MAX_OFFSET, (label, off)
        worst_dec = max(worst_dec, abs(off))
    print(f"    the decoded events are within the limit (largest {worst_dec * 1000:.2f} ms){note}")

    if parts["voice"] is not None:
        check_voice(x, parts)


def _am_depth(x, a: float = 3.0, b: float = 20.5) -> float:
    """The pad's amplitude modulation as the ear hears it: the RMS in 40 ms windows every 10 ms, its log, band-passed at
    4-20 Hz; peak to peak in dB over a..b s. The waveform's own ripple at its fundamental and harmonics is not in it."""
    w, h = round(0.040 * SR), round(0.010 * SR)
    starts = np.arange(0, len(x) - w, h)
    frames = x[starts[:, None] + np.arange(w)[None, :]]
    env = 20 * np.log10(np.sqrt(np.mean(frames ** 2, axis=1)) + 1e-12)
    y = sosfilt(butter(2, [4.0, 20.0], "bandpass", fs=SR / h, output="sos"), env)
    t = (starts + w / 2) / SR
    sel = (t >= a) & (t < b)
    return float(y[sel].max() - y[sel].min())


def _partial_share(x, a: float = 3.0, b: float = 20.5):
    """The largest single partial's share of the pad's energy (Hann window, +-6 Hz around each partial, 20-2000 Hz)."""
    seg = x[round(a * SR):round(b * SR)] * np.hanning(round((b - a) * SR))
    p = np.abs(np.fft.rfft(seg)) ** 2
    f = np.fft.rfftfreq(len(seg), 1.0 / SR)
    total = p[(f >= 20.0) & (f <= 2000.0)].sum()
    shares = {h * PAD_F0: p[np.abs(f - h * PAD_F0) <= 6.0].sum() / total for h, *_ in PAD_PARTIALS}
    top = max(shares, key=shares.get)
    return float(shares[top]), float(top)


def check_not_alarm(film, parts: dict, bus: dict, log: list) -> None:
    """The objective checks against an alarm, on the music alone (the stem, before the master): (1) the pitch of every
    sustained voice, from the synthesis parameters; (2) the spectral centroid in every second, within 300-700 Hz, and
    at least half of the energy above 250 Hz in every second (a phone speaker plays little below that); (3) the 2-5 kHz
    level against 100-800 Hz, outside the first 60 ms of each hit; (4) the pad's amplitude modulation (the 40 ms RMS
    envelope, its 4-20 Hz band, at most 3 dB) and no single partial above 40 % of the pad's energy; (5) the plucks under
    the pad's peak."""
    print("\nNOT AN ALARM: objective checks on the music alone (the stem before the master)")
    end = int(round(timing(film)["end"]))

    voices = parts["voices"]
    for v in voices:
        assert v["spread"] <= 5.0 and v["f"] < 1000.0, v
        assert v["kind"] == "pluck" or v["t1"] - v["t0"] >= 2.0, v
    n_pl = sum(v["kind"] == "pluck" for v in voices)
    print(f"    (1) {len(voices)} voices ({n_pl} plucks): the pitch of each held note is fixed, largest spread "
          f"{max(v['spread'] for v in voices):.1f} cents (limit 5); highest {max(v['f'] for v in voices):.0f} Hz (limit 1000); "
          f"every pad and santur note held 2 s or more")

    stem = parts["stem"]
    mono = stem.mean(axis=1)
    freqs = np.fft.rfftfreq(SR, 1.0 / SR)
    win = np.hanning(SR)
    cent, share = [], []
    for k in range(end):
        p = np.abs(np.fft.rfft(mono[k * SR:(k + 1) * SR] * win)) ** 2
        cent.append(float((freqs * p).sum() / p.sum()))
        share.append(float(p[freqs > 250.0].sum() / p.sum()))
    lo, top = int(np.argmin(cent)), int(np.argmax(cent))
    print(f"    (2) spectral centroid in each second, 0-{end} s: lowest {cent[lo]:.0f} Hz in {lo}-{lo + 1} s, highest "
          f"{cent[top]:.0f} Hz in {top}-{top + 1} s (band 300-700 Hz)")
    assert 300.0 <= cent[lo] and cent[top] <= 700.0, cent
    least = int(np.argmin(share))
    print(f"    (2b) energy above 250 Hz in each second: least {share[least]:.0%} in {least}-{least + 1} s "
          f"(limit 50%)")
    assert share[least] >= 0.5, share

    hits = [e[2] for e in log if e[3]]
    nfft, hop = 2048, 1024
    w = np.hanning(nfft)
    f3 = np.fft.rfftfreq(nfft, 1.0 / SR)
    hi_m, lo_m = (f3 >= 2000.0) & (f3 <= 5000.0), (f3 >= 100.0) & (f3 <= 800.0)
    worst3, where3 = -np.inf, 0
    for k in range(end):
        hi = lo = 0.0
        for s0 in range(k * SR, (k + 1) * SR, hop):
            if any(s0 < (h + 0.06) * SR and s0 + nfft > h * SR for h in hits):
                continue
            p = np.abs(np.fft.rfft(mono[s0:s0 + nfft] * w)) ** 2
            hi += p[hi_m].sum()
            lo += p[lo_m].sum()
        if lo > 0:
            r = 10 * np.log10(max(hi, 1e-30) / lo)
            if r > worst3:
                worst3, where3 = r, k
    print(f"    (3) 2-5 kHz against 100-800 Hz, each second, outside the first 60 ms of each hit: highest "
          f"{worst3:+.1f} dB in {where3}-{where3 + 1} s (limit -20 dB)")
    assert worst3 <= -20.0, worst3

    pad_m = bus["pad"].mean(axis=1)
    depth = _am_depth(pad_m)
    print(f"    (4) the pad's amplitude modulation: the 40 ms RMS envelope every 10 ms, its 4-20 Hz band, 3-20.5 s: "
          f"{depth:.2f} dB peak to peak (limit 3 dB)")
    assert depth <= 3.0, depth
    share, top = _partial_share(pad_m)
    print(f"    (4b) the largest single partial: {top:.1f} Hz with {share:.0%} of the pad's energy, 3-20.5 s (limit 40%)")
    assert share <= 0.40, share

    margin = float(20 * np.log10(np.abs(bus["pad"]).max() / np.abs(bus["plucks"]).max()))
    print(f"    (5) the plucks' peak {margin:.1f} dB under the pad's peak (limit 24 dB)")
    assert margin >= 24.0, margin


def check_voice(x: np.ndarray, parts: dict) -> None:
    """The narration on the film's clock, and the voice over the music after the master."""
    print("\n(8) the narration: each segment on the film's clock, and the voice over the ducked music")
    xm = x.mean(axis=1)
    g = _mastered_gain(xm, parts["total"].mean(axis=1))
    v_m, m_m = parts["voice"].mean(axis=1), parts["music"].mean(axis=1)
    ratios = []
    for name, a, b in parts["spans"]:
        i0, i1 = round(a * SR), round(b * SR)
        ratio = 10 * np.log10(np.mean((g * v_m[i0:i1]) ** 2) / np.mean((g * m_m[i0:i1]) ** 2))
        ratios.append(ratio)
        seg = next(s for s in NARRATION if s["name"] == name)
        print(f"    {name}  speech {a:6.2f}-{b:6.2f} s (window {seg['start']:.2f}-{seg['end']:.2f} s, "
              f"length scale {seg['length']:.2f}, {b - a:.2f} s)  voice over music {ratio:+.1f} dB")
    worst_ratio = min(ratios)
    print(f"    the voice over the ducked music, the least in a segment: {worst_ratio:+.1f} dB (limit {RATIO_MIN:.0f} dB)")
    assert worst_ratio >= RATIO_MIN, worst_ratio
    # the speech must not leave its window, and the music must duck: the music is quieter under the speech
    duck = [20 * np.log10(np.sqrt(np.mean(m_m[round(a * SR):round(b * SR)] ** 2) + 1e-30)) for _, a, b in parts["spans"]]
    print(f"    the music under the speech, RMS {', '.join(f'{d:.1f}' for d in duck)} dBFS")
    assert all(b <= s["end"] + 1e-9 for (_, _a, b), s in zip(parts["spans"], NARRATION)), parts["spans"]


def _share_above(x, fc: float) -> float:
    x = np.asarray(x, float)
    x = x.mean(axis=1) if x.ndim == 2 else x
    p = np.abs(np.fft.rfft(x)) ** 2
    f = np.fft.rfftfreq(len(x), 1.0 / SR)
    return float(10 * np.log10(max(p[f > fc].sum(), 1e-30) / max(p.sum(), 1e-30)))


def check_video(video, out, untouched: bool) -> None:
    vid, mux_p = _probe(video), _probe(out)
    print(f"\ndurations: silent reel video {float(vid['format']['duration']):.3f} s; "
          f"muxed MP4 {float(mux_p['format']['duration']):.3f} s")
    print("\n(7) the video stream of the muxed MP4 against the silent reel")
    v_md5, m_md5 = _md5(video, "0:v:0"), _md5(out, "0:v:0")
    print(f"    silent reel {v_md5}")
    print(f"    muxed reel  {m_md5}")
    assert v_md5 == m_md5, "the video stream changed"
    assert untouched, "the silent reel was rewritten"
    print("    the same packets; the silent reel was not rewritten")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-voice", action="store_true", help="the music-only track, as before")
    ap.add_argument("--video", type=Path, default=None, help="the silent reel (default: the film's)")
    ap.add_argument("--outdir", type=Path, default=None, help="where the WAV and the MP4 go (default: social/)")
    ap.add_argument("--out-mp4", type=Path, default=None, help="the MP4's full path (overrides --outdir)")
    ap.add_argument("--accept-stale-video", action="store_true",
                    help="skip the check that the silent reel is newer than src/onebit_air.py (a preview)")
    args = ap.parse_args()
    film = onebit_air.AirFilm()
    social = args.outdir or onebit.OUT / "social"
    video = args.video or onebit.OUT / "social" / f"{BASE}_reel.mp4"
    stem = f"{BASE}_music" if args.no_voice else f"{BASE}_voice"
    wav = social / f"{stem}.wav"
    out = args.out_mp4 or social / f"{stem}_reel.mp4"
    if not args.accept_stale_video and video.stat().st_mtime < Path(onebit_air.__file__).stat().st_mtime:
        sys.exit(f"{video.name} is older than src/onebit_air.py: render the film first "
                 f"(python -I src/onebit_air.py), then run this score again")
    st = os.stat(video)
    before = (st.st_size, st.st_mtime_ns)
    log: list = []
    track, parts, bus = render(film, log, voice=not args.no_voice)
    social.mkdir(parents=True, exist_ok=True)
    write_wav(wav, track)
    print("saved", wav)
    kit.mux(video, wav, out)
    print("saved", out)
    check_audio(film, wav, out, log, parts, bus)
    st2 = os.stat(video)
    check_video(video, out, untouched=before == (st2.st_size, st2.st_mtime_ns))
    print("\nall checks pass")


if __name__ == "__main__":
    main()
