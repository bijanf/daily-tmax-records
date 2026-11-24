"""The sound of the Kerman reel (kerman_fa, no narration): the "pulse" of the ice-age film's documentary cut, which
the owner chose on 23 Nov 2026 (daf, tombak and a santur figure at about 100 beats a minute under a bowed kamancheh),
moved to Chahargah on C for this film, and a layer of sound tied to what the picture does. Written without being heard
(the writer has no ears): checked for level, evenness and how much of it a phone's speaker can play; the ear is his.

    the layer   a low blow and air at frame 0; a soft ping as each place lands on the map; a tick for each year the
                pole's counter runs through (1393 .. 1401) and a blow when the drop is named; water under the qanat that
                flows, then air and a dull drop as the dry one comes up; a whoosh along the wipe of 1366 to 1404 and a
                chime when the green lights up; a rise as the year's warmth draws and a knock on its number; the ground
                cracking under Kerman; a whoosh and a daf stroke into every scene
    the music   one sustained ground on C and G (C3 and up: a phone plays nothing under 150 Hz); the groove sparse at the
                sinking ground, thinned to the santur at the dry qanat, full at the wells, warm and city; the kamancheh
                rising through the film and ending open on the fifth

    python -I src/onebit_score_kerman.py     # outputs/onebit/social/kerman_fa_music.wav and, when the silent reel is
                                              # there, kerman_fa_music_reel.mp4
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfiltfilt

sys.path.insert(0, str(Path(__file__).resolve().parent))

import onebit  # noqa: E402
import onebit_persian as kit  # noqa: E402
import onebit_score_air_light as light  # noqa: E402
import onebit_score_cycles_doc as doc  # noqa: E402  (whoosh, wash, tick, crack, Mix)

ROOT = Path(__file__).resolve().parents[1]
FILM = ROOT / "outputs" / "onebit" / "kerman" / "film.json"
BASE = "kerman_fa"
SR = kit.SR
LUFS, MASTER_TP, TP_AAC = doc.LUFS, doc.MASTER_TP, doc.TP_AAC      # -16 LUFS, the level the owner heard last
MODE = "chahargah"                                    # C, D koron, E, F, G, A koron, B
TONIC = kit.note_hz("C4")
ROOM, ROOM_T60, TOP_HZ = 0.32, 3.0, 5800.0


def hz(step: int, octave: int = 0) -> float:
    return kit.degree(MODE, step, octave, TONIC)


def layer(mx, c: dict, q: dict) -> None:
    rng, put = mx.rng, mx.put
    put(kit.impact(2.0, vel=0.26, pitch=52.0), 0.0)                                         # frame 0
    put(doc.whoosh(rng, 0.9, 0.16, 200.0, 2200.0), 0.0)
    d0, d1 = q["sink"]["dive"]                                                              # the dive from Iran to the plain
    put(kit.riser(d1 - d0, vel=0.16, f0=120.0, f1=760.0), d0)
    put(kit.impact(1.8, vel=0.22, pitch=58.0), d1 - 0.05)
    s0 = c["sink"][0]
    for k, t in enumerate(q["sink"]["chips"]):                                              # the places land
        put(kit.santur(hz(4 + 3 * k, 1), dur=2.2, vel=0.12, t60=1.8, detune=2.0, spread=0.3, bright=0.3), s0 + t, 1.0, 0.3 - 0.6 * k)
    p0, p1 = q["sink"]["pole"]
    for k in range(9):                                                                     # the years 1393 .. 1401 on the pole
        u = k / 8
        put(doc.tick(0.09, 1600.0 - 40.0 * k), s0 + p0 + u * (p1 - p0), 1.0, 0.2 * (-1) ** k)
    put(kit.sub(kit.note_hz("C2"), p1 - p0, vel=0.05, drive=0.6), s0 + p0)                 # the ground going down
    put(kit.impact(2.2, vel=0.3, pitch=46.0), s0 + q["sink"]["tag"])
    q0 = c["qanat"][0]                                                                     # the qanat: water, then dry air
    put(doc.wash(rng, q["qanat"]["swap"][0] + 0.8, 0.12), q0 + 0.1)
    put(doc.whoosh(rng, 0.9, 0.14, 160.0, 1400.0), q0 + q["qanat"]["swap"][0])
    put(kit.impact(1.6, vel=0.2, pitch=60.0), q0 + q["qanat"]["swap"][1] - 0.3)
    w0 = c["wells"][0]                                                                     # the wipe, the green
    a, b = q["wells"]["wipe"]
    put(doc.whoosh(rng, b - a + 0.3, 0.2, 240.0, 3000.0), w0 + a - 0.1)
    for j, step in enumerate((0, 2, 4)):
        put(kit.santur(hz(step, 1), dur=3.0, vel=0.16 - 0.02 * j, t60=2.4, detune=2.0, spread=0.35, bright=0.3), w0 + q["wells"]["green"][0] + 0.1 * j, 1.0, 0.3 - 0.3 * j)
    m0 = c["warm"][0]                                                                      # the warmth draws, its number lands
    d0, d1 = q["warm"]["draw"]
    put(kit.riser(d1 - d0, vel=0.14, f0=160.0, f1=900.0), m0 + d0)
    put(kit.tombak("tom", vel=0.2, pitch=90.0), m0 + q["warm"]["gap"])
    k0 = c["city"][0]                                                                      # Kerman: the ground cracks
    put(doc.crack(rng, 0.26), k0 + q["city"]["small"][0] - 0.6, 1.0, 0.2)
    put(kit.impact(2.0, vel=0.26, pitch=50.0), k0 + q["city"]["small"][0] - 0.58)
    for key in ("qanat", "wells", "warm", "city"):                                         # into each scene
        put(doc.whoosh(rng, 0.6, 0.18), c[key][0] - 0.42)
        put(kit.daf("bam", vel=0.2, pitch=70.0), c[key][0] + 0.02)


def ground(mx, c: dict) -> None:
    low = dict(C=kit.note_hz("C3"), G=kit.note_hz("G3"), c=kit.note_hz("C4"), E=kit.note_hz("E4"), Db=kit.note_hz("C#4") * 2 ** (-0.5 / 12), g=kit.note_hz("G4"))
    notes = dict(sink=("C", "G", "c"), qanat=("C", "G", "c", "E"), wells=("C", "G", "c", "E", "g"), warm=("C", "G", "c", "Db"), city=("C", "G", "c", "E"))
    vel = dict(sink=0.15, qanat=0.14, wells=0.16, warm=0.17, city=0.16)
    end = max(b for _, b in c.values())
    for i, key in enumerate(notes):
        t0, t1 = c[key]
        start, stop = (t0 if i == 0 else t0 - 1.4), min(t1 + 1.6, end + 3.0)
        mx.put(kit.pad([low[n] for n in notes[key]], stop - start, vel=vel[key], width=0.85, detune=6.0,
                       cutoff=1300.0 if key != "warm" else 1700.0, attack=0.5 if i == 0 else 2.2, release=2.8), start)
        mx.put(kit.sub(low["C"] / 2, stop - start - 0.4, vel=0.045, drive=0.5), start + 0.2)


def groove(mx, c: dict, q: dict) -> None:
    """Daf, tombak and the santur in eighths; every scene holds a whole number of beats (about 100 a minute)."""
    beats = {k: round((t1 - t0) / 0.6) for k, (t0, t1) in c.items()}                        # about 100 a minute, whole beats a scene
    drum = dict(sink=0.6, qanat=0.75, wells=1.0, warm=1.0, city=0.85)
    figure = dict(sink=(0, 4, 2, 4), qanat=(0, 2, 4, 2), wells=(0, 2, 4, 7), warm=(0, 1, 2, 4), city=(0, 4, 7, 4))
    dry = (c["qanat"][0] + q["qanat"]["swap"][0], c["qanat"][1])                       # the dry qanat: the santur alone
    crack = c["city"][0] + q["city"]["small"][0] - 0.6
    for key, nb in beats.items():
        t0, t1 = c[key]
        b = (t1 - t0) / nb
        assert 0.52 < b < 0.68, (key, b)
        g = drum[key]
        for k in range(nb):
            tb = t0 + k * b
            j = lambda s=0.006: mx.rng.normal(0, s)                                        # noqa: E731
            quiet = dry[0] <= tb < dry[1] or crack - 0.5 < tb < crack + 0.25                # the drums leave the dry qanat and the crack alone
            if not quiet:
                if k % 2 == 0:
                    mx.put(kit.daf("bam", vel=0.34 * g, pitch=112.0), tb + j())
                    if g >= 0.7:
                        mx.put(kit.daf("tak", vel=0.15 * g), tb + 0.75 * b + j())
                        mx.put(kit.tombak("tom", vel=0.13 * g, pitch=165.0), tb + 0.5 * b + j())
                else:
                    if g >= 0.7:
                        mx.put(kit.daf("tak", vel=0.18 * g), tb + 0.5 * b + j())
                        mx.put(kit.tombak("bak", vel=0.08 * g), tb + 0.25 * b + j(), 1.0, 0.3)
                    if g >= 1.0:
                        mx.put(kit.daf("zang", vel=0.05 * g), tb + j())
            for e in range(2):
                step = figure[key][(2 * k + e) % 4]
                mx.put(kit.santur(hz(step % 7, step // 7), dur=1.4, vel=(0.13 if e == 0 and k % 2 == 0 else 0.09) * min(1.0, 0.55 + 0.5 * g),
                                  t60=1.1, detune=2.0, spread=0.3, bright=0.3), tb + 0.5 * e * b + j(0.004), 1.0, 0.35 if e else -0.35)


def voice(mx, c: dict, q: dict) -> None:
    def sing(t: float, dur: float, step: int, octave: int = 0, vel: float = 0.46) -> None:
        f = hz(step, octave)
        mx.put(kit.kamancheh(f, dur=dur + 0.25, vel=vel, vib_hz=4.6, vib_cents=22.0, bow=min(0.7, 0.3 * dur)), t, 1.0, -0.12)
        mx.put(kit.kamancheh(f / 2, dur=dur + 0.25, vel=0.42 * vel, vib_hz=4.2, vib_cents=14.0, bow=min(0.9, 0.36 * dur)), t + 0.03, 1.0, 0.16)
    # the tune was laid on scenes of 10.5, 9.25, 10.5, 10 and 9.25 s; each scene's notes stretch with its own length,
    # except where a note answers a cue (the drop named, the dry qanat), which keeps its moment
    old = dict(sink=10.5, qanat=9.25, wells=10.5, warm=10.0, city=9.25)
    f = {k: (c[k][1] - c[k][0]) / old[k] for k in old}
    s0, q0, w0, m0, k0 = (c[k][0] for k in ("sink", "qanat", "wells", "warm", "city"))
    sw, tg = q["qanat"]["swap"][0], q["sink"]["tag"]
    S = lambda key, x: x * f[key]                                                          # noqa: E731
    for t, dur, step, octave, vel in (
            (s0 + 0.6, 2.6, 0, 0, 0.42), (s0 + 3.4, tg - 3.6, 1, 0, 0.42), (s0 + tg - 0.1, 3.4, 0, 0, 0.46),         # sink: C, D koron, C
            (s0 + tg + 3.6, c["sink"][1] - s0 - tg - 3.4, 4, -1, 0.4),
            (q0 + 0.3, 2.4, 2, 0, 0.42), (q0 + 2.9, sw - 3.0, 3, 0, 0.42), (q0 + sw + 0.4, 3.2, 1, 0, 0.38),         # qanat: up, then down at the dry one
            (q0 + sw + 3.8, c["qanat"][1] - q0 - sw - 3.6, 0, 0, 0.36),
            (w0 + S("wells", 0.3), S("wells", 2.4), 2, 0, 0.46), (w0 + S("wells", 3.0), S("wells", 2.6), 4, 0, 0.5), (w0 + S("wells", 6.0), S("wells", 3.6), 5, 0, 0.5),   # wells: the climb
            (m0 + S("warm", 0.3), S("warm", 2.8), 4, 0, 0.5), (m0 + S("warm", 3.4), S("warm", 2.4), 5, 0, 0.52), (m0 + S("warm", 6.0), S("warm", 3.2), 7, 0, 0.54),   # warm: the top
            (k0 + S("city", 0.3), S("city", 2.2), 5, 0, 0.48), (k0 + S("city", 2.9), S("city", 2.4), 4, 0, 0.46), (k0 + S("city", 5.6), S("city", 3.4), 4, 0, 0.44)):   # city: open on the fifth
        sing(t, dur, step, octave, vel)


def score(film: dict) -> tuple:
    c = {s["key"]: (s["start"], s["start"] + s["length"]) for s in film["scenes"]}
    q, end = film["cues"], film["end"]
    mx = doc.Mix(end, 1405)
    layer(mx, c, q)
    ground(mx, c)
    groove(mx, c, q)
    voice(mx, c, q)
    wet = kit.reverb(mx.track, t60=ROOM_T60, predelay=0.03, seed=17)[:len(mx.track)]
    track = sosfiltfilt(butter(4, TOP_HZ, "lowpass", fs=SR, output="sos"), mx.track + ROOM * wet, axis=0)
    return light._bass_mono(track), sorted(mx.onsets), end


def main() -> None:
    film = json.loads(FILM.read_text(encoding="utf-8"))
    social = onebit.OUT / "social"
    video, wav, mp4 = social / f"{BASE}_reel.mp4", social / f"{BASE}_music.wav", social / f"{BASE}_music_reel.mp4"
    kit.reseed(1405)
    track, onsets, end = score(film)
    music = kit.master(track, lufs=LUFS, tp=MASTER_TP, seconds=end, fade_out=1.6)
    light.write_wav(wav, music)
    m = light._read_wav(wav)
    lufs, tp = kit.integrated_lufs(m), kit.true_peak_dbtp(m)
    mono = m.mean(axis=1)
    rms = [20 * np.log10(np.sqrt(np.mean(mono[k:k + SR] ** 2)) + 1e-12) for k in range(0, len(mono) - SR, SR // 10)]
    body = rms[:int((end - 2.0) * 10)]
    spec = np.abs(np.fft.rfft(mono * np.hanning(len(mono)))) ** 2
    freq = np.fft.rfftfreq(len(mono), 1 / SR)
    share = lambda lo, hi: float(spec[(freq >= lo) & (freq < hi)].sum() / spec.sum())   # noqa: E731
    fails = []
    print(f"level     {lufs:+.2f} LUFS (aim {LUFS:+.0f}); true peak WAV {tp:+.2f} dBTP")
    if abs(lufs - LUFS) > 0.6:
        fails.append("level")
    print(f"evenness  one-second windows before the ending: quietest {min(body):.1f} dBFS, loudest {max(body):.1f} dBFS")
    if min(body) < -60 or max(body) - min(body) > 18:
        fails.append("uneven")
    print(f"spectrum  energy below 150 Hz {100 * share(0, 150):.0f} %, 150-800 Hz {100 * share(150, 800):.0f} %, above 800 Hz {100 * share(800, 24000):.0f} %")
    if share(150, 24000) < 0.4:
        fails.append("too little above 150 Hz for a phone speaker")
    print(f"sounds    {len(onsets)}; first at {onsets[0]:.3f} s")
    print("saved", wav)
    if video.exists():
        kit.mux(video, wav, mp4)
        aac = kit.aac_true_peak(mp4)
        print(f"decoded AAC true peak {aac:+.2f} dBTP")
        if aac > TP_AAC:
            fails.append("AAC peak")
        if light._md5(video, "0:v:0") != light._md5(mp4, "0:v:0"):
            fails.append("the picture changed")
        print("saved", mp4)
    if fails:
        sys.exit("CHECKS NOT PASSED: " + "; ".join(fails))
    print("all checks pass")


if __name__ == "__main__":
    main()
