"""The light score of the eight-winter Tehran and Istanbul NO2 film (compare8_tehran_istanbul_fa, 24 s): the light score
of the one-winter film (onebit_score_compare_light.py), on this film's own clock.

The engine and the checks are the light score's own (imported from onebit_score_air_light.py, not copied): a sparse line
of setar plucks that start and decay, no sustained tone, silence between the phrases, and the music ducked under the
speech. What changes here: the clock (read from onebit_compare8.py and asserted), the narration (five lines, synthesized
once in the offline voice and kept in data/air/compare/narration8/ with a manifest; the score re-synthesizes only a
segment whose text, length scale or voice changed), and the notes (soft plucks that may mark the bars of the strip).

    the key       Mahur on C: C D E F G A B.
    the notes     a soft C5 at 0.00 s, so frame 0 is not silent; a gentle note at each month switch (G4 at 1.55 s,
                  A4 at 3.80 s) and C5 at 2.30 s; soft marks at the strip's bars (C5 at 4.50, 5.90, 7.30 and 14.30 s,
                  G4 at 8.70 s, D5 at 11.50 s; the bars at 10.10 s and 12.90 s are not marked, because a mark there
                  would make three onsets in one second or sit a semitone from a note that rings); a second pass in
                  short phrases with rests (9.60-10.50 s, 13.00-13.80 s); a rising phrase into the hold (C4, E4, G4), the
                  hold's C5 at T_HOLD = 17.0 s; then G5 and E5 (18.40, 19.20 s) and the ending, C4 and G4 struck together
                  at 20.60 s, which rings out before the 24.0 s end. Every pair of notes that rings together is a unison,
                  third, fourth, fifth, sixth or octave (checked).
    the timbre    setar, Karplus-Strong, bright 0.15, T60 2.5 s, low-passed warm at 1.6 kHz; the notes alternate a little
                  left and right; the bass below 120 Hz is one channel.
    the duck      the music is ducked 7 dB from 0.6 s before each speech to its end, so it is down when the voice starts.

The narration (the offline voice, ganji, length scale 0.9; shorter words rather than a faster voice):
    N1 0.20-5.50 s   N2 5.50-10.20 s   N3 10.20-14.20 s   N4 17.00-19.70 s   N5 19.90-24.00 s
A line whose speech does not end inside its window stops the script; it is then shortened, not sped up.

Three files are written, each with its WAV (48 kHz, 16 bit):
    compare8_tehran_istanbul_fa_light_reel.mp4       the voice and the light music
    compare8_tehran_istanbul_fa_voiceonly_reel.mp4   the voice alone, at the same level as in the mix
    compare8_tehran_istanbul_fa_lightmusic_reel.mp4  the light music alone, at -26 LUFS

The silent reel (outputs/onebit/social/compare8_tehran_istanbul_fa_reel.mp4) must be newer than src/onebit_compare8.py
(or pass --accept-stale-video for a preview). It is not rewritten. Existing outputs are never overwritten: the script
stops if one of the six files exists.

    python -I src/onebit_score_compare8_light.py     synthesizes the missing narration, writes the three reels and
                                                     their WAVs, then runs the checks
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
from fractions import Fraction
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

sys.path.insert(0, str(Path(__file__).resolve().parent))

import onebit  # noqa: E402
import onebit_compare8 as film  # noqa: E402
import onebit_persian as kit  # noqa: E402
import onebit_score_air_light as light  # noqa: E402

SR = kit.SR
BASE = "compare8_tehran_istanbul_fa"
END = 24.0                                          # s: the length of the reel
TAIL = light.TAIL
MUSIC_LUFS, MIX_LUFS = -26.0, -14.5
TP_WAV, TP_AAC = -1.5, -1.0
MASTER_TP = -2.0
RATIO_MIN = light.RATIO_MIN                         # dB: the voice over the ducked music, in every segment
NARR_DIR = onebit.ROOT / "data" / "air" / "compare" / "narration8"
TTS_ENV_BIN, TTS_ENV_MODEL = "ONEBIT_TTS_BIN", "ONEBIT_TTS_MODEL"   # the offline engine and the voice file, from the
                                                                  # environment (no local paths in the repo)
VOICE = "fa_IR-ganji-medium"
PAD = 0.03                                          # s of silence kept before each speech
LENGTH_SCALE = 0.90                                 # the voice's length scale (not below 0.88: shorter words, not speed)
DUCK_LEAD = 0.6                                     # s: the music is ducked this long before each speech
VEL_SOFT, VEL, VEL_HOLD, VEL_MARK = 0.55, 0.80, 0.90, 0.42
NARRATION = (
    dict(name="n1", start=0.20, end=5.50, length=LENGTH_SCALE, noise=0.0,
         text="هشت زمستان از فضا: دی‌اکسیدِ نیتروژنِ کدام شهر بیشتر است؟"),
    dict(name="n2", start=5.50, end=10.20, length=LENGTH_SCALE, noise=0.0,
         text="رنگِ نارنجی یعنی دی‌اکسیدِ نیتروژن."),
    dict(name="n3", start=10.20, end=14.20, length=LENGTH_SCALE, noise=0.0,
         text="در هر هشت زمستان، تهران بیشتر بود."),
    dict(name="n4", start=17.00, end=19.70, length=LENGTH_SCALE, noise=0.0,
         text="میانگین، تقریباً شش برابر."),
    dict(name="n5", start=19.90, end=24.00, length=LENGTH_SCALE, noise=0.0,
         text="دلیلِ احتمالی: وارونگیِ زمستان. شما چه فکر می‌کنید؟"),
)
BAR_MARKS = ((4.50, 72), (5.90, 72), (7.30, 72), (8.70, 67), (11.50, 74), (14.30, 72))   # (s, MIDI): soft, optional


# ── the film's clock, read from onebit_compare8.py and asserted ─────────────

def clock() -> dict:
    """The film's clock as this score was written for it. A change in onebit_compare8.py that moves it fails here."""
    assert abs(film.DURATION - END) < 1e-9, film.DURATION
    assert abs(film.STEP_A[0] - 0.8) < 1e-9 and abs(film.STEP_A[1] - 2.3) < 1e-9, film.STEP_A
    assert abs(film.STEP_B[0] - 2.8) < 1e-9 and abs(film.STEP_B[1] - 4.8) < 1e-9, film.STEP_B
    assert len(film.WORD_SWITCH) == 2 and all(abs(a - b) < 1e-9 for a, b in zip(film.WORD_SWITCH, (1.55, 3.8))), \
        film.WORD_SWITCH
    assert abs(film.T_HOLD - 17.0) < 1e-9, film.T_HOLD
    bars = tuple(float(t) for t in film.BAR_TIMES)
    assert len(bars) == 8 and abs(bars[0] - 4.5) < 1e-9 and abs(bars[-1] - 14.3) < 1e-9, bars
    for t, _ in BAR_MARKS:
        assert any(abs(t - b) < 1e-9 for b in bars), ("a mark is not on a bar", t)
    for seg in NARRATION:
        assert 0.0 <= seg["start"] < seg["end"] <= END and seg["length"] >= 0.88, seg["name"]
    return dict(sw1=float(film.WORD_SWITCH[0]), sw2=float(film.WORD_SWITCH[1]), hold=float(film.T_HOLD), end=END)


