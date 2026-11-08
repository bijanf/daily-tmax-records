"""The light score of the self-describing El Niño reel, version B (elnino26s_fa, 35.5 s): the light score's engine and
checks (onebit_score_air_light.py, imported, not copied; the checks of onebit_score_elnino2_light.py, copied and kept),
on the clock of onebit_elnino26s.py, in E Mahur (the key of the other two films, D and A Mahur, is not used here).

    the key       E Mahur: E F# G# A B C# D# (the D Mahur plan of the light score, transposed up a major second).
    the notes     a soft E5 at 0.00 s, so frame 0 is not silent; soft marks on the reel's own beats: the four autumn
                  counts (scene 2), two soft marks in the Iran-rain bar (scene 3), the four winter counts (scene 4); the
                  rising phrase into the answer (from 0.5 s before scene 5), the hold, then A5 and F#5; the ending, E4 and
                  B4 struck together 0.39 s after the last speech ends. Every pair of notes that rings together is a
                  unison, third, fourth, fifth, sixth or octave (checked).
    the timbre    setar, Karplus-Strong, bright 0.15, T60 2.5 s, low-passed warm at 1.6 kHz; the notes alternate a
                  little left and right; the bass below 120 Hz is one channel.
    the duck      the music is ducked 7 dB from 0.6 s before each speech to its end, so it is down when the voice starts.

The narration is the owner's own voice (recorded 8 Nov 2026; cut and cleaned by src/elnino26s_voice.py into
data/enso/elnino26s/narration_own/n1.wav .. n5.wav, with manifest.json). Each piece's speech starts 0.15 s after its
scene starts, inside that scene's window:
    n1 scene 1 (the hook)     n2 scene 2 (the 26 autumns)     n3 scene 3 (the 23 %)
    n4 scene 4 (the 22 winters)     n5 scene 5 (the verdict and the question)
Nothing is synthesized here: a missing piece stops the score.

Three files are written, each with its WAV (48 kHz, 16 bit):
    elnino26s_fa_light_reel.mp4        the voice and the light music
    elnino26s_fa_voiceonly_reel.mp4    the voice alone, at the same level as in the mix
    elnino26s_fa_lightmusic_reel.mp4   the light music alone, at -26 LUFS

The silent master (outputs/onebit/social/elnino26s_fa_reel.mp4) must be newer than src/onebit_elnino26s.py (or pass
--accept-stale-video for a preview). It is not rewritten. Existing outputs are never overwritten.

    python -I src/onebit_score_elnino26s_light.py     writes the three reels and their WAVs, then runs the checks
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
import onebit_elnino26s as film  # noqa: E402
import onebit_persian as kit  # noqa: E402
import onebit_score_air_light as light  # noqa: E402

SR = kit.SR
BASE = "elnino26s_fa"
END = film.END                                      # s: the length of the reel (the film's clock)
TAIL = light.TAIL
MUSIC_LUFS, MIX_LUFS = -26.0, -14.5
TP_WAV, TP_AAC = -1.5, -1.0
MASTER_TP = -2.0
RATIO_MIN = light.RATIO_MIN                         # dB: the voice over the ducked music, in every segment
OWN_DIR = onebit.ROOT / "data" / "enso" / "elnino26s" / "narration_own"
VOICE = "own voice, recorded 8 Nov 2026"
PIECES = ("n1", "n2", "n3", "n4", "n5")
SPEECH_LEAD = 0.15                                  # s: each piece's speech starts this long after its scene starts
SCENE_TAIL = 0.05                                   # s: a piece's window ends this long before the next scene
DUCK_LEAD = 0.6                                     # s: the music is ducked this long before each speech
ENDING_AFTER = 0.39                                 # s: the ending follows the last speech by this long
VEL_SOFT, VEL, VEL_HOLD, VEL_MARK = 0.55, 0.80, 0.90, 0.42
KEY_SHIFT = 2                                       # semitones: the plan is written in D Mahur, sounded in E Mahur
MAHUR_E = {4, 6, 8, 9, 11, 1, 3}                    # pitch classes of E Mahur (E F# G# A B C# D#)
# the notes, as offsets (s) after the start of their scene; (offset, MIDI) on the plan of D Mahur (before KEY_SHIFT)
AUTUMN_MARKS = ((0.9, 69), (2.3, 74), (3.7, 78), (5.1, 81))     # scene 2: the four autumn counts
RAIN_MARKS = ((1.5, 78), (2.9, 74))                             # scene 3: the rain bar
WINTER_MARKS = ((0.3, 74), (1.4, 69), (2.5, 78), (3.6, 74))     # scene 4: the four winter counts
ANSWER_NOTES = ((-0.5, 62, 0.70), (0.5, 66, 0.75), (1.5, 74, VEL_HOLD), (2.2, 81, 0.75), (3.0, 78, 0.70))
#                 the rise into the answer (D4, F#4), the hold (D5), A5, F#5: scene 5
HOOK_NOTES = ((0.00, 74, VEL_SOFT), (1.55, 69, VEL), (2.30, 74, VEL), (3.80, 67, VEL))   # scene 1 (D plan)


# ── the film's clock, read from onebit_elnino26s.py and asserted ───────────

def clock() -> dict:
    """The film's clock as this score was written for it: the scene starts, the speech windows, the ending."""
    beat = 60 / film.PACE["bpm"]
    starts = np.cumsum([0.0] + [b * 4 * beat for b in film.PACE["bars"]])
    assert abs(starts[-1] - film.END) < 1e-9, (starts, film.END)
    assert abs(film.WET_T0[film.AUTUMN] - 1.0) < 1e-9 and abs(film.WET_SPAN[film.AUTUMN] - 3.6) < 1e-9
    assert abs(film.WET_T0[film.WINTER] - 0.8) < 1e-9 and abs(film.WET_SPAN[film.WINTER] - 3.2) < 1e-9
    man = manifest()
    windows = []
    for i, name in enumerate(PIECES):
        start = float(starts[i]) + SPEECH_LEAD
        end = float(starts[i + 1]) - SCENE_TAIL
        m = man[name]
        assert start + m["speech"] <= end, (name, start, m["speech"], end)
        windows.append(dict(name=name, start=start, end=end, speech=m["speech"], lead=m["lead"]))
    for o, _ in AUTUMN_MARKS:
        assert 0.5 <= o <= starts[2] - starts[1], ("an autumn mark is outside scene 2", o)
    for o, _ in RAIN_MARKS:
        assert 0.0 <= o <= starts[3] - starts[2], ("a rain-bar mark is outside scene 3", o)
    for o, _ in WINTER_MARKS:
        assert 0.0 <= o <= starts[4] - starts[3], ("a winter mark is outside scene 4", o)
    n5 = windows[-1]
    assert n5["name"] == "n5" and n5["end"] == float(film.END) - SCENE_TAIL
    ending = n5["start"] + n5["speech"] + ENDING_AFTER
    return dict(starts=tuple(float(s) for s in starts), end=float(film.END), windows=windows, ending=ending)


