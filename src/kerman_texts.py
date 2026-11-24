"""The texts that go with the Kerman reel (kerman_fa): the caption and the first comment (sources, method, the credits
the photographs' licences ask for). Every number comes from the film's own file (outputs/onebit/kerman/film.json, which
src/kerman.py writes) or is a published figure of src/kerman.py's LIT; what the sentences take for granted is asserted.
Limits: the caption at most 2,100 UTF-8 bytes and five hashtags, the comment at most 2,200 characters.

Read at the source on 23 Nov 2026 (by a helper; its notes are in the session's scratch folder, the quotes here):
Motagh et al. 2017, Eng. Geol. 218, 134-151 (accepted manuscript): wells "from approximately 70 in the 1960s to more than
1300 in the 2000s"; Mirnezami et al. 2020, Env. Dev. Sustain. 22, 8183-8210: drawdown "more than 70 cm per year" (citing
IWRMC 2006) and "all Qanats have dried up"; ICOMOS 2016 (WHC-16/40.COM/INF.8B1): Gowharriz, Jupar, "c 600 CE"; Asadi
Oskouei et al. 2023, Nivar 47, Table 2 (Ohadi 900 h) and Javanshah et al. 2010 (800 h); Mehr News 6995870 (10 Aban
1405): the Kerman water company's head on the broken main (3-4 cm of settlement, a 1,200-mm pipe), as Mehr reports it.
Not used: Nivar's "1 winter in 4" at Rafsanjan (not reproduced from hourly ERA5-Land); any claim that the settlement is
permanent (not checked at a source here).

    python -I src/kerman_texts.py     # outputs/onebit/social/kerman_fa_caption_fa.txt, kerman_fa_first_comment_fa.txt
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kerman as K  # noqa: E402
import onebit  # noqa: E402
from onebit import fa  # noqa: E402


def dec(v: float, n: int = 1) -> str:
    return K.dec(v, n)


def texts() -> dict:
    F = json.loads((K.BUILD / "film.json").read_text(encoding="utf-8"))
    N, P = F["numbers"], F["photos"]
    s, g, a, c = N["sink"], N["green"], N["air"], N["chill"]
    assert round(s["block_B"] / 5) * 5 == 30 and s["drop_m"] > 2 and round(s["years_B"]) == 8
    assert round(g["ratio"], 1) == 1.4 and round(a["warming"], 1) == 1.7 and round(-c["ch"]["change_pct"]) == 10
    w1, w2 = K.LIT["wells"]
    caption = f"""زمینِ رفسنجان سالی تا ۳۰ سانتی‌متر پایین می‌رود؛ در {fa(8)} سال بیش از ۲ متر، بلندتر از یک آدم. این را ماهواره‌های راداری اندازه گرفته‌اند.

💧 قرن‌ها قنات آبِ کرمان را می‌آورد؛ قناتِ گوهرریزِ جوپار حدودِ ۱۴۰۰ سال پیش ساخته شد. پژوهشگران می‌گویند قنات‌های دشتِ رفسنجان همه خشک شده‌اند.
🟢 چاه‌های دشتِ رفسنجان از حدودِ {fa(w1)} در دهه‌ی ۱۳۴۰ به بیش از {K.thou(w2)} رسیدند و سطحِ آبِ زیرِ زمین سالی بیش از {fa(K.LIT["drawdown_cm"])} سانتی‌متر پایین رفت. باغِ سبز از فضا حدودِ {dec(g["ratio"])} برابر شده است (لندست، ۱۳۶۶ تا ۱۴۰۴).
🔴 وقتی آبِ زیرِ زمین کم می‌شود، لایه‌های خاک فشرده می‌شوند و زمین پایین می‌رود.
🌡️ هوای رفسنجان حدودِ {dec(a["warming"])} درجه گرم‌تر شده و ساعت‌های سردِ زمستان، که پسته به آن نیاز دارد، حدودِ ۱۰٪ کمتر شده است.

آبانِ ۱۴۰۵ در شهرِ کرمان، به گفته‌ی مدیرعاملِ آبفای استان، نشستِ {fa(3)} تا {fa(4)} سانتی‌متریِ زمین لوله‌ی اصلیِ آب را شکست.

شما در کرمان یا رفسنجان ترکِ زمین یا لوله‌ی چاهی که از زمین بیرون زده دیده‌اید؟

