"""The light score of the winter NO2 reel (air_tehran_fa, 24 s): a sparse line of plucked notes in Mahur on D,
under the narration, timed to the film's own clock. Everything is synthesized here: no samples.

This is a different kind of music from the pad score (air_tehran_fa_voice): no sustained tone at all. Every sound
is a setar pluck that starts and decays (T60 2.5 s), with silence between the phrases. The music is light: the
music alone sits at -26 LUFS, and under the narration it is ducked a further 7 dB.

    the notes     one note per month of the dial: the 24 month ticks of the film (1.00 s, 1.77 s, ... 19.06 s, one
                  every 0.77 s), in short phrases of two to four notes, with a rest between the phrases and at the
                  turn (9.46-10.60 s). Mahur on D: D, E, F#, G, A, B, C#. The melody moves by thirds, fourths,
                  fifths and sixths, so every pair of notes that rings together is a consonant interval.
    the ending    A4 and E5 struck together at 20.60 s: an open fifth, not the tonic; it rings out with the master's fade.
    the timbre    setar, Karplus-Strong, bright 0.15 (a soft pick), low-passed warm at 1.6 kHz (sixth order);
                  notes alternate a little left and right (pan 0.2), the bass below 120 Hz is one channel.

Narration: the four cached segments of data/air/narration (read only, never written), placed on the film's clock
exactly as in onebit_score_air.py (NARRATION, the speech of each one starts at its start and ends inside its window).
The music is ducked DUCK_DB under the speech with an attack of DUCK_ATTACK and a release of DUCK_RELEASE. The voice
sits RATIO_TARGET dB above the ducked music in every segment; the mix is then mastered to -14.5 LUFS, and the
true peak is -1.5 dBTP in the WAV (-1 dBTP decoded).

Three files are written, each with its WAV (48 kHz, 16 bit):
    air_tehran_fa_light_reel.mp4       the voice and the light music
    air_tehran_fa_voiceonly_reel.mp4   the voice alone, at the same level as in the mix
    air_tehran_fa_lightmusic_reel.mp4  the light music alone, at -26 LUFS

The silent reel must be newer than src/onebit_air.py (render the film first, or pass --accept-stale-video). The silent
reel is not rewritten, and the existing outputs are never overwritten: the script stops if one of the six files exists.

The checks, on the files as delivered:
    (a) no sustained tone: every spectral peak within 10 dB of the music's loudest peak that rises (an onset) must
        fall 12 dB or more within 2.0 s of its onset (a re-struck note counts by its dips between strikes)
    (b) no beeping, by the onsets: (b1) at most 2 onsets in any 1 s; (b2) no run of 3 successive notes of one pitch
        at a constant interval shorter than 1.0 s; (b3) no two successive onsets closer than 0.35 s
    (c) the simultaneous intervals: every pair of notes that rings together (the earlier one within 24 dB of its peak
        at the later onset) is a unison, third, fourth, fifth, sixth or octave (mod 12 in 0, 3, 4, 5, 7, 8, 9)
    (d) the levels: music -26 LUFS; ducked 6-8 dB under the speech; voice over the ducked music at least 18 dB in every
        segment; mix -15 to -14 LUFS; true peak at most -1.5 dBTP (WAV) and -1 dBTP (decoded); most energy in
        300-1500 Hz; the 2-5 kHz level at least 20 dB under 100-800 Hz; every note in C4-C6
    and: the video packets identical to the silent master, the narration cached and on the film's clock.

    python -I src/onebit_score_air_light.py     writes the three reels and their WAVs, then runs the checks
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt, sosfiltfilt

sys.path.insert(0, str(Path(__file__).resolve().parent))

import onebit  # noqa: E402
import onebit_air  # noqa: E402
import onebit_persian as kit  # noqa: E402

SR = kit.SR
BASE = "air_tehran_fa"
TAIL = 3.0                                      # s of room past the end, for the echo of the master's fade
BASS = 120.0                                    # Hz: below this the two channels are one
AIR = 12000.0                                   # Hz: above this the mix has no content (the AAC overshoot)
END = 24.0                                      # s: the length of the reel
T60 = 2.5                                       # s: the ring of each note, 60 dB down (the rule: 1.2-3 s)
PLUCK_DUR = 4.0                                 # s: the pluck's synthesis length (about -96 dB at its end)
PLUCK_BRIGHT = 0.15                             # the setar's pick: soft
WARM = 1600.0                                   # Hz: the notes are low-passed here (sixth order)
WARM_SOS = butter(6, WARM, "lowpass", fs=SR, output="sos")
PAN = 0.2                                       # the notes alternate this far left and right
VEL_START, VEL_REST = 1.0, 0.85                 # the first note of a phrase, and the others
END_CHORD = (20.6, (69, 76), 0.8)               # s, (MIDI notes struck together), velocity: A4 and E5, an open fifth

# The melody. Each entry: (the month tick g of the dial, MIDI note, first note of a phrase). The 24 ticks are the film's
# own: g 0-11 is the first pass (Aban 1404 to Mehr 1405, 1.00-9.46 s), g 12-23 the second (10.60-19.06 s). Rests are
# the ticks with no note. The scale is Mahur on D (D E F# G A B C#). Pitches are MIDI: 69 is A4, 74 is D5.
MELODY = (
    (0, 74, True), (1, 69, False), (2, 66, False),                  # D5 A4 F#4
    (4, 69, True), (5, 74, False), (6, 78, False), (7, 74, False),  # A4 D5 F#5 D5
    (9, 71, True), (10, 67, False),                                 # B4 G4
    (13, 74, True), (14, 78, False), (15, 81, False), (16, 78, False),  # D5 F#5 A5 F#5
    (18, 76, True), (19, 71, False), (20, 67, False),               # E5 B4 G4
    (22, 69, True), (23, 74, False),                                # A4 D5
)
NOTE_RANGE = (60, 84)                           # MIDI: C4 to C6
ALLOWED_CLASSES = {0, 3, 4, 5, 7, 8, 9}         # unison, third, fourth, fifth, sixth (minor and major), octave
OVERLAP_DB = -24.0                              # dB: an earlier note this far down still counts as sounding together

# ── the narration (the cached segments, read only) ──────────────────────────
NARR_DIR = onebit.ROOT / "data" / "air" / "narration"
VOICE = "fa_IR-ganji-medium"
PAD = 0.03
DUCK_DB = 7.0                                   # dB: the music under the speech (the rule: 6-8 dB)
DUCK_ATTACK = 0.15                              # s: the music goes down over this time, ahead of the speech
DUCK_RELEASE = 0.40                             # s: the music comes back over this time after it
RATIO_TARGET = 19.5                             # dB: the voice over the ducked music, in the segment with the least
RATIO_MIN = 18.0                                # dB: the limit, in every segment, after the master
MUSIC_LUFS, MIX_LUFS = -26.0, -14.5
TP_WAV, TP_AAC = -1.5, -1.0                     # dBTP: the WAV and the decoded MP4
MASTER_TP = -2.0                                # dBTP: the master's ceiling (the limiter settles under it)
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


@dataclass(frozen=True)
class Note:
    t: float            # s: the onset
    midi: int
    vel: float
    pan: float


NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def midi_hz(m: int) -> float:
    return 440.0 * 2 ** ((m - 69) / 12)


def timing(film) -> dict:
    """The film's clock: the 24 month ticks, the turn and the hold, read from the film."""
    sch = film.schedule()
    ticks = [float(t) for t, _ in sch["ticks"]]
    assert len(ticks) == 2 * len(onebit_air.MONTHS), ticks
    assert all(a < b for a, b in zip(ticks, ticks[1:])), ticks
    assert float(sch["end"]) == END, sch["end"]
    return dict(ticks=ticks, end=END)


