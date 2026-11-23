"""The texts that go with the documentary cut of the ice-age film (cycles_fa, cut "d", «دالانِ زندگی»): the caption with
two endings, the first comment (sources, method, the credits the photographs' licences ask for) and a timed script for
a narrator. Every number is taken from the film's own file (outputs/onebit/cycles/film.json, which src/cycles.py
writes); what the sentences take for granted is asserted. Limits: the caption at most 2,100 UTF-8 bytes and five
hashtags, the comment at most 2,200 characters.

The caption's two endings, for the owner to choose between (23 Nov 2026). "caption_with_ask" carries his own call to
send the reel on and to repost it. "caption" ends on an open question, as the film's last card does: Instagram's
@creators account said in June 2024 that content which "explicitly asks for engagement through shares, comments, tags,
or other actions" is not recommended, while open-ended calls are fine. That was read as quoted by Social Media Today,
not at Instagram itself; the owner's own reels with a send line had reached well.

The sentences that are not computed here rest on the film's sources (src/cycles.py names them) and on these, read on
23 Nov 2026. The owner's rule is to check the primary source before posting; "search results" below means that the
page itself was not opened and that check is still to do.
- COP31: UN News, 22 Nov 2026, "COP31 ends without climate pact ..." (news.un.org/en/story/2026/11/1168855), and the
  Secretary-General on its end "without consensus on an overarching outcome". Search results.
- "About 10 times faster" and "4 to 7 degrees in about 5,000 years" are NASA's (Earth Observatory). The film's own data
  give a larger ratio (numbers.rate_ratio), so the caption keeps NASA's rounder figure and names NASA; the same
  reconstruction's fastest 5,000 years are computed below and set beside NASA's range in the comment.
- "Today is above the warmest period of the last 10,000 years": IPCC AR6 WG1, Summary for Policymakers, A.2.2 (the
  decade 2011-2020 against the warmest multi-century period, about 6,500 years ago; medium confidence, which the
  caption says). ipcc.ch refuses automated reading. Search results that index the IPCC's own pages.
- The Gulf's filling (Lambeck 1996) is the sentence of the first cut's comment (cycles_fa_first_comment_fa.txt).
- The Holocene's start, 11,700 years ago: the International Commission on Stratigraphy's definition.

No voice was recorded: the owner will not narrate ("not my voice", 23 Nov 2026), and a synthetic Persian voice could not
be checked by anyone who hears it. The script stays for a narrator of his choosing; its times are the film's cues.

    python -I src/cycles.py              # first: outputs/onebit/cycles/film.json
    python -I src/cycles_doc_texts.py    # outputs/onebit/social/cycles_fa_doc_caption_fa.txt, _caption_with_ask_fa.txt,
                                         # _first_comment_fa.txt, _narration_fa.txt
"""

from __future__ import annotations

import json
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cycles as C  # noqa: E402
import onebit  # noqa: E402
from onebit import fa  # noqa: E402

ASK = "برای کسی بفرستید که می‌گوید زمین همیشه گرم و سرد شده. اگر می‌خواهید ادامه بدهم، بازنشر کنید؛ با هم آگاهی را بیشتر می‌کنیم."
OPEN = "دفعه‌ی بعد که کسی گفت «زمین همیشه گرم و سرد شده»، جوابش همین‌جاست. شما چه فکر می‌کنید؟"
SHOWN = (("zagros", "تندیسِ تپه سراب (موزه‌ی ملیِ ایران)"), ("sukhteh", "جامِ شهرِ سوخته"), ("persepolis", "تخت‌جمشید"),
         ("today", "برجِ میلاد"), ("end", "پایان"))               # the photographs in the film's order, as the comment names them
PACE = 2.5                                                         # words a second: no line of the script may ask for more


def half(v: float, n: int = 0) -> str:
    """v to n decimals with halves up (427.35 is 427.4), in Persian digits."""
    q = Decimal(repr(float(v))).quantize(Decimal(1).scaleb(-n), rounding=ROUND_HALF_UP)
    return fa(f"{q:f}").replace(".", "٫")


def at(t: float) -> str:
    return "[۰۰:%s]" % ("%04.1f" % t).translate(str.maketrans("0123456789.", "۰۱۲۳۴۵۶۷۸۹٫"))


