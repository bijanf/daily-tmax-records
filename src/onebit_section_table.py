"""THE WATER TABLE UNDER THE TEHRAN PLAIN (the slide «ground» of the dams long cut): the Alborz and the city on the
horizon, wells pumping on the plain, and the table falling from its 1372 level by about 15 m in 28 years while the
year runs. One of the four cross-sections of src/onebit_sections.py; drawn with src/onebit_section.py (the kit) and
src/onebit_scenery.py.

The picture says what the fact check of 9 Nov 2026 allows and no more (src/onebit_damsexplain2.py): the four lines
of words["ground_labels"] and the years. Depths are not to scale: the break band under the surface says so.

    python -I src/onebit_sections.py ground --sheet
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from PIL import Image, ImageChops  # noqa: E402

import onebit_scenery as Y  # noqa: E402
import onebit_section as S  # noqa: E402

SECONDS = 20.0                                      # the slide's length in the voiced cut (damsexplain2v_fa)
CUE = dict(                                         # scene-local seconds, on the owner's words (piece v08)
    line=2.2,                                       # «زیرِ زمینه»: the 1372 level, its label and the year
    fall=(3.0, 4.6),                                # «آبِ زیرزمینیِ تهران سالی حدودِ نیم متر داره پایین میره»: start, length
    deeper=7.0,                                     # the 15 m as the fall ends
    iran=9.0,                                       # «چهار تا پنج میلیارد»
    storm=13.4,                                     # «بیشتر از اونی که به زمین داره میده»: the storm's damp skin
)
GY = 250.0                                          # the ground's surface
BREAK = (284.0, 300.0)                              # the break band: the depth below it is not to scale
Y1372, DROP, CONE = 410.0, 220.0, 34.0              # the old level; the fall and the cones at the wells, px
WELLS = (84.0, 250.0, 416.0)
CLAY = ((505.0, 40.0, 30.0, 400.0), (616.0, 44.0, 300.0, 806.0), (712.0, 30.0, 60.0, 390.0))


def surf(x):
    return GY


def break_band(b: S.Box, y0: float, y1: float, a: float = 1.0, tooth: float = 12.0):
    """Two zigzag lines with paper between them: the ground between is left out."""
    xs = np.arange(-tooth, b.w + 2 * tooth, tooth)
    up = [(x, y0 + (4.0 if k % 2 else -4.0)) for k, x in enumerate(xs)]
    low = [(x, y1 + (4.0 if k % 2 else -4.0)) for k, x in enumerate(xs)]
    b.poly(up + low[::-1], S.rgba(S.PAPER, a))
    for pts in (up, low):
        b.line(pts, S.rgba(S.INK, 0.55 * a), 1.6)


def scene(w: int, h: int, t: float, words: dict, tp: float | None = None, cue: dict = CUE,
          years: tuple = (1372, 1400)) -> Image.Image:
    """The box at the scene's time t (inf: everything shown); `tp` is the running clock of the pumps."""
    tp = (t if np.isfinite(t) else 0.0) if tp is None else tp
    L = words["ground_labels"]
    b = S.Box(w, h, t)
    g = S.ground("table", w, h, surf, 14, clay=CLAY)

    Y.sky(b, GY)
    Y.cloud(b, 520 + 2.5 * tp, 54, 210, 80, 1)
    Y.cloud(b, 150 + 1.6 * tp, 92, 150, 56, 2, a=0.85)
    Y.alborz(b, GY - 14)
    Y.city(b, GY - 12, 80, 0, 0.27)
    b.paste(g.dry, g.mask)
    Y.top_face(b, surf, 14)

    damp = S.fade(t, cue["storm"], dur=1.2)          # this storm's water: a damp skin, far above the table
    if damp > 0:
        skin = ImageChops.subtract(b.below(GY + 1.0), b.below(GY + 30.0))
        b.paste(g.damp, skin, alpha=damp)
        b.rect(0, GY + 1.0, w, GY + 30.0, S.rgba(S.WATER, 0.30 * damp))    # wet, not only dark

    p = S.ramp(t, *cue["fall"])

    def table(x):
        cones = sum(np.exp(-((x - xw) / 46.0) ** 2) for xw in WELLS)
        return Y1372 + DROP * p + CONE * (0.3 + 0.7 * p) * cones

    S.water_table(b, g, table)
    break_band(b, *BREAK)
    a_line = S.fade(t, cue["line"])
    if a_line > 0:
        b.dashed(0, w, Y1372, S.rgba(S.WHITE, 0.95 * a_line), 3.0)
    for k, xw in enumerate(WELLS):
        Y.well(b, xw, GY, 742, table(xw), tp, 1.0, side=-1 if k == 2 else 1)
    Y.buildings(b, 478, 650, GY - 6, 3)
    Y.buildings(b, 700, 822, GY - 6, 5, 50, 90)
    for x, hh, seed in ((168, 56, 3), (336, 60, 1), (674, 66, 2)):
        Y.tree(b, x, GY - 4, hh, seed)
    Y.grass(b, surf, 0, 60, 1)
    Y.grass(b, surf, 110, 150, 2)
    Y.grass(b, surf, 186, 226, 3)
    Y.grass(b, surf, 356, 392, 4)

    a_drop = S.fade(t, cue["deeper"])
    if a_drop > 0:
        b.arrow(804, Y1372 + 10, 804, table(804) - 6, S.rgba(S.INK, a_drop), 3.6, 13.0)   # right of the pills

    year = int(round(years[0] + (years[1] - years[0]) * p))
    b.label(22, 78, words["fa_digits"](year), at=cue["line"], size=58, anchor="ls")
    b.label(776, Y1372 + 39, L[0], at=cue["line"], size=28)
    b.label(770, 548, L[1], at=cue["deeper"], size=38)
    two = L[2].replace(": ", ":\n", 1)
    b.label(806, 338, two, at=cue["storm"], size=28, lead=(640, GY + 16))
    b.label(806, 778, L[3], at=cue["iran"], size=27, colour=S.WATER_DARK)
    return b.done()