def score_notes(film) -> list:
    """The notes on the film's clock, the ending chord last. Each note is one month tick (or the ending)."""
    ticks = timing(film)["ticks"]
    notes, n = [], 0
    for g, m, start in MELODY:
        vel = VEL_START if start else VEL_REST
        pan = PAN if n % 2 == 0 else -PAN
        notes.append(Note(ticks[g], m, vel, pan))
        n += 1
    t_e, pitches, vel = END_CHORD
    for i, m in enumerate(pitches):
        notes.append(Note(t_e, m, vel, PAN if i == 0 else -PAN))
    return sorted(notes, key=lambda nt: nt.t)


def pluck(m: int, vel: float) -> np.ndarray:
    """One setar pluck on MIDI note m, mono, low-passed warm."""
    x = np.asarray(kit.setar(midi_hz(m), dur=PLUCK_DUR, vel=vel, t60=T60, bright=PLUCK_BRIGHT, buzz=0.0), float)
    return sosfilt(WARM_SOS, x)


def stem_raw(film) -> tuple:
    """The notes laid on their buses, before the master. Returns (the stereo stem, the notes)."""
    kit.reseed(41)
    notes = score_notes(film)
    track = kit.new_track(END, TAIL)
    for nt in notes:
        kit.place(track, pluck(nt.midi, nt.vel), nt.t, 1.0, nt.pan)
    return track, notes


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


