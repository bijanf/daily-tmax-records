"""The caption and the first comment of the Hormuz NO2 reel (hormuz_fa), written from the film's own numbers
(outputs/onebit/hormuz/film.json, which src/hormuz.py film writes): no number is typed here except the dates and the
processor versions, and those are asserted. Limits: the caption at most 2,100 UTF-8 bytes and five hashtags, the
first comment at most 2,200 characters.

    python -I src/hormuz_texts.py       # outputs/onebit/social/hormuz_fa_caption_fa.txt, _first_comment_fa.txt
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hormuz as H  # noqa: E402
import onebit  # noqa: E402
from onebit import fa  # noqa: E402

THEN, NOW = str(H.THEN), str(H.NOW)


def p(x: float) -> str:
    return fa(f"{round(100 * abs(x))}٪")


def versions() -> dict:
    """The processor versions of the orbits of the closure window, per year (from the fields' logs)."""
    out = {}
    for y in ("2023", "2024", THEN, NOW):
        out[y] = set()
        for k in H.CLOSURE:
            out[y].update(json.loads((H.FIELDS / f"{y}-{k}.json").read_text())["versions"])
    return out


def texts() -> tuple:
    F = json.loads((H.BUILD / "film.json").read_text(encoding="utf-8"))
    n = F["numbers"]
    ch, sh, parts, rg = n["change"], n["ships"], {q["key"]: q for q in n["parts"]}, n["ranges"]
    s, st, b, ratio, normal = ch["sites"], n["closure"]["sites"], n["before"], n["ratio"], n["normal"]
    inside = n["closure"]["inside"]
    # what the sentences below take for granted
    assert round(100 * s["jubail"]) == round(100 * s["dubai"]), (s["jubail"], s["dubai"])            # «جبیل و دبی»
    assert all(parts[k]["inside"] < 0 for k in ("j04", "j05", "j08")) and parts["j06"]["inside"] > 0
    assert abs(parts["j07"]["inside"]) < 0.005                                                         # «برابر (مهر)»
    assert all(q["inside"] > 0 for q in normal) and len(normal) == 2 and b["inside"] > 0 and b["outside"] > 0
    assert n["below_all"] == ["asaluyeh", "ras_laffan", "jubail", "kuwait"], n["below_all"]
    assert versions() == {"2023": {"2.4.0", "2.5.0"}, "2024": {"2.6.0"}, THEN: {"2.8.0"}, NOW: {"02.09.01"}}, versions()
    assert rg["outside"][0] < 0 < rg["outside"][1] and ch["outside"] > 0 and b["seas"]["gulf"] < 0
    out_lo, out_hi = min(q["outside"] for q in n["parts"]), max(q["outside"] for q in n["parts"])
    assert out_lo < 0 < out_hi
    # the six places against the three on the Gulf of Oman: in the window, and in the parts after it
    rel = lambda q: (1 + q["inside"]) / (1 + q["outside"]) - 1                                        # noqa: E731
    rel_window = (1 + ch["inside"]) / (1 + ch["outside"]) - 1
    after = [rel(parts[k]) for k in H.AFTER]
    # «فاصله کم شد و در پاییز دوباره بیشتر»: right after the window less than half of it, in the last part more than half
    assert all(v < 0 for v in after) and max(abs(v) for v in after[:2]) < 0.5 * abs(rel_window) < abs(after[-1]), (after, rel_window)
    r3 = sorted(ratio[y] for y in ("2023", "2024", THEN))
    cap = f"""آلاینده‌ی هوا روی خلیجِ فارس: حدودِ {fa(5 * round(100 * abs(ch['inside']) / 5))}٪ کمتر از پارسال

این نقشه‌ها دی‌اکسیدِ نیتروژن (NO₂) را از دیدِ ماهواره‌ی Sentinel-5P نشان می‌دهند: گازی که از سوختنِ سوخت در موتورِ کشتی و خودرو، نیروگاه و صنعتِ نفت و گاز می‌آید و فقط چند ساعت در هوا می‌ماند.

از ۱۰ اسفندِ ۱۴۰۴ عبورِ کشتی‌ها از تنگه‌ی هرمز به‌شدت کم شد. ۱۰ اسفند تا ۲۷ خرداد را با همان روزهای پارسال مقایسه کرده‌ایم:
• شش جا در خلیجِ فارس: عسلویه {p(s['asaluyeh'])}، رأس لفان {p(s['ras_laffan'])}، جبیل و دبی {p(s['dubai'])}، بندرعباس {p(s['bandar'])} و کویت {p(s['kuwait'])} کمتر؛ روی‌هم {p(ch['inside'])} کمتر از پارسال و {p(n['three']['inside'])} کمتر از میانگینِ سه سالِ پیش.
• سه جا در دریای عمان (فجیره، صحار، مسقط): تقریباً بدونِ تغییر.
• کشتی‌های شمرده‌شده در هرمز (با فرستنده‌ی AIS): از حدودِ {fa(round(sh['then']))} به {fa(round(sh['now']))} در روز. کشتی‌های بی‌فرستنده شمرده نمی‌شوند.

این فقط اثرِ کشتی‌ها نیست: دی‌اکسیدِ نیتروژن روی بندرها و مراکزِ نفت و گاز هم کمتر شد و سهمِ هر کدام را از فضا نمی‌شود جدا کرد.

این کاهش بهبودِ پایدارِ هوا نیست: بعد از ۲۷ خرداد اختلاف با پارسال کمتر شد، هرچند نامنظم (در ۱ تا ۱۶ آبان هنوز {p(parts['j08']['inside'])} کمتر).

منابع و روش در کامنتِ اول.

شما در جنوب، هوای این بهار را چطور دیدید؟

#خلیج_فارس #تنگه_هرمز #آلودگی_هوا #ماهواره #بندرعباس
"""
    com = f"""منابع و روش (۱ مارس ۲۰۲۶ = ۱۰ اسفندِ ۱۴۰۴؛ ۱۷ ژوئن = ۲۷ خرداد، روزِ تفاهم‌نامه):
۱) داده: ستونِ دی‌اکسیدِ نیتروژن در پایینِ جو، ماهواره‌ی Sentinel-5P (TROPOMI، ESA)، محصولِ OFFL با فیلترِ کیفیتِ توصیه‌شده (qa_value بالای ۰٫۷۵)، روی شبکه‌ی ۰٫۰۲۵ درجه. نقشه: Blue Marble، ناسا.
۲) هر «جا» میانگینِ کادرِ ±۰٫۲ درجه (حدودِ ۴۰ کیلومتر) است. شش جای خلیجِ فارس: از {fa(f"{inside[THEN]:.1f}")} به {fa(f"{inside[NOW]:.1f}")} (×۱۰¹⁵ مولکول بر سانتی‌مترمربع)، {p(ch['inside'])} کمتر (بازه‌ی ۹۰٪ با بازنمونه‌گیریِ روزها: {p(rg['inside'][1])} تا {p(rg['inside'][0])}). سه جای دریای عمان: {p(ch['outside'])} بیشتر (از {p(rg['outside'][0])} کمتر تا {p(rg['outside'][1])} بیشتر).
۳) پیش از ماجرا (۱ ژانویه تا ۲۸ فوریه) هر دو گروه بیشتر از پارسال بودند: {p(b['inside'])} و {p(b['outside'])}. فاصله‌ی دو گروه از ۱۰ اسفند باز شد.
۴) سال‌های عادی: شش جا از ۲۰۲۳ به ۲۰۲۴، {p(normal[0]['inside'])} و از ۲۰۲۴ به ۲۰۲۵، {p(normal[1]['inside'])} بیشتر شدند؛ ۲۰۲۶ از میانگینِ سه سالِ پیش {p(n['three']['inside'])} کمتر است (۲۰۲۳ با نسخه‌ی ۲٫۴ و ۲٫۵ و ۲۰۲۴ با ۲٫۶ پردازش شده‌اند). نسبتِ شش جا به سه جای دریای عمان در آن سه سال {fa(f"{r3[0]:.1f}")} تا {fa(f"{r3[-1]:.1f}")} بود و در ۲۰۲۶: {fa(f"{ratio[NOW]:.1f}")}. عسلویه، رأس لفان، جبیل و کویت از هر سه سالِ پیش کمترند؛ دبی و بندرعباس فقط از پارسال.
۵) روی آبِ خلیجِ فارس {p(ch['seas']['gulf'])} کمتر (پیش از ماجرا {p(b['seas']['gulf'])} کمتر).
۶) نسخه‌ی پردازش از ۲٫۸ به ۲٫۹٫۱ عوض شده است؛ KNMI: برای بیشترِ کاربردها تغییرِ کمی دارد ولی شاید ناپیوستگی دیده شود. پیکسلِ معتبر در ۲۰۲۶ کمتر بود ({p(rg['valid'][NOW])} در برابرِ {p(rg['valid'][THEN])}).
۷) کشتی‌ها: IMF PortWatch (AIS)؛ ۱ مارس تا ۱۷ ژوئن: {fa(round(sh['then']))} و {fa(f"{sh['now']:.1f}")} در روز. بعد از آن هم {fa(round(sh['after_now']))} در برابرِ {fa(round(sh['after_then']))}؛ منابعِ دیگر (Kpler، Windward) برای ماه‌های بعد عددهای بالاتری می‌دهند. دی‌اکسیدِ نیتروژن فقط با شمارِ کشتی توضیح داده نمی‌شود.
۸) بعد از ۱۷ ژوئن، شش جا نسبت به پارسال: {p(parts['j04']['inside'])} کمتر (تا ۱۱ تیر)، {p(parts['j05']['inside'])} کمتر (۲۱ تا ۳۱ مرداد)، {p(parts['j06']['inside'])} بیشتر (شهریور)، برابر (مهر)، {p(parts['j08']['inside'])} کمتر (۱ تا ۱۶ آبان). نسبت به سه جای دریای عمان، در این بخش‌ها {p(max(after))} تا {p(min(after))} پایین‌تر ماندند (در بازه‌ی اصلی: {p(rel_window)}): فاصله کم شد و در پاییز دوباره بیشتر. ماهواره از ۳ ژوئیه تا ۱۱ اوتِ ۲۰۲۵ داده ندارد.
۹) عمرِ کوتاهِ این گاز: Beirle و همکاران ۲۰۱۱، doi:10.1126/science.1207824. مسیرِ تقریبیِ کشتی‌ها (نه رفت‌وآمدِ ۲۰۲۶): فهرستِ انتشارِ EDGAR v8.1 برای ۲۰۲۲ (Crippa و همکاران ۲۰۲۴، doi:10.5194/essd-16-2811-2024). کد: github.com/bijanf/daily-tmax-records (شاخه‌ی elnino-iran).
"""
    return cap, com


def main() -> None:
    cap, com = texts()
    social = onebit.OUT / "social"
    (social / "hormuz_fa_caption_fa.txt").write_text(cap, encoding="utf-8")
    (social / "hormuz_fa_first_comment_fa.txt").write_text(com, encoding="utf-8")
    c, m = cap.rstrip("\n"), com.rstrip("\n")
    print(f"caption: {len(c)} characters, {len(c.encode('utf-8'))} bytes (limit 2,100), {c.count('#')} hashtags")
    print(f"first comment: {len(m)} characters (limit 2,200)")
    assert len(c.encode("utf-8")) <= 2100 and c.count("#") <= 5 and len(m) <= 2200


if __name__ == "__main__":
    main()
