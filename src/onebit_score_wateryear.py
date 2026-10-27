"""Soundtrack for the water-year reel (iran_wateryear_zafaran_fa_24s): a half-time Persian groove at
120 BPM, Dashti on the setar and santur, built from the sound kit in onebit_persian.

Timing comes from the film object alone: its scene starts (starts), the six squares (fill_at), and
the moments its words land (later(1) for 'normal', later(2) for '6 years'). The film's 60 BPM grid
is one beat per second, so the music's beat is 0.5 s and a bar 2 s. Every event falls on that grid
except 'normal' (7.3 s), which the resolving chord lands on exactly.

Sections, by the film's scenes:
- intro, 0-6 s: the hook from the first sample over the full groove, a daf bam on the bar line.
- calm, 6-14 s: tension on A-koron at 6 s, resolved at 7.3 s ('normal') to the G chord and a santur
  chord; a santur answer, a falling setar phrase and a riser into scene 3.
- breakdown, 14-17.5 s: the beat thins (full, snare, kick only) while the squares fill.
- drop, 17.5 s ('6 years'): an impact, the kick, the hook an octave up over a fifth drone.
- outro, 21.5-24 s: the hook's last phrase lands on G, the groove drops to the kick, and the track
  fades over its last second.

The data layer: the six squares are six daf strokes, one step of the Dashti scale each (F, Eb, D,
C, Bb, A-koron), from the first water year to the last, so the line goes down with the years. The
strokes start on the squares' own times and pan from right to left, the way Persian is read.

    python -I src/onebit_score_wateryear.py
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from scipy.io import wavfile  # noqa: E402

import onebit_persian as kit  # noqa: E402

MODE = "dashti"                                       # G, A-koron, Bb, C, D, Eb, F
LOW, HIGH = kit.note_hz("G3"), kit.note_hz("G4")      # the setar's tonic, and the octave above
YEAR_STEPS = (6, 5, 4, 3, 2, 1)                       # 1399-1400 .. 1404-1405: one step lower each year
HOOK = ((0, 0, 1), (2, 1, 1), (4, 2, 2), (5, 4, 1), (4, 5, 1), (1, 6, 2))     # (step, beat, beats)
VARIANT = ((2, 0, 1), (4, 1, 1), (5, 2, 2), (4, 4, 1), (2, 5, 1), (0, 6, 2))  # the same shape, to G
OUTRO = ((2, 0, 1), (4, 1, 1), (0, 2, 4))
SEED = 41
TAIL = 3.0                                            # s of tail on each bus, cut at the end
# the groove's levels from each time on: full, calm (no 'and' kick, quarter hats), snare, kick only
LEVELS = ((0.0, "full"), (6.0, "calm"), (14.0, "full"), (15.0, "snare"), (16.0, "kick"),
          (17.5, "full"), (21.5, "kick"))
WHO = {"kick": ("full", "calm", "kick"), "and": ("full",), "bam": ("full", "calm", "kick"),
       "snare": ("full", "calm", "snare"), "tak": ("full",), "hat8": ("full",), "hat4": ("calm",)}


GEO_STACK = ("shapely", "cartopy", "fiona", "rasterio", "pyproj", "geopandas")


def block_geo_stack() -> None:
    """Keep the geo stack out of this process. xarray imports every installed backend plugin when it
    first opens a file, and the rasterio plugin pulls in shapely, cartopy and fiona next to netCDF,
    which corrupts the heap (the repo's rule, see enso.py). The film reads only netCDF, so blocking
    these imports changes nothing it computes: the film's own assertions still check its numbers."""
    for name in GEO_STACK:
        if name not in sys.modules:
            sys.modules[name] = None


def plan(film) -> dict:
    """The film's visual events in seconds, and the times the music puts its hits on them."""
    st = [float(s) for s in film.starts]
    return dict(end=st[-1], starts=st, normal=st[1] + float(film.later(1)),
                squares=[float(t) for t in film.fill_at], six=st[2] + float(film.later(2)))


def level(t: float) -> str:
    lv = "kick"
    for start, name in LEVELS:
        if t >= start:
            lv = name
    return lv


def bass_mono(x, fc: float = 120.0) -> np.ndarray:
    """Mono below fc: the side (L minus R) loses every bin below fc, the middle keeps all of it, so
    the sub sits in the centre whatever the reverb and the stereo pads do under it. Above fc nothing
    changes. Done on the whole spectrum (the track is rendered offline, so there is no latency)."""
    n = len(x)
    f = np.fft.rfftfreq(n, 1 / kit.SR)
    mid = np.fft.rfft(0.5 * (x[:, 0] + x[:, 1]))
    side = np.fft.rfft(0.5 * (x[:, 0] - x[:, 1]))
    side[f < fc] = 0.0
    m, s = np.fft.irfft(mid, n), np.fft.irfft(side, n)
    return np.stack([m + s, m - s], axis=1)


def soundtrack(film) -> np.ndarray:
    """Stereo track (n, 2), float, 48 kHz, cut to the film's length and mastered to -14 LUFS."""
    kit.reseed(SEED)
    p = plan(film)
    end, b, t6 = p["end"], kit.BEAT, p["six"]
    drums, bass, music, sfx, send, echo = (kit.new_track(end, TAIL) for _ in range(6))
    kick, snare = kit.kick808(kit.note_hz("G1")), kit.snare()
    bam, hat, open_hat = kit.daf("bam"), kit.hat(False), kit.hat(True)
    kicks = []

    def deg(step, base=LOW, octave=0):
        return kit.degree(MODE, step, octave, tonic_hz=base)

    def pluck(t, step, base, gain, pan=0.0):
        s = kit.setar(deg(step, base), dur=1.6, vel=0.9, t60=1.1)
        kit.place(music, s, t, gain, pan=pan)
        kit.place(send, s, t, 0.3, pan=pan)
        kit.place(echo, s, t, 0.35, pan=pan)

    def phrase(t0, notes, base, gain):
        for i, (step, beat, _) in enumerate(notes):
            pluck(t0 + beat * b, step, base, gain, pan=(-0.25, 0.25)[i % 2])

    # the groove, bar by bar: each kind of hit only where the groove level allows it
    for b0 in np.arange(0.0, end, kit.BAR):
        grid = [(b0, "kick"), (b0, "bam"), (b0 + 1.0, "snare"), (b0 + 1.25, "and"), (b0 + 1.25, "tak")]
        grid += [(b0 + i * b, "hat4") for i in range(4)]
        grid += [(b0 + i * b / 2, "hat8") for i in range(8)]
        for t, kind in grid:
            if t >= end or level(t) not in WHO[kind]:
                continue
            if kind in ("kick", "and"):
                kicks.append(t)
                kit.place(drums, kick, t, 0.95 if kind == "kick" else 0.8)
            elif kind == "bam":
                kit.place(drums, bam, t, 0.55)
            elif kind == "snare":
                kit.place(drums, snare, t, 0.5)
            elif kind == "tak":
                kit.place(drums, kit.daf("tak", vel=0.35), t, 0.4, pan=0.3)
            else:
                odd = round((t - b0) / (b / 2)) % 2
                kit.place(drums, hat, t, 0.12 + 0.04 * odd, pan=-0.25 + 0.5 * odd)

    # the drop at '6 years': the kick, an open hat and an impact on the same beat
    kicks.append(t6)
    kit.place(drums, kick, t6, 0.95)
    kit.place(drums, open_hat, t6, 0.2)
    kit.place(sfx, kit.impact(2.2, vel=1.0, pitch=42.0), t6, 0.8)
    kit.place(sfx, kit.riser(1.0, vel=0.6), 13.0, 0.5)

    # the data: one daf stroke per square, on its own step of the scale, panned right to left
    for k, t in enumerate(p["squares"]):
        kit.place(drums, kit.daf("tak", vel=1.0, pitch=deg(YEAR_STEPS[k], HIGH)), t, 0.55, pan=0.4 - 0.16 * k)

    # harmony: A-koron (tension) and G (rest); a pad and one sub note per chord, the drone a fifth up
    chords = ((0.0, (0, 2, 4)), (4.0, (1, 4, 6)), (p["normal"], (0, 2, 4)), (12.0, (1, 4, 6)), (14.0, (0, 2, 4)))
    ends = [t for t, _ in chords[1:]] + [end]
    for (t0, steps), t1 in zip(chords, ends):
        kit.place(music, kit.pad([deg(s) for s in steps], dur=t1 - t0 + 0.6, vel=0.3), t0, 0.5)
        kit.place(bass, kit.sub(deg(steps[0], LOW, -2), t1 - t0, vel=0.75), t0, 0.7)
    kit.place(bass, kit.sub(deg(4, LOW, -1), end - t6, vel=0.35), t6, 0.6)

    # the melody: the hook, its variant landing on G under 'normal', the drop an octave up, the outro
    phrase(0.0, HOOK, LOW, 0.5)
    phrase(4.0, VARIANT, LOW, 0.5)
    pluck(12.0, 4, LOW, 0.4, -0.2)
    pluck(12.5, 2, LOW, 0.4, 0.2)
    pluck(14.0, 0, LOW, 0.4, -0.2)
    pluck(16.0, 2, LOW, 0.35, 0.2)
    phrase(t6, HOOK, HIGH, 0.6)
    phrase(21.5, OUTRO, HIGH, 0.45)
    for i, step in enumerate((4, 2, 0, 2, 4, 5, 4, 2)):        # the santur answer, eighths from 8 s
        s = kit.santur(deg(step, HIGH), dur=2.2, vel=0.7)
        kit.place(music, s, 8.0 + i * b / 2, 0.35)
        kit.place(send, s, 8.0 + i * b / 2, 0.15)
    for step in (0, 2, 4):                                      # the resolved chord on 'normal'
        s = kit.santur(deg(step, HIGH), dur=3.0, vel=0.6)
        kit.place(music, s, p["normal"], 0.45)
        kit.place(send, s, p["normal"], 0.2)

    # the mix: the music ducks under the kick, the send goes to a room, the echo to a ping-pong
    music_d = kit.duck(music, kicks, depth_db=4.0, release=0.15)
    wet = kit.reverb(send, t60=2.2) * 0.5
    dly = kit.pingpong(echo, delay=0.375, feedback=0.42, taps=8) * 0.6
    n = len(drums)
    mix = bass_mono(drums + music_d + bass + sfx + wet[:n] + dly[:n])
    return kit.master(mix, lufs=-14.0, tp=-1.5, seconds=end, fade_out=1.0)


def write(film, path) -> Path:
    """The soundtrack as a 48 kHz 16-bit stereo WAV."""
    return kit.write_wav(path, soundtrack(film))


# ── checks ──────────────────────────────────────────────────────────────────

def onsets(x, n_fft: int = 512, hop: int = 96):
    """Spectral flux of the log magnitude: a 512-sample Hann window, a 2 ms hop. Returns the centre
    time of each frame and its flux."""
    mono = np.asarray(x, float).mean(axis=1)
    frames = 1 + (len(mono) - n_fft) // hop
    idx = np.arange(n_fft)[None, :] + hop * np.arange(frames)[:, None]
    mag = np.abs(np.fft.rfft(mono[idx] * np.hanning(n_fft), axis=1))
    logm = np.log1p(1000.0 * mag)
    flux = np.maximum(np.diff(logm, axis=0, prepend=logm[:1]), 0.0).sum(axis=1)
    return (np.arange(frames) * hop + n_fft / 2) / kit.SR, flux


def onset_offset(te: float, centre, flux, tol: float = 0.1) -> float:
    """The time of the strongest flux within tol of te, minus te (s)."""
    m = (centre >= te - tol) & (centre <= te + tol)
    return float(centre[m][np.argmax(flux[m])] - te)


def streams(media) -> list:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "stream=codec_type,codec_name,width,height,nb_frames,duration,sample_rate,channels",
                          "-of", "json", str(media)], check=True, capture_output=True, text=True).stdout
    return json.loads(out)["streams"]