def manifest() -> dict:
    """The pieces' manifest: lead and speech per piece, the voice checked."""
    rows = json.loads((OWN_DIR / "manifest.json").read_text(encoding="utf-8"))
    out = {}
    for r in rows:
        assert r["voice"] == VOICE, r
        out[r["name"]] = r
    assert set(out) == set(PIECES), sorted(out)
    return out


def piece(name: str) -> np.ndarray:
    rate, pcm = wavfile.read(str(OWN_DIR / f"{name}.wav"))
    assert rate == SR and pcm.ndim == 1 and pcm.dtype == np.int16, (name, rate, pcm.shape, pcm.dtype)
    return pcm.astype(float) / 32767.0


# ── the notes (MIDI: 60 is C4; the plan is in D Mahur and sounds KEY_SHIFT semitones higher: E Mahur) ──

def score_notes(c: dict) -> list:
    """Every note on the film's clock, sorted. The ending is two notes at one onset."""
    S = c["starts"]
    plan = list(HOOK_NOTES)
    plan += [(S[4] + o, m, v) for o, m, v in ANSWER_NOTES]
    plan += [(c["ending"], 62, VEL), (c["ending"], 69, VEL)]     # D4 and A4: an open fifth on the tonic
    marks = [(S[1] + o, m, VEL_MARK) for o, m in AUTUMN_MARKS]
    marks += [(S[2] + o, m, VEL_MARK) for o, m in RAIN_MARKS]
    marks += [(S[3] + o, m, VEL_MARK) for o, m in WINTER_MARKS]
    allnotes = sorted([(t, m + KEY_SHIFT, v) for t, m, v in plan] + [(t, m + KEY_SHIFT, v) for t, m, v in marks],
                      key=lambda p: p[0])
    notes = []
    for i, (t, m, vel) in enumerate(allnotes):
        notes.append(light.Note(float(t), m, vel, light.PAN if i % 2 == 0 else -light.PAN))
    assert all(m % 12 in MAHUR_E for _, m, _ in allnotes), "every note is in E Mahur"
    assert all(0.0 <= nt.t < END - 0.8 for nt in notes[-2:]), "the ending must ring out before the end"
    return sorted(notes, key=lambda nt: nt.t)


