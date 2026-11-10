"""THE LONG CUT WITH THE OWNER'S VOICE (damsexplain2v_fa): damsexplain2_fa's eleven slides, each as long as his
piece of narration (src/damsexplain_voice.py: LEAD before, TAIL after; the last slide keeps END_TAIL for the closing
chord). The four cross-sections under Tehran (rain, soil, water table, subsidence) are drawn in the newsroom look
(src/onebit_sections.py: the real Alborz skyline and section, textured ground), each reveal timed on his words.

    python -I src/damsexplain_voice.py <recording>        the pieces and their manifest
    python -I src/onebit_damsexplain2v.py --stills
    python -I src/onebit_damsexplain2v.py                  the silent master; then the score's --part 5
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from PIL import Image, ImageEnhance  # noqa: E402

import damsexplain_voice as voice  # noqa: E402
import onebit  # noqa: E402
import onebit_damsexplain2 as two  # noqa: E402
import onebit_sections as sections  # noqa: E402
from onebit import OUT, SIZES, SOCIAL_CRF  # noqa: E402
from onebit_slides import COLOURS  # noqa: E402

BASE = "damsexplain2v_fa"
END_TAIL = 2.8                                      # s after the last word: the open chord rings out
MAN = json.loads((voice.OUT / "manifest.json").read_text(encoding="utf-8"))
assert [q["scene"] for q in MAN["pieces"]] == list(two.SCENES)
SCENES = two.SCENES


def _len(q, last):
    return math.ceil((MAN["lead"] + q["seconds"] + (END_TAIL if last else MAN["tail"])) * 4) / 4


SECONDS_OF = {q["scene"]: _len(q, k == len(MAN["pieces"]) - 1) for k, q in enumerate(MAN["pieces"])}
SECONDS = tuple(SECONDS_OF[k] for k in SCENES)
PACE = dict(bpm=60, bars=tuple(s / 4 for s in SECONDS))
END = sum(SECONDS)
assert END <= 179.0, END                            # Instagram recommends reels up to 3 minutes
COVER_T = 1.0
for _k in ("rain", "soil", "ground", "sink"):       # the four cross-sections: their cues are on the owner's words
    assert sections.module(_k).SECONDS == SECONDS_OF[_k], _k


class DamsFilm2V(two.DamsFilm2):
    def __init__(self, th: onebit.Theme, colour: dict):
        self.n = json.loads((two.one.num.DATA / "numbers.json").read_text(encoding="utf-8"))
        self.check_data()
        self.words = two.words2()
        self.setup(th, "fa", colour, self.words, PACE, two.APP)
        assert abs(self.starts[-1] - END) < 1e-9
        self.hook_at_once = True
        self.th = th
        self.grid_pic = two.one.five_dams()
        snow = Image.open(two.one.SNOW_PIC).convert("RGB")
        self.snow = snow.resize((snow.width // 3, snow.height // 3), Image.LANCZOS)
        self.sprites = {k: two.one.el2.ElNino2Film.sprite(self, k) for k in ("pale", "wet")}
        storm, self.storm_xy = two.storm_picture()
        self.storm = ImageEnhance.Color(ImageEnhance.Contrast(storm).enhance(1.18)).enhance(1.12)

    def section(self, c, name, dt, **kw):               # the newsroom look: src/onebit_sections.py
        im = sections.scene(name, two.BOX[2], two.BOX[3], dt, self.words, tp=dt if np.isfinite(dt) else None, **kw)
        c.im.paste(im, (c.X(two.BOX[0]), c.Y(two.BOX[1])))

    def s_rain(self, c, dt):
        self.section(c, "rain", dt)

    def s_soil(self, c, dt):
        self.section(c, "soil", dt, wet_cm=two.WET_CM)

    def s_ground(self, c, dt):
        self.section(c, "ground", dt, years=two.GW_YEARS)

    def s_sink(self, c, dt):
        self.section(c, "sink", dt)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stills", action="store_true")
    ap.add_argument("--at", type=float, nargs="*")
    args = ap.parse_args()
    film = DamsFilm2V(onebit.THEMES["kahgel"], COLOURS["kahgel"])
    print("seconds", SECONDS, "end", END)
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / BASE
    film.draw(1, COVER_T).save(f"{base}_cover.png", optimize=True)
    if args.stills or args.at:
        times = args.at or sorted({round(float(film.starts[i] + f * (film.starts[i + 1] - film.starts[i])), 2)
                                   for i in range(len(SECONDS)) for f in (0.3, 0.97)})
        for t in times:
            film.draw(1, t).save(f"{base}_t{t:06.2f}.png")
        print("stills", len(times))
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="silent")


if __name__ == "__main__":
    main()
