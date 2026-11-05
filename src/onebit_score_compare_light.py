"""The light score of the Tehran and Istanbul NO2 film (compare_tehran_istanbul_fa, 24 s): the same kind of music as the
light score of the winter NO2 reel (onebit_score_air_light.py), on this film's own clock, in a different key.

The engine and every check are the light score's own (imported from onebit_score_air_light.py, not copied): a sparse
line of setar plucks that start and decay, no sustained tone at all, silence between the phrases, and the music ducked
under the speech. The narration is the cached segments of this film (onebit_score_compare.py, NARRATION and the
manifest in data/air/compare/narration, read only); the mix and the mux are those of the compare score.

    the key       Mahur on C: C D E F G A B. Bright, and not the NO2 reel's D.
    the notes     a soft C5 at 0.00 s, so frame 0 is not silent; a gentle note at each month switch (G4 at 1.55 s,
                  A4 at 3.80 s), and C5 at 2.30 s between them; the second pass in short
                  phrases with rests (9.60-10.50 s, 13.00-13.80 s); a rising phrase into the hold: C4, E4, G4, then the
                  hold's C5 at T_HOLD = 17.0 s; then G5 and E5 (18.40, 19.20 s) and the ending, C4 and G4 struck
                  together at 20.60 s (an open fifth on the tonic), which rings out before the 24.0 s end.
                  No note is struck inside the second speech (4.80-9.60 s): the music is quiet under it, and the
                  duck starts 0.6 s ahead of each speech so that it is fully down when the voice begins.
                  Every pair of notes that rings together is a unison, third, fourth, fifth, sixth or octave.
    the timbre    setar, Karplus-Strong, bright 0.15 (a soft pick), T60 2.5 s, low-passed warm at 1.6 kHz; the notes
                  alternate a little left and right; the bass below 120 Hz is one channel.

Three files are written, each with its WAV (48 kHz, 16 bit):
    compare_tehran_istanbul_fa_light_reel.mp4       the voice and the light music
    compare_tehran_istanbul_fa_voiceonly_reel.mp4   the voice alone, at the same level as in the mix
    compare_tehran_istanbul_fa_lightmusic_reel.mp4  the light music alone, at -26 LUFS

The silent reel (outputs/onebit/social/compare_tehran_istanbul_fa_reel.mp4) must be newer than src/onebit_compare.py
(or pass --accept-stale-video for a preview). It is not rewritten. Existing outputs are never overwritten: the script
stops if one of the six files exists.

The checks are the light score's, on the files as delivered; see onebit_score_air_light.py for their limits.
    python -I src/onebit_score_compare_light.py     writes the three reels and their WAVs, then runs the checks
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import onebit  # noqa: E402
import onebit_compare as film  # noqa: E402
import onebit_persian as kit  # noqa: E402
import onebit_score_air_light as light  # noqa: E402
import onebit_score_compare as cmp  # noqa: E402

SR = kit.SR
BASE = "compare_tehran_istanbul_fa"
END = 24.0                                          # s: the length of the reel
TAIL = light.TAIL
MUSIC_LUFS, MIX_LUFS = -26.0, -14.5
TP_WAV, TP_AAC = -1.5, -1.0
MASTER_TP = -2.0
RATIO_MIN = light.RATIO_MIN                         # dB: the voice over the ducked music, in every segment
NARR_DIR = cmp.NARR_DIR
NARRATION = cmp.NARRATION                           # the five segments of this film (n1-n5), on this film's clock
VEL_SOFT, VEL, VEL_HOLD = 0.55, 0.80, 0.90
DUCK_LEAD = 0.6                                      # s: the music is ducked this long before each speech (the light score: 0.15)

# ── the film's clock, read from onebit_compare.py and asserted ───────────────

def clock() -> dict:
    """The film's clock as this score was written for it. A change in onebit_compare.py that moves it fails here."""
    assert abs(film.DURATION - END) < 1e-9, film.DURATION
    assert abs(film.STEP_A[0] - 0.8) < 1e-9 and abs(film.STEP_A[1] - 2.3) < 1e-9, film.STEP_A
    assert abs(film.STEP_B[0] - 2.8) < 1e-9 and abs(film.STEP_B[1] - 4.8) < 1e-9, film.STEP_B
    assert len(film.WORD_SWITCH) == 2 and all(abs(a - b) < 1e-9 for a, b in zip(film.WORD_SWITCH, (1.55, 3.8))), \
        film.WORD_SWITCH
    assert abs(film.T_HOLD - 17.0) < 1e-9, film.T_HOLD
    return dict(sw1=float(film.WORD_SWITCH[0]), sw2=float(film.WORD_SWITCH[1]), hold=float(film.T_HOLD), end=END)


# ── the notes (MIDI: 60 is C4, 72 is C5; C Mahur) ───────────────────────────

def score_notes() -> list:
    """Every note on the film's clock, sorted. Each entry: (t s, MIDI, velocity). The ending is two notes at one onset."""
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
    notes = []
    for i, (t, m, vel) in enumerate(plan):
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


# ── the mixes: the light score's engine, on this film's narration ───────────

def narration_voice(n: int) -> tuple:
    v = np.zeros(n)
    spans = []
    for seg in NARRATION:
        hit = cmp._cached(seg)
        if hit is None:
            sys.exit(f"the cached segment {seg['name']} in {NARR_DIR} does not match NARRATION: this script does not "
                     f"re-render it; re-render it with onebit_score_compare.py first")
        y, lead, speech = hit
        assert seg["start"] + speech <= seg["end"], (seg["name"], speech)
        i0 = round((seg["start"] - lead) * SR)
        v[i0:i0 + len(y)] += y[:max(0, n - i0)]
        spans.append((seg["name"], seg["start"], seg["start"] + speech))
    return v, spans


def build(notes) -> dict:
    """The stem (music alone, -26 LUFS), the ducked music, the voice, and the mixes, as in the light score."""
    raw = stem_raw(notes)
    stem = light._bass_mono(light._air_cut(raw))
    stem_m = kit.master(stem, lufs=MUSIC_LUFS, tp=MASTER_TP, seconds=END, fade_out=1.0)
    n = len(stem_m)
    v, spans = narration_voice(n)
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
                    help="skip the check that the silent reel is newer than src/onebit_compare.py (a preview)")
    args = ap.parse_args()

    clock()
    social = args.outdir or onebit.OUT / "social"
    video = args.video or onebit.OUT / "social" / f"{BASE}_reel.mp4"
    if not args.accept_stale_video and video.stat().st_mtime < Path(film.__file__).stat().st_mtime:
        sys.exit(f"{video.name} is older than src/onebit_compare.py: render the film first")
    outs = output_paths(social)
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
    for key, (wav, mp4, mode) in results.items():
        dec = light._decode(mp4)
        aac_l, aac_tp = kit.integrated_lufs(dec), kit.aac_true_peak(mp4)
        print(f"    {mp4.name}: decoded {aac_l:+.2f} LUFS, {aac_tp:+.2f} dBTP (limit -1)")
        if aac_tp > TP_AAC:
            fails.append(f"decoded true peak {key}")
        v_md5, m_md5 = light._md5(video, "0:v:0"), light._md5(mp4, "0:v:0")
        if v_md5 != m_md5:
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
