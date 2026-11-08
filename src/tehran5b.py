"""THE TEHRAN DAMS, FOLLOW-UP (the reel of 9 Nov 2026, tehran5b_fa): the newest official figures for the five dams
that supply Tehran, the storage at the start of the water year, and the rain to mid-Aban, each with its source and
its date. Official figures only: no volume here is measured from space, and no percentage full is derived from a
satellite picture. The one number that is our arithmetic is the sum of the five capacities (1,930), and it is
labelled as such on screen and in the first comment.

Sources, each quoted in its own words (Persian, kept exact; the film asserts its numbers in them):

  DIDBAN  Didban Iran, citing Tasnim, 16 Aban 1405 (7 Nov 2026), 11:56. Behnam Bakhshi, spokesman of the Tehran
          province water and wastewater company (آبفای استان تهران). The newest official figures: no later figure
          was published by 8 Nov 2026 in the sources checked.
  MEHR    Mehr News, article 6989418, 4 Aban 1405 (26 Oct 2026), citing the Tehran Regional Water Company's data for
          1 Aban 1405 (23 Oct 2026). Source of the 1 Aban storage (src/tehran5.py) and of the framing sentence.
  CAP     Mehr News, article 6981337, 26 Mehr 1405 (18 Oct 2026): the capacities of the five dams (about). Used only
          for the sum, labelled as our arithmetic. Its Lar figure (about 960) differs from the 920 of article 6989418;
          the sum uses 960 and the first comment says so.

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
CAPACITY = dict(  # Mehr 6981337, 26 Mehr 1405: million m3, "about"; the sum is our arithmetic
    source="Mehr News, article 6981337, 26 Mehr 1405 (18 Oct 2026); the capacities are 'about' figures",
    amir_kabir=205, latyan=95, lar=960, mamlu=250, taleqan=420,
    lar_other=920,   # Mehr 6989418 (4 Aban 1405) gives 920 for Lar as a nominal capacity
)
MEHR_FRAME = "افزایش بارندگی به‌تنهایی به معنای پر شدن مخازن یا رفع کمبود ذخایر آبی نیست"  # Mehr 6989418 (4 Aban 1405)
TOTAL_CAPACITY = sum(v for k, v in CAPACITY.items() if k in ("amir_kabir", "latyan", "lar", "mamlu", "taleqan"))
WATER_YEAR_START = DIDBAN["start_now"]             # 1405's water year opened with about 450 (Didban)
ONE_ABAN = tehran5.TOTAL["value"]                  # 359 on 1 Aban 1405 (Mehr 6989418, the five dams)
NOW = DIDBAN["total_now"]                          # 340 on 16 Aban 1405 (Didban)
RAIN_NOW = DIDBAN["rain_now"]                      # 16 mm to mid-Aban (Didban)
RAIN_EXPECTED = DIDBAN["rain_expected"]            # 38.9 mm expected for the same days (Didban)
NEED = (DIDBAN["need_low"], DIDBAN["need_high"])   # 800-850 million m3 for the stable state (Didban)


def check() -> None:
    """Every figure on screen, asserted against the quotes and against the arithmetic."""
    tehran5.check()
    assert tehran5.jalali(DIDBAN["date"]) == "16 Aban 1405", tehran5.jalali(DIDBAN["date"])
    assert tehran5.jalali(tehran5.ARTICLE["stored"]) == "1 Aban 1405"
    assert TOTAL_CAPACITY == 1930, TOTAL_CAPACITY
    assert round(100 * NOW / TOTAL_CAPACITY) == DIDBAN["share_pct"] == 18
    assert round(100 * ONE_ABAN / TOTAL_CAPACITY, 1) == 18.6 and ONE_ABAN < TOTAL_CAPACITY
    assert NOW < ONE_ABAN < WATER_YEAR_START, (WATER_YEAR_START, ONE_ABAN, NOW)
    assert ONE_ABAN - NOW == 19 and WATER_YEAR_START - NOW == 110
    assert DIDBAN["start_last"] < DIDBAN["start_now"]
    assert RAIN_NOW < RAIN_EXPECTED / 2, "less than half of the expected rain"
    assert round(RAIN_EXPECTED, 1) == 38.9 and RAIN_NOW == 16
    assert NEED[0] <= NEED[1] and NOW < NEED[0], "the dams are below the stable state"
    assert NEED[0] / TOTAL_CAPACITY > 0.4 and NOW / TOTAL_CAPACITY < 0.2
    assert fa(DIDBAN["start_now"]) == "۴۵۰" and fa(NOW) == "۳۴۰" and fa(RAIN_NOW) == "۱۶"
    assert fa_thousands(TOTAL_CAPACITY) == "۱٬۹۳۰"
    assert DIDBAN["quote_total"].split("حدود ")[1].split(" میلیون")[0] == "340"
    assert "450 میلیون" in DIDBAN["quote_start"] and "250 میلیون" in DIDBAN["quote_start"]
    assert "38.9" in DIDBAN["quote_rain"] and "16" in DIDBAN["quote_rain_now"]
    assert "800 تا 850" in DIDBAN["quote_need"]


if __name__ == "__main__":
    check()
    print(f"{DIDBAN['via']}; {DIDBAN['published']}; {DIDBAN['spokesman']}, {DIDBAN['office']}")
    print(f"  water year 1405 opened with about {WATER_YEAR_START} million m3 (last year about "
          f"{DIDBAN['start_last']})")
    print(f"  1 Aban 1405 (Mehr): {ONE_ABAN} million m3 (the five dams)")
    print(f"  16 Aban 1405 (Didban): about {NOW} million m3 = {100 * NOW / TOTAL_CAPACITY:.1f} % of {TOTAL_CAPACITY} "
          f"(sum of the capacities, our arithmetic) -> {DIDBAN['share_pct']} %")
    print(f"  Tehran rain to mid-Aban: {RAIN_NOW} mm; expected for the same days: {RAIN_EXPECTED} mm "
          f"({100 * RAIN_NOW / RAIN_EXPECTED:.0f} % of the expected)")
    print(f"  stable state needs about {NEED[0]} to {NEED[1]} million m3 in the five dams")
    print("all checks pass")