def video_md5(media) -> str:
    """Checksum of the video packets as stored (no decode): equal when the stream is copied as it is."""
    return subprocess.run(["ffmpeg", "-v", "error", "-i", str(media), "-map", "0:v:0", "-c", "copy",
                           "-f", "md5", "-"], check=True, capture_output=True, text=True).stdout.strip()


def report(film, wav: Path, video: Path, mp4: Path) -> None:
    p = plan(film)
    _, pcm = wavfile.read(str(wav))
    x = pcm.astype(float) / 32768.0                                 # the file as a listener gets it
    lufs, tp = kit.integrated_lufs(x), kit.true_peak_dbtp(x)
    aac_tp = kit.aac_true_peak(mp4)
    v_streams = [s for s in streams(video) if s["codec_type"] == "video"]
    m_streams = streams(mp4)
    print(f"audio {len(x) / kit.SR:.3f} s (WAV), LUFS {lufs:.2f}, true peak {tp:.2f} dBTP "
          f"(decoded AAC {aac_tp:.2f} dBTP)")
    print(f"video {float(v_streams[0]['duration']):.3f} s, muxed {[s['codec_type'] for s in m_streams]}")
    geo = sorted({m.split(".")[0] for m in sys.modules if m.split(".")[0] in GEO_STACK and sys.modules[m]})
    print(f"geo stack loaded in this process: {geo or 'none'}")

    # (1)-(3) level, start and end
    head = 20 * np.log10(np.abs(x[:int(0.1 * kit.SR)]).max() + 1e-12)
    tail = x[-int(1.0 * kit.SR):]
    rms = [20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-12) for seg in np.split(tail, 10)]
    click = float(np.abs(np.diff(x[-int(0.1 * kit.SR):], axis=0)).max())
    print(f"(1) LUFS {lufs:.2f} in [-15, -13]: {'PASS' if -15 <= lufs <= -13 else 'FAIL'}; "
          f"TP {tp:.2f} and decoded {aac_tp:.2f} <= -1: {'PASS' if max(tp, aac_tp) <= -1 else 'FAIL'}")
    print(f"(2) peak in the first 0.1 s {head:.1f} dBFS: {'PASS' if head > -30 else 'FAIL'}")
    print(f"(3) last 1 s in 100 ms steps (dBFS): {' '.join(f'{v:.0f}' for v in rms)}; "
          f"last sample {np.abs(x[-1]).max():.1e}; largest step in the last 0.1 s {click:.4f}: "
          f"{'PASS' if rms[-1] < rms[0] - 20 and np.abs(x[-1]).max() < 1e-4 else 'FAIL'}")

    # (4) the hits: the spectral flux peak within 0.1 s of each visual event
    centre, flux = onsets(x)
    rows = [("scene 1 starts, title whole", 0.0), ("scene 2 starts", p["starts"][1]),
            ("'normal' lands", p["normal"]), ("scene 3 starts", p["starts"][2])]
    rows += [(f"square {k + 1} ({1399 + k}-{1400 + k}) fills", t) for k, t in enumerate(p["squares"])]
    rows += [("'6 years' lands: drop", p["six"])]
    print("(4) EVENT TABLE   visual s   hit placed s   onset s   offset ms")
    worst = 0.0
    for label, te in rows:
        off = onset_offset(te, centre, flux)
        worst = max(worst, abs(off))
        print(f"    {label:<32}{te:8.3f}   {te:8.3f}   {te + off:8.3f}   {off * 1000:+7.1f}")
    print(f"    largest offset {worst * 1000:.1f} ms: {'PASS' if worst <= 0.03 else 'FAIL'} (30 ms)")

    # (5) the picture: the same packets in the muxed file
    same = video_md5(video) == video_md5(mp4)
    keys = ("codec_name", "width", "height", "nb_frames", "duration")
    vs = {k: v_streams[0].get(k) for k in keys}
    ms = {k: next(s for s in m_streams if s["codec_type"] == "video").get(k) for k in keys}
    print(f"(5) video packets identical: {'PASS' if same else 'FAIL'}; original {vs}; muxed {ms}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Water-year reel: soundtrack, mux and checks.")
    ap.add_argument("--cut", default="24s", choices=["24s"],
                    help="the film's cut; the music's section times are set for the 24 s cut")
    args = ap.parse_args()
    block_geo_stack()
    import onebit
    from onebit_slides import COLOURS
    from onebit_wateryear import WaterYearFilm
    film = WaterYearFilm(onebit.THEMES["zafaran"], COLOURS["zafaran"], args.cut)
    base = onebit.OUT / "social" / f"iran_wateryear_zafaran_fa_{args.cut}"
    wav = write(film, base.with_name(base.name + "_music.wav"))
    video = base.with_name(base.name + "_reel.mp4")
    mp4 = base.with_name(base.name + "_music_reel.mp4")
    kit.mux(video, wav, mp4)
    print("saved", wav)
    print("saved", mp4)
    report(film, wav, video, mp4)


if __name__ == "__main__":
    main()
