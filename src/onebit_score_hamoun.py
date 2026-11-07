"""The score of the Hamoun reel (hamoun_fa, 26 s): «هامون بیش از پنج برابرِ تهران بود؛ بهارِ امسال، حدودِ یک تهران».
An original track in Dashti (the Shur set on G: G, A-koron, Bb, C, D, Eb, F), the avaz of folk laments, built from the
Persian sound kit (onebit_persian) and timed to the film's clock (data/hamoun/reel/timeline.json). Everything in the
music is synthesized here: no samples. The one voice is the narration: seven Persian segments, synthesized offline
(the fa_IR ganji medium voice) and placed on the film's clock; the music is ducked under them.

The lake is the music's data: each spring on the counter plays one note whose pitch is its area on fourteen Dashti
steps from G3 (no water) to G5 (4,267 km2, the lakes' whole bed): the runs climb with the full lakes of 1366-1372
and fall into the dry springs; a spring under 100 km2 plays a muted tombak stroke on the floor instead of a note, and
a spring without a trusted number (1381) plays nothing.

    0.00 s         the hook: a santur strike, G4 over G3, and the Dashti descent D4 C4 Bb3 A-koron3 G3 on the setar
    1.60-2.80 s    the rewind: the hook's first second played backwards on tape, slowing to a halt, over a swell
    2.80-4.30 s    run A (1366-1372): a santur note and a daf tak on each spring, climbing to the full lake
    4.30 s         the full lake (1372, the hero frame): an impact on G1, a daf bam and its jingles (zang), the santur chord G3 D4 G4,
                   the pad on G (G3 D4 G4) to 5.9 s
    5.90-7.02 s    run A2 (1373-1377): santur notes on the springs
    7.30-11.21 s   run B (1378-1395): setar plucks on the springs (muted tombak where under 100 km2), the pad gone,
                   a low drone on G2
    11.45-15.95 s  run C (the last ten springs): santur and a soft daf on each, the five dry springs as muted strokes
    15.95 s        1405 lands: a soft impact, the santur on G3 D4, the pad on G3 Bb3 D4 to 25.4 s
    20.30 s        the kamancheh: the Dashti cadence C4 Bb3 A-koron3 G3
    23.85 s        the hook returns; a reversed santur strike on G4 swells into 26.00 s (the loop lands on the first
                   frame's strike)

Narration (seven segments; the start of each speech is fixed; the music is ducked DUCK_DB under each, with an attack
of DUCK_ATTACK before the speech and a release of DUCK_RELEASE after it). The Piper text differs from the subtitles
only where the voice needs it («کیلُمِتر», «صد» spelled for the voice, a comma after «شما»). The measured speech
times are written to data/hamoun/reel/narration/manifest.json, which the film reads for its subtitles.

Mix: -14 LUFS integrated, true peak -1.5 dBTP in the WAV (the decoded AAC stays at -1 dBTP or below).

    python -I src/onebit_score_hamoun.py                    both cuts
    python -I src/onebit_score_hamoun.py --narration-only   the voice segments and their timing only

The narration needs ONEBIT_TTS_BIN (the piper executable) and ONEBIT_TTS_MODEL (the fa_IR-ganji-medium .onnx) the
first time; the segments are cached in data/hamoun/reel/narration/.
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
from scipy.signal import butter, lfilter, resample_poly, sosfiltfilt

sys.path.insert(0, str(Path(__file__).resolve().parent))
for _m in ("shapely", "cartopy", "fiona", "geopandas"):      # the geo stack stays out of this process
    sys.modules.setdefault(_m, None)

import onebit  # noqa: E402
import onebit_persian as kit  # noqa: E402

SR = kit.SR
ROOT = onebit.ROOT
REEL = ROOT / "data" / "hamoun" / "reel"
SOCIAL = onebit.OUT / "social"
BASE = "hamoun_fa"
MODE = "dashti"
TONIC = kit.note_hz("G3")
LAKES_KM2 = 4267.0
STEPS = 14                                      # the springs' notes: 14 Dashti steps from G3 to G5
DRY = 100.0                                     # km2: under this a spring plays a muted stroke
LUFS, TP = -14.0, -1.5
TAIL = 3.0
END_FADE = 0.03
SEED = 29

TTS_ENV_BIN, TTS_ENV_MODEL = "ONEBIT_TTS_BIN", "ONEBIT_TTS_MODEL"
NARR_DIR = REEL / "narration"
VOICE = "fa_IR-ganji-medium"
LENGTH = 0.85
NOISE_W = 0.0
PAD_S = 0.03
DUCK_DB, DUCK_ATTACK, DUCK_RELEASE = 9.5, 0.15, 0.40
RATIO_TARGET = 14.0                             # dB: the voice over the ducked music, over all the speech
GAP = 0.03
# (name, start s, subtitle lines, the text for the voice, its length scale)
NARRATION = (
    ("s1", 0.15, ("هامونِ سیستان، بیش از پنج برابرِ تهران بود.",),
     "هامونِ سیستان، بیش از پنج برابرِ تهران بود.", LENGTH),
    ("s2", 3.40, ("در اواخرِ بهارِ سال‌های پُرآب، حدودِ ۴٬۰۰۰ کیلومتر مربع.",),
     "در اواخرِ بهارِ سال‌های پُرآب، حدودِ چهار هزار کیلُمِتر مربع.", LENGTH),
    ("s3", 7.95, ("بعد، کم و زیاد شد؛ گاهی تقریباً بی‌آب.",),
     "بعد، کم و زیاد شد؛ گاهی تقریباً بی‌آب.", LENGTH),
    ("s4", 11.45, ("در اواخرِ بهارِ ده سالِ آخر،", "پنج بار کمتر از ۱۰۰ کیلومتر مربع."),
     "در اواخرِ بهارِ ده سالِ آخر، پنج بار کمتر از صد کیلُمِتر مربع.", LENGTH),
    ("s5", 16.25, ("بهارِ امسال، سیلاب‌های فصلی بخشی از هامون را پُر کرد.",),
     "بهارِ امسال، سیلاب‌های فصلی بخشی از هامون را پُر کرد:", LENGTH),
    ("s6", 20.30, ("حدودِ یک تهران؛ حدودِ یک‌هفتمِ هامونِ پُر.",),
     "حدودِ یک تهران؛ حدودِ یک‌هفتمِ هامونِ پُر.", LENGTH),
    ("s7", 23.85, ("شما هامونِ پُر را دیده‌اید؟",),
     "شما، هامونِ پُر را دیده‌اید؟", 0.95),
)


# ── the film's clock ────────────────────────────────────────────────────────

def timeline() -> dict:
    return json.loads((REEL / "timeline.json").read_text())


def steps(tl: dict) -> list:
    return [dict(s, run=r["name"]) for r in tl["runs"] for s in r["steps"]]


def pitch_of(km2: float) -> float:
    k = int(round(min(max(km2, 0.0), LAKES_KM2) / LAKES_KM2 * STEPS))
    return kit.degree(MODE, k % 7, k // 7, TONIC)


# ── narration ───────────────────────────────────────────────────────────────

def _cached(name: str, text: str, ls: float):
    try:
        man = {m["name"]: m for m in json.loads((NARR_DIR / "manifest.json").read_text(encoding="utf-8"))}
        m = man[name]
        if m["voice_text"] != text or m["length_scale"] != ls or m["voice"] != VOICE or m["noise_w_scale"] != NOISE_W:
            return None
        rate, pcm = wavfile.read(str(NARR_DIR / f"{name}.wav"))
        assert rate == SR
        return pcm.astype(float) / 32767.0, m["lead"], m["speech"]
    except (OSError, KeyError, ValueError, AssertionError):
        return None


def synth(name: str, text: str, ls: float) -> tuple:
    """One segment: the offline voice, cut to its speech (PAD_S kept before and after), at SR, mono, peak 0.9.
    Returns (samples, lead s before the speech, speech s)."""
    hit = _cached(name, text, ls)
    if hit is not None:
        return hit
    binary, model = os.environ.get(TTS_ENV_BIN), os.environ.get(TTS_ENV_MODEL)
    if not binary or not model:
        sys.exit(f"the narration needs {TTS_ENV_BIN} and {TTS_ENV_MODEL} (or the cached segments in {NARR_DIR})")
    assert Path(model).name.startswith(VOICE), (model, VOICE)
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "raw.wav"
        subprocess.run([binary, "-m", model, "--length-scale", str(ls), "--noise-w-scale", str(NOISE_W),
                        "-f", str(raw)], input=(text + "\n").encode("utf-8"), check=True, capture_output=True)
        rate, pcm = wavfile.read(str(raw))
    x = pcm.astype(float) / 32768.0
    x = x[:, 0] if x.ndim > 1 else x
    a = np.flatnonzero(np.abs(x) > 0.01 * np.abs(x).max())
    on, off = int(a[0]), int(a[-1]) + 1
    pad = int(round(PAD_S * rate))
    x = x[max(on - pad, 0): min(off + pad, len(x))]
    lead, speech = (on - max(on - pad, 0)) / rate, (off - on) / rate
    f = Fraction(SR, rate)
    y = resample_poly(x, f.numerator, f.denominator)
    edge = int(0.01 * SR)
    y[:edge] *= np.linspace(0, 1, edge)
    y[-edge:] *= np.linspace(1, 0, edge)
    y = 0.9 * y / np.abs(y).max()
    NARR_DIR.mkdir(parents=True, exist_ok=True)
    wavfile.write(str(NARR_DIR / f"{name}.wav"), SR, (np.clip(y, -1, 1) * 32767).astype(np.int16))
    return y, lead, speech


def split_at(y: np.ndarray, lead: float, speech: float, n_lines: int) -> list:
    """Where a segment's subtitle changes line: the longest pause (RMS under -38 dB of the peak, at least 80 ms) in
    the middle of the speech (30-85 %). Returns the times (s after the speech's onset)."""
    if n_lines == 1:
        return []
    hop = int(0.01 * SR)
    env = np.sqrt(np.convolve(y ** 2, np.ones(hop) / hop, mode="same"))[::hop]
    db = 20 * np.log10(env / env.max() + 1e-9)
    quiet = db < -38
    t = np.arange(len(db)) * 0.01 - lead
    best, run = None, []
    for k, q in enumerate(quiet):
        if q and 0.30 * speech <= t[k] <= 0.85 * speech:
            run.append(t[k])
        else:
            if len(run) >= 8 and (best is None or len(run) > len(best)):
                best = run
            run = []
    assert best is not None, "no pause to split the subtitle at"
    return [round(float(np.mean(best)), 3)]


def narration(n: int) -> tuple:
    """The voice on the clock: (voice, spans [(name, start, end)], manifest)."""
    v = np.zeros(n)
    spans, man, prev = [], [], 0.0
    for name, start, lines, text, ls in NARRATION:
        y, lead, speech = synth(name, text, ls)
        assert start >= prev + GAP, (name, start, prev)
        assert start + speech <= 25.85, (name, start + speech)
        i0 = round((start - lead) * SR)
        v[i0:i0 + len(y)] += y[:max(0, n - i0)]
        cuts = split_at(y, lead, speech, len(lines))
        bounds = [start] + [start + c for c in cuts] + [start + speech]
        subs = [dict(text=s, start=round(bounds[k], 3), end=round(bounds[k + 1] + (0.25 if k == len(lines) - 1 else 0),
                                                                        3)) for k, s in enumerate(lines)]
        spans.append((name, start, start + speech))
        man.append(dict(name=name, start=start, speech=round(speech, 4), lead=round(lead, 4), length_scale=ls,
                        noise_w_scale=NOISE_W, voice=VOICE, voice_text=text, subtitles=subs))
        prev = start + speech
        print(f"  {name}: {start:6.2f}-{start + speech:6.2f} s ({speech:.2f} s)  " + " | ".join(
            f"{s['start']:.2f}-{s['end']:.2f}" for s in subs))
    subs = [x for m in man for x in m["subtitles"]]                 # a line stays up to 0.25 s after its speech,
    for a, b in zip(subs, subs[1:] + [dict(start=25.98)]):           # never past the next line or the end
        a["end"] = round(min(a["end"], b["start"] - 0.05 if b["start"] < 25.98 else 25.98), 3)
    NARR_DIR.mkdir(parents=True, exist_ok=True)
    (NARR_DIR / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")
    return v, spans, man


def duck_gain(mask: np.ndarray) -> np.ndarray:
    a, r = math.exp(-1 / (SR * DUCK_ATTACK)), math.exp(-1 / (SR * DUCK_RELEASE))
    target = np.where(mask, -DUCK_DB, 0.0)
    g = np.empty(len(target))
    cur = 0.0
    edges = np.flatnonzero(np.diff(target)) + 1
    for s0, s1 in zip(np.r_[0, edges], np.r_[edges, len(target)]):
        k = a if target[s0] < cur else r
        g[s0:s1] = lfilter([1 - k], [1, -k], np.full(s1 - s0, target[s0]), zi=[k * cur])[0]
        cur = g[s1 - 1]
    return 10 ** (g / 20)


# ── the music ───────────────────────────────────────────────────────────────

def deg(step: int, octave: int = 0) -> float:
    return kit.degree(MODE, step % 7, octave + step // 7, TONIC)


def compose(tl: dict, log: list) -> np.ndarray:
    kit.reseed(SEED)
    dur = tl["duration"]
    bus = {k: kit.new_track(dur, TAIL) for k in ("santur", "setar", "kam", "daf", "low", "pad", "fx", "drone")}
    ev = []

    def hit(name, sound, t, gain=1.0, pan=0.0):
        kit.place(bus[name], sound, t, gain, pan)
        ev.append((round(t, 3), name))

    def hook(t0: float):
        hit("santur", kit.santur(deg(0, 1), 3.0, 0.32), t0)
        hit("santur", kit.santur(deg(0), 3.0, 0.18), t0)
        for k, st in enumerate((4, 3, 2, 1, 0)):
            hit("setar", kit.setar(deg(st), 1.0, 0.55), t0 + 0.35 + 0.22 * k, pan=-0.2)

    hook(0.0)
    # the rewind: the hook's first 1.2 s on tape, backwards, slowing to a halt; a swell under it
    seg = kit.new_track(1.6)
    kit.place(seg, kit.santur(deg(0, 1), 1.6, 0.3), 0.0)
    for k, st in enumerate((4, 3, 2)):
        kit.place(seg, kit.setar(deg(st), 1.0, 0.5), 0.35 + 0.22 * k)
    hit("fx", kit.rewind(seg, seconds=tl["run_a"] - tl["rewind"]), tl["rewind"], 0.8)
    hit("fx", kit.riser(tl["run_a"] - tl["rewind"], 0.25, 120, 900), tl["rewind"], 0.6)
    # the springs
    land_a = tl["runs"][0]["steps"][-1]["t"]
    for s in steps(tl):
        t, run = s["t"], s["run"]
        if s.get("gap"):
            continue
        if s["km2"] < DRY:
            hit("low", kit.tombak("tom", 0.5, pitch=72.0), t, 0.7)
            continue
        f = pitch_of(s["km2"])
        if run in ("A", "A2"):
            hit("santur", kit.santur(f, 1.2, 0.42), t, pan=0.15)
            if run == "A":
                hit("daf", kit.daf("tak", 0.45 + 0.08 * tl["runs"][0]["steps"].index(
                    next(x for x in tl["runs"][0]["steps"] if x["year"] == s["year"]))), t)
        elif run == "B":
            hit("setar", kit.setar(f, 0.7, 0.55), t, pan=-0.15)
        else:
            hit("santur", kit.santur(f, 1.6, 0.42), t, pan=0.1)
            hit("daf", kit.daf("tak", 0.4), t)
    # the full lake (the hero frame)
    hit("low", kit.impact(2.2, 0.75, kit.note_hz("G1")), land_a)
    hit("daf", kit.daf("bam", 0.9), land_a)
    hit("daf", kit.daf("zang", 0.5), land_a + 0.02)
    for st, o in ((0, 0), (4, 0), (0, 1)):
        hit("santur", kit.santur(deg(st, o), 2.4, 0.3), land_a)
    hit("pad", kit.pad([deg(0), deg(4), deg(0, 1)], tl["runs"][1]["t0"] - land_a + 0.6, 0.35), land_a)
    # the drone under the dry decades
    b0, b1 = tl["runs"][2]["t0"], tl["land"]
    hit("drone", kit.pad([deg(0, -1)], b1 - b0 + 0.8, 0.30, cutoff=500.0, attack=0.8), b0)
    # 1405 lands
    land = tl["land"]
    hit("low", kit.impact(1.8, 0.45, kit.note_hz("G1")), land)
    hit("santur", kit.santur(deg(0), 3.0, 0.3), land)
    hit("santur", kit.santur(deg(4), 3.0, 0.22), land + 0.03)
    hit("pad", kit.pad([deg(0), deg(2), deg(4)], 25.4 - land, 0.32, cutoff=1400.0, release=1.6), land)
    for t, st in ((17.2, 4), (18.0, 3), (22.2, 2), (22.9, 1)):
        hit("setar", kit.setar(deg(st), 1.0, 0.4), t, pan=-0.25)
    for st, dt, d in ((3, 0.0, 1.0), (2, 0.9, 0.6), (1, 1.4, 0.6), (0, 1.9, 1.6)):
        hit("kam", kit.kamancheh(deg(st, 1), d, 0.45), 20.3 + dt, pan=0.2)
    hook(23.85)
    swell = kit.reverse(kit.santur(deg(0, 1), 1.2, 0.3))
    hit("fx", swell, dur - len(swell) / SR)
    # the mix: sends to the room, the levels
    sends = dict(santur=0.35, setar=0.35, kam=0.35, daf=0.2, low=0.15, pad=0.0, fx=0.25, drone=0.0)
    level = dict(santur=0.9, setar=0.8, kam=0.6, daf=0.7, low=0.8, pad=0.45, fx=0.6, drone=0.5)
    n = len(bus["santur"])
    room = np.zeros((n, 2))
    dry = np.zeros((n, 2))
    for k, x in bus.items():
        dry += level[k] * x
        if sends[k]:
            room += sends[k] * level[k] * x
    wet = kit.reverb(room, t60=2.4)[:n]
    log.append(f"events: {len(ev)}; first {ev[:4]}; last {ev[-3:]}")
    return dry + wet


def _air_cut(x, fc: float = 12000.0):
    return sosfiltfilt(butter(4, fc, "lowpass", fs=SR, output="sos"), x, axis=0)


def _bass_mono(x, fc: float = 120.0):
    lo = sosfiltfilt(butter(4, fc, "lowpass", fs=SR, output="sos"), x, axis=0)
    m = lo.mean(axis=1, keepdims=True)
    return x - lo + m


def md5_stream(media) -> str:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(media), "-map", "0:v:0", "-c", "copy", "-f", "data", "-"],
                         check=True, capture_output=True).stdout
    return hashlib.md5(raw).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--narration-only", action="store_true")
    args = ap.parse_args()
    tl = timeline()
    dur = tl["duration"]
    n = int(round((dur + TAIL) * SR))
    print("narration:")
    voice, spans, _ = narration(n)
    if args.narration_only:
        return
    log = []
    music = compose(tl, log)
    print("\n".join(log))
    music = _air_cut(music)
    track_m = kit.master(_bass_mono(music), lufs=LUFS, tp=TP, seconds=dur, fade_out=END_FADE)
    mask = np.zeros(n, bool)
    core = np.zeros(n, bool)
    for _, a, b in spans:
        mask[max(0, round((a - DUCK_ATTACK) * SR)):round(b * SR)] = True
        core[round(a * SR):round(b * SR)] = True
    music_d = music * duck_gain(mask)[:, None]
    rms = lambda z: float(np.sqrt(np.mean(np.square(z))))  # noqa: E731
    v = sosfiltfilt(butter(2, 60.0, "highpass", fs=SR, output="sos"), voice)
    v *= rms(music_d[core]) * 10 ** (RATIO_TARGET / 20) / rms(v[core])
    total = _air_cut(music_d + np.stack([v, v], axis=1))
    for name, a, b in spans:                                     # the voice over the ducked music, each sentence
        i0, i1 = round(a * SR), round(b * SR)
        ratio = 20 * math.log10(rms(v[i0:i1]) / rms(music_d[i0:i1]))
        print(f"  {name}: voice {ratio:5.1f} dB over the ducked music")
        assert ratio >= 10.0, (name, ratio)
    track_v = kit.master(_bass_mono(total), lufs=LUFS, tp=TP, seconds=dur, fade_out=END_FADE)
    for name, track, video in (("music", track_m, f"{BASE}_reel.mp4"), ("voice", track_v, f"{BASE}_voice_reel.mp4")):
        wav = kit.write_wav(SOCIAL / f"{BASE}_{name}.wav", track)
        x = wavfile.read(str(wav))[1].astype(float) / 32768
        print(f"{wav.name}: {kit.integrated_lufs(x):.2f} LUFS, true peak {kit.true_peak_dbtp(x):.2f} dBTP, "
              f"{len(x) / SR:.2f} s")
        src = SOCIAL / video
        out = SOCIAL / f"{BASE}{'_voice' if name == 'voice' else ''}_music_reel.mp4"
        if not src.exists():
            print(f"  no {src.name} yet: not muxed")
            continue
        kit.mux(src, wav, out)
        same = md5_stream(src) == md5_stream(out)
        dec = subprocess.run(["ffmpeg", "-v", "error", "-i", str(out), "-vn", "-f", "f32le", "-ac", "2", "-ar",
                              str(SR), "-"], check=True, capture_output=True).stdout
        y = np.frombuffer(dec, dtype="<f4").reshape(-1, 2).astype(float)
        print(f"  {out.name}: decoded {kit.integrated_lufs(y):.2f} LUFS, true peak {kit.true_peak_dbtp(y):.2f} dBTP; "
              f"video stream {'identical to' if same else 'DIFFERENT from'} {src.name}")
        assert same and kit.true_peak_dbtp(y) <= -1.0


if __name__ == "__main__":
    main()