# ── the notes (MIDI: 60 is C4, 72 is C5; C Mahur) ───────────────────────────

def score_notes() -> list:
    """Every note on the film's clock, sorted. The ending is two notes at one onset."""
    c = clock()
    plan = (
        (0.00, 72, VEL_SOFT),                       # C5: soft, the first sound (frame 0 is not silent)
        (c["sw1"], 67, VEL),                        # G4: the first month switch
        (2.30, 72, VEL),                            # C5
        (c["sw2"], 69, VEL),                        # A4: the second month switch
        (9.60, 74, VEL),                            # D5: the second pass, a short phrase
        (10.50, 67, VEL),                           # G4
        (13.00, 76, VEL),                           # E5
        (13.80, 79, VEL),                           # G5
        (15.00, 60, 0.70),                          # C4: the rising phrase into the hold
        (15.50, 64, 0.75),                          # E4
        (16.00, 67, VEL),                           # G4
        (c["hold"], 72, VEL_HOLD),                  # C5: the hold, 17.0 s
        (18.40, 79, 0.75),                          # G5
        (19.20, 76, 0.70),                          # E5
        (20.60, 60, VEL),                           # C4: the ending, an open fifth on the tonic
        (20.60, 67, VEL),                           # G4
    )
    marks = [(t, m, VEL_MARK) for t, m in BAR_MARKS]
    allnotes = sorted(list(plan) + marks, key=lambda p: p[0])
    notes = []
    for i, (t, m, vel) in enumerate(allnotes):
        notes.append(light.Note(float(t), m, vel, light.PAN if i % 2 == 0 else -light.PAN))
    assert all(0.0 <= nt.t < END - 3.0 for nt in notes[-2:]), "the ending must ring out before the end"
    assert notes[-1].t > c["hold"], "the ending follows the hold"
    return sorted(notes, key=lambda nt: nt.t)