# ── narration: the cached segments only ─────────────────────────────────────

def _cached(seg: dict):
    """The segment rendered before (same text, length scale, voice and duration jitter), or None. The segments in
    NARR_DIR are the source; this script reads them and never writes there."""
    try:
        man = {m["name"]: m for m in json.loads((NARR_DIR / "manifest.json").read_text(encoding="utf-8"))}
        m = man[seg["name"]]
        if (m["text"] != seg["text"] or m["length_scale"] != seg["length"] or m.get("voice") != VOICE
                or m.get("noise_w_scale", 0.0) != seg.get("noise", 0.0)):
            return None
        rate, pcm = wavfile.read(str(NARR_DIR / f"{seg['name']}.wav"))
        assert rate == SR and pcm.ndim == 1, (rate, pcm.shape)
        return pcm.astype(float) / 32767.0, m["lead"], m["speech"]
    except (OSError, KeyError, ValueError):
        return None


def narration_voice(n: int) -> tuple:
    """The voice on the film's clock (mono, before its level is set), and the speech spans (name, start, end)."""
    v = np.zeros(n)
    spans = []
    for seg in NARRATION:
        hit = _cached(seg)
        if hit is None:
            sys.exit(f"the cached segment {seg['name']} in {NARR_DIR} does not match NARRATION: the narration is not "
                     f"re-rendered by this script; re-render it with onebit_score_air.py first")
        y, lead, speech = hit
        assert seg["start"] + speech <= seg["end"], (seg["name"], speech)
        i0 = round((seg["start"] - lead) * SR)
        v[i0:i0 + len(y)] += y[:max(0, n - i0)]
        spans.append((seg["name"], seg["start"], seg["start"] + speech))
    return v, spans


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


def _highpass20(x):
    return sosfiltfilt(butter(2, 20.0, "highpass", fs=SR, output="sos"), x, axis=0)