def texts() -> dict:
    F = json.loads((C.BUILD / "film.json").read_text(encoding="utf-8"))
    N, Q, P, D = F["numbers"], F["cues"], F["photos"], F["cuts"]["d"]
    st = {s["key"]: s["start"] for s in D["scenes"]}
    T = {int(a): v for a, v in F["series"]["temp"]}                      # Osman et al. 2021: 200-year means by years ago
    fast = max(T[a] - T[a + 5000] for a in T if a + 5000 in T)              # the most warming in any 5,000 years of it
    shown = json.dumps([F["words"], D], ensure_ascii=False)                 # every word of the picture

    # what the fixed words take for granted
    assert (half(N["melt"]), half(N["holo_span"])) == ("۶", "۱"), N         # «حدودِ ۶ درجه», «حدودِ ۱ درجه», «شش درجه»
    assert abs((T[9900] - T[20100]) - N["melt"]) < 2e-3                     # «از ۲۰ تا ۱۰ هزار سال پیش»: 20,100 to 9,900
    assert abs((F["corridor"][1] - F["corridor"][0]) - N["holo_span"]) < 2e-3   # the corridor is that 1 degree
    assert N["rate_ratio"] >= 10                                            # «حدودِ ۱۰ برابر (ناسا)»: this film's own ratio is larger
    assert 4 <= fast <= 7                                                   # NASA's «۴ تا ۷ درجه» holds in this reconstruction
    assert N["co2_span"] >= 800_000 and N["co2_max_old"] < 300              # «در ۸۰۰ هزار سال هرگز بالای ۳۰۰»
    assert (N["mlo_year"], round(N["mlo"])) == (2025, 427)                  # the script spells it: «چهارصد و بیست و هفت»
    assert fa(round(N["mlo"])) in shown and half(N["now"], 1) + " درجه" in shown   # today's two figures are the picture's
    assert "۷۰۰۰ تا ۶۱۰۰" in P["zagros"]["what"] and {k for k, _ in SHOWN} == set(P), sorted(P)

    def caption(ending: str) -> str:
        return f"""COP31 بدونِ توافق تمام شد. «زمین همیشه گرم و سرد شده»؟ آره؛ ولی تمدن فقط در آرامش ساخته شد:

🔵 طبیعی: ۲۰ هزار سال پیش خلیجِ فارس خشکی بود. بعد از آخرین یخبندان، زمین حدودِ {half(N["melt"])} درجه در حدودِ ۱۰ هزار سال گرم شد.
🟡 دالانِ زندگی: در ۱۰ هزار سالِ بعد (هولوسن) دمای زمین فقط حدودِ {half(N["holo_span"])} درجه بالا و پایین شد. اهلی شدنِ بز در زاگرس، شهرِ سوخته و تخت‌جمشید، همه در همین دالان.
🔴 انسانی: {half(N["now"], 1)} درجه در حدودِ ۱۵۰ سال؛ حدودِ ۱۰ برابر تندتر از گرم شدنِ پس از یخبندان (ناسا). دمای امروز از گرم‌ترین دوره‌ی ۱۰ هزار سالِ گذشته بالاتر رفته است (IPCC، با اطمینانِ متوسط).
دی‌اکسیدِ کربن در ۸۰۰ هزار سال هرگز بالای ۳۰۰ ppm نرفت (بالاترین نمونه {half(N["co2_max_old"], 1)})؛ امروز {fa(round(N["mlo"]))}. بیشترِ افزایشِ آن از سوزاندنِ نفت، گاز و زغال‌سنگ است.

{ending}

منابع و نامِ عکاس‌ها در اولین کامنت.
#تغییر_اقلیم #گرمایش_زمین #ایران #تخت_جمشید #هولوسن
"""

    credit = {k: v["credit"].replace("Photo: ", "") for k, v in P.items()}
    photo_line = "• عکس‌ها (Wikimedia Commons): " + "؛ ".join(f"{name}: {credit[k]}" for k, name in SHOWN) + "."
    comment = f"""منابع و روش 🙏
• یخ‌ها و خشکیِ خلیجِ فارس: مدلِ ICE-6G_C (Peltier و همکاران ۲۰۱۵) روی عمق‌سنجیِ ETOPO1؛ خلیجِ فارس حدودِ ۲۰ هزار سال پیش خشکی بود و حدودِ ۸ تا ۶ هزار سال پیش پُر شد (Lambeck ۱۹۹۶). دریای کاسپین (خزر)، دریای سیاه و آرال با ساحلِ امروز کشیده شده‌اند.
• دمای ۲۰ هزار سال: Osman و همکاران ۲۰۲۱، مجله‌ی Nature (میانگین‌های ۲۰۰ ساله). {half(N["melt"])} درجه: از ۲۰ تا ۱۰ هزار سال پیش. ناسا: ۴ تا ۷ درجه در حدودِ ۵ هزار سال؛ در همین بازسازی {half(fast, 1)} درجه در تندترین ۵ هزار سال.
• دالانِ زندگی: سردترین و گرم‌ترین میانگینِ ۲۰۰ ساله‌ی ۱۰ هزار سالِ اخیر در همان بازسازی (حدودِ {half(N["holo_span"])} درجه فاصله). IPCC (AR6، SPM A.2.2): دمای دهه‌ی ۲۰۱۱ تا ۲۰۲۰ از گرم‌ترین دوره‌ی چندصدساله‌ی حدودِ ۶۵۰۰ سال پیش بالاتر است (اطمینانِ متوسط). هولوسن از ۱۱٬۷۰۰ سال پیش آغاز شده است.
• تمدن‌ها: اهلی شدنِ بز در زاگرس، حدودِ ۱۰ هزار سال پیش (Zeder و Hesse، مجله‌ی Science، ۲۰۰۰)؛ تندیسِ گِلیِ تپه سراب، ۷۰۰۰ تا ۶۱۰۰ پیش از میلاد (موزه‌ی ملیِ ایران)؛ شهرِ سوخته، بنیاد در حدودِ ۳۲۰۰ پیش از میلاد، و تخت‌جمشید، ۵۱۸ پیش از میلاد (فهرستِ میراثِ جهانیِ یونسکو).
• ۱۵۰ سالِ اخیر: HadCRUT5 (Met Office)، میانگینِ ۲۰۱۶ تا ۲۰۲۵ نسبت به ۱۸۵۰ تا ۱۹۰۰: {half(N["now"], 2)} درجه.
• دی‌اکسیدِ کربن: هسته‌های یخِ قطبِ جنوب (Bereiter و همکاران ۲۰۱۵؛ بیشترین {half(N["co2_max_old"], 1)} ppm) و مائونالوآ (NOAA، میانگینِ {fa(N["mlo_year"])}: {half(N["mlo"], 1)}).
• COP31 (آنتالیا) بدونِ توافقِ نهایی تمام شد: UN News، ۲۲ نوامبرِ ۲۰۲۶ (۱ آذر ۱۴۰۵).
{photo_line} عکس‌ها بریده شده‌اند.
• تصویرِ زمین: NASA Blue Marble؛ برجستگی‌ها برای دیده شدن اغراق شده است.
"""

    # the script: each group of lines is a scene; a line starts at its moment and has until the next one starts
    life, marks = st["life"], Q["life"]["marks"]
    groups = [[(0.3, "بیست هزار سال پیش، خلیجِ فارس خشکی بود."),
               (Q["gulf"]["turn"] + 0.2, "زمین همیشه گرم و سرد شده؟ آره.")],
              [(st["thaw"] + 0.3, "یخ‌ها آب شدند. زمین شش درجه گرم شد؛ در ده هزار سال.")],
              [(life + marks[0] - 1.6, "ده هزار سال پیش، در زاگرس بز را اهلی کردیم."),
               (life + marks[1] - 0.3, "بعد شهرِ سوخته را ساختیم."),
               (life + marks[2] - 0.3, "و تخت‌جمشید را."),
               (life + Q["life"]["last"], "همه در یک دالان.")],
              [(st["exit"] + 0.5, "حالا در صد و پنجاه سال، از دالان بیرون زده‌ایم."),
               (st["exit"] + Q["exit"]["small"][-1] - 1.0, "چرا؟ دی‌اکسیدِ کربن. امروز: چهارصد و بیست و هفت.")],
              [(st["send"] + 0.6, "دفعه‌ی بعد که کسی گفت زمین همیشه گرم و سرد شده، جوابش همین‌جاست.")]]
    said = [x for g in groups for x in g]
    until = [t for t, _ in said[1:]] + [D["end"]]
    pace = max(len(s.split()) / (e - t) for (t, s), e in zip(said, until))
    assert all(a[0] < b[0] for a, b in zip(said, said[1:])) and pace <= PACE, pace
    spoken = "\n\n".join("\n".join(f"{at(t)}  {s}" for t, s in g) for g in groups)
    script = f"""متنِ گفتار برای نسخه‌ی مستند «دالانِ زندگی» ({C.dec(D["end"], 2)} ثانیه)
برای گوینده. آرام بخوانید: تندترین خط حدودِ {half(pace, 1)} کلمه در ثانیه می‌خواهد. عددها با حروف نوشته شده‌اند تا راحت خوانده شوند.
هر خط از لحظه‌ای که جلویش نوشته شده شروع می‌شود؛ بینِ خط‌ها مکث کنید تا تصویر عوض شود.

{spoken}

یادداشت:
- هر جمله یک عدد یا یک نام دارد که همان لحظه روی تصویر می‌آید؛ اگر عقب افتادید، جمله را کوتاه نکنید، مکثِ بعدی را کم کنید.
- اگر صدای هوش مصنوعی گذاشته شد، در اینستاگرام برچسبِ «اطلاعاتِ هوش مصنوعی» را روشن کنید.
"""
    return dict(caption=caption(OPEN), caption_with_ask=caption(ASK), first_comment=comment, narration=script)


def main() -> None:
    social = onebit.OUT / "social"
    T = texts()
    for k, v in T.items():
        (social / f"cycles_fa_doc_{k}_fa.txt").write_text(v, encoding="utf-8")
    for k in ("caption", "caption_with_ask"):
        c = T[k]
        print(f"{k}: {len(c)} characters, {len(c.encode('utf-8'))} bytes (limit 2,100), {c.count('#')} hashtags")
        assert len(c.encode("utf-8")) <= 2100 and c.count("#") <= 5
    assert not any(w in T["caption"] for w in ("بفرست", "بازنشر"))          # this ending asks for no send and no repost
    print(f"first comment: {len(T['first_comment'])} characters (limit 2,200)")
    assert len(T["first_comment"]) <= 2200
    for banned in ("تقصیر", "سوءمدیریت", "مقصر"):                           # the owner's rule: no words of blame
        assert not any(banned in v for v in T.values()), banned
    print("\n" + T["caption"] + "\n" + T["first_comment"])


if __name__ == "__main__":
    main()