def stem_raw(notes) -> np.ndarray:
    kit.reseed(41)
    track = kit.new_track(END, TAIL)
    for nt in notes:
        kit.place(track, light.pluck(nt.midi, nt.vel), nt.t, 1.0, nt.pan)
    return track


# ── the narration: the owner's own pieces, read from their folder ───────────

def narration_voice(n: int, windows: list) -> tuple:
    v = np.zeros(n)
    spans = []
    for w in windows:
        y = piece(w["name"])
        i0 = round((w["start"] - w["lead"]) * SR)           # the piece starts so that its speech starts at w.start
        v[i0:i0 + len(y)] += y[:max(0, n - i0)]
        spans.append((w["name"], w["start"], w["start"] + w["speech"]))
    return v, spans


def build(notes, c: dict) -> dict:
    """The stem (music alone, -26 LUFS), the ducked music, the voice, and the mixes, as in the light score."""
    raw = stem_raw(notes)
    k = round(0.025 * SR)                               # a 25-ms raised-cosine fade-in: no click at the first sample
    w = 0.5 - 0.5 * np.cos(np.linspace(0.0, np.pi, k))
    raw[:k] *= w.reshape(-1, *([1] * (raw.ndim - 1)))
    stem = light._bass_mono(light._air_cut(raw))
    stem_m = kit.master(stem, lufs=MUSIC_LUFS, tp=MASTER_TP, seconds=END, fade_out=1.0)
    n = len(stem_m)
    v, spans = narration_voice(n, c["windows"])
    mask = np.zeros(n, bool)
    core = np.zeros(n, bool)
    for _, a, b in spans:
        mask[max(0, round((a - DUCK_LEAD) * SR)):round(b * SR)] = True
        core[round(a * SR):round(b * SR)] = True
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
                    help="skip the check that the silent reel is newer than src/onebit_elnino26s.py (a preview)")
    args = ap.parse_args()

    clk = clock()
    social = args.outdir or onebit.OUT / "social"
    video = args.video or onebit.OUT / "social" / f"{BASE}_reel.mp4"
    if not args.accept_stale_video and video.stat().st_mtime < Path(film.__file__).stat().st_mtime:
        sys.exit(f"{video.name} is older than src/onebit_elnino26s.py: render the film first")
    outs = output_paths(social)
    print("the narration (the owner's own voice, cut by src/elnino26s_voice.py):")
    for w in clk["windows"]:
        print(f"    {w['name']} speech {w['start']:6.2f}-{w['start'] + w['speech']:6.2f} s "
              f"(window {w['start']:.2f}-{w['end']:.2f} s)")
    narr_before = {p.name: _file_md5(p) for p in sorted(OWN_DIR.glob("*"))}
    st = os.stat(video)
    before = (st.st_size, st.st_mtime_ns)

    notes = score_notes(clk)
    d = build(notes, clk)
    print("the notes (on the film's clock, E Mahur):")
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
    print(f"    (key) every note is in E Mahur: {all(nt.midi % 12 in MAHUR_E for nt in notes)}")
    if not all(nt.midi % 12 in MAHUR_E for nt in notes):
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
    narr_after = {p.name: _file_md5(p) for p in sorted(OWN_DIR.glob("*"))}
    if narr_before != narr_after:
        fails.append("the narration directory changed")
    print("    the narration files are unchanged; each segment is in its scene's window:")
    for (name, a, b), seg in zip(d["spans"], clk["windows"]):
        print(f"      {name} speech {a:6.2f}-{b:6.2f} s (window {seg['start']:.2f}-{seg['end']:.2f} s)")
        if not (abs(a - seg["start"]) < 1e-9 and b <= seg["end"] + 1e-9):
            fails.append(f"narration timing {name}")
    if clk["ending"] < d["spans"][-1][2] + 0.05:
        fails.append("the ending does not follow N5")
    print(f"    the ending {clk['ending']:.2f} s; the reel {END:.1f} s, N5 ends {d['spans'][-1][2]:.2f} s "
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
