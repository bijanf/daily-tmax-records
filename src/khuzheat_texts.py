"""The texts that go with the Khuzestan heat reel (khuzheat_fa): the caption, the first comment (sources and method)
and reply drafts. Every number is taken from the film's own file (outputs/onebit/khuzheat/film.json, which
src/khuzheat.py writes); what the sentences take for granted is asserted. Limits: the caption at most 2,100 UTF-8
bytes and five hashtags, the comment at most 2,200 characters.

The one outside statement (the cause): IPCC AR6, Working Group I, Chapter 11 (Seneviratne et al. 2021,
doi:10.1017/9781009157896.013), Table 11.7, the row of West Central Asia, read in the published chapter on
20 November 2026: observed trend "Very likely increase in the intensity and frequency of hot extremes", detection
and attribution "High confidence in a human contribution to the observed increase in the intensity and frequency of
hot extremes". Abadan (48.23 E, 30.37 N) and Ahvaz (48.76 E, 31.34 N) lie inside that region's outline (IPCC-WGI
reference regions v4: its south edge runs along 30 N to 47.6 E and from there to 60 E, 23.5 N), checked in REGION.

    python -I src/khuzheat_texts.py     # outputs/onebit/social/khuzheat_fa_caption_fa.txt, _first_comment_fa.txt,
                                        # _replies_fa.txt
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import air  # noqa: E402
import get_khuzheat  # noqa: E402
import khuzheat as K  # noqa: E402
import onebit  # noqa: E402
from onebit import fa  # noqa: E402

MONTHS = ("فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند")
REGION = ((40.0, 30.0), (40.0, 45.0), (75.0, 45.0), (75.0, 30.0), (60.0, 30.0), (60.0, 23.5), (47.6, 30.0))     # West Central Asia (lon, lat)


def day(iso: str) -> str:
    y, m, d = air.jalali(iso)
    return f"{fa(d)} {MONTHS[m - 1]} {fa(y)}"


def yr(g: int) -> str:
    return fa(K.fa_year(g))


def row(xs) -> str:
    return "، ".join(fa(x) for x in xs)


def inside(lon: float, lat: float, poly=REGION) -> bool:
    hit = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > lat) != (y2 > lat) and lon < x1 + (lat - y1) * (x2 - x1) / (y2 - y1):
            hit = not hit
    return hit


def texts() -> dict:
    F = json.loads((K.BUILD / "film.json").read_text(encoding="utf-8"))
    N, W, P = F["numbers"], F["words"], F["pictures"]
    t, n, a0, a1, e = N["then"], N["now"], N["ahvaz_before"], N["ahvaz_now"], N["era"]
    h = K.half_up
    # what the sentences take for granted
    assert t["years"] == [1949, 1950, 1951, 1952, 1953, 1954, 1955, 1958]                   # «۱۳۲۸ تا ۱۳۳۴ و ۱۳۳۷»
    assert n["years"] == a1["years"] == list(range(2015, 2025)) and a0["years"] == list(range(2005, 2015))
    assert (h(t["mean"]), h(n["mean"]), h(a0["mean"]), h(a1["mean"])) == (4, 38, 14, 35)
    assert n["low"] > t["high"] and a1["mean"] > 2 * a0["mean"]                             # the caption's two bullets
    assert N["outside"] == 0 and h(N["plain_now"]) == 41
    gap = [y for y in N["abadan_full"] if t["years"][-1] < y < n["years"][0]]
    assert min(gap) == 2006, gap                                                            # «از ۱۳۳۸ تا ۱۳۸۴ سالِ کامل نیست»
    miss_t = [K.DAYS - d for d in t["days"]]
    miss_a0 = [K.DAYS - d for d in a0["days"]]
    assert miss_t[0] == 8 and h(sum(miss_t) / len(miss_t)) == 3 and h(sum(miss_a0) / 10) == 6, (miss_t, miss_a0)
    # even if every day without a report had been hot, the rise stands
    assert t["mean"] + sum(miss_t) / len(miss_t) < 0.25 * n["mean"] and a0["mean"] + sum(miss_a0) / 10 < 0.6 * a1["mean"]
    assert (h(e["then"]), h(e["now"])) == (4, 31) and e["now"] < n["mean"]                  # «مدل کمتر می‌شمارد»
    assert N["ahvaz_top"] == dict(value=53.7, day="2017-06-29") and N["isd_last"] == "2025-08-24"
    assert all(inside(s["lon"], s["lat"]) for s in get_khuzheat.STATIONS.values())          # both stations in West Central Asia
    assert K.HOT_F == 119 and K.FULL == 140 and K.DAYS == 153 and K.MONTHS == (5, 6, 7, 8, 9)
    then_span, now_span = f"{yr(1949)} تا {yr(1958)}", f"{yr(2015)} تا {yr(2024)}"
    top = fa(f"{N['ahvaz_top']['value']:.1f}".replace(".", "٫"))

    caption = f"""آبادان: روزهای بالای ۴۸ درجه، از {fa(h(t['mean']))} به {fa(h(n['mean']))} روز در سال

