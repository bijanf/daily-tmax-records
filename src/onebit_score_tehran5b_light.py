"""The light score of the Tehran dams follow-up (tehran5b_fa, 25 s): the light score's engine and checks
(onebit_score_air_light.py, imported, not copied), on the clock of onebit_tehran5b.py.

    the key       Chahargah on C. The interval checks accept the C scale (C D E F G A B), so the notes are the C scale
                  in 12-tone equal temperament: the koron steps of Chahargah (D and A) are played as D and A here,
                  not as quarter-tones. The mode's name is the choice; the sound is the scale's.
    the notes     a soft G4-C5 pair of plucks: the first sound at 0.00 s (soft, so frame 0 is not silent), then sparse
                  plucks on the film's beats: four in the hook and the first bar, the three bars of 1,930 and 340 (4.4-9.2 s),
                  the three columns (9.9-12.7 s), the rain bar (15.4 s), the rising phrase into the answer (20.5-23.1 s),
                  and the ending, C4 and G4 struck together 0.12 s after the last speech ends (ENDING_T, 24.15 s).
                  Every pair of notes that rings together (within 24 dB at the later onset) is a unison, third, fourth,
                  fifth, sixth or octave (checked).
    the timbre    setar, Karplus-Strong, bright 0.15, T60 2.5 s, low-passed warm at 1.6 kHz; the notes alternate a
                  little left and right; the bass below 120 Hz is one channel.
    the duck      the music is ducked 7 dB from 0.6 s before each speech to its end, so it is down when the voice starts.

The narration (the offline voice, ganji, length scale 0.88-0.94: shorter words, never a faster voice), in the window of
each scene of the film:
    N1 0.10-3.90 s   N2 4.10-9.40 s   N3 9.60-14.90 s   N4 15.10-19.90 s   N5 20.10-24.40 s
The take of each segment is the one faster-whisper 'medium' transcribes closest to its text (chosen once, cached in
data/air/tehran5b/narration with a manifest; a segment whose text, length scale or voice differs is synthesized again).

Three files are written, each with its WAV (48 kHz, 16 bit):
    tehran5b_fa_light_reel.mp4        the voice and the light music
    tehran5b_fa_voiceonly_reel.mp4    the voice alone, at the same level as in the mix
    tehran5b_fa_lightmusic_reel.mp4   the light music alone, at -26 LUFS

The silent master (outputs/onebit/social/tehran5b_fa_reel.mp4) must be newer than src/onebit_tehran5b.py (or pass
--accept-stale-video for a preview). It is not rewritten. Existing outputs are never overwritten.

    python -I src/onebit_score_tehran5b_light.py     writes the three reels and their WAVs, then runs the checks
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, str(Path(__file__).resolve().parent))

import onebit  # noqa: E402
import onebit_persian as kit  # noqa: E402
import onebit_score_air_light as light  # noqa: E402
import onebit_score_compare8_light as seven  # noqa: E402  (the synthesis of one narration segment, shared)
import onebit_tehran5b as film  # noqa: E402

SR = kit.SR
BASE = "tehran5b_fa"
END = 25.0                                          # s: the length of the reel (the film's clock)
TAIL = light.TAIL
MUSIC_LUFS, MIX_LUFS = -26.0, -14.5
TP_WAV, TP_AAC = -1.5, -1.0
MASTER_TP = -2.0
RATIO_MIN = light.RATIO_MIN                         # dB: the voice over the ducked music, in every segment
NARR_DIR = onebit.ROOT / "data" / "air" / "tehran5b" / "narration"
TTS_ENV_BIN, TTS_ENV_MODEL = "ONEBIT_TTS_BIN", "ONEBIT_TTS_MODEL"
VOICE = "fa_IR-ganji-medium"
PAD = 0.03                                          # s of silence kept before each speech
DUCK_LEAD = 0.6                                     # s: the music is ducked this long before each speech
VEL_SOFT, VEL, VEL_HOLD, VEL_MARK = 0.55, 0.80, 0.90, 0.42
ENDING_T = 24.15                                    # s: the ending chord, 0.12 s after N5's speech ends (24.03 s, measured; a later one would ring past the end)
CSCALE = {0, 2, 4, 5, 7, 9, 11}                     # pitch classes of the C scale (Chahargah on C, 12-TET)
NARRATION = (
    dict(name="n1", start=0.10, end=3.90, length=0.92, noise=0.0,
         text="با این باران‌ها، سدهای تهران پر می‌شوند؟"),
    dict(name="n2", start=4.10, end=9.40, length=0.94, noise=0.0,
         text="تا شانزده آبان، پنج سد حدودِ هجده درصد پُر است."),
    dict(name="n3", start=9.60, end=14.90, length=0.94, noise=0.0,
         text="سالِ آبی با حدودِ چهارصد و پنجاه شروع شد؛ حالا سیصد و چهل."),
    dict(name="n4", start=15.10, end=19.90, length=0.88, noise=0.0,
         text="باران تا نیمه‌ی آبان، شانزده میلی‌متر؛ کمتر از نصفِ معمول."),
    dict(name="n5", start=20.10, end=24.40, length=0.92, noise=0.0,
         text="چند روز باران پرشان نمی‌کند. برفِ البرز به میانگین می‌رسد؟"),
)
# the plan: (s, MIDI, velocity). Sounded as written (C scale). Soft notes (VEL_MARK) on the film's bars.
PLAN = (
    (0.00, 72, VEL_SOFT), (1.10, 74, VEL), (2.20, 79, VEL), (3.30, 74, VEL),
    (4.40, 76, VEL_MARK), (5.40, 69, VEL_MARK), (6.60, 64, VEL), (7.90, 62, VEL), (9.20, 65, VEL_MARK),
    (9.90, 72, VEL_MARK), (11.30, 74, VEL_MARK), (12.70, 69, VEL_MARK), (14.00, 74, VEL),
    (15.40, 71, VEL_MARK), (16.60, 74, VEL), (17.80, 72, VEL), (19.00, 74, VEL),
    (20.50, 81, 0.70), (21.40, 77, 0.75), (22.30, 72, VEL_HOLD), (23.10, 77, 0.75), (23.70, 72, 0.70),
)
ENDING = ((ENDING_T, 60, VEL), (ENDING_T, 67, VEL))  # C4 and G4 struck together: an open fifth on the tonic


# ── the film's clock, read from onebit_tehran5b.py and asserted ───────────

def clock() -> dict:
    """The film's clock as this score was written for it. A change in onebit_tehran5b.py that moves it fails here."""
    beat = 60 / film.PACE["bpm"]
    starts = np.cumsum([0.0] + [b * 4 * beat for b in film.PACE["bars"]])
    assert np.allclose(starts, [0.0, 4.0, 9.5, 15.0, 20.0, 25.0]), starts
    assert np.allclose(starts, film.STARTS), (starts, film.STARTS)
    scene_of = {"n1": 0, "n2": 1, "n3": 2, "n4": 3, "n5": 4}
    for seg in NARRATION:
        assert 0.0 <= seg["start"] < seg["end"] <= END and seg["length"] >= 0.88, seg["name"]
        i = scene_of[seg["name"]]
        assert seg["start"] >= starts[i] - 1e-9 and seg["end"] <= starts[i + 1] + 1e-9, seg["name"]
    assert NARRATION[-1]["end"] <= END - 0.6, "N5 must end at least 0.6 s before the end"
    for t, _, _ in PLAN:
        assert 0.0 <= t < END - 0.8, ("a plan note rings out too late", t)
    return dict(starts=tuple(float(s) for s in starts), end=END)


