"""Slow slide reels: one window that never moves, one bold line per scene, a story progress bar.

The frame shared by the slide films (onebit_snowloss, onebit_snowbands, onebit_glacier): a dot
grid over the whole 9:16 frame, one window whose top holds the scene's bold line (typed in, no
motion), its title bar the film's name and the scene counter (the follow line in the last
scene), a progress bar over it with one segment per scene, and the sources under it in the
film's language. A film subclasses Slides, sets itself up with setup() and draws its picture
in body(c, t); appear(i) says when each word of scene i comes in. Persian (lang "fa") reads
from the right: the progress bar fills from the right.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np

import onebit
from onebit import FA_TEXT, FULL, PIXEL, SIZES, TEXT, Canvas, Scene, Timeline, fa, title, words_of

WIN = (60, 196, 900, 1356)                       # the one window, clear of the app's buttons
BAR = 40                                         # its title bar
LEFT, RIGHT = 96, 924                            # type inside the window
RULE = 560                                       # the rule under the title
SMALL = 48                                       # px of the small line: readable on a phone
FOOTER = 1592                                    # baseline of the first source line
PROGRESS = 10                                    # height of the progress bar over the window
# themes in full colour (by their key), checked with the dataviz validator: a loss is an ordinal
# ramp of one hue (light end at least 2:1 on the field), snow a colour apart from it, and the
# land without snow a cool grey, so that even the lightest step stands apart from it
COLOURS = {"kashi": dict(land="#E2E5E7", snow="#5B9BC8", ramp=("#E39A63", "#C7612F", "#93351F")),
           "flieder": dict(land="#E3E1E8", snow="#6F8FD8", ramp=("#A98BD4", "#7E52B8", "#4B2280")),
           "baran": dict(land="#D3DEE5", rain="#2F6FB3")}


def span(years, lang: str = "fa") -> str:
    """A period in full years, one format everywhere: «۱۹۵۱ تا ۱۹۸۰», 1951–1980."""
    return f"{fa(years[0])} تا {fa(years[1])}" if lang == "fa" else f"{years[0]}–{years[1]}"


def decimal(v: float, digits: int = 1) -> str:
    """A German decimal comma: 2,1."""
    return f"{v:.{digits}f}".replace(".", ",")


def seasons(years) -> str:
    """Winters named by their March, written as seasons: (2016, 2025) -> 2015/16–2024/25."""
    return f"{years[0] - 1}/{str(years[0])[2:]}–{years[1] - 1}/{str(years[1])[2:]}"


class Slides:
    """The shared frame; a film calls setup() once its words are known and draws in body()."""

    def setup(self, th: onebit.Theme, lang: str, colour: dict | None, words: dict, pace: dict, app: str):
        """words: scenes ((bold line, small line), ...), follow, sources; pace: bpm and bars per scene."""
        self.th, self.lang, self.fa, self.colour = th, lang, lang == "fa", colour
        self.words, self.pace, self.app = words, pace, app
        self.bpm = pace["bpm"]
        self.beat = 60 / self.bpm
        scenes = tuple(Scene(b, FULL, t, line) for b, (t, line) in zip(pace["bars"], words["scenes"]))
        self.check(scenes)
        starts = np.cumsum([0.0] + [sc.bars * 4 * self.beat for sc in scenes])
        self.starts = starts
        self.L = Timeline(0, 0, 0, 0, 0, end=float(starts[-1]), camera=((0.0, FULL),),
                          scenes=tuple(float(t) for t in starts[:-1]))
        self.S = SimpleNamespace(scenes=scenes, os_name=app.upper(), lang=lang, race=[])
        dots = np.zeros((1920, 1080), bool)
        dots[4::8, 4::8] = dots[5::8, 4::8] = dots[4::8, 5::8] = dots[5::8, 5::8] = True
        dots[FOOTER - 36:FOOTER + 50] = False
        self.dots = dots

    def check(self, scenes):
        """Every small line on one line at SMALL px."""
        path, way = (FA_TEXT, "rtl") if self.fa else (TEXT, None)
        font = onebit._font(path, SMALL)
        for sc in scenes:
            assert font.getlength(sc.line, direction=way) <= RIGHT - LEFT, sc.line

    # ── time ──

    def scene(self, t: float) -> int:
        return int(np.searchsorted(self.starts[:-1], t, side="right")) - 1 if np.isfinite(t) else 0

    def appear(self, i: int) -> list:
        """When each word of scene i comes in (s into the scene). Slow: a line comes in over
        1.6 s; a line with a break shows its first part over 1.2 s and its second at later(i)."""
        ws = [w for w, _ in words_of(self.S.scenes[i].title, self.th)]
        n = len(ws) - ws.count("//")
        if "//" not in ws:
            return [0.3 + 1.6 * k / n for k in range(n)]
        first = ws.index("//")
        return [0.3 + 1.2 * k / first for k in range(first)] + [self.later(i) + 0.3 * k for k in range(n - first)]

    def settled(self, t: float) -> bool:
        """Past the second scene's picture (its fade, turn or sinking, self.done s into it)."""
        i = self.scene(t)
        return i > 1 or (i == 1 and t - self.starts[1] > self.done)

    def later(self, i: int) -> float:
        """When the part after a line break comes in: two beats on; a film can wait for its picture."""
        return 2 * self.beat + 0.3

    # ── drawing ──

    def say(self, c: Canvas, x, y, s, size=34, bold=False, colour=None, anchor=None):
        """A line in the film's script: Vazirmatn right to left in Persian, Inter otherwise."""
        if self.fa:
            return c.text(x, y, fa(s), onebit.FA_BOLD if bold else FA_TEXT, size, colour, anchor or "rs", "rtl")
        return c.text(x, y, s, onebit.BOLD if bold else TEXT, size, colour, anchor or "ls")

    def window(self, c: Canvas, i: int):
        th = self.th
        x, y, w, h = WIN
        c.frame(x, y, x + w, y + h, fill=th.paper)
        c.fill(x, y, x + w, y + BAR, th.ink)
        c.frame(x + 3, y + BAR + 3, x + w - 3, y + h - 3)
        last = i == len(self.S.scenes) - 1
        if last and self.fa:
            c.text(x + w - 12, y + BAR - 10, self.words["follow"], FA_TEXT, 28, th.title, "rs", "rtl")
        else:
            c.text(x + 12, y + BAR - 9, self.words["follow"] if last else self.app, PIXEL, 32, th.title)
            if not last:
                c.text(x + w - 12, y + BAR - 9, f"[{i + 1:02d}/{len(self.S.scenes):02d}]", PIXEL, 32, th.title, "rs")
        c.fill(x + 3, RULE, x + w - 3, RULE + 2, th.ink)

    def progress(self, c: Canvas, t: float):
        """Above the window, one segment per scene, as in a story: the scenes before are full, the
        scene playing fills as it plays, so a viewer sees there is more to come; on the cover all
        are empty. Persian fills from the right."""
        n, gap = len(self.S.scenes), 12
        x0, x1, y = WIN[0], WIN[0] + WIN[2], WIN[1] - 34
        seg = (x1 - x0 - gap * (n - 1)) / n
        i = self.scene(t)
        track = self.colour["land"] if self.colour else self.th.dots
        for k in range(n):
            if not np.isfinite(t) or k > i:
                frac = 0.0
            elif k < i:
                frac = 1.0
            else:
                frac = (t - self.starts[k]) / (self.starts[k + 1] - self.starts[k])
            a = x1 - (k + 1) * seg - k * gap if self.fa else x0 + k * (seg + gap)
            c.fill(a, y, a + seg, y + PROGRESS, track)
            done = seg * min(1.0, frac)
            if self.fa:
                c.fill(a + seg - done, y, a + seg, y + PROGRESS, self.th.mark)
            else:
                c.fill(a, y, a + done, y + PROGRESS, self.th.mark)

    def sources(self, c: Canvas):
        for k, line in enumerate(self.words["sources"]):         # under the window, inside its width
            if self.fa:
                c.text(WIN[0] + WIN[2], FOOTER + 34 * k, line, FA_TEXT, 26, self.th.head, "rs", "rtl")
            else:
                c.text(WIN[0], FOOTER + 34 * k, line, TEXT, 22, self.th.head)
            assert c.width(line, FA_TEXT if self.fa else TEXT, 26 if self.fa else 22,
                           "rtl" if self.fa else None) <= WIN[2], line

    def body(self, c: Canvas, t: float):
        raise NotImplementedError

    def draw(self, s: int, t: float = np.inf, size=SIZES["reel"]):
        c = Canvas(s, self.th, 1.0, (0.0, 0.0), size)
        c.pixels(0, 0, self.dots, self.th.dots)
        i = self.scene(t)
        dt = t - self.starts[i] if np.isfinite(t) else np.inf
        self.window(c, i)
        self.progress(c, t)
        at = self.appear(i)
        title(c, self.th, self.S.scenes[i], dt, self.lang, 1.0, LEFT, RIGHT, WIN[1] + BAR + 96, at,
              motion=False, line_at=at[-1] + 0.6, small=SMALL)
        self.body(c, t)
        self.sources(c)
        return c.im
