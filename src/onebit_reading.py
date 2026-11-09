"""READING TIME of a slide reel. The owner on 9 Nov 2026, about the El Niño reels of 55 and 47 s: «جفتشون سریع هستند
وقت برا خواندم کم» (both are fast, too little time to read). They carried 3.6 and 4.8 words a second.

For every slide of a `onebit_slides.Slides` film: the Persian strings on screen at the slide's end (headline and
small line in full, every other label at half weight; a token of digits and signs counts 0.4; Latin-only strings such
as the source line and the app name are not counted), the moment the last string appears, and the length it needs:

    need = max(now, last + 3 s, 1 s + (headline + small line + labels / 2) / 2.5 words a second), rounded up to 0.25 s

Fewer words beat longer slides: the five-dam reel of 106,677 views carried one number a slide at 4 s.

    python -I src/onebit_reading.py onebit_damsexplain              # the table and a SECONDS_OF to paste
    python -I src/onebit_reading.py onebit_twodeg --theme kahgel
"""

from __future__ import annotations

import argparse
import importlib
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import onebit  # noqa: E402
from onebit_slides import COLOURS, Slides  # noqa: E402

WPS, SETTLE, HOLD, LABELS = 2.5, 1.0, 3.0, 0.5
FA = re.compile(r"[؀-ۿ]")
NUM = re.compile(r"^[\d۰-۹٪%٫٬.,:+\-−–()\[\]/«»؟?؛]+$")


def weight(s: str) -> float:
    """Words a reader must take in: 0 for Latin-only strings, 0.4 for a token of digits and signs."""
    if not s or not FA.search(s):
        return 0.0
    toks = [t for t in s.replace("{", "").replace("}", "").split() if t != "//" and re.search(r"[\w؀-ۿ۰-۹]", t)]
    return sum(0.4 if NUM.match(t) else 1.0 for t in toks)


def load(film: Slides, scenes, seconds, step: float = 0.25) -> list:
    """Per slide: head words, label words, when the last string appears, the length it needs."""
    drawn: list = []
    orig = onebit.Canvas.text

    def text(self, x, y, s, path=onebit.PIXEL, size=22, colour=None, anchor="ls", direction=None):
        if path != onebit.PIXEL:
            drawn.append(s)
        return orig(self, x, y, s, path, size, colour, anchor, direction)

    onebit.Canvas.text = text
    try:
        out = []
        for i, name in enumerate(scenes):
            sc = film.S.scenes[i]
            head = weight(sc.title) + weight(sc.line or "")
            t0, dur = float(film.starts[i]), float(seconds[i])
            frames = []
            for k in range(int(dur / step)):
                drawn.clear()
                film.draw(1, t0 + k * step)
                frames.append((k * step, frozenset(drawn)))
            last = max([frames[k][0] for k in range(1, len(frames)) if frames[k][1] != frames[k - 1][1]] or [0.0])
            labels = sum(weight(s) for s in frames[-1][1])
            need = max(dur, last + HOLD, SETTLE + (head + LABELS * labels) / WPS)
            out.append(dict(scene=name, now=dur, last=last, head=round(head, 1), labels=round(labels, 1),
                            wps=round((head + LABELS * labels) / dur, 2), need=math.ceil(need * 4) / 4))
        return out
    finally:
        onebit.Canvas.text = orig


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("module", help="the film module, e.g. onebit_damsexplain")
    ap.add_argument("--theme", default="kahgel")
    args = ap.parse_args()
    m = importlib.import_module(args.module)
    cls = [v for v in vars(m).values() if isinstance(v, type) and issubclass(v, Slides) and v is not Slides
           and v.__module__ == m.__name__][0]
    film = cls(onebit.THEMES[args.theme], COLOURS[args.theme])
    rows = load(film, m.SCENES, m.SECONDS)
    for r in rows:
        flag = "  <- longer" if r["need"] > r["now"] else ""
        print(f'{r["scene"]:10s} now {r["now"]:6.2f}  last {r["last"]:5.2f}  head {r["head"]:5.1f}  labels {r["labels"]:5.1f}'
              f'  {r["wps"]:4.2f} w/s  need {r["need"]:6.2f}{flag}')
    print(f'total now {sum(r["now"] for r in rows):.2f} s, need {sum(r["need"] for r in rows):.2f} s')
    print("SECONDS_OF = dict(" + ", ".join(f'{r["scene"]}={r["need"]}' for r in rows) + ")")


if __name__ == "__main__":
    main()