گزارش‌های ایستگاهِ هواشناسیِ آبادان و اهواز را در بایگانیِ NOAA شمردیم: روزهایی که بیشینه‌ی دما از ۴۸ درجه بالاتر رفت.
• آبادان، {then_span} ({fa(len(t['years']))} سالِ کامل): میانگین {fa(h(t['mean']))} روز در سال؛ داغ‌ترین سال {fa(t['high'])} روز.
• آبادان، {now_span}: میانگین {fa(h(n['mean']))} روز در سال؛ خنک‌ترین سال {fa(n['low'])} روز.
• اهواز: {yr(2005)} تا {yr(2014)} میانگین {fa(h(a0['mean']))} روز؛ {now_span} میانگین {fa(h(a1['mean']))} روز. داغ‌ترین روزِ این داده‌ها: {top} درجه، {day(N['ahvaz_top']['day'])}.

برای سال‌های میانی، که بایگانی گزارشِ کاملِ ایستگاه را ندارد، نمودار از برآوردِ مدلِ ERA5-Land است (مدل است، نه دماسنج). همان جهت را نشان می‌دهد: از {fa(h(e['then']))} روز در سال ({yr(1950)} تا {yr(1959)}) به {fa(h(e['now']))} روز ({now_span}).

چرا؟ گزارشِ ششمِ IPCC درباره‌ی منطقه‌ای که خوزستان در آن است می‌گوید گرمای شدید «به احتمالِ بسیار زیاد» بیشتر و شدیدتر شده و سهمِ انسان در آن با «اطمینانِ بالا» دیده می‌شود. عامل‌های محلی، مثل تغییرِ محیطِ اطرافِ ایستگاه یا کم‌آبی، هم ممکن است اثر داشته باشند؛ این داده‌ها سهمِ هرکدام را جدا نمی‌کنند.

منابع و روش در کامنتِ اول.

تابستانِ بچگیِ شما در خوزستان چطور بود؟

#خوزستان #آبادان #اهواز #گرما #تغییر_اقلیم
"""

    comment = f"""منابع و روش:
۱) ایستگاه‌ها: بایگانیِ ISD در NOAA (گزارش‌های ساعتیِ جهانی)، آبادان (۴۰۸۳۱) و اهواز (۴۰۸۱۱). بیشینه‌ی هر روز از گزارشِ «بیشینه‌ی دما»ی خودِ ایستگاه است.
۲) شمارش: گزارش‌های قدیمیِ آبادان به درجه‌ی فارنهایتِ کامل‌اند (۱۱۸ فارنهایت = ۴۷٫۸ و ۱۱۹ = ۴۸٫۳ درجه). برای اینکه همه‌ی سال‌ها یک‌جور شمرده شوند، روزی شمرده شده که بیشینه‌اش، گردشده به فارنهایت، ۱۱۹ یا بیشتر باشد: یعنی بالای ۴۸ درجه. با مرزِ «۴۸٫۰ یا بیشتر» سال‌های قدیم همان می‌ماند و {now_span} می‌شود {fa(h(N['plain_now']))} روز.
۳) بازه‌ی شمارش: ۱۱ اردیبهشت تا ۸ مهر؛ در سال‌های شمرده‌شده هیچ روزِ بالای ۴۸ بیرون از آن نبود. «سالِ کامل»: دست‌کم {fa(K.FULL)} روز از این {fa(K.DAYS)} روز گزارش دارد.
۴) آبادان، سال‌های کاملِ دوره‌ی اول: {yr(1949)} تا {yr(1955)} و {yr(1958)}. شمارِ هر سال: {row(t['counts'])}. در این سال‌ها به‌طورِ میانگین {fa(h(sum(miss_t) / len(miss_t)))} روز در سال گزارش نیست ({yr(1949)}: {fa(miss_t[0])} روز).
۵) آبادان، {now_span}: {row(n['counts'])}.
۶) اهواز، {yr(2005)} تا {yr(2014)}: {row(a0['counts'])} (میانگین {fa(h(sum(miss_a0) / 10))} روز در سال بی‌گزارش)؛ {now_span}: {row(a1['counts'])}.
۷) از {yr(1959)} تا {yr(2005)} بایگانی سالِ کامل از این گزارش برای آبادان ندارد. نمودارِ سال‌به‌سال از ERA5-Land است (کوپرنیک و ECMWF): برآوردِ مدل از دمای هوا در نقطه‌ی ایستگاه، با همان شمارش. مدل کمتر از ایستگاه می‌شمارد ({fa(h(e['now']))} در برابرِ {fa(h(n['mean']))}).
۸) نشانِ ایستگاه روی تصویر، جای امروزِ آن در فهرستِ NOAA است. جابه‌جایی یا تغییرِ دماسنج را در منابعی که دیدیم نیافتیم؛ تاریخچه‌ی ایستگاه را نتوانستیم بررسی کنیم.
۹) این بایگانی تا {day(N['isd_last'])} است؛ برای همین ده سالِ کاملِ آخر {now_span} است.
۱۰) علت: IPCC، گزارشِ ششم (۲۰۲۱)، گروهِ کاریِ یک، فصلِ ۱۱، جدولِ ۱۱٫۷، منطقه‌ی «غربِ آسیای مرکزی».
۱۱) تصویرها: Sentinel-2، کوپرنیک؛ آبادان {day(P['abadan']['day'])}، اهواز {day(P['ahvaz']['day'])}.
"""

    replies = f"""پاسخ‌های آماده (برای کامنت‌ها):

