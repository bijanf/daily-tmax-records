"""FOUR SHORT CUTS OF THE LONG DAMS EXPLAINER (damscut1..4_fa): the voiced long cut damsexplain2v_fa_voice_reel_v3.mp4
(178 s, posted 10 Nov 2026) cut at its own slide boundaries into four reels of 18 to 40 s, one misconception each.
Nothing is redrawn and no word or number changes: picture and sound are the posted film's.

    1 rain + soil     «این همه سیل آمد؛ پس آب کجا رفت؟»            the flood is not stored water; a storm wets the top 20-30 cm
    2 snow + seasons  «در ارتفاعات، آبِ این طوفان هنوز برف است»       the snow is the spring's water of the Karaj dam
    3 ground          «آبِ زیرِ زمینِ تهران: سالی حدودِ نیم متر پایین‌تر»
    4 sink            «زمینِ غربِ تهران فرو می‌نشیند»

The slide starts come from the voice manifest (src/onebit_damsexplain2v.py: SECONDS). Two things of the long film are
hidden, because they count its nine slides: the story's progress dashes (a strip of the same paper from 24 px above,
three periods of its 8-px dot pattern, is laid over them) and the counter "[n/9]" in the title bar (the bar's own
colour). The sound fades in over 0.15 s and out over the last 0.45 s (the voice ends at least 0.5 s before each slide does).

    python -I src/onebit_damscuts.py            # the four reels and their covers in outputs/onebit/social/
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import onebit_damsexplain2v as long  # noqa: E402

SOCIAL = long.OUT / "social"
SOURCE = SOCIAL / "damsexplain2v_fa_voice_reel_v3.mp4"
CUTS = (("damscut1_fa", ("rain", "soil")), ("damscut2_fa", ("snow", "seasons")), ("damscut3_fa", ("ground",)),
        ("damscut4_fa", ("sink",)))
DASHES = dict(x=56, y=152, w=912, h=24, up=24)      # the progress dashes (y 156-171) and the clean paper above them
COUNTER = dict(x=850, y=200, w=102, h=60, colour="0x2C1F17")   # "[n/9]" inside the title bar (y 196-263)
FADE_IN, FADE_OUT = 0.15, 0.45


def main() -> None:
    starts = dict(zip(long.SCENES, [sum(long.SECONDS[:k]) for k in range(len(long.SCENES))]))
    for stem, scenes in CUTS:
        k0, k1 = long.SCENES.index(scenes[0]), long.SCENES.index(scenes[-1])
        assert list(scenes) == list(long.SCENES[k0:k1 + 1]), scenes
        t0, dur = starts[scenes[0]], sum(long.SECONDS_OF[s] for s in scenes)
        out = SOCIAL / f"{stem}_voice_reel.mp4"
        d, c = DASHES, COUNTER
        video = (f"[0:v]split[a][b];[b]crop={d['w']}:{d['h']}:{d['x']}:{d['y'] - d['up']}[p];"
                 f"[a][p]overlay={d['x']}:{d['y']},drawbox=x={c['x']}:y={c['y']}:w={c['w']}:h={c['h']}:"
                 f"color={c['colour']}:t=fill,scale=out_color_matrix=bt709:out_range=tv,format=yuv420p[v]")
        audio = f"[0:a]afade=t=in:st=0:d={FADE_IN},afade=t=out:st={dur - FADE_OUT}:d={FADE_OUT}[au]"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t0}", "-t", f"{dur}", "-i", str(SOURCE),
                        "-filter_complex", video + ";" + audio, "-map", "[v]", "-map", "[au]", "-r", "30",
                        "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-profile:v", "high",
                        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "1.0", "-i", str(out), "-frames:v", "1",
                        str(SOCIAL / f"{stem}_cover.png")], check=True)
        print(f"saved {out.name}: {' + '.join(scenes)}, from {t0:.2f} s, {dur:.2f} s")


if __name__ == "__main__":
    main()
