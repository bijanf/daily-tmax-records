"""THE FIVE TEHRAN DAMS: the storage of each dam as officially reported, for the reel of the same name (the
finale of the series) and its caption. Official, not measured from space: every volume here is the figure the
Tehran Regional Water Company gave the press, and no capacity or percentage full is derived from one.

Source: Mehr News, article 6989418 of 4 Aban 1405 (26 Oct 2026), citing the company's data for 1 Aban 1405
(23 Oct 2026): the storage of each dam in million m3, the same date a year earlier, and the long-term average.
The sentences in QUOTE are the article's own words (Persian), kept exact; the film asserts its numbers in them.
The nominal capacity of Lar in the same article (920 million m3) is a capacity, not a storage: it is not used.

Order: from the worst to the best against the long-term average (the film's order).

    python -I src/tehran5.py                 # the checks, and the figures the reel and the caption use
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wateryear import farvardin1  # noqa: E402


def fa(n) -> str:
    """Persian digits (ASCII in, Persian out)."""
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))

ARTICLE = dict(id="6989418", published=date(2026, 10, 26), stored=date(2026, 10, 23),
               source="Mehr News, article 6989418, 4 Aban 1405 (26 Oct 2026); the Tehran Regional Water Company's "
                      "data for 1 Aban 1405 (23 Oct 2026)")
MONTHS = ("Farvardin", "Ordibehesht", "Khordad", "Tir", "Mordad", "Shahrivar", "Mehr", "Aban", "Azar", "Dey",
          "Bahman", "Esfand")
UNIT = "million m3"
DAMS = (
    dict(key="mamlu", name="ماملو", label="سدِ ماملو", value=28, last_year=18, long_term=92,
         quote='سد ماملو نیز در اول آبان امسال ۲۸ میلیون مترمکعب ذخیره داشته است. این رقم در مدت مشابه سال گذشته ۱۸ میلیون مترمکعب و میانگین بلندمدت آن ۹۲ میلیون مترمکعب بوده است.'),
    dict(key="lar", name="لار", label="سدِ لار", value=29, last_year=16, long_term=79,
         quote='سد لار نیز در اول آبان امسال ۲۹ میلیون مترمکعب ذخیره داشته است. این رقم در مدت مشابه سال گذشته ۱۶ میلیون مترمکعب و میانگین بلندمدت ذخایر آن ۷۹ میلیون مترمکعب بوده است.'),
    dict(key="latyan", name="لتیان", label="سدِ لتیان", value=21, last_year=10, long_term=42,
         quote='در سد لتیان، حجم ذخایر به ۲۱ میلیون مترمکعب رسیده است؛ در حالی که این رقم در مدت مشابه سال گذشته ۱۰ میلیون مترمکعب و میانگین بلندمدت آن ۴۲ میلیون مترمکعب بوده است.'),
    dict(key="taleqan", name="طالقان", label="سدِ طالقان", value=158, last_year=156, long_term=232,
         quote='در سد طالقان، حجم ذخایر به ۱۵۸ میلیون مترمکعب رسیده است؛ رقمی که در مقایسه با ۱۵۶ میلیون مترمکعب در سال گذشته، افزایش ۲ میلیون مترمکعبی را نشان می\u200cدهد. با این حال، میانگین بلندمدت ذخایر این سد ۲۳۲ میلیون مترمکعب است و حجم فعلی آن ۷۴ میلیون مترمکعب کمتر از این میانگین است.'),
    dict(key="karaj", name="کرج", label="سدِ کرج", value=123, last_year=17, long_term=103,
         quote='بررسی جزئیات آمار نشان می\u200cدهد سد امیرکبیر با ذخیره ۱۲۳ میلیون مترمکعبی، در مقایسه با ۱۷ میلیون مترمکعب در سال گذشته و میانگین بلندمدت ۱۰۳ میلیون مترمکعب، وضعیت بهتری از نظر حجم ذخیره نسبت به میانگین بلندمدت دارد.'),
)
TOTAL = dict(value=359, last_year=217, long_term=548,
             quote='مجموع ذخایر پنج سد امیرکبیر، لتیان، لار، طالقان و ماملو به ۳۵۹ میلیون مترمکعب رسیده است. این رقم در مدت مشابه سال گذشته ۲۱۷ میلیون مترمکعب و میانگین بلندمدت ذخایر این سدها ۵۴۸ میلیون مترمکعب بوده است.')
DAM_NAMES = {"mamlu": "Mamlu", "lar": "Lar", "latyan": "Latyan", "taleqan": "Taleqan", "karaj": "Karaj (Amir Kabir)"}


def jalali(d: date) -> str:
    """A date of Persian years 1403-1405 as the Persian press writes it: 1 Aban 1405 = 23 October 2026."""
    for p in (1403, 1404, 1405):
        if farvardin1(p) <= d < farvardin1(p + 1):
            n = (d - farvardin1(p)).days
            jm, day = (n // 31, n % 31 + 1) if n < 186 else (6 + (n - 186) // 30, (n - 186) % 30 + 1)
            return f"{day} {MONTHS[jm]} {p}"
    raise ValueError(d)


def share(dam: dict) -> float:
    """The storage of 1 Aban 1405 as a share of the long-term average."""
    return dam["value"] / dam["long_term"]


def check() -> None:
    """The article's totals: the five add up to 359, 217 and 548; each figure is in its quote."""
    assert jalali(ARTICLE["stored"]) == "1 Aban 1405", jalali(ARTICLE["stored"])
    assert (ARTICLE["published"] - ARTICLE["stored"]).days == 3
    assert sum(d["value"] for d in DAMS) == TOTAL["value"] == 359
    assert sum(d["last_year"] for d in DAMS) == TOTAL["last_year"] == 217
    assert sum(d["long_term"] for d in DAMS) == TOTAL["long_term"] == 548
    assert [d["key"] for d in DAMS] == sorted((d["key"] for d in DAMS), key=lambda k: share(
        next(d for d in DAMS if d["key"] == k)))           # worst to best against the average
    for d in DAMS:                                         # each figure is in the article's words
        for n in (d["value"], d["last_year"], d["long_term"]):
            assert f"{fa(n)} میلیون مترمکعب" in d["quote"], (d["key"], n)
    for n in (TOTAL["value"], TOTAL["last_year"], TOTAL["long_term"]):
        assert f"{fa(n)} میلیون مترمکعب" in TOTAL["quote"], n
    assert [d["key"] for d in DAMS if share(d) > 1] == ["karaj"], "only Karaj is above its average"


if __name__ == "__main__":
    check()
    print(f"{ARTICLE['source']}; storage on {jalali(ARTICLE['stored'])} ({ARTICLE['stored']:%d %b %Y})")
    for d in DAMS:
        print(f"  {DAM_NAMES[d['key']]:<20} {d['value']:>4} now  {d['last_year']:>4} a year earlier  "
              f"{d['long_term']:>4} average  {100 * share(d):6.1f} % of the average")
    print(f"  {'five dams':<20} {TOTAL['value']:>4} now  {TOTAL['last_year']:>4} a year earlier  "
          f"{TOTAL['long_term']:>4} average  {100 * TOTAL['value'] / TOTAL['long_term']:6.1f} % of the average")
    print("all checks pass")