منابع و نامِ عکاس‌ها در اولین کامنت.
#کرمان #رفسنجان #فرونشست #پسته #تغییر_اقلیم
"""
    credit = {k: v["credit"].replace("Photo: ", "") for k, v in P.items()}
    names = dict(flow="قناتِ شفیع‌آباد", dry="درونِ قنات", nuts="پسته", city="مسجدِ جامعِ کرمان")
    photo_line = "• عکس‌ها (Wikimedia Commons): " + "؛ ".join(f"{names[k]}: {credit[k]}" for k in ("flow", "dry", "nuts", "city")) + ". عکس‌ها بریده شده‌اند."
    comment = f"""منابع و روش 🙏
• فرونشست: ماهواره‌ی Sentinel-1، دو پژوهشِ جدا: Payne و همکاران ۲۰۲۵ (JGR Solid Earth، مهرِ ۱۳۹۳ تا دیِ ۱۴۰۱) و Haghshenas Haghighi و Motagh ۲۰۲۴ (Science Advances، ۲۰۱۴ تا ۲۰۲۰). تندترین یک کیلومترمربع، نزدیکِ بهرمان (نوق): {dec(s["block_B"])} و {dec(s["block_A"])} سانتی‌متر در سال. {dec(s["drop_m"], 2)} متر = {dec(s["block_B"])} سانتی‌متر × {dec(s["years_B"])} سال. حدودِ {fa(int(round(s["area_ge10_B"], -1)))} کیلومترمربع سالی بیش از ۱۰ سانتی‌متر پایین می‌رود.
• چاه‌ها: Motagh و همکاران ۲۰۱۷ (Engineering Geology). افتِ آبِ زیرزمینی و خشک شدنِ قنات‌ها: Mirnezami و همکاران ۲۰۲۰. قناتِ گوهرریز: ICOMOS و یونسکو ۲۰۱۶ (حدودِ ۶۰۰ میلادی).
• باغِ سبز: لندست ۵ و ۸ و ۹ (USGS)، اواخرِ تابستانِ ۱۳۶۶ تا ۱۳۶۹ و ۱۴۰۱ تا ۱۴۰۴، دشت زیرِ ۲۰۰۰ متر، NDVI با اصلاحِ تفاوتِ سنجنده‌ها: {fa(int(round(g["then_km2"])))} به {fa(int(round(g["now_km2"])))} کیلومترمربع ({dec(g["ratio_lo"], 2)} تا {dec(g["ratio_hi"], 2)} برابر). فقط تاجِ سبز شمرده شده؛ باغِ خشکیده یا کم‌برگ نه.
• دما: CRU TS 4.10، میانگینِ ۱۹۹۶ تا ۲۰۲۵ نسبت به ۱۹۵۱ تا ۱۹۸۰.
• سرما: ERA5-Land ساعتی، یاخته‌ی رفسنجان، ساعت‌های ۰ تا ۷٫۲ درجه از نوامبر تا فوریه: {fa(int(round(c["ch"]["first"])))} به {fa(int(round(c["ch"]["last"])))} (همان دو دوره). نیازِ پسته‌ی اوحدی: ۸۰۰ تا ۹۰۰ ساعت (Asadi Oskouei و همکاران ۲۰۲۳، مجله‌ی نیوار؛ Javanshah و همکاران ۲۰۱۰).
• لوله‌ی کرمان: خبرگزاری مهر، ۱۰ آبانِ ۱۴۰۵، از قولِ مدیرعاملِ آبفای استانِ کرمان.
{photo_line}
"""
    return dict(caption=caption, first_comment=comment)


def main() -> None:
    social = onebit.OUT / "social"
    T = texts()
    for k, v in T.items():
        (social / f"kerman_fa_{k}_fa.txt").write_text(v, encoding="utf-8")
    c = T["caption"]
    print(f"caption: {len(c)} characters, {len(c.encode('utf-8'))} bytes (limit 2,100), {c.count('#')} hashtags")
    assert len(c.encode("utf-8")) <= 2100 and c.count("#") <= 5
    print(f"first comment: {len(T['first_comment'])} characters (limit 2,200)")
    assert len(T["first_comment"]) <= 2200
    for banned in ("تقصیر", "سوءمدیریت", "مقصر", "فاجعه"):
        assert not any(banned in v for v in T.values()), banned
    print("\n" + c + "\n" + T["first_comment"])


if __name__ == "__main__":
    main()
