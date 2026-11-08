"""THE TEHRAN DAMS, FOLLOW-UP (the reel of 9 Nov 2026, tehran5b_fa): the newest official figures for the five dams
that supply Tehran, the storage at the start of the water year, and the rain to mid-Aban, each with its source and
its date. Official figures only: no volume here is measured from space. On screen the storage is shown as volumes
(million m3) against the long-term average and the amount needed; no percentage of capacity is shown anywhere.

Sources, each quoted in its own words (Persian, kept exact; the film asserts its numbers in them):

  TAADOL  Ta'adol newspaper, 17-18 Mehr 1405 (9-10 Oct 2026): the spokesman of the Tehran water company gives the
          storage at the start of Mehr as 391 million m3 («۳۹۱ میلیون مترمکعب در ابتدای مهر ۱۴۰۵»). Headline
          «سدهای پایتخت همچنان چقدر کسری آب دارد؟», article 406363. Source of the 391 on screen.
  MEHR26  Mehr News, article 6981337, 26 Mehr 1405 (18 Oct 2026), data to 19 Mehr: 383 million m3 in the five dams
          (headline «آخرین وضعیت سدهای تهران؛ ذخایر ۳۸۳ میلیون مترمکعب شد»). Also the capacities of the five dams
          (about), used only as data in the checks below.
  MEHR    Mehr News, article 6989418, 4 Aban 1405 (26 Oct 2026), citing the Tehran Regional Water Company's data for
          1 Aban 1405 (23 Oct 2026): 359 million m3 (the five dams), last year 217, long-term average 548. Source of
          the 1 Aban storage (src/tehran5.py) and of the framing sentence.
  DIDBAN  Didban Iran, citing Tasnim, 16 Aban 1405 (7 Nov 2026), 11:56. Behnam Bakhshi, spokesman of the Tehran
          province water and wastewater company (آبفای استان تهران). The newest official figures: no later figure
          was published by 8 Nov 2026 in the sources checked. Source of the 340 on screen and of the rain.
          Its «حدود ۴۵۰» for the year's start conflicts with its own contemporaneous 391 (TAADOL): not used.

    python -I src/tehran5b.py                 # the checks, and the figures the reel and the caption use
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tehran5  # noqa: E402  (the 1 Aban storage and the article: imported, not copied)


def fa(n) -> str:
    """Persian digits (ASCII in, Persian out)."""
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def fa_thousands(n: int) -> str:
    """1930 as the Persian press writes it: ۱٬۹۳۰."""
    return fa(f"{n:,}").replace(",", "٬")


DIDBAN = dict(
    date=date(2026, 11, 7), published="16 آبان ۱۴۰۵، ساعتِ ۱۱:۵۶", spokesman="بهنام بخشی",
    office="سخن‌گوی آبفای استان تهران", via="تسنیم، به نقل از دیدبان ایران",
    start_now=450, start_last=250,
    quote_start=('سال گذشته ... سال آبی را با حدود 250 میلیون مترمکعب ذخیره آغاز کردیم، اما امسال این رقم به حدود '
                 '450 میلیون مترمکعب رسید'),
    total_now=340, share_pct=18, share_text="حدود 18 درصد",
    quote_total=('در حال حاضر مجموع ذخایر پنج سد تهران حدود 340 میلیون مترمکعب است'),
    quote_lar="سد لار تنها 3 درصد", quote_latyan="لتیان 29 درصد", quote_mamlu="ماملو حدود 11 درصد",
    quote_share="مجموع 5 سد تهران حدود 18 درصد",
    rain_now=16, rain_expected=38.9, quote_rain=("تهران در این بازه زمانی باید 38.9 میلیمتر بارندگی دریافت می‌کرد"),
    quote_rain_now="میزان بارندگی تهران ... 16 میلیمتر",
    quote_period="اکنون به نیمه آبانماه ... بیش از 40 روز از سال آبی سپری شده است",
    quote_rain_last_year=("بارندگی تهران در سال گذشته تا همین مقطع حتی به صفر میلیمتر رسیده بود"),
    quote_need=("تهران برای عبور از شرایط پایدار به حدود 800 تا 850 میلیون مترمکعب ذخیره آبی در پنج سد خود نیاز دارد"),
    need_low=800, need_high=850,
)
TAADOL = dict(
    date=date(2026, 10, 9), published="17 مهر ۱۴۰۵، ساعتِ ۱۳:۴۵", article="406363", paper="روزنامه‌ی تعادل",
    headline="سدهای پایتخت همچنان چقدر کسری آب دارد؟",
    quote_start="۳۹۱ میلیون مترمکعب در ابتدای مهر ۱۴۰۵",
)
MEHR26 = dict(date=date(2026, 10, 18), article="6981337", value=383, headline="آخرین وضعیت سدهای تهران؛ ذخایر ۳۸۳ میلیون مترمکعب شد")
CAPACITY = dict(  # Mehr 6981337, 26 Mehr 1405: million m3, "about"; data only, never on screen
    source="Mehr News, article 6981337, 26 Mehr 1405 (18 Oct 2026); the capacities are 'about' figures",
    amir_kabir=205, latyan=95, lar=960, mamlu=250, taleqan=420,
    lar_other=920,   # Mehr 6989418 (4 Aban 1405) gives 920 for Lar as a nominal capacity
)
MEHR_FRAME = "افزایش بارندگی به‌تنهایی به معنای پر شدن مخازن یا رفع کمبود ذخایر آبی نیست"  # Mehr 6989418 (4 Aban 1405)
TOTAL_CAPACITY = sum(v for k, v in CAPACITY.items() if k in ("amir_kabir", "latyan", "lar", "mamlu", "taleqan"))
START_MEHR = 391                                             # million m3 at the start of Mehr 1405 (Taadol, 17 Mehr)
ONE_ABAN = tehran5.TOTAL["value"]                           # 359 on 1 Aban 1405 (Mehr 6989418, the five dams)
AVG_1ABAN = tehran5.TOTAL["long_term"]                      # 548: the long-term average for 1 Aban (Mehr 6989418)
NOW = DIDBAN["total_now"]                                   # 340 on 16 Aban 1405 (Didban)
RAIN_NOW = DIDBAN["rain_now"]                               # 16 mm to mid-Aban (Didban)
RAIN_EXPECTED = DIDBAN["rain_expected"]                     # 38.9 mm expected for the same days (Didban)
NEED = (DIDBAN["need_low"], DIDBAN["need_high"])            # 800-850 million m3 for the stable state (Didban)
SCALE_MAX = 900                                             # million m3: the storage bar's scale on screen


def check() -> None:
    """Every figure on screen, asserted against the quotes and against the arithmetic."""
    tehran5.check()
    assert tehran5.jalali(DIDBAN["date"]) == "16 Aban 1405", tehran5.jalali(DIDBAN["date"])
    assert tehran5.jalali(tehran5.ARTICLE["stored"]) == "1 Aban 1405"
    assert tehran5.jalali(TAADOL["date"]) == "17 Mehr 1405", tehran5.jalali(TAADOL["date"])
    assert tehran5.jalali(MEHR26["date"]) == "26 Mehr 1405", tehran5.jalali(MEHR26["date"])
    assert START_MEHR == 391 and fa(START_MEHR) == "۳۹۱" and "391 میلیون" not in TAADOL["quote_start"]
    assert TAADOL["quote_start"].startswith("۳۹۱ میلیون") and fa(START_MEHR) in TAADOL["quote_start"]
    assert MEHR26["value"] == 383 and fa(MEHR26["value"]) == "۳۸۳"
    assert TOTAL_CAPACITY == 1930, TOTAL_CAPACITY                       # data only: the sum of the capacities
    assert round(100 * NOW / TOTAL_CAPACITY) == DIDBAN["share_pct"] == 18  # data only: never on screen
    assert round(100 * AVG_1ABAN / TOTAL_CAPACITY) == 28                  # data only: 548 is about 28 % of 1,930
    assert abs(NOW / AVG_1ABAN - 0.62) < 0.01, NOW / AVG_1ABAN            # 340 is about 62 % of 1 Aban's normal
    assert abs(ONE_ABAN / AVG_1ABAN - 0.655) < 0.005, ONE_ABAN / AVG_1ABAN  # 359 was 65.5 % of it
    assert AVG_1ABAN == 548 and ONE_ABAN == 359
    assert START_MEHR > MEHR26["value"] > ONE_ABAN > NOW, (START_MEHR, MEHR26["value"], ONE_ABAN, NOW)
    assert ONE_ABAN - NOW == 19 and START_MEHR - NOW == 51
    assert DIDBAN["start_last"] < DIDBAN["start_now"]
    assert RAIN_NOW < RAIN_EXPECTED / 2, "less than half of the expected rain"
    assert round(RAIN_EXPECTED, 1) == 38.9 and RAIN_NOW == 16
    assert NEED[0] <= NEED[1] and NOW < NEED[0], "the dams are below the stable state"
    assert NOW < AVG_1ABAN <= SCALE_MAX and NEED[1] < SCALE_MAX, "the marks fit the 0-900 scale"
    assert fa(NOW) == "۳۴۰" and fa(RAIN_NOW) == "۱۶" and fa(AVG_1ABAN) == "۵۴۸"
    assert DIDBAN["quote_total"].split("حدود ")[1].split(" میلیون")[0] == "340"
    assert "450 میلیون" in DIDBAN["quote_start"] and "250 میلیون" in DIDBAN["quote_start"]
    assert "38.9" in DIDBAN["quote_rain"] and "16" in DIDBAN["quote_rain_now"]
    assert "800 تا 850" in DIDBAN["quote_need"]


if __name__ == "__main__":
    check()
    print(f"{DIDBAN['via']}; {DIDBAN['published']}; {DIDBAN['spokesman']}, {DIDBAN['office']}")
    print(f"  start of Mehr 1405 (Taadol): {START_MEHR} million m3; 17 Mehr; Mehr 26: {MEHR26['value']}")
    print(f"  1 Aban 1405 (Mehr): {ONE_ABAN} million m3; long-term average for 1 Aban: {AVG_1ABAN}")
    print(f"  16 Aban 1405 (Didban): about {NOW} million m3 (data only: {100 * NOW / TOTAL_CAPACITY:.1f} % of "
          f"the capacities' sum {TOTAL_CAPACITY})")
    print(f"  Tehran rain to mid-Aban: {RAIN_NOW} mm; expected for the same days: {RAIN_EXPECTED} mm "
          f"({100 * RAIN_NOW / RAIN_EXPECTED:.0f} % of the expected)")
    print(f"  stable state needs about {NEED[0]} to {NEED[1]} million m3 in the five dams")
    print("all checks pass")