def build(film) -> dict:
    """The three mixes: the music stem (-26 LUFS), the voice-and-music mix before its master, and the voice alone."""
    raw, notes = stem_raw(film)
    n = len(raw)
    stem = _bass_mono(_air_cut(raw))
    stem_m = kit.master(stem, lufs=MUSIC_LUFS, tp=MASTER_TP, seconds=END, fade_out=1.0)   # the music alone, -26 LUFS
    n = len(stem_m)                                 # the reel: END seconds, the tail is cut
    v, spans = narration_voice(n)
    mask = np.zeros(n, bool)
    core = np.zeros(n, bool)
    for _, a, b in spans:
        mask[round((a - DUCK_ATTACK) * SR):round(b * SR)] = True
        core[round(a * SR):round(b * SR)] = True
    music_d = stem_m * duck_gain(mask)[:, None]
    v = _highpass20(v)
    # one gain for the voice: the least of the segments' voice-over-music ratios sits at RATIO_TARGET
    mono_m = music_d.mean(axis=1)
    ratios = [10 * np.log10(np.mean(v[round(a * SR):round(b * SR)] ** 2)
                            / np.mean(mono_m[round(a * SR):round(b * SR)] ** 2)) for _, a, b in spans]
    v = v * 10 ** ((RATIO_TARGET - min(ratios)) / 20.0)
    voice = np.stack([v, v], axis=1)
    total = _highpass20(_air_cut(music_d + voice))
    mix = _bass_mono(kit.master(total, lufs=MIX_LUFS, tp=MASTER_TP, seconds=END, fade_out=1.0))
    g_eff = _mastered_gain(mix.mean(axis=1), total.mean(axis=1))
    voice_only_pre = voice * g_eff
    voice_only = kit.master(voice_only_pre, lufs=kit.integrated_lufs(voice_only_pre), tp=MASTER_TP,
                            seconds=END, fade_out=1.0)
    return dict(notes=notes, stem=stem_m, music_d=music_d, voice=voice, spans=spans, core=core, mask=mask,
                mix=mix, total=total, g_eff=g_eff, voice_only=voice_only, ratios=ratios)


def _mastered_gain(x_mean: np.ndarray, ref_mean: np.ndarray) -> float:
    """The one gain that takes the pre-master mix to the mastered one (the limiter aside)."""
    m = min(len(x_mean), len(ref_mean)) - SR                 # the last second is the fade
    return float(np.dot(x_mean[:m], ref_mean[:m]) / np.dot(ref_mean[:m], ref_mean[:m]))


# ── files ───────────────────────────────────────────────────────────────────

def write_wav(path, x) -> Path:
    """The 48 kHz, 16-bit WAV with one TPDF dither for both channels (seeded, so a re-run is identical)."""
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


def _md5(media, stream: str) -> str:
    return subprocess.run(["ffmpeg", "-v", "error", "-i", str(media), "-map", stream, "-c", "copy", "-f", "md5", "-"],
                          check=True, capture_output=True, text=True).stdout.strip()


def _file_md5(path) -> str:
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


# ── checks ──────────────────────────────────────────────────────────────────

def stft_db(x, win: float = 0.25, hop: float = 0.05, nfft: int = 2 ** 15):
    W, H = round(win * SR), round(hop * SR)
    starts = np.arange(0, len(x) - W, H)
    frames = x[starts[:, None] + np.arange(W)[None, :]] * np.hanning(W)
    db = 20 * np.log10(np.abs(np.fft.rfft(frames, n=nfft, axis=1)) + 1e-12)
    f = np.fft.rfftfreq(nfft, 1.0 / SR)
    return (starts + W / 2) / SR, f, db


def check_sustained(mono: np.ndarray) -> tuple:
    """(a): every rising spectral peak within 10 dB of the loudest one must fall 12 dB within 2.0 s of its onset.
    Returns (onsets tested, the smallest fall in dB, the number of sustained peaks)."""
    t, f, db = stft_db(mono)
    band = (f >= 80.0) & (f <= 2500.0)
    thr = db[:, band].max() - 10.0
    hop_s = t[1] - t[0]
    k_win, k_back = round(2.0 / hop_s), round(0.3 / hop_s)
    tested, falls = 0, []
    for k in range(len(t)):
        row = db[k]
        peaks = np.flatnonzero(band[:] & (row >= thr))
        peaks = [p for p in peaks if 0 < p < len(f) - 1 and row[p] >= row[p - 1] and row[p] >= row[p + 1]]
        for p in peaks:
            lvl = row[p]
            lo, hi = int(round(0.99 * f[p] / (f[1] - f[0]))), int(round(1.01 * f[p] / (f[1] - f[0]))) + 1
            if k >= k_back and db[k - k_back, lo:hi].max() >= lvl - 6.0:
                continue                                    # not a rise: the peak was already there
            seg = db[k:min(k + k_win, len(t) - 1) + 1, lo:hi].max(axis=1)
            tested += 1
            falls.append(float(lvl - seg.min()))
    falls = np.asarray(falls) if falls else np.array([np.inf])
    return tested, float(falls.min()), int((falls < 12.0).sum())