«عدد از کجاست؟»
از گزارش‌های خودِ ایستگاهِ هواشناسی، که در بایگانیِ جهانیِ NOAA هست. روش و شمارِ هر سال در کامنتِ اول آمده.

«چرا ۵۰ درجه را نشمردید؟»
گزارش‌های قدیمی به فارنهایتِ کامل‌اند و مرزِ ۵۰ درجه با آن‌ها دقیق شمرده نمی‌شود. مرزِ بالای ۴۸ درجه در همه‌ی سال‌ها یک‌جور شمرده می‌شود.

«این به خاطرِ تغییرِ اقلیم است یا شهر و خشکی؟»
این داده‌ها سهم‌ها را جدا نمی‌کنند. گزارشِ ششمِ IPCC برای این منطقه افزایشِ گرمای شدید را «به احتمالِ بسیار زیاد» می‌داند و سهمِ انسان را با «اطمینانِ بالا». عامل‌های محلی هم ممکن است اثر داشته باشند.

«چرا مدل ۳۱ می‌گوید و ایستگاه ۳۸؟»
مدل، دمای یک خانه‌ی چندکیلومتری را برآورد می‌کند و ایستگاه یک نقطه را می‌سنجد. جهتِ هر دو یکی است: در مدل از {fa(h(e['then']))} به {fa(h(e['now']))} روز، در ایستگاه از {fa(h(t['mean']))} به {fa(h(n['mean']))} روز.

«سال‌های بینِ {yr(1959)} و {yr(2005)} چه؟»
بایگانی برای آن سال‌ها گزارشِ کاملِ بیشینه‌ی آبادان را ندارد. برای همین آن سال‌ها را فقط با برآوردِ مدل نشان داده‌ایم.
"""
    # the film's own words agree with the caption's
    assert fa(h(t["mean"])) in W["hook"] and fa(h(n["mean"])) in W["hook"] and top in W["c_top"]
    return dict(caption=caption, first_comment=comment, replies=replies)


def main() -> None:
    social = onebit.OUT / "social"
    T = texts()
    for k, v in T.items():
        (social / f"khuzheat_fa_{k}_fa.txt").write_text(v, encoding="utf-8")
    c = T["caption"]
    print(f"caption: {len(c)} characters, {len(c.encode('utf-8'))} bytes (limit 2,100), {c.count('#')} hashtags")
    assert len(c.encode("utf-8")) <= 2100 and c.count("#") <= 5
    print(f"first comment: {len(T['first_comment'])} characters (limit 2,200)")
    assert len(T["first_comment"]) <= 2200
    for banned in ("رکورد", "خشک شد", "مُرد", "مقصر", "فاجعه"):
        assert not any(banned in v for v in T.values()), banned
    print("\n" + c + "\n" + T["first_comment"])


if __name__ == "__main__":
    main()