def stem_raw(notes) -> np.ndarray:
    kit.reseed(41)
    track = kit.new_track(END, TAIL)
    for nt in notes:
        kit.place(track, light.pluck(nt.midi, nt.vel), nt.t, 1.0, nt.pan)
    return track


# ── the narration: synthesized once, then read from its folder ──────────────

def _cached(seg: dict):
    """The segment rendered before (same text, length scale and voice), or None."""
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


def synth_segment(seg: dict, binary: str, model: str) -> tuple:
    """One segment: the offline voice, cut to its speech (PAD kept before it), resampled to SR, mono, peak 0.9.
    Returns (samples, lead, speech). Raises if the speech does not end inside the segment's window."""
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "raw.wav"
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
    assert seg["start"] + speech <= seg["end"], (seg["name"], round(speech, 3), seg["end"] - seg["start"])
    return y, lead, speech


def ensure_narration() -> None:
    """Synthesize the segments whose cached copy does not match NARRATION (needs the offline voice from the
    environment). A segment that matches is kept as it is."""
    if all(_cached(seg) is not None for seg in NARRATION):
        return
    binary, model = os.environ.get(TTS_ENV_BIN), os.environ.get(TTS_ENV_MODEL)
    if not binary or not model:
        sys.exit(f"the narration needs the offline voice: set {TTS_ENV_BIN} and {TTS_ENV_MODEL} (the {VOICE} voice "
                 f"file), or provide the segments in {NARR_DIR}")
    assert Path(model).name.startswith(VOICE), (model, VOICE)
    NARR_DIR.mkdir(parents=True, exist_ok=True)
    old = {m["name"]: m for m in json.loads((NARR_DIR / "manifest.json").read_text(encoding="utf-8"))} \
        if (NARR_DIR / "manifest.json").exists() else {}
    manifest = []
    for seg in NARRATION:
        if _cached(seg) is not None:                # a segment that matches its text is kept as it is
            manifest.append(old[seg["name"]])
            continue
        y, lead, speech = synth_segment(seg, binary, model)
        wavfile.write(str(NARR_DIR / f"{seg['name']}.wav"), SR, (np.clip(y, -1, 1) * 32767).astype(np.int16))
        manifest.append(dict(name=seg["name"], start=seg["start"], speech=round(speech, 4), lead=round(lead, 4),
                             length_scale=seg["length"], noise_w_scale=seg.get("noise", 0.0), voice=VOICE,
                             text=seg["text"]))
        print(f"    synthesized {seg['name']}: speech {speech:.2f} s in the window {seg['start']:.2f}-{seg['end']:.2f} s")
    (NARR_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def narration_voice(n: int) -> tuple:
    v = np.zeros(n)
    spans = []
    for seg in NARRATION:
        hit = _cached(seg)
        if hit is None:
            sys.exit(f"the segment {seg['name']} in {NARR_DIR} does not match NARRATION")
        y, lead, speech = hit
        assert seg["start"] + speech <= seg["end"], (seg["name"], speech)
        i0 = round((seg["start"] - lead) * SR)
        v[i0:i0 + len(y)] += y[:max(0, n - i0)]
        spans.append((seg["name"], seg["start"], seg["start"] + speech))
    return v, spans


def duck_gain(mask: np.ndarray) -> np.ndarray:
    return light.duck_gain(mask)


def build(notes) -> dict:
    """The stem (music alone, -26 LUFS), the ducked music, the voice, and the mixes, as in the light score."""
    raw = stem_raw(notes)
    k = round(0.025 * SR)                               # a 25-ms raised-cosine fade-in: no click at the first sample
    w = 0.5 - 0.5 * np.cos(np.linspace(0.0, np.pi, k))
    raw[:k] *= w.reshape(-1, *([1] * (raw.ndim - 1)))
    stem = light._bass_mono(light._air_cut(raw))
    stem_m = kit.master(stem, lufs=MUSIC_LUFS, tp=MASTER_TP, seconds=END, fade_out=1.0)
    n = len(stem_m)
    v, spans = narration_voice(n)
    mask = np.zeros(n, bool)
    core = np.zeros(n, bool)
    for _, a, b in spans:
        mask[max(0, round((a - DUCK_LEAD) * SR)):round(b * SR)] = True
        core[round(a * SR):round(b * SR)] = True
    music_d = stem_m * duck_gain(mask)[:, None]
    v = light._highpass20(v)
    mono_m = music_d.mean(axis=1)
    ratios = [10 * np.log10(np.mean(v[round(a * SR):round(b * SR)] ** 2)
                            / np.mean(mono_m[round(a * SR):round(b * SR)] ** 2)) for _, a, b in spans]
    v = v * 10 ** ((light.RATIO_TARGET - min(ratios)) / 20.0)
    voice = np.stack([v, v], axis=1)
    total = light._highpass20(light._air_cut(music_d + voice))
    mix = light._bass_mono(kit.master(total, lufs=MIX_LUFS, tp=MASTER_TP, seconds=END, fade_out=1.0))
    g_eff = light._mastered_gain(mix.mean(axis=1), total.mean(axis=1))
    voice_only_pre = voice * g_eff
    voice_only = kit.master(voice_only_pre, lufs=kit.integrated_lufs(voice_only_pre), tp=MASTER_TP,
                            seconds=END, fade_out=1.0)
    return dict(stem=stem_m, music_d=music_d, voice=voice, spans=spans, core=core, mask=mask,
                mix=mix, total=total, g_eff=g_eff, voice_only=voice_only, ratios=ratios)


# ── files ───────────────────────────────────────────────────────────────────

def output_paths(social: Path) -> dict:
    outs = {
        "light": (social / f"{BASE}_light.wav", social / f"{BASE}_light_reel.mp4"),
        "voiceonly": (social / f"{BASE}_voiceonly.wav", social / f"{BASE}_voiceonly_reel.mp4"),
        "lightmusic": (social / f"{BASE}_lightmusic.wav", social / f"{BASE}_lightmusic_reel.mp4"),
    }
    for wav, mp4 in outs.values():
        if wav.exists() or mp4.exists():
            sys.exit(f"{wav.name} or {mp4.name} exists: the outputs are never overwritten; move it first")
    return outs


def _file_md5(path) -> str:
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--video", type=Path, default=None, help="the silent reel (default: the film's)")
    ap.add_argument("--outdir", type=Path, default=None, help="where the WAVs and MP4s go (default: social/)")
    ap.add_argument("--accept-stale-video", action="store_true",
                    help="skip the check that the silent reel is newer than src/onebit_compare8.py (a preview)")
    args = ap.parse_args()

    clock()
    social = args.outdir or onebit.OUT / "social"
    video = args.video or onebit.OUT / "social" / f"{BASE}_reel.mp4"
    if not args.accept_stale_video and video.stat().st_mtime < Path(film.__file__).stat().st_mtime:
        sys.exit(f"{video.name} is older than src/onebit_compare8.py: render the film first")
    outs = output_paths(social)
    print("the narration (cache or synthesis):")
    ensure_narration()
    narr_before = {p.name: _file_md5(p) for p in sorted(NARR_DIR.glob("*"))}
    st = os.stat(video)
    before = (st.st_size, st.st_mtime_ns)

    notes = score_notes()
    d = build(notes)
    print("the notes (on the film's clock):")
    for nt in notes:
        print(f"    {nt.t:6.2f} s  {light.NAMES[nt.midi % 12]}{nt.midi // 12 - 1}  {light.midi_hz(nt.midi):7.2f} Hz")

    fails = []
    results = {}
    for key, mode in (("light", "voice+music"), ("voiceonly", "voice only"), ("lightmusic", "music only")):
        wav, mp4 = outs[key]
        x = {"light": d["mix"], "voiceonly": d["voice_only"], "lightmusic": d["stem"]}[key]
        light.write_wav(wav, x)
        kit.mux(video, wav, mp4)
        print(f"saved {wav}")
        print(f"saved {mp4}")
        results[key] = (wav, mp4, mode)

    print("\n(a) no sustained tone, the music alone (the WAV of the music-only reel)")
    music = light._read_wav(outs["lightmusic"][0])
    tested, min_fall, sustained = light.check_sustained(music.mean(axis=1))
    print(f"    onsets tested {tested}; smallest fall within 2.0 s {min_fall:.1f} dB (limit 12); "
          f"sustained peaks {sustained}")
    if sustained or min_fall < 12.0:
        fails.append("(a) a sustained spectral peak")

    print("\n(b) no beeping: the onset pattern, not the decay of each note")
    on = sorted({nt.t for nt in notes})
    rate = max(sum(1 for u in on if s0 <= u < s0 + 1.0) for s0 in np.arange(0.0, END, 0.01))
    gaps = np.diff(on)
    print(f"    (b1) onsets per second, the most in any 1-s window: {rate} (limit 2)")
    print(f"    (b3) the closest successive onsets: {gaps.min():.3f} s (limit 0.35 s)")
    b2_worst = None
    by_pitch = {}
    for nt in notes:
        by_pitch.setdefault(nt.midi, []).append(nt.t)
    for m, ts in by_pitch.items():
        for a, b, c in zip(ts, ts[1:], ts[2:]):
            i1, i2 = b - a, c - b
            if abs(i1 - i2) <= 0.10 * max(i1, i2) and max(i1, i2) < 1.0:
                b2_worst = (m, a, c) if b2_worst is None else b2_worst
    print(f"    (b2) runs of 3 or more successive notes of one pitch at a constant interval shorter than 1.0 s: "
          f"{'none' if b2_worst is None else 'FOUND ' + str(b2_worst)} (limit none)")
    if rate > 2:
        fails.append(f"(b1) {rate} onsets in one second")
    if gaps.min() < 0.35:
        fails.append(f"(b3) onsets {gaps.min():.3f} s apart")
    if b2_worst is not None:
        fails.append("(b2) a constant-interval run of three")
    print(f"    (info) the 3-12 Hz envelope depth, not a limit: {light.am_depth(music.mean(axis=1)):.1f} dB")

    print("\n(c) the simultaneous intervals (mod 12 in 0, 3, 4, 5, 7, 8, 9)")
    pairs, classes, bad = light.check_intervals(notes)
    print(f"    {pairs} pairs ring together (within {-light.OVERLAP_DB:.0f} dB at the later onset); intervals used "
          f"{classes}; violations {len(bad)}")
    if bad:
        fails.append("(c) a forbidden interval")
    lo_n, hi_n = light.NOTE_RANGE
    if not all(lo_n <= nt.midi <= hi_n for nt in notes):
        fails.append("register")

    print("\n(d) the levels")
    lufs_music = kit.integrated_lufs(music)
    tp_music = kit.true_peak_dbtp(music)
    mix = light._read_wav(outs["light"][0])
    lufs_mix, tp_mix = kit.integrated_lufs(mix), kit.true_peak_dbtp(mix)
    vo = light._read_wav(outs["voiceonly"][0])
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
                             / np.sqrt(np.mean(d["stem"][round(a * SR):round(b * SR)] ** 2)))
               for _, a, b in d["spans"]]
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
    print("    voice over the ducked music, per segment: "
          + ", ".join(f"{nm} {r:+.1f}" for (nm, _, _), r in zip(d["spans"], rat)) + f" dB (limit {RATIO_MIN:.0f})")
    if min(rat) < RATIO_MIN:
        fails.append("voice over music")

    share = light.band_share(music.mean(axis=1), 300.0, 1500.0)
    print(f"    the music's energy in 300-1500 Hz: {share:.0%} (limit 50%)")
    if share < 0.5:
        fails.append("energy band")
    harsh = 10 * np.log10(light.band_share(music.mean(axis=1), 2000.0, 5000.0)
                          / light.band_share(music.mean(axis=1), 100.0, 800.0))
    print(f"    the music's 2-5 kHz against 100-800 Hz: {harsh:+.1f} dB (limit -20)")
    if harsh > -20.0:
        fails.append("harsh 2-5 kHz")

    print("\n(e) the picture and the narration")
    v_md5 = light._md5(video, "0:v:0")
    for key, (wav, mp4, mode) in results.items():
        dec = light._decode(mp4)
        aac_l, aac_tp = kit.integrated_lufs(dec), kit.aac_true_peak(mp4)
        print(f"    {mp4.name}: decoded {aac_l:+.2f} LUFS, {aac_tp:+.2f} dBTP (limit -1)")
        if aac_tp > TP_AAC:
            fails.append(f"decoded true peak {key}")
        if v_md5 != light._md5(mp4, "0:v:0"):
            fails.append(f"the video stream of {mp4.name} changed")
    print("    the video stream of all three MP4s is the silent master's (the same packets)")
    st2 = os.stat(video)
    if before != (st2.st_size, st2.st_mtime_ns):
        fails.append("the silent reel was rewritten")
    narr_after = {p.name: _file_md5(p) for p in sorted(NARR_DIR.glob("*"))}
    if narr_before != narr_after:
        fails.append("the narration directory changed")
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
