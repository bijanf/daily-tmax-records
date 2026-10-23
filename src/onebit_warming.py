"""WHO HEATED THE PLANET: the ten countries whose fossil fuels and industry warmed the Earth most.

The index is the warming each country's emissions of CO2, methane and nitrous oxide from fossil
fuels and industry have caused so far, as a share of the world's (warming.py: Jones et al.,
Scientific Data 2023, release 2025.1), from 1860 to 2024. Land use is not counted, and the
screen says so: with it the USA leads from the start (warming.py). The ranking changes hands as
the film runs: the UK leads until 1900, the USA from 1901; China is second since 1997. Then the
same ten are rated by the Climate Action Tracker on whether their plans and policies are enough
for 1.5 °C: none of the nine rated is (Ukraine's rating is suspended during the war; France's
target is the EU's). The film closes on the USA, the largest share of all.

One still 1-bit desktop: a dot grid over the whole frame and one window that never moves. Its
top holds the scene's bold line, so the title is part of the chart, not a band above it; below
it the year and ten rows that jump to their places on the beat (rank, country, bar, share). The
country the caption names is set in inverse video. The effort scene adds a five-cell battery to
each row, one row per half beat, filled to the tracker's grade; none is full. Persian (--lang fa)
mirrors the rows: the rank and the name on the right, the bars growing to the left.

Cuts: 20s (8 bars of 96 BPM, one year per beat) and 25s (10 bars, calmer, captions a tenth
bigger). Sound: onebit_steam, a steam engine whose beat thickens with the industry, and a steam
organ playing the data.

    outputs/onebit/social/who_heated_<theme>_<cut>[_fa]_reel.mp4, _cover.png, _music.wav

    python -I src/onebit_warming.py                       # Berliner.Luft.1bit, 20 s, English
    python -I src/onebit_warming.py --lang fa --cut 25s
    python -I src/onebit_warming.py --stills              # cover and frames, no video
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

import onebit  # noqa: E402
import warming  # noqa: E402
from onebit import (FA_BOLD, FA_TEXT, FULL, GROTESK, MONO, OUT, PIXEL, SIZES, SOCIAL_CRF, Canvas,  # noqa: E402
                    Scene, Timeline, fa, title, words_of)

# Climate Action Tracker overall rating, 1 critically insufficient, 2 highly insufficient,
# 3 insufficient, 4 almost sufficient, 5 1.5 °C Paris Agreement compatible (climateactiontracker.org,
# country pages read 23 October 2026: USA and Canada 13 Oct 2026, China 30 Jun 2026, Germany and EU
# 3 Aug 2026, India 9 Sep 2026, UK 28 Oct 2025, Russia 30 Sep 2025, Japan 4 Nov 2024). France has
# no rating of its own: its target is the EU's, rated 3. Ukraine: rating suspended since the
# Russian invasion (4 Mar 2022). None of CAT's 42 countries is rated 1.5 °C compatible overall.
CAT = {"USA": 1, "China": 2, "Russia": 1, "Germany": 3, "India": 2, "United Kingdom": 3, "Japan": 3,
       "Canada": 2, "France": 3, "Ukraine": None}
VIA_EU = {"France"}
# the USA: 344,480 of 8,126,964 thousand people on 1 January 2024 (UN World Population Prospects
# 2024, Summary of Results, Table A2): 4.2 %
USA_PEOPLE = 100 * 344_480 / 8_126_964

# tempo, scene lengths (bars), the years of the race (one per step), beats per race step,
# beats before the batteries and per battery, caption scale (1.2 would run the small lines
# past the window). The last scene lasts the last two bars: onebit_steam's close.
CUTS = {"20s": dict(bpm=96, bars=(1, 3, 2, 2), per=1, lead=1, cell=1 / 2, caption=1.0,
                    years=(1870, 1880, 1890, 1901, 1915, 1930, 1950, 1970, 1985, 2000, 2012, 2024)),
        "25s": dict(bpm=96, bars=(1.5, 4, 2.5, 2), per=1, lead=1, cell=1 / 2, caption=1.1,
                    years=(1868, 1876, 1884, 1892, 1901, 1910, 1925, 1940, 1955, 1970, 1980, 1990, 2000,
                           2008, 2016, 2024))}
# the hook's board (not 1851: that board rests on 0.3 thousandths of a degree of warming); the
# steps at which the caption names the USA (first since 1901: 24.4 against 23.8) and China
# (second since 1997, but 8.0 against Russia's 8.0 on screen then; 8.5 against 7.8 in 2000)
FIRST, USA_YEAR, CHINA_YEAR = 1860, 1901, 2000
SCALE = 35.0                                        # per cent at the bars' full length (USA 1930: 34.7)
WIN = (60, 196, 900, 1356)                          # the one window, clear of the app's buttons
BAR = 40                                            # its title bar
LEFT, RIGHT = 96, 924                               # type inside the window
RULE, HEAD, ROW0, PITCH = 560, 650, 724, 80         # rule under the title; chart head; rows
NAME, BX, BW, BH = 150, 392, 320, 44                # x of the name and the bar; bar length, height
CELLS, CELL, GAP = 770, 22, 5                       # the battery column: x, cell width, gap
FOOTER = 1592                                       # the source line; the note under it

WORDS = {
    "en": dict(
        scenes=((("Which countries {heated the planet?}",), "from fossil fuels and industry, since 1851"),
                (("First the {UK},", "then the {USA}.", "// {China} is now #2"), ""),
                (("Doing enough to cut emissions? {Not one of 9}",), "rated by the Climate Action Tracker"),
                (("Biggest share: the {USA}",), "{usa:.1f} % of the warming, but {people:.1f} % of people")),
        head="share of greenhouse warming so far", effort="effort (full = enough)", unrated="unrated: war",
        eu="EU rating", app="Warming.Rank", follow="Follow for more climate data in 1-bit",
        source="Data: Jones et al. 2023 (2025.1) · UN WPP 2024 · Climate Action Tracker",
        note="CO2, methane and N2O from fossil fuels and industry; land use not counted"),
    "fa": dict(
        scenes=((("کدام کشورها {زمین را گرم کردند؟}",), "گرمایشِ سوخت‌های فسیلی و صنعت، از ۱۸۵۱ تاکنون"),
                (("اول {بریتانیا}،", "بعد {آمریکا}.", "// حالا {چین} دوم است"), ""),
                (("تلاشِ کافی برای کاهش انتشار؟ {هیچ‌یک از ۹ کشور}",), "ارزیابی Climate Action Tracker"),
                (("بیشترین سهم: {آمریکا}",), "{usa:.1f}٪ از گرمایش، اما {people:.1f}٪ از جمعیت جهان")),
        head="سهم از گرمایش گلخانه‌ای تا آن سال", effort="تلاش (پر = کافی)", unrated="بدون رتبه: جنگ",
        eu="رتبهٔ EU", app="Warming.Rank", follow="برای داده‌های اقلیمی بیشتر، فالو کنید",
        source="Data: Jones et al. 2023 (2025.1) · UN WPP 2024 · Climate Action Tracker",
        note="CO2، متان و N2O از سوخت‌های فسیلی و صنعت؛ تغییر کاربری زمین حساب نشده"),
}


class WarmingFilm:
    """Draws the film; exposes L, S, bpm, beat, appear(), steps_t, cells_t and hits for onebit_steam."""

    def __init__(self, th: onebit.Theme, cut: str = "20s", lang: str = "en", component: str = "Fossil"):
        self.th, self.cut, self.lang, self.fa, self.component = th, cut, lang, lang == "fa", component
        self.pace = CUTS[cut]
        self.words = WORDS[lang]
        self.bpm = self.pace["bpm"]
        self.beat = 60 / self.bpm
        self.share = warming.shares(component)
        self.world = warming.warming(component)
        self.years = (FIRST,) + self.pace["years"]
        assert USA_YEAR in self.years and CHINA_YEAR in self.years
        assert len(self.years) - 1 == round(self.pace["bars"][1] * 4 / self.pace["per"]), "one step per beat"
        assert self.pace["bars"][-1] == 2, "the close is the last two bars of the soundtrack"
        self.final = warming.board(self.years[-1], component)
        assert set(self.final.index) == set(CAT), "the effort ratings must cover the last top 10"
        usa = self.final["USA"]
        assert self.final.index[0] == "USA", self.final
        lines = [line.format(usa=usa, people=USA_PEOPLE) for _, line in self.words["scenes"]]
        if self.fa:
            lines = [fa(line) for line in lines]
        scenes = tuple(Scene(b, FULL, " ".join(groups), line)
                       for b, (groups, _), line in zip(self.pace["bars"], self.words["scenes"], lines))
        self.groups = [groups for groups, _ in self.words["scenes"]]
        starts = np.cumsum([0.0] + [sc.bars * 4 * self.beat for sc in scenes])
        self.starts = starts
        self.L = Timeline(0, 0, 0, 0, 0, end=float(starts[-1]), camera=((0.0, FULL),),
                          scenes=tuple(float(t) for t in starts[:-1]))
        self.S = SimpleNamespace(scenes=scenes, os_name="WHO.HEATED", lang=lang, race=[])
        b = self.beat
        self.steps_t = [float(starts[1]) + k * self.pace["per"] * b for k in range(len(self.years) - 1)]
        self.cells_t = [float(starts[2]) + (self.pace["lead"] + k * self.pace["cell"]) * b
                        for k in range(len(self.final))]
        self.hits = [self.step_time(USA_YEAR), self.step_time(CHINA_YEAR), float(starts[3])]
        dots = np.zeros((1920, 1080), bool)
        dots[4::8, 4::8] = dots[5::8, 4::8] = dots[4::8, 5::8] = dots[5::8, 5::8] = True
        dots[FOOTER - 32:FOOTER + 44] = False
        self.dots = dots

    # ── time: everything steps, nothing glides ──
    # Scenes from 0: 0 the question (the board of 1860), 1 the race, 2 the effort, 3 the USA.

    def scene(self, t: float) -> int:
        return int(np.searchsorted(self.starts[:-1], t, side="right")) - 1 if np.isfinite(t) else 0

    def step_time(self, year: int) -> float:
        return self.steps_t[self.years.index(year) - 1]

    def year_at(self, t: float) -> int:
        i = self.scene(t)
        if i == 0:
            return FIRST
        if i > 1:
            return self.years[-1]
        return self.years[int(np.searchsorted(self.steps_t, t, side="right"))]

    def cells_at(self, t: float) -> int:
        """Rows with their battery: none before the effort scene, one more per half beat in it."""
        i = self.scene(t)
        return 0 if i < 2 else len(self.final) if i > 2 else int(np.searchsorted(self.cells_t, t, side="right"))

    def appear(self, i: int) -> list:
        """When each word of scene i's bold line comes in (s into the scene): the race's three
        phrases as their turn comes, the other lines typed within 0.6 s."""
        groups = self.groups[i]
        n = [sum(w != "//" for w, _ in words_of(g, self.th)) for g in groups]
        if len(groups) == 1:
            return [0.15 + 0.6 * k / n[0] for k in range(n[0])]
        at = (0.0, self.step_time(USA_YEAR) - self.starts[i], self.step_time(CHINA_YEAR) - self.starts[i])
        return [a + 0.1 + 0.3 * k / m for a, m in zip(at, n) for k in range(m)]

    def named(self, t: float) -> str | None:
        """The country the caption speaks of: set in inverse video."""
        i = self.scene(t)
        if i == 1:
            y = self.year_at(t)
            return "China" if y >= CHINA_YEAR else "USA" if y >= USA_YEAR else "United Kingdom"
        return "USA" if i == 3 else None

    # ── words in two scripts, rows mirrored in Persian ──

    def x(self, v: float) -> float:
        """A position inside the window, mirrored about its centre in Persian."""
        return WIN[0] + WIN[0] + WIN[2] - v if self.fa else v

    def span(self, a: float, b: float) -> tuple:
        a, b = self.x(a), self.x(b)
        return min(a, b), max(a, b)

    def text(self, c: Canvas, x, y, s, kind="small", size=30, colour=None, end=False):
        """kind small: the pixel font (Vazirmatn in Persian); big: the grotesk (Vazirmatn bold,
        Persian digits); name: the bold grotesk. Anchored at the start of the line, or with end at
        its end."""
        anchor = "rs" if self.fa != end else "ls"
        if self.fa:
            path = FA_TEXT if kind == "small" else FA_BOLD
            return c.text(self.x(x), y, fa(s), path, size - (2 if kind == "small" else 0), colour, anchor, "rtl")
        path = {"small": PIXEL, "big": GROTESK, "name": onebit.BOLD}[kind]
        return c.text(x, y, s, path, size, colour, anchor)

    def pct(self, v: float) -> str:
        """One decimal always: the leaders are close when they change places (1901: 24.4 and 23.8)."""
        return f"{v:.1f}%" if self.fa else f"{v:.1f} %"

    def melody(self):
        """(time, step, length, gain): each step of the race a pipe that climbs with the world's
        warming that year (square root: the early years are small), each battery a pipe as low
        as its grade."""
        b, top = self.beat, self.world.loc[self.years[-1]]
        out = [(t, int(round(9 * np.sqrt(self.world.loc[y] / top))), 0.8 * self.pace["per"] * b, 0.3)
               for t, y in zip(self.steps_t, self.years[1:])]
        out += [(t, (CAT[country] or 1) - 1, 0.5, 0.25) for t, country in zip(self.cells_t, self.final.index)]
        return out

    # ── drawing ──

    def window(self, c: Canvas, i: int):
        th = self.th
        x, y, w, h = WIN
        c.frame(x, y, x + w, y + h, fill=th.paper)
        c.fill(x, y, x + w, y + BAR, th.ink)
        c.frame(x + 3, y + BAR + 3, x + w - 3, y + h - 3)
        last = i == len(self.S.scenes) - 1
        label = self.words["follow"] if last else self.words["app"]
        if self.fa and last:
            c.text(x + w - 12, y + BAR - 10, label, FA_TEXT, 28, th.title, "rs", "rtl")
        else:
            c.text(x + 12, y + BAR - 9, label, PIXEL, 32, th.title)
        if not last:
            c.text(x + w - 12, y + BAR - 9, f"[{i + 1:02d}/{len(self.S.scenes):02d}]", PIXEL, 32, th.title, "rs")
        c.fill(x + 3, RULE, x + w - 3, RULE + 2, th.ink)

    def head(self, c: Canvas, t: float, i: int):
        th = self.th
        self.text(c, LEFT, HEAD - 6, self.words["head"], size=34)
        year = str(self.year_at(t))
        if self.fa:
            c.text(self.x(RIGHT), HEAD + 8, fa(year), FA_BOLD, 96, th.ink, "ls")
        else:
            c.text(RIGHT, HEAD + 8, year, GROTESK, 96, th.ink, "rs")
        if i >= 2:          # the battery column's head, ending over the nub
            self.text(c, CELLS + 5 * (CELL + GAP) + 5, ROW0 - 20, self.words["effort"], size=30, end=True)

    def rows(self, c: Canvas, t: float, i: int):
        th = self.th
        year = self.year_at(t)
        board = self.final if i >= 2 else warming.board(year, self.component)
        focus, cells = self.named(t), self.cells_at(t)
        for r, (country, v) in enumerate(board.items()):
            y = ROW0 + r * PITCH
            base = y + BH - 4
            ink = th.ink
            if country == focus:          # inverse video: the whole row a black band
                a, b = self.span(WIN[0] + 10, WIN[0] + WIN[2] - 10)
                c.fill(a, y - 10, b, y + BH + 10, th.ink)
                ink = th.field
            self.text(c, LEFT, base, f"{r + 1}", "small", 48, ink)
            self.text(c, NAME, base, warming.name(country, self.lang), "name", 40, ink)
            w = BW * min(v, SCALE) / SCALE
            a, b = self.span(BX, BX + w)
            c.fill(a, y, b, y + BH, ink)
            self.text(c, BX + w + 14, base, self.pct(v), "big", 38, ink)
            if i >= 2 and r < cells:
                self.battery(c, y, country, ink)

    def battery(self, c: Canvas, y, country: str, ink):
        """Five cells, filled to the tracker's grade (5 = enough for 1.5 °C); France with the EU's,
        tagged; a country without a rating gets words, not an empty battery."""
        grade, x0 = CAT[country], CELLS
        if grade is None:
            self.text(c, x0, y + BH - 10, self.words["unrated"], size=28, colour=ink)
            return
        if country in VIA_EU:
            self.text(c, x0 - 12, y + BH - 10, self.words["eu"], size=30, colour=ink, end=True)
        for k in range(5):
            a, b = self.span(x0 + k * (CELL + GAP), x0 + k * (CELL + GAP) + CELL)
            if k < grade:
                c.fill(a, y + 4, b, y + BH - 4, ink)
            else:
                c.frame(a, y + 4, b, y + BH - 4, colour=ink)
        a, b = self.span(x0 + 5 * (CELL + GAP), x0 + 5 * (CELL + GAP) + 5)
        c.fill(a, y + 14, b, y + BH - 14, ink)            # the battery's nub

    def draw(self, s: int, t: float = np.inf, size=SIZES["reel"]):
        c = Canvas(s, self.th, 1.0, (0.0, 0.0), size)
        c.pixels(0, 0, self.dots, self.th.dots)
        i = self.scene(t)
        dt = t - self.starts[i] if np.isfinite(t) else np.inf
        self.window(c, i)
        sc = self.S.scenes[i]
        title(c, self.th, sc, dt, self.lang, self.pace["caption"], LEFT, RIGHT,
              WIN[1] + BAR + 96 + round(40 * (self.pace["caption"] - 1)), self.appear(i))
        self.head(c, t, i)
        self.rows(c, t, i)
        c.text(onebit.LEFT, FOOTER, self.words["source"], MONO, 20, self.th.head)
        if self.fa:
            c.text(onebit.RIGHT, FOOTER + 30, self.words["note"], FA_TEXT, 22, self.th.head, "rs", "rtl")
        else:
            c.text(onebit.LEFT, FOOTER + 28, self.words["note"], MONO, 20, self.th.head)
        return c.im


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", default="luft1", choices=list(onebit.THEMES), help="colour theme")
    ap.add_argument("--cut", default="20s", choices=list(CUTS))
    ap.add_argument("--lang", default="en", choices=("en", "fa"))
    ap.add_argument("--stills", action="store_true", help="cover and frames only, no video")
    args = ap.parse_args()
    film = WarmingFilm(onebit.THEMES[args.theme], args.cut, args.lang)
    (OUT / "social").mkdir(parents=True, exist_ok=True)
    base = OUT / "social" / (f"who_heated_{args.theme}_{args.cut}" + ("" if args.lang == "en" else f"_{args.lang}"))
    film.draw(1).save(f"{base}_cover.png", optimize=True)
    print("saved", f"{base}_cover.png")
    if args.stills:
        st = film.starts
        for t in (st[1] + 0.4, film.step_time(USA_YEAR) + 0.4, film.step_time(CHINA_YEAR) + 0.4, st[2] - 0.1,
                  st[2] + 2.0, st[3] - 0.1, st[4] - 0.1):
            film.draw(1, t).save(f"{base}_t{t:04.1f}.png")
        print("saved", f"{base}_t*.png")
        return
    onebit.video(film, Path(f"{base}_reel.mp4"), SOCIAL_CRF, SIZES["reel"], audio="steam")


if __name__ == "__main__":
    main()