def am_depth(mono: np.ndarray) -> float:
    """(b): the 40 ms RMS envelope every 10 ms, in dB (floored 60 dB under its peak), band-passed 3-12 Hz; peak to
    peak in dB over 0.5-23.5 s."""
    w, h = round(0.040 * SR), round(0.010 * SR)
    starts = np.arange(0, len(mono) - w, h)
    fr = mono[starts[:, None] + np.arange(w)[None, :]]
    env = 10 * np.log10(np.mean(fr ** 2, axis=1) + 1e-12)
    env = np.maximum(env, env.max() - 60.0)
    t = (starts + w / 2) / SR
    sel = (t >= 0.5) & (t < 23.5)
    y = sosfiltfilt(butter(2, [3.0, 12.0], "bandpass", fs=1.0 / 0.010, output="sos"), env[sel])
    return float(y.max() - y.min())


def check_intervals(notes) -> tuple:
    """(c): every pair of notes that rings together, the earlier one within OVERLAP_DB of its peak at the later onset.
    Returns (pairs, the interval classes used, the violations)."""
    pairs, classes, bad = 0, set(), []
    for i, a in enumerate(notes):
        for b in notes[i + 1:]:
            dt = b.t - a.t
            level = 0.0 if dt <= 0 else -60.0 * dt / T60
            if level < OVERLAP_DB:
                continue
            cls = abs(a.midi - b.midi) % 12
            pairs += 1
            classes.add(cls)
            if cls not in ALLOWED_CLASSES:
                bad.append((a.t, a.midi, b.t, b.midi, cls))
    return pairs, sorted(classes), bad


def band_share(mono, lo: float, hi: float) -> float:
    p = np.abs(np.fft.rfft(mono)) ** 2
    f = np.fft.rfftfreq(len(mono), 1.0 / SR)
    return float(p[(f >= lo) & (f <= hi)].sum() / p.sum())


def check_video(video, out) -> str:
    v_md5, m_md5 = _md5(video, "0:v:0"), _md5(out, "0:v:0")
    assert v_md5 == m_md5, "the video stream changed"
    return v_md5


