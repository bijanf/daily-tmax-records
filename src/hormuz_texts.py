"""The texts that go with the Hormuz NO2 reel (hormuz_fa): the caption, the first comment (sources and method), the
second comment (where the ship counts come from, beside the counters of other publishers) and reply drafts.
Every number of ours is taken from the film's own file (outputs/onebit/hormuz/film.json, which src/hormuz.py film
writes) or counted here from the PortWatch file; what the sentences take for granted is asserted. The numbers of other
publishers are typed in OTHERS with the page each was read on. Limits: the caption at most 2,100 UTF-8 bytes and five
hashtags, each comment at most 2,200 characters.

    python -I src/hormuz_texts.py     # outputs/onebit/social/hormuz_fa_caption_fa.txt, _first_comment_fa.txt,
                                      # _second_comment_fa.txt, _replies_fa.txt
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
# What other publishers say, each read on its own page on 18 November 2026:
#   portwatch: its dataset's own description (ArcGIS item 3da2b9ca97684916b75c4013f95d18ab, owner IMF PortWatch): "a
#       transit call is defined when a ship transits through the chokepoint boundary", a ship is counted again after
#       48 hours, AIS is "our primary data source"; n_total is tankers plus cargo ships (container, dry bulk, general
#       cargo, ro-ro; checked on every row of the file). "PortWatch is a joint initiative of the International Monetary
#       Fund (IMF), the University of Oxford, and Delft University of Technology" (University of Oxford, Environmental
#       Change Institute, news of 4 December 2025).
#   clarksons: Clarksons Research update of 16 March 2026, as reprinted by Cyprus Shipping News on 17 March ("av. 5
#       transits per day past week vs ~125 pre-conflict"), cyprusshippingnews.com/2026/03/17/...
#   windward_march: Windward, "Iran War at Sea", 20 March 2026 ("a pre-war average of 120 daily transits to just
#       6.9"; "an 84.4% reduction in large vessels physically present in the corridor", satellite pictures of 17
#       January and 13 March; "Qatar confirmed a full halt to gas production on March 19" at Ras Laffan),
#       windward.ai/blog/iran-war-global-trade-and-energy-disruptions/
#   windward_may: Windward, "Hormuz Reopens: What Marine Insurers Are Facing Now", 18 June 2026 ("Over May 2026,
#       Windward tracked 156 transits through the Strait, 22% of which were dark"),
#       windward.ai/blog/hormuz-reopens-what-marine-insurers-are-facing/
#   cao: Cao et al. 2026, The Innovation 7(6), 101367, doi:10.1016/j.xinn.2026.101367, a letter (Sentinel-1 radar: the
#       ships seen per picture of the strait fell from 15.25 to 0.5, 22-28 February against 1-7 March, "approximately
#       97%"). Yang et al. 2026 (doi:10.1016/j.ocecoaman.2026.108265) is NOT used: its "130 to fewer than 10" stands in
#       the background of the abstract, not among its radar results.
#   kpler: Kpler blog of 23 July 2026 ("daily Strait of Hormuz crossings falling from roughly 45 to just 13", 45 being
#       the mean of 7 June to 7 July), kpler.com/blog/strait-of-hormuz-crossings-drop-70-...
#   lloyds: Lloyd's List Intelligence, Strait of Hormuz Brief of 5 November 2026 (transits of ships that are not
#       Iranian-linked: a weekly mean of 121 over 5-25 October)
#   weathernews: Weathernews (Japan), news item of 1 May 2026 on Sentinel-5P NO2: March 2026 about 30 to 40 % below
#       March 2025 around the Persian Gulf, weathernews.jp/news/202604/290061/
#   edgar: the EDGAR v8.1 air-pollutant page asks for a reference to itself and names Crippa et al. (2024, the EDGAR
#       v8.0 paper, doi:10.5194/essd-16-2811-2024) for its spatial proxies, edgar.jrc.ec.europa.eu/dataset_ap81
OTHERS = dict(clarksons=(125, 5), windward_march=(120, 6.9), windward_sat=0.84, windward_may=(156, 0.22), cao=0.97,
              kpler=(45, "06-07", "07-07"), lloyds=(121, "10-05", "10-25"), weathernews=(30, 40))


def p(x: float) -> str:
    return fa(f"{round(100 * abs(x))}٪")


def n(x) -> str:
    """A count in Persian digits with the Persian thousands mark."""
    return fa(f"{x:,}".replace(",", "٬"))


def versions() -> dict:
    """The processor versions of the orbits of the closure window, per year (from the fields' logs)."""
    out = {}
    for y in ("2023", "2024", THEN, NOW):
        out[y] = set()
        for k in H.CLOSURE:
            out[y].update(json.loads((H.FIELDS / f"{y}-{k}.json").read_text())["versions"])
    return out


def transits() -> dict:
    """Counted from the PortWatch file: the transit calls of the closure window in both years, of May of both years,
    and the later year's mean a day over the days that Kpler and Lloyd's List report on."""
    import pandas as pd
    d = pd.read_csv(H.DATA / "portwatch_hormuz_daily.csv", parse_dates=["date"]).set_index("date")["n_total"]
    a, b = H.PARTS[H.CLOSURE[0]][0], H.PARTS[H.CLOSURE[-1]][1]
    w = {y: d[f"{y}-{a}":f"{y}-{b}"] for y in (THEN, NOW)}
    span = lambda q: float(d[f"{NOW}-{q[1]}":f"{NOW}-{q[2]}"].mean())                               # noqa: E731
    return dict(days=len(w[NOW]), then=int(w[THEN].sum()), now=int(w[NOW].sum()), may=int(d[f"{NOW}-05-01":f"{NOW}-05-31"].sum()),
                may_then=float(d[f"{THEN}-05-01":f"{THEN}-05-31"].mean()), kpler_days=span(OTHERS["kpler"]),
                lloyds_days=span(OTHERS["lloyds"]))


def texts() -> dict:
    F = json.loads((H.BUILD / "film.json").read_text(encoding="utf-8"))
    m = F["numbers"]
    ch, sh, parts, rg = m["change"], m["ships"], {q["key"]: q for q in m["parts"]}, m["ranges"]
    s, b, ratio, normal = ch["sites"], m["before"], m["ratio"], m["normal"]
    inside = m["closure"]["inside"]
    tr, O = transits(), OTHERS
    # what the sentences below take for granted
    assert round(100 * s["jubail"]) == round(100 * s["dubai"]), (s["jubail"], s["dubai"])            # «جبیل و دبی»
    assert all(q["inside"] > 0 for q in normal) and len(normal) == 2 and b["inside"] > 0 and b["outside"] > 0
    assert m["below_all"] == ["asaluyeh", "ras_laffan", "jubail", "kuwait"], m["below_all"]
    assert versions() == {"2023": {"2.4.0", "2.5.0"}, "2024": {"2.6.0"}, THEN: {"2.8.0"}, NOW: {"02.09.01"}}, versions()
    assert rg["outside"][0] < 0 < rg["outside"][1] and ch["outside"] > 0 and b["seas"]["gulf"] < 0
    assert (F["scale"]["v0"], F["scale"]["v1"], F["scale"]["log"]) == (1.0, 10.0, True), F["scale"]      # «مقیاسِ لگاریتمی از ۱ تا ۱۰»
    assert 0.145 < m["ship_share"] < 0.185, m["ship_share"]                                            # «حدودِ یک‌ششم»
    # the six places against the three on the Gulf of Oman: in the window, and in the parts after it
    rel = lambda q: (1 + q["inside"]) / (1 + q["outside"]) - 1                                        # noqa: E731
    rel_window = (1 + ch["inside"]) / (1 + ch["outside"]) - 1
    after = [rel(parts[k]) for k in H.AFTER]
    after_in = [parts[k]["inside"] for k in H.AFTER]
    assert all(v < 0 for v in after) and min(after_in) < 0 < max(after_in), (after, after_in)          # «از … کمتر تا … بیشتر»
    assert abs(min(after_in) - parts["j08"]["inside"]) < 1e-9, after_in                                # the caption's «۱ تا ۱۶ آبان»
    r3 = sorted(ratio[y] for y in ("2023", "2024", THEN))
    # the season: the same days of both years, and each month of the window by itself (the six places against the same month of last year)
    assert all(parts[k]["inside"] < -0.2 for k in H.CLOSURE), [parts[k]["inside"] for k in H.CLOSURE]
    mo = [p(parts[k]["inside"]) for k in H.CLOSURE]
    months = "، ".join(mo[:-1]) + " و " + mo[-1]
    # the ships: our count, and the counts of other publishers
    assert tr["days"] == 109 and abs(tr["now"] / tr["days"] - sh["now"]) < 1e-6 and abs(tr["then"] / tr["days"] - sh["then"]) < 1e-6, tr
    visible = round(O["windward_may"][0] * (1 - O["windward_may"][1]))
    assert visible == tr["may"], (visible, tr["may"])                    # Windward's transits with AIS in May, and PortWatch's May
    may_all = O["windward_may"][0] / 31                                  # May with the ships that sailed dark, a day
    assert round(may_all) == 5 and 1 - may_all / tr["may_then"] > 0.9, (may_all, tr["may_then"])
    assert 1 - O["clarksons"][1] / O["clarksons"][0] > 0.9 and 1 - O["windward_march"][1] / O["windward_march"][0] > 0.9
    assert round(sh["then"]) < O["windward_march"][0] < O["clarksons"][0] == 125                        # «۹۷ تا ۱۲۵»
    assert 16.5 < tr["kpler_days"] < 17.5 and 3.5 < tr["lloyds_days"] < 4.5 and 16.5 < O["lloyds"][0] / 7 < 17.5, tr

    cap = f"""آلاینده‌ی هوا روی خلیجِ فارس: حدودِ {fa(5 * round(100 * abs(ch['inside']) / 5))}٪ کمتر از پارسال

این نقشه‌ها دی‌اکسیدِ نیتروژن (NO₂) را روی خلیجِ فارس، تنگه‌ی هرمز و دریای عمان از دیدِ ماهواره‌ی Sentinel-5P نشان می‌دهند: گازی که از سوختنِ سوخت در موتورِ کشتی و خودرو، نیروگاه و صنعتِ نفت و گاز می‌آید و چند ساعت در هوا می‌ماند.

از ۱۰ اسفندِ ۱۴۰۴ عبورِ کشتی‌ها از تنگه‌ی هرمز به‌شدت کم شد. ۱۰ اسفند تا ۲۷ خرداد را با همان روزهای پارسال مقایسه کرده‌ایم:
• شش جا در خلیجِ فارس: عسلویه {p(s['asaluyeh'])}، رأس لفان {p(s['ras_laffan'])}، جبیل و دبی {p(s['dubai'])}، بندرعباس {p(s['bandar'])} و کویت {p(s['kuwait'])} کمتر؛ روی‌هم {p(ch['inside'])} کمتر از پارسال و {p(m['three']['inside'])} کمتر از میانگینِ سه سالِ پیش.
• سه جا در دریای عمان (فجیره، صحار، مسقط): تقریباً بدونِ تغییر.
• عبورِ کشتی‌ها از هرمز (IMF PortWatch، با فرستنده‌ی AIS): از حدودِ {fa(round(sh['then']))} به {fa(round(sh['now']))} در روز. کشتی‌های بی‌فرستنده شمرده نمی‌شوند.

این فقط اثرِ کشتی‌ها نیست: دی‌اکسیدِ نیتروژن روی بندرها و مراکزِ نفت و گاز هم کمتر شد و سهمِ هر کدام را از فضا نمی‌شود جدا کرد.

این کاهش بهبودِ پایدارِ هوا نیست: بعد از ۲۷ خرداد اختلاف با پارسال کمتر شد، هرچند نامنظم (در ۱ تا ۱۶ آبان هنوز {p(parts['j08']['inside'])} کمتر).

منابع و روش در کامنتِ اول؛ منبعِ شمارِ کشتی‌ها در کامنتِ دوم.

شما در جنوب، هوای این بهار را چطور دیدید؟

#خلیج_فارس #تنگه_هرمز #آلودگی_هوا #ماهواره #بندرعباس
"""
    com = f"""منابع و روش (۱ مارس ۲۰۲۶ = ۱۰ اسفندِ ۱۴۰۴؛ ۱۷ ژوئن = ۲۷ خرداد، روزِ تفاهم‌نامه):
۱) داده: ستونِ دی‌اکسیدِ نیتروژن در پایینِ جو، ماهواره‌ی Sentinel-5P (TROPOMI، ESA)، محصولِ OFFL با فیلترِ کیفیتِ توصیه‌شده (qa_value بالای ۰٫۷۵). نقشه: Blue Marble، ناسا. رنگ: مقیاسِ لگاریتمی از ۱ تا ۱۰ (×۱۰¹⁵ مولکول بر سانتی‌مترمربع).
۲) هر «جا» میانگینِ کادرِ ±۰٫۲ درجه (حدودِ ۴۰ کیلومتر) است. شش جای خلیجِ فارس: از {fa(f"{inside[THEN]:.1f}")} به {fa(f"{inside[NOW]:.1f}")}، {p(ch['inside'])} کمتر (بازه‌ی ۹۰٪ با بازنمونه‌گیریِ روزها: {p(rg['inside'][1])} تا {p(rg['inside'][0])}). سه جای دریای عمان: {p(ch['outside'])} بیشتر (از {p(rg['outside'][0])} کمتر تا {p(rg['outside'][1])} بیشتر).
۳) فصل: همه‌ی مقایسه‌ها میانِ همان روزهای دو سال است؛ ماه به ماه (اسفند تا خرداد) شش جا {months} کمتر بودند.
۴) پیش از ۱۰ اسفند (۱ ژانویه تا ۲۸ فوریه) هر دو گروه بیشتر از پارسال بودند: {p(b['inside'])} و {p(b['outside'])}. فاصله‌ی دو گروه از ۱۰ اسفند باز شد.
۵) سال‌های پیش: شش جا از ۲۰۲۳ به ۲۰۲۴، {p(normal[0]['inside'])} و از ۲۰۲۴ به ۲۰۲۵، {p(normal[1]['inside'])} بیشتر شدند؛ ۲۰۲۶ از میانگینِ سه سالِ پیش {p(m['three']['inside'])} کمتر است (۲۰۲۳ با نسخه‌ی ۲٫۴ و ۲٫۵ و ۲۰۲۴ با ۲٫۶ پردازش شده‌اند). نسبتِ شش جا به سه جای دریای عمان در آن سه سال {fa(f"{r3[0]:.1f}")} تا {fa(f"{r3[-1]:.1f}")} بود و در ۲۰۲۶: {fa(f"{ratio[NOW]:.1f}")}. عسلویه، رأس لفان، جبیل و کویت از هر سه سالِ پیش کمترند؛ دبی و بندرعباس فقط از پارسال.
۶) روی آبِ خلیجِ فارس {p(ch['seas']['gulf'])} کمتر (پیش از ۱۰ اسفند {p(b['seas']['gulf'])} کمتر).
۷) نسخه‌ی پردازش از ۲٫۸ به ۲٫۹٫۱ عوض شده است؛ به نوشته‌ی KNMI شاید ناپیوستگی دیده شود. پیکسلِ معتبر در ۲۰۲۶ کمتر بود ({p(rg['valid'][NOW])} در برابرِ {p(rg['valid'][THEN])}).
۸) کشتی‌ها: IMF PortWatch، عبورِ نفتکش‌ها و کشتی‌های باریِ دارای فرستنده‌ی AIS؛ ۱ مارس تا ۱۷ ژوئن: {fa(round(sh['then']))} عبور در روز در ۲۰۲۵ و {fa(f"{sh['now']:.1f}")} در ۲۰۲۶ (جزئیات: کامنتِ دوم). این کاهش فقط از کشتی‌ها نیست: در فهرستِ انتشارِ EDGAR کشتی‌ها حدودِ یک‌ششمِ NOx این منطقه را دارند، و به نوشته‌ی Windward تولیدِ گازِ رأس لفان از ۱۹ مارس متوقف شد.
۹) بعد از ۱۷ ژوئن، شش جا نسبت به پارسال: از {p(min(after_in))} کمتر تا {p(max(after_in))} بیشتر در بخش‌های مختلف؛ نسبت به سه جای دریای عمان {p(max(after))} تا {p(min(after))} پایین‌تر (در بازه‌ی اصلی: {p(rel_window)}). در بایگانی‌ای که از آن خوانده‌ایم مدارهای ۳ ژوئیه تا ۱۱ اوتِ ۲۰۲۵ نیست.
۱۰) تحلیلِ جداگانه‌ی شرکتِ Weathernews (۱ ماهِ مه ۲۰۲۶) روی همین ماهواره: مارسِ ۲۰۲۶ حدودِ {fa(O['weathernews'][0])} تا {fa(O['weathernews'][1])}٪ کمتر از مارسِ ۲۰۲۵.
۱۱) عمرِ این گاز: Beirle و همکاران ۲۰۱۱، doi:10.1126/science.1207824. مسیرِ تقریبیِ کشتی‌ها: EDGAR v8.1 برای ۲۰۲۲ (edgar.jrc.ec.europa.eu/dataset_ap81). کد: github.com/bijanf/daily-tmax-records (شاخه‌ی elnino-iran).
"""
    cl, wm, wy, kp, ll = O["clarksons"], O["windward_march"], O["windward_may"], O["kpler"], O["lloyds"]
    com2 = f"""شمارِ کشتی‌ها از کجاست؟
۱) عددِ ریل از IMF PortWatch است: پایگاهِ بازِ صندوقِ بین‌المللیِ پول، دانشگاهِ آکسفورد و دانشگاهِ صنعتیِ دلفت. هر نفتکش یا کشتیِ باری (کانتینری، فله‌بر، بارِ عمومی، رو-رو) که با فرستنده‌ی روشنِ AIS از مرزِ تنگه بگذرد یک عبور است. ۱ مارس تا ۱۷ ژوئنِ ۲۰۲۶: {n(tr['now'])} عبور در {fa(tr['days'])} روز ({fa(f"{sh['now']:.1f}")} در روز)؛ همان روزهای ۲۰۲۵: {n(tr['then'])} عبور ({fa(round(sh['then']))} در روز).
۲) شمارنده‌های دیگر افتی نزدیک به همین اندازه نشان می‌دهند:
• شرکتِ Clarksons Research، هفته‌ی منتهی به ۱۶ مارس: حدودِ {fa(cl[1])} عبور در روز در برابرِ حدودِ {fa(cl[0])} پیش از آن.
• شرکتِ Windward، تا ۲۰ مارس: از {fa(wm[0])} به {fa(f"{wm[1]:.1f}")} عبور در روز؛ در تصویرِ ماهواره هم کشتی‌های بزرگِ این آبراه {p(O['windward_sat'])} کمتر بودند.
• شرکتِ Windward، ماهِ مه: {fa(wy[0])} عبور که {p(wy[1])} آن بی‌فرستنده بود، یعنی حدودِ {fa(visible)} عبور با فرستنده؛ PortWatch برای همان ماه {fa(tr['may'])} عبور دارد.
• بررسیِ Cao و همکاران ۲۰۲۶ (doi:10.1016/j.xinn.2026.101367) با رادارِ ماهواره‌ی Sentinel-1، که به فرستنده نیاز ندارد: در تصویرهای هفته‌ی اولِ مارس حدودِ {p(O['cao'])} کشتیِ کمتر در تنگه دیده شد تا هفته‌ی پیش از آن.
۳) عددِ پایه در این منابع فرق دارد ({fa(round(sh['then']))} تا {fa(cl[0])} عبور در روز)؛ PortWatch فقط نفتکش و کشتیِ باری را می‌شمارد. اندازه‌ی افت نزدیک است.
۴) کشتی‌های بی‌فرستنده: با شمردنِ همه‌ی عبورهای Windward، ماهِ مه حدودِ {fa(round(may_all))} عبور در روز داشت؛ باز بیش از ۹۰٪ کمتر از پارسال.
۵) بعد از ۱۷ ژوئن شمارنده‌ها هم‌نظر نیستند. ۷ ژوئن تا ۷ ژوئیه: Kpler حدودِ {fa(kp[0])} و PortWatch حدودِ {fa(round(tr['kpler_days']))} عبور در روز. ۵ تا ۲۵ اکتبر: Lloyd's List حدودِ {fa(round(ll[0] / 7))} عبورِ کشتی‌های غیرِ مرتبط با ایران و PortWatch حدودِ {fa(round(tr['lloyds_days']))} عبور در روز. برای همین ریل فقط تا ۲۷ خرداد از شمارِ کشتی‌ها حرف می‌زند.
"""
    rep = f"""پیش‌نویسِ پاسخ به نظرهای احتمالی (هر کدام را با زبانِ خودتان کوتاه کنید)

۱) «این که خوب است، هوا پاک‌تر شده!»
این کاهش به کم شدنِ فعالیتِ کشتی‌رانی، بندرها و صنعت مربوط است و بهبودِ پایدارِ هوا نیست: دی‌اکسیدِ نیتروژن چند ساعت در هوا می‌ماند و بعد از ۲۷ خرداد اختلاف با پارسال کمتر شد.

۲) «از کجا معلوم که از کشتی‌هاست؟»
معلوم نیست، و ریل هم همین را می‌گوید: کشتی‌ها، بندرها و صنعتِ نفت و گاز با هم کم شدند و از فضا نمی‌شود سهمِ هر کدام را جدا کرد. چیزی که روشن است: شش جای خلیجِ فارس روی‌هم حدودِ {fa(5 * round(100 * abs(ch['inside']) / 5))}٪ کمتر از پارسال بودند و سه جای دریای عمان تقریباً تغییری نکردند.

۳) «چرا تنگه بسته شد؟ مقصر کیست؟»
این ریل فقط چیزی را نشان می‌دهد که ماهواره اندازه گرفته است و درباره‌ی دلیل‌های سیاسی حرفی نمی‌زند.

۴) «بندرعباس که هوایش فرقی نکرد.»
دی‌اکسیدِ نیتروژن با چشم دیده نمی‌شود. بندرعباس میانِ این شش جا از کمترین کاهش‌ها را داشت: {p(s['bandar'])} کمتر از پارسال، ولی نه کمتر از دو سالِ پیش از آن.

۵) «این داده‌ها از کجاست؟»
داده‌ی ماهواره‌ی Sentinel-5P آژانسِ فضاییِ اروپا رایگان است. روش، منابع و نشانیِ کد در کامنتِ اول آمده.

۶) «عددِ کشتی‌ها را از کجا آورده‌اید؟ {fa(round(sh['now']))} کشتی در روز؟»
از IMF PortWatch (صندوقِ بین‌المللیِ پول با دانشگاه‌های آکسفورد و دلفت) که عبورِ کشتی‌های دارای فرستنده را می‌شمارد: {fa(round(sh['then']))} عبور در روز پارسال و {fa(round(sh['now']))} عبور در روز امسال، در همان روزها. Clarksons و Windward هم در ماهِ مارس افتی بیش از ۹۰٪ دیده‌اند. جزئیات و نشانیِ منابع در کامنتِ دوم است.

۷) «فصل را حساب کرده‌اید؟ هوای زمستان و تابستان فرق دارد.»
بله. همه‌ی مقایسه‌ها میانِ همان روزهای تقویم است: ۱۰ اسفند تا ۲۷ خرداد در هر دو سال. ماه به ماه هم شش جای خلیجِ فارس {months} کمتر از همان ماهِ پارسال بودند، و {p(m['three']['inside'])} کمتر از میانگینِ همان روزها در سه سالِ پیش.

۸) «رنگ‌های نقشه یعنی چه؟»
هرچه رنگ تیره‌تر (از زردِ کم‌رنگ تا بنفش)، دی‌اکسیدِ نیتروژنِ بیشتری در ستونِ هوا بوده است. جایی که نقشه رنگ ندارد، مقدار کمتر از پایینِ مقیاس است.
"""
    return dict(caption=cap, first_comment=com, second_comment=com2, replies=rep)


def main() -> None:
    T = texts()
    social = onebit.OUT / "social"
    for k, v in T.items():
        (social / f"hormuz_fa_{k}_fa.txt").write_text(v, encoding="utf-8")
    c = T["caption"].rstrip("\n")
    print(f"caption: {len(c)} characters, {len(c.encode('utf-8'))} bytes (limit 2,100), {c.count('#')} hashtags")
    assert len(c.encode("utf-8")) <= 2100 and c.count("#") <= 5
    for k in ("first_comment", "second_comment"):
        x = T[k].rstrip("\n")
        print(f"{k}: {len(x)} characters (limit 2,200)")
        assert len(x) <= 2200, k


if __name__ == "__main__":
    main()