# ── the notes ──

def score_notes() -> list:
    """Every note on the film's clock, sorted. The ending is two notes at one onset."""
    clock()
    allnotes = [(t, m, v) for t, m, v in PLAN] + [(t, m, v) for t, m, v in ENDING]
    notes = []
    for i, (t, m, vel) in enumerate(sorted(allnotes, key=lambda p: p[0])):
        notes.append(light.Note(float(t), int(m), float(vel), light.PAN if i % 2 == 0 else -light.PAN))
    assert all(m % 12 in CSCALE for _, m, _ in allnotes), "every note is on the C scale"
    assert ENDING_T >= 24.03 + 0.05, "the ending follows N5 (its speech ends at 24.03 s, measured)"
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


def ensure_narration() -> None:
    """Synthesize the segments whose cached copy does not match NARRATION (needs the offline voice)."""
    missing = [seg for seg in NARRATION if _cached(seg) is None]
    if not missing:
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
        if _cached(seg) is not None:
            manifest.append(old[seg["name"]])
            continue
        y, lead, speech = seven.synth_segment(seg, binary, model)
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
    for _, a, b in spans:
        mask[max(0, round((a - DUCK_LEAD) * SR)):round(b * SR)] = True
    music_d = stem_m * light.duck_gain(mask)[:, None]
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
    return dict(stem=stem_m, music_d=music_d, voice=voice, spans=spans, core=None, mask=mask,
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
                    help="skip the check that the silent reel is newer than src/onebit_tehran5b.py (a preview)")
    args = ap.parse_args()

    clock()
    social = args.outdir or onebit.OUT / "social"
    video = args.video or onebit.OUT / "social" / f"{BASE}_reel.mp4"
    if not args.accept_stale_video and video.stat().st_mtime < Path(film.__file__).stat().st_mtime:
        sys.exit(f"{video.name} is older than src/onebit_tehran5b.py: render the film first")
    outs = output_paths(social)
    print("the narration (cache or synthesis):")
    ensure_narration()
    narr_before = {p.name: _file_md5(p) for p in sorted(NARR_DIR.glob("*"))}
    st = os.stat(video)
    before = (st.st_size, st.st_mtime_ns)

    notes = score_notes()
    d = build(notes)
    print("the notes (on the film's clock, Chahargah on C = the C scale):")
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
    print(f"    (key) every note is on the C scale: {all(nt.midi % 12 in CSCALE for nt in notes)}")
    if not all(nt.midi % 12 in CSCALE for nt in notes):
        fails.append("key")

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
    print("    the narration files are unchanged; each segment is in its scene's window:")
    for (name, a, b), seg in zip(d["spans"], NARRATION):
        print(f"      {name} speech {a:6.2f}-{b:6.2f} s (window {seg['start']:.2f}-{seg['end']:.2f} s)")
        if not (abs(a - seg["start"]) < 1e-9 and b <= seg["end"] + 1e-9):
            fails.append(f"narration timing {name}")
    if ENDING_T < d["spans"][-1][2] + 0.05:
        fails.append("the ending does not follow N5")
    print(f"    the ending {ENDING_T:.2f} s; the reel {END:.1f} s, N5 ends {d['spans'][-1][2]:.2f} s "
          f"({END - d['spans'][-1][2]:.2f} s before the end, limit 0.6)")
    if END - d["spans"][-1][2] < 0.6:
        fails.append("N5 ends too close to the end")

    print()
    if fails:
        print("CHECKS NOT PASSED: " + "; ".join(fails))
        sys.exit(1)
    print("all checks pass")


if __name__ == "__main__":
    main()
