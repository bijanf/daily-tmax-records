"""The score of the five-dam reel (tehran5_kahgel_fa, 28 s): an original track in Chahargah, built from the Persian
sound kit (onebit_persian) and timed to the film's own clock. Everything is synthesized here: no samples, no voices.

The data are the music's data. Each dam has one bar of the film (4 s): its 1405 storage as a share of its long-term
average (film: tehran5.DAMS) is the pitch of its pluck on the bar line, on a log scale between the lowest share (Mamlu,
30 %) and the highest (Karaj, 119 %), quantized to nine steps from C3. The groove follows the same share: thin for the
dams below two thirds of their average, mid for Taleqan (68 %), full only at Karaj. The total of the last bar (65.5 %
of the average) lands on an open chord, G and B, with no tonic: no full cadence.

    0.00-4.00 s      bar 1, the hook: two bars on santur (C, E, G, E, D), from the first frame
    0.20-2.00 s      the five 1405 lakes appear one by one, a soft tick each (0.4 s apart)
    4 + 4k s         bar 2+k, one dam (Mamlu, Lar, Latyan, Taleqan, Karaj): its bar line, one pluck on its share
    4-24 s           the groove, one bar line every 2 s, its level from the dam's share (the total for bar 7)
    24.00 s          bar 7: the total lands on the open chord G and B, with an impact and a daf stroke
    28.00 s          the master's fade takes the tails to the end

(the times are the film's, read from film_mod; the numbers are those of the cut the score was last run on)

Mix: -14 LUFS integrated; the WAV's true peak at -6 dBTP, because the kick and the sub overshoot in AAC (at -1.5 and
-4 dBTP the decoded audio peaked at +1.1 and -0.3 dBTP): the decoded audio must stay at -1 dBTP or below. The top
octave (above 12 kHz) is taken out before the master, and after the master the bass below 120 Hz is one channel in
the spectrum, so the sub is mono. The plucks have a ping-pong echo; the hook and the pad have a room, and are ducked
under the kick.

    python -I src/onebit_score_tehran5.py

writes outputs/onebit/social/tehran5_kahgel_fa_music.wav and muxes it under the silent reel into
tehran5_kahgel_fa_music_reel.mp4 (the silent reel is not rewritten). The silent reel must be newer than
src/onebit_tehran5.py: render the video first (the driver's render onebit_tehran5). The script prints the loudness and
the true peak of the WAV and of the MP4's decoded audio, the times taken from the film, the groove's levels, the RMS
per second against the share on screen, the side against the mid below each frequency, the onsets of every event (in
the WAV, cleared of the rest of the mix; the accents also in the decoded MP4), and the video stream against the
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
from scipy.signal import butter, sosfilt

sys.path.insert(0, str(Path(__file__).resolve().parent))

import onebit  # noqa: E402
import onebit_persian as kit  # noqa: E402
import onebit_tehran5 as film_mod  # noqa: E402
import tehran5  # noqa: E402
from onebit_slides import COLOURS  # noqa: E402

SR = kit.SR
BEAT, BAR = kit.BEAT, kit.BAR                  # 0.5 s and 2 s at 120 BPM: the film's 60 BPM, half-time
MODE = "chahargah"                             # the dastgah of the reel: its seven steps from C4 (kit.MODES)
STEPS = 9                                      # the pluck's pitch: nine steps, C3 to about E4
PLUCK_TONIC = kit.note_hz("C3")
HOOK_TONIC = kit.note_hz("C4")                 # the hook, the chords and the sting: C4 and up, G3 and below
KICK, SUB = kit.note_hz("C1"), kit.note_hz("C2")
TAIL = 3.0                                     # s of room past the end, for the reverb and the echo
LUFS, TP = -14.0, -6.0                         # the kick and the sub overshoot in AAC: -6 keeps the decoded audio under -1
AIR = 12000.0                                  # Hz: above this the mix has no content (the AAC overshoot)
BASS = 120.0                                   # Hz: below this the two channels are one
MAX_OFFSET = 0.030                             # s: a hit may sit at most this far from its event
BASE = "tehran5_kahgel_fa"
BUSES = ("intro", "ticks", "pluck", "drum", "kick", "pad", "hook", "sub", "fx")
SEED = 37
HOOK = ((0, 0.0, 1.0), (2, 1.0, 1.0), (4, 2.0, 2.0), (2, 4.0, 1.0), (1, 5.0, 3.0))  # (step, beat, length in beats)
PAD_CHORD = ((0, -1), (4, -1))                 # C3 and G3: the open fifth under the groove of the dams
END_CHORD = ((4, -1), (6, -1))                 # G3 and B3: an open chord with no tonic, no cadence
MID, FULL = 0.6, 1.0                           # the groove's levels: the share of the average on screen at the bar
                                               # line; full at the average or above, mid from 60 %, thin below
ECHO = dict(delay=0.375, feedback=0.4, taps=6) # the plucks' ping-pong: a dotted eighth at 120 BPM


def block_geo_stack() -> None:
    """Keep the geo stack out of this process: the film reads only CSV and npz, and the repo's rule is that no
    process holding netCDF readers imports shapely or cartopy (see onebit_score_zayandeh)."""
    for name in ("shapely", "cartopy", "fiona", "geopandas"):
        if name not in sys.modules:
            sys.modules[name] = None


# ── the film's clock, the dams and the shares on screen ──────────────────────

def timing(film) -> dict:
    """The film's own times: the hook's five lakes, the dams' bar lines (4 + 4k s), the total's bar (24 s), the end."""
    tm = dict(lakes=[film_mod.HL_STEP * k for k in range(len(film_mod.ORDER))],
              bars=[film_mod.DAM_T0 + film_mod.SEG * k for k in range(len(film_mod.ORDER))],
              stack=float(film_mod.STACK), end=float(film_mod.END))
    assert tm["bars"][0] == film_mod.SEG and tm["stack"] == tm["bars"][-1] + film_mod.SEG, tm
    assert [float(s) for s in film.starts] == [4.0 * k for k in range(8)], film.starts
    return tm


def shares() -> list:
    """Each dam's 1405 storage as a share of its long-term average, in the film's order (worst to best)."""
    by = {d["key"]: d for d in tehran5.DAMS}
    return [by[k]["value"] / by[k]["long_term"] for k in film_mod.ORDER]


def total_share() -> float:
    return tehran5.TOTAL["value"] / tehran5.TOTAL["long_term"]


def shown_share(film, t: float) -> float:
    """The share of the average on screen at time t: a bar grows once from 0 to its value over GROW s, then holds;
    the total's bar at the stack."""
    if t < film_mod.DAM_T0:
        return 0.0
    if t >= film_mod.STACK:
        p = min(max((t - film_mod.STACK) / film_mod.GROW, 0.0), 1.0)
        p = p * p * (3 - 2 * p)
        return total_share() * p
    k = min(int((t - film_mod.DAM_T0) // film_mod.SEG), len(film_mod.ORDER) - 1)
    d = {x["key"]: x for x in tehran5.DAMS}[film_mod.ORDER[k]]
    p = min(max((t - film_mod.DAM_T0 - k * film_mod.SEG) / film_mod.GROW, 0.0), 1.0)
    p = p * p * (3 - 2 * p)
    return d["value"] * p / d["long_term"]


def share_curve(film, end: float) -> np.ndarray:
    """The share on screen once per millisecond from 0 to end."""
    return np.array([shown_share(film, i / 1000.0) for i in range(int(round(end * 1000)) + 1)])


def level_of(share: float) -> str:
    """The groove's layers against the average: full at the average or above, mid from 60 %, thin below."""
    return "full" if share >= FULL else "mid" if share >= MID else "thin"


def voice(share: float, lo: float, hi: float) -> tuple:
    """(step, u, velocity, ring) of a dam's pluck. u is the share on a log scale between the lowest (lo) and the
    highest (hi) share of the reel: 0 at lo, 1 at hi. The step is u on the nine steps; the velocity and the ring
    (t60, the seconds to fall 60 dB) grow with u, so a big share rings and a small one is dry."""
    u = (math.log(share) - math.log(lo)) / (math.log(hi) - math.log(lo))
    return int(round(STEPS * u)), u, 0.60 + 0.30 * u, 0.22 + 0.55 * u


def pan_of(k: int, n: int) -> float:
    """Right to left across the dams, as the picture reads: the first dam on the right, the last on the left."""
    return 0.35 - 0.7 * k / (n - 1)


# ── sounds ──────────────────────────────────────────────────────────────────

def _tick() -> np.ndarray:
    """A soft tick: a band-passed click of 3 ms, with its own noise seed."""
    n = int(0.02 * SR)
    t = np.arange(n) / SR
    noise = np.random.default_rng(31).standard_normal(n)
    x = sosfilt(butter(2, (1500.0, 5000.0), "bandpass", fs=SR, output="sos"), noise) * np.exp(-t / 0.003)
    x = x * np.minimum(1.0, t / 0.0005)
    return x / np.abs(x).max()


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

def _compose(film, rec: list):
    """Lay the score on its buses. Returns (buses, the kick times, the groove's levels). rec receives one entry per
    checked event: (label, visual time, time of the hit, the sounds placed for it as (sound, gain, pan))."""
    kit.reseed(SEED)
    tm = timing(film)
    end = tm["end"]
    sh = shares()
    lo, hi = min(sh), max(sh)                                   # the reel's lowest and highest share
    bus = {k: kit.new_track(end, TAIL) for k in BUSES}
    kicks: list = []
    levels: list = []
    tick = _tick()
    kick = kit.kick808(KICK, vel=1.0, decay=0.9, drive=1.3)
    snare, hat = kit.snare(), kit.hat(False)
    bam = kit.daf("bam", pitch=kit.note_hz("C2"))
    tak = kit.daf("tak", pitch=kit.note_hz("G3"))
    n_dams = len(film_mod.ORDER)

    def event(label, t, items):
        """items: (bus name, sound, gain, pan). Placed at t, and logged for the check."""
        for name, sound, gain, pan in items:
            kit.place(bus[name], sound, t, gain, pan)
        rec.append((label, t, t, [(s, g, p) for _, s, g, p in items]))

    def pluck(k: int):
        step, _, vel, t60 = voice(sh[k], lo, hi)
        return kit.setar(kit.degree(MODE, step, 0, tonic_hz=PLUCK_TONIC), dur=1.2, vel=vel, t60=t60, bright=0.6,
                         buzz=0.0)

    def tone(step: int, octave: int, **kw):
        return kit.santur(kit.degree(MODE, step, octave, tonic_hz=HOOK_TONIC), **kw)

    def pad_of(pairs, **kw):
        return kit.pad([kit.degree(MODE, s, o, tonic_hz=HOOK_TONIC) for s, o in pairs], **kw)

    # bar 1, the hook: five notes in two bars on santur, C E G E D; the last note rings on
    for step, beat, length in HOOK:
        s = tone(step, 0, dur=length * BEAT + 1.6, vel=0.7, t60=2.2)
        event(f"hook step {step}", beat * BEAT, [("hook", s, 0.75, 0.0)])

    # the five lakes appear one by one: a soft tick each
    for k, t in enumerate(tm["lakes"]):
        event(f"lake {k}: appears", t, [("ticks", tick, 0.30, pan_of(k, n_dams))])

    # bars 2-6: one dam each, on its bar line: one pluck on its 1405 share
    for k in range(n_dams):
        pan = pan_of(k, n_dams)
        event(f"dam {k}: its bar, its pluck", tm["bars"][k], [("ticks", tick, 0.36, pan), ("pluck", pluck(k), 1.0, pan)])

    # the groove on each bar line from the first dam on: its level from the dam's share, the total's for bar 7
    for b0 in np.arange(tm["bars"][0], end - 1e-9, BAR):
        if b0 < tm["stack"]:
            k = min(int((b0 - tm["bars"][0]) // film_mod.SEG), n_dams - 1)
            share = sh[k]
        else:
            share = total_share()
        lvl = level_of(share)
        levels.append((float(b0), share, lvl))
        for t in ([b0] if lvl == "thin" else [b0, b0 + 1.25]):
            event(f"groove {b0:.0f} s: kick", t, [("kick", kick, 0.9, 0.0)])
            kicks.append(t)
        if lvl == "full":
            for j in range(8):
                kit.place(bus["drum"], hat, b0 + 0.25 * j, 0.12 if j % 2 == 0 else 0.07, 0.25 if j % 2 else -0.25)
            kit.place(bus["drum"], snare, b0 + 1.0, 0.5, 0.0)
            kit.place(bus["drum"], bam, b0, 0.5, 0.0)
        if lvl == "mid":
            for j in range(4):
                kit.place(bus["drum"], hat, b0 + 0.5 * j, 0.10, 0.25 if j % 2 else -0.25)
        if lvl in ("mid", "full"):
            kit.place(bus["sub"], kit.sub(SUB, dur=BAR + 0.03, vel=0.8), b0, 0.35)
            kit.place(bus["pad"], pad_of(PAD_CHORD, dur=BAR + 0.25, vel=0.3, width=0.9, cutoff=1800.0, attack=0.3,
                                         release=0.25), b0, 1.0)

    # bar 7: the total lands on an open chord, G and B, with an impact and a daf stroke (no tonic, no cadence)
    items = [("fx", kit.impact(2.2, vel=0.7, pitch=kit.note_hz("G1")), 0.9, 0.0), ("fx", tak, 0.6, 0.0)]
    items += [("fx", tone(s, o, dur=3.5, vel=0.5, t60=2.8), 0.9, 0.0) for s, o in END_CHORD]
    event(f"{tm['stack']:.0f} s: the total lands on G and B", tm["stack"], items)
    kit.place(bus["pad"], pad_of(END_CHORD, dur=end - tm["stack"], vel=0.22, width=0.9, cutoff=1500.0, attack=1.2,
                                 release=1.5), tm["stack"], 1.0)
    return bus, kicks, levels


# ── the mix ─────────────────────────────────────────────────────────────────

def _fit(x, n: int):
    """Crop or zero-pad x along time to n rows."""
    return x[:n] if len(x) >= n else np.concatenate([x, np.zeros((n - len(x),) + x.shape[1:])])


def mix_bus(bus: dict, kicks: list, n: int) -> np.ndarray:
    """The buses summed, the top octave cut. The hook and the pad are ducked under the kick and have a room; the
    plucks have a ping-pong echo; the ticks, the plucks and the accents are dry."""
    harm = kit.duck(kit.widen(bus["hook"], 0.3) + kit.widen(bus["pad"], 0.3), kicks, depth_db=3.0, release=0.15)
    wet = kit.reverb(harm, t60=1.8) * 0.25
    echo = kit.pingpong(bus["pluck"] * 0.5, delay=ECHO["delay"], feedback=ECHO["feedback"], taps=ECHO["taps"]) * 0.5
    mix = (bus["drum"] + bus["kick"] + harm + _fit(wet, n) + bus["sub"] + bus["fx"] + bus["ticks"]
           + bus["pluck"] + _fit(echo, n) + bus["intro"])
    return _air_cut(mix)


def render(film, log: list | None = None):
    """The mastered track (bass in mono), the mix before the master (for the verification), the groove's levels.
    The bass is made mono after the master: the limiter's gain changes would otherwise leave stereo below 120 Hz."""
    rec = [] if log is None else log
    bus, kicks, levels = _compose(film, rec)
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
    cut before the master, the first and the last 0.1 s, the groove and the pitch against the shares, the bass in
    mono, and the events' onsets."""
    x = _read_wav(wav)
    lufs, tp = kit.integrated_lufs(x), kit.true_peak_dbtp(x)
    dec = _decode(out)
    aac_lufs, aac_tp = kit.integrated_lufs(dec), kit.aac_true_peak(out)
    a_dur = [float(s["duration"]) for s in _probe(out)["streams"] if s["codec_type"] == "audio"][0]
    tm = timing(film)
    print(f"times from the film: lakes {[round(v, 2) for v in tm['lakes']]}, dam bars {tm['bars']}, "
          f"total bar {tm['stack']:.2f} s, end {tm['end']:.2f} s")
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

    print("\n(4) the groove against the dam on screen: the share of the average on each bar line")
    for b0, share, lvl in levels:
        print(f"    {b0:5.1f} s   {share:6.3f} of the average   {lvl}")
    print(f"    thin below {MID:.0%}, mid from {MID:.0%}, full from {FULL:.0%} of the average; the stack is "
          f"{total_share():.1%}")
    got = {round(b0): lvl for b0, _s, lvl in levels}
    # Mamlu 4-8 s, Lar 8-12, Latyan 12-16 thin; Taleqan 16-20 mid; Karaj 20-24 full; the total's bar 24-28 mid
    assert all(got[b] == "thin" for b in (4, 6, 8, 10, 12, 14)) and got[16] == "mid" and got[18] == "mid"
    assert got[20] == "full" and got[22] == "full" and got[24] == "mid" and got[26] == "mid", got

    print("\n(5) RMS per 1 s of the WAV (dBFS) against the share on screen (mean over the second)")
    rms = [_db(x[k * SR:(k + 1) * SR]) for k in range(int(len(x) / SR))]
    on = [float(curve[k * 1000:(k + 1) * 1000].mean()) for k in range(len(rms))]
    print("    s     " + " ".join(f"{k:>5d}" for k in range(len(rms))))
    print("    dB    " + " ".join(f"{v:>5.0f}" for v in rms))
    print("    share " + " ".join(f"{v:>5.2f}" for v in on))
    sh = shares()
    steps = np.array([voice(s, min(sh), max(sh))[0] for s in sh])
    r_step = float(np.corrcoef(np.log(sh), steps)[0, 1])
    print(f"    the five plucks: the pitch step against log(share) r = {r_step:.3f}; steps "
          f"{steps.tolist()} for shares {[round(s, 3) for s in sh]}")
    assert r_step >= 0.9, r_step

    print("\n(6) the bass in mono: the side against the mid in the spectrum of the WAV, below each frequency")
    marks = {f: _side_db(x, f) for f in (60.0, 90.0, 120.0)}
    print("    " + "   ".join(f"below {f:.0f} Hz {v:+.1f} dB" for f, v in marks.items()))
    assert marks[120.0] < -60, "the bass is not mono"

    print("\n(7) the events' onsets: each event's own sound (its first significant flux rise), and the same in the WAV")
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

    hp = butter(2, 12.0, "highpass", fs=SR, output="sos")          # the master's DC blocker
    lead = round(0.2 * SR)                                         # silence in front: the events at 0 s have a window
    mx = np.concatenate([np.zeros(lead), x.mean(axis=1)])
    u = np.concatenate([np.zeros(lead), sosfilt(hp, mm[:len(x)])])
    w1 = round(0.001 * SR) | 1
    gain = (uniform_filter1d(mx * u, w1, mode="nearest")
            / np.maximum(uniform_filter1d(u * u, w1, mode="nearest"), 1e-12))   # the master as a gain curve
    wav_off = []
    for label, visual, hit_t, items in log:
        a0 = round((hit_t - 0.1) * SR)
        a = a0 + lead
        b = a + round(0.4 * SR)
        ev = kit.new_track(0.4)
        for sound, g, pan in items:
            kit.place(ev, sound, (round(hit_t * SR) - a0) / SR, g, pan)
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
        if not label.startswith(("groove", "hook")):
            print(f"    {label:<60}{visual:10.3f}{o * 1000:+10.2f}{wv * 1000:+10.2f}")
    for group in ("groove", "hook"):
        idx = [i for i, e in enumerate(log) if e[0].startswith(group)]
        if idx:
            o_arr = np.array([own[i] for i in idx]) * 1000
            w_arr = np.array([wav_off[i] for i in idx]) * 1000
            print(f"    {group + ' events, n=' + str(len(idx)):<60} own sound: largest |{np.abs(o_arr).max():.2f}| ms; "
                  f"WAV: largest |{np.abs(w_arr).max():.2f}| ms")
    print(f"    all {len(log)} events: the sounds within {worst_own * 1000:.2f} ms, the WAV within "
          f"{worst_wav * 1000:.2f} ms (limit {MAX_OFFSET * 1000:.0f} ms): pass")

    print("\n    through the MP4's AAC audio, decoded (the accents: the strongest flux peak, offset in ms):")
    dtimes, drise = _flux(dec.mean(axis=1))
    worst_dec = 0.0
    for label, visual, hit_t, _items in log:
        if not label.startswith(("groove", "hook")) and visual > 0.1:
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
    film = film_mod.Tehran5Film(onebit.THEMES["kahgel"], COLOURS["kahgel"])
    base = onebit.OUT / "social" / BASE
    video = Path(f"{base}_reel.mp4")
    wav = Path(f"{base}_music.wav")
    out = Path(f"{base}_music_reel.mp4")
    if video.stat().st_mtime < Path(film_mod.__file__).stat().st_mtime:
        sys.exit(f"{video.name} is older than src/onebit_tehran5.py: render the film first "
                 f"(python -I src/onebit_tehran5.py), then run this score again")
    st = os.stat(video)
    before = (st.st_size, st.st_mtime_ns)
    end = float(film.starts[-1])
    curve = share_curve(film, end)
    log: list = []
    track, mix, levels = render(film, log)
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