def output_paths(social: Path) -> dict:
    """The three WAVs and reels. Refuses to overwrite: the six paths must be new."""
    outs = {
        "light": (social / f"{BASE}_light.wav", social / f"{BASE}_light_reel.mp4"),
        "voiceonly": (social / f"{BASE}_voiceonly.wav", social / f"{BASE}_voiceonly_reel.mp4"),
        "lightmusic": (social / f"{BASE}_lightmusic.wav", social / f"{BASE}_lightmusic_reel.mp4"),
    }
    for wav, mp4 in outs.values():
        if wav.exists() or mp4.exists():
            sys.exit(f"{wav.name} or {mp4.name} exists: the outputs are never overwritten; move it first")
    return outs


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--video", type=Path, default=None, help="the silent reel (default: the film's)")
    ap.add_argument("--outdir", type=Path, default=None, help="where the WAVs and MP4s go (default: social/)")
    ap.add_argument("--accept-stale-video", action="store_true",
                    help="skip the check that the silent reel is newer than src/onebit_air.py (a preview)")
    args = ap.parse_args()

    film = onebit_air.AirFilm()
    social = args.outdir or onebit.OUT / "social"
    video = args.video or onebit.OUT / "social" / f"{BASE}_reel.mp4"
    if not args.accept_stale_video and video.stat().st_mtime < Path(onebit_air.__file__).stat().st_mtime:
        sys.exit(f"{video.name} is older than src/onebit_air.py: render the film first")
    outs = output_paths(social)
    narr_before = {p.name: _file_md5(p) for p in sorted(NARR_DIR.glob("*"))}
    st = os.stat(video)
    before = (st.st_size, st.st_mtime_ns)

    d = build(film)
    print("the notes (on the film's clock):")
    for nt in d["notes"]:
        print(f"    {nt.t:6.2f} s  {NAMES[nt.midi % 12]}{nt.midi // 12 - 1}  {midi_hz(nt.midi):7.2f} Hz")

    fails = []
    results = {}
    for key, mode in (("light", "voice+music"), ("voiceonly", "voice only"), ("lightmusic", "music only")):
        wav, mp4 = outs[key]
        x = {"light": d["mix"], "voiceonly": d["voice_only"], "lightmusic": d["stem"]}[key]
        write_wav(wav, x)
        kit.mux(video, wav, mp4)
        print(f"saved {wav}")
        print(f"saved {mp4}")
        results[key] = (wav, mp4, mode)

    print("\n(a) no sustained tone, the music alone (the WAV of the music-only reel)")
    music = _read_wav(outs["lightmusic"][0])
    tested, min_fall, sustained = check_sustained(music.mean(axis=1))
    print(f"    onsets tested {tested}; smallest fall within 2.0 s {min_fall:.1f} dB (limit 12); "
          f"sustained peaks {sustained}")
    if sustained or min_fall < 12.0:
        fails.append("(a) a sustained spectral peak")

    print("\n(b) no beeping: what makes an alarm beep is the onset pattern, not the decay of each note")
    on = sorted({nt.t for nt in d["notes"]})                      # the onsets of the stem (a chord is one onset)
    rate = max(sum(1 for u in on if s0 <= u < s0 + 1.0) for s0 in np.arange(0.0, END, 0.01))
    gaps = np.diff(on)
    b1_ok = rate <= 2
    print(f"    (b1) onsets per second, the most in any 1-s window: {rate} (limit 2)")
    print(f"    (b3) the closest successive onsets: {gaps.min():.3f} s (limit 0.35 s)")
    b2_worst = None
    by_pitch = {}
    for nt in d["notes"]:
        by_pitch.setdefault(nt.midi, []).append(nt.t)
    for m, ts in by_pitch.items():
        for a, b, c in zip(ts, ts[1:], ts[2:]):
            i1, i2 = b - a, c - b
            if abs(i1 - i2) <= 0.10 * max(i1, i2) and max(i1, i2) < 1.0:
                b2_worst = (m, a, c) if b2_worst is None else b2_worst
    print(f"    (b2) runs of 3 or more successive notes of one pitch at a constant interval shorter than 1.0 s: "
          f"{'none' if b2_worst is None else 'FOUND ' + str(b2_worst)} (limit none)")
    if not b1_ok:
        fails.append(f"(b1) {rate} onsets in one second")
    if gaps.min() < 0.35:
        fails.append(f"(b3) onsets {gaps.min():.3f} s apart")
    if b2_worst is not None:
        fails.append("(b2) a constant-interval run of three")
    print(f"    (info) the 3-12 Hz envelope depth of the earlier check, not a limit: "
          f"{am_depth(music.mean(axis=1)):.1f} dB")

    print("\n(c) the simultaneous intervals (mod 12 in 0, 3, 4, 5, 7, 8, 9)")
    pairs, classes, bad = check_intervals(d["notes"])
    print(f"    {pairs} pairs ring together (within {-OVERLAP_DB:.0f} dB at the later onset); intervals used {classes}; "
          f"violations {len(bad)}")
    if bad:
        fails.append("(c) a forbidden interval")
    lo_n, hi_n = NOTE_RANGE
    if not all(lo_n <= nt.midi <= hi_n for nt in d["notes"]):
        fails.append("register")

    print("\n(d) the levels")
    lufs_music = kit.integrated_lufs(music)
    tp_music = kit.true_peak_dbtp(music)
    mix = _read_wav(outs["light"][0])
    lufs_mix, tp_mix = kit.integrated_lufs(mix), kit.true_peak_dbtp(mix)
    vo = _read_wav(outs["voiceonly"][0])
    lufs_vo, tp_vo = kit.integrated_lufs(vo), kit.true_peak_dbtp(vo)
    print(f"    music alone (WAV)   {lufs_music:+.2f} LUFS (target -26)   {tp_music:+.2f} dBTP")
    print(f"    voice and music     {lufs_mix:+.2f} LUFS (target -15 to -14)   {tp_mix:+.2f} dBTP (WAV limit -1.5)")
    print(f"    voice alone         {lufs_vo:+.2f} LUFS   {tp_vo:+.2f} dBTP")
    if not -26.3 <= lufs_music <= -25.7:
        fails.append("music level")
    if not -15.0 <= lufs_mix <= -14.0:
        fails.append("mix level")
    if tp_mix > TP_WAV or tp_vo > TP_WAV or tp_music > TP_WAV:
        fails.append("WAV true peak")

    duck_db = [20 * np.log10(np.sqrt(np.mean(d["music_d"][round(a * SR):round(b * SR)] ** 2))
                             / np.sqrt(np.mean(d["stem"][round(a * SR):round(b * SR)] ** 2))) for _, a, b in d["spans"]]
    print(f"    the duck under each speech, the music ducked by {', '.join(f'{x:.1f}' for x in duck_db)} dB "
          f"(limit 6 to 8)")
    if not all(-8.0 <= x <= -6.0 for x in duck_db):
        fails.append("ducking depth")

    gm = d["g_eff"]
    v_m, m_m = d["voice"].mean(axis=1), d["music_d"].mean(axis=1)
    rat = []
    for name, a, b in d["spans"]:
        i0, i1 = round(a * SR), round(b * SR)
        rat.append(10 * np.log10(np.mean((gm * v_m[i0:i1]) ** 2) / np.mean((gm * m_m[i0:i1]) ** 2)))
    print("    voice over the ducked music, per segment: " + ", ".join(f"{nm} {r:+.1f}" for (nm, _, _), r in zip(d["spans"], rat))
          + f" dB (limit {RATIO_MIN:.0f})")
    if min(rat) < RATIO_MIN:
        fails.append("voice over music")

    share = band_share(music.mean(axis=1), 300.0, 1500.0)
    print(f"    the music's energy in 300-1500 Hz: {share:.0%} (limit 50%)")
    if share < 0.5:
        fails.append("energy band")
    harsh = 10 * np.log10(band_share(music.mean(axis=1), 2000.0, 5000.0) / band_share(music.mean(axis=1), 100.0, 800.0))
    print(f"    the music's 2-5 kHz against 100-800 Hz: {harsh:+.1f} dB (limit -20)")
    if harsh > -20.0:
        fails.append("harsh 2-5 kHz")

    print("\n(e) the picture and the narration")
    for key, (wav, mp4, mode) in results.items():
        dec = _decode(mp4)
        aac_l, aac_tp = kit.integrated_lufs(dec), kit.aac_true_peak(mp4)
        print(f"    {mp4.name}: decoded {aac_l:+.2f} LUFS, {aac_tp:+.2f} dBTP (limit -1)")
        if aac_tp > TP_AAC:
            fails.append(f"decoded true peak {key}")
        check_video(video, mp4)
    st2 = os.stat(video)
    assert before == (st2.st_size, st2.st_mtime_ns), "the silent reel was rewritten"
    print("    the video stream of all three MP4s is the silent master's (the same packets); the silent reel is untouched")
    narr_after = {p.name: _file_md5(p) for p in sorted(NARR_DIR.glob("*"))}
    assert narr_before == narr_after, "the narration directory changed"
    print("    the narration files are unchanged; each segment is on the film's clock:")
    for (name, a, b), seg in zip(d["spans"], NARRATION):
        print(f"      {name} speech {a:6.2f}-{b:6.2f} s (window {seg['start']:.2f}-{seg['end']:.2f} s)")
        if not (abs(a - seg["start"]) < 1e-9 and b <= seg["end"] + 1e-9):
            fails.append(f"narration timing {name}")

    print()
    if fails:
        print("CHECKS NOT PASSED: " + "; ".join(fails))
        sys.exit(1)
    print("all checks pass")


if __name__ == "__main__":
    main()
