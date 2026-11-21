"""The texts that go with the Köppen reel (koppen_fa): the caption, the first comment (sources, method, the credits
the licences ask for) and reply drafts. Every number is taken from the film's own file (outputs/onebit/koppen/film.json,
which src/koppen.py writes); what the sentences take for granted is asserted. Limits: the caption at most 2,100 UTF-8
bytes and five hashtags, the comment at most 2,200 characters.

Read in the sources on 21 November 2026: the paper (Beck et al. 2023, Scientific Data 10, 724): the future maps add each
model's monthly change to the 1991-2020 climatology (the delta method) and take, cell by cell, the most common class
among the models of the "Model Subset" (42 of 67 CMIP6 models; 29 of them for SSP1-2.6, SSP2-4.5 and SSP5-8.5); the
maps' page (gloh2o.org/koppen) links its "latest version (V3)" to figshare file 61012822, the file the film uses, under
CC BY 4.0. The Copernicus DEM's notice is the one of its licence; NASA's Blue Marble comes from NASA GIBS.

    python -I src/koppen_texts.py     # outputs/onebit/social/koppen_fa_caption_fa.txt, _first_comment_fa.txt, _replies_fa.txt
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import koppen as K  # noqa: E402
import onebit  # noqa: E402
from onebit import fa  # noqa: E402

COPERNICUS = ("© DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the "
              "European Union and ESA; all rights reserved")
MODELS = dict(subset=42, all=67, ssp=29)                    # the paper's model counts (see the docstring)


def texts() -> dict:
    F = json.loads((K.BUILD / "film.json").read_text(encoding="utf-8"))
    N, W = F["numbers"], F["words"]
    M = N["maps"]
    h = K.half_up
    p = lambda v: f"{fa(h(v))}٪"                                                          # noqa: E731
    y = lambda g: fa(K.fa_year(g))                                                       # noqa: E731
    now, later = M[K.NOW], M[K.LATER]
    low, high = M[K.RANGE[0]], M[K.RANGE[2]]
    TC, E5, CF = N["tehran_city"], N["era5"], N["confident"]
    # what the sentences take for granted
    assert (h(now["hot_dry"]), h(later["hot_dry"]), h(low["hot_dry"]), h(high["hot_dry"])) == (52, 63, 58, 72)
    assert (h(now["freezing"]), h(later["freezing"])) == (13, 8)
    assert (h(now["desert"]), h(later["desert"]), h(high["desert"])) == (51, 53, 56)       # «کلِ بیابان … تقریباً ثابت؛ با انتشارِ زیاد ۵۶٪»
    G0, G1 = now["groups"], later["groups"]
    assert (h(G0["bwh"]), h(G1["bwh"]), h(G0["bwk"]), h(G1["bwk"])) == (43, 52, 8, 2), (G0, G1)          # hot desert up, cold desert down
    assert N["freezing_high"] > 90                                                        # «تقریباً همه در کوهستان»
    assert (h(TC[K.NOW]["BSk"]), h(TC[K.LATER]["BSh"]), h(TC[K.RANGE[0]]["BSh"]), h(TC[K.RANGE[2]]["BSh"])) == (66, 53, 34, 69)
    assert (h(CF[K.NOW]), h(CF[K.LATER])) == (53, 65)
    assert (h(E5["1961_1990"]["era5"]), h(E5[K.NOW]["era5"]), h(E5["1961_1990"]["maps"]), h(E5[K.NOW]["maps"])) == (44, 49, 46, 52)
    assert h(M["1961_1990"]["changed"]) == 15
    assert all(N["cities"][c][t]["cls"][0] == "C" for c in ("رشت", "ساری") for t in (K.NOW, *K.RANGE)), N["cities"]   # «ساحلِ خزر معتدل می‌ماند»
    assert W["hook"].count(p(now["hot_dry"])) == 1 and W["hook"].count(p(later["hot_dry"])) == 1
    now_span, later_span = f"{y(1991)} تا {y(2020)}", f"{y(2071)} تا {y(2099)}"

    caption = f"""اقلیمِ ایران: مناطقِ خشکِ گرم از {p(now['hot_dry'])} امروز ({now_span}) به {p(later['hot_dry'])} در آینده‌ی دور ({later_span}، با انتشارِ میانه)

نقشه‌های ۱ کیلومتریِ اقلیمِ کوپن (Beck و همکاران، ۲۰۲۳) را برای ایران شمردیم. «گرم» در این طبقه‌بندی یعنی میانگینِ دمای سال ۱۸ درجه یا بیشتر.
• امروز، {now_span}: {p(now['hot_dry'])} از ایران خشک و گرم است.
• آینده‌ی دور، {later_span}، با انتشارِ میانه: {p(later['hot_dry'])} (با انتشارِ کم {p(low['hot_dry'])}، با انتشارِ زیاد {p(high['hot_dry'])}).
• مناطقِ زمستانِ یخ‌بندان (میانگینِ سردترین ماه صفر یا کمتر): از {p(now['freezing'])} به {p(later['freezing'])} از ایران؛ تقریباً همه در کوهستان‌ها.
• بیشترِ شهرِ تهران امروز نیمه‌خشکِ سرد است و با انتشارِ میانه به نیمه‌خشکِ گرم می‌رسد ({p(TC[K.LATER]['BSh'])} از شهر؛ با انتشارِ کم {p(TC[K.RANGE[0]]['BSh'])}).

کلِ بیابان (گرم و سرد) با انتشارِ میانه تقریباً ثابت می‌ماند (از {p(now['desert'])} به {p(later['desert'])}؛ با انتشارِ زیاد {p(high['desert'])})، اما بیابانِ گرم از {p(G0['bwh'])} به {p(G1['bwh'])} می‌رسد و بیابانِ سرد از {p(G0['bwk'])} به {p(G1['bwk'])} کم می‌شود. آنچه بیشتر تغییر می‌کند، گرماست.

این‌ها تیپ‌های اقلیمی‌اند، نه تصویرِ زمین؛ گیاه و کشاورزی با تأخیر تغییر می‌کنند. آینده برآوردِ مدل‌های اقلیمی است.

منابع، روش و حقِ نشرِ تصویرها در کامنتِ اول.

شهرِ شما امروز چه رنگی است؟ و در آینده‌ی دور؟

#اقلیم #ایران #تغییر_اقلیم #گرمایش_جهانی #تهران
"""

    comment = f"""منابع و روش:
۱) داده: Beck و همکاران (۲۰۲۳)، نقشه‌های ۱ کیلومتریِ اقلیمِ کوپن-گایگر، Scientific Data ۱۰، ۷۲۴، doi:10.1038/s41597-023-02549-6؛ آخرین نسخه‌ی داده‌ها از figshare، مجوزِ CC BY 4.0. گروه‌بندی، شمارش و نقشه‌ها از ماست.
۲) «خشکِ گرم» = بیابانی و نیمه‌خشک با میانگینِ سالانه‌ی ۱۸ درجه یا بیشتر (BWh و BSh). «زمستانِ یخ‌بندان» = همه‌ی رده‌های D (میانگینِ سردترین ماه صفر یا کمتر).
۳) امروز = ۱۹۹۱ تا ۲۰۲۰ ({now_span})، از داده‌های رصدی. آینده‌ی دور = ۲۰۷۱ تا ۲۰۹۹ ({later_span}): اقلیمِ امروز به‌اضافه‌ی تغییرِ ماهانه‌ی هر مدل؛ رده‌ی هر نقطه، رایج‌ترین رده در میانِ {fa(MODELS['ssp'])} مدلِ اقلیمیِ CMIP6 است. انتشارِ کم، میانه و زیاد = SSP1-2.6، SSP2-4.5 و SSP5-8.5.
۴) سهم‌ها از مساحتِ ایران‌اند. اگر فقط نقطه‌هایی را بشماریم که بیشترِ مجموعه بر سرِ رده‌شان هم‌نظرند، {p(CF[K.NOW])} و {p(CF[K.LATER])} می‌شود.
۵) تهران، در جعبه‌ای دورِ شهر: امروز {p(TC[K.NOW]['BSk'])} نیمه‌خشکِ سرد؛ در آینده‌ی دور {p(TC[K.LATER]['BSh'])} نیمه‌خشکِ گرم (با انتشارِ کم {p(TC[K.RANGE[0]]['BSh'])}، با انتشارِ زیاد {p(TC[K.RANGE[2]]['BSh'])}).
۶) آزمونِ مستقل با دمای ERA5-Land: سهمِ خشکیِ بالای ۱۸ درجه {p(E5['1961_1990']['era5'])} (۱۹۶۱ تا ۱۹۹۰) و {p(E5[K.NOW]['era5'])} (۱۹۹۱ تا ۲۰۲۰)؛ نقشه‌ها {p(E5['1961_1990']['maps'])} و {p(E5[K.NOW]['maps'])}. جهت یکی است.
۷) به گفته‌ی خودِ مقاله، در کوهستان‌ها و کرانه‌ها نقشه‌های آینده را باید با احتیاطِ بیشتر خواند؛ در کوهستان شاید تغییر را کمتر از واقع نشان دهند.
۸) «چقدر از ایران رده عوض می‌کند» را نشان نداده‌ایم: دو نقشه‌ی رصدیِ ۱۹۶۱ تا ۱۹۹۰ و ۱۹۹۱ تا ۲۰۲۰ هم در {p(M['1961_1990']['changed'])} از ایران با هم فرق دارند، بیشترش در مرزِ رده‌ها.
۹) پستی‌وبلندی: Copernicus DEM؛ {COPERNICUS}.
۱۰) تصویرِ زمینه: NASA Blue Marble (Shaded Relief and Bathymetry)، از NASA GIBS.
"""

    replies = f"""پاسخ‌های آماده (برای کامنت‌ها):

«یعنی ایران بیابان می‌شود؟»
تا حدی. کلِ بیابان (گرم و سرد) با انتشارِ میانه تقریباً ثابت است ({p(now['desert'])} به {p(later['desert'])})؛ با انتشارِ زیاد به {p(high['desert'])} می‌رسد. بیابانِ گرم بیشتر می‌شود (از {p(G0['bwh'])} به {p(G1['bwh'])}) و بیابانِ سرد کم می‌شود. آنچه بیشتر تغییر می‌کند گرماست: خشکی‌های خنک گرم‌تر می‌شوند و زمستان‌های یخ‌بندان کم می‌شوند.

«این پیش‌بینیِ قطعی است؟»
نه؛ برآوردِ مدل‌های اقلیمی برای سه سناریوی انتشار است. هرچه انتشار کمتر، تغییر کمتر: {p(low['hot_dry'])} با انتشارِ کم، {p(high['hot_dry'])} با انتشارِ زیاد.

«۱۸ درجه که گرم نیست!»
۱۸ درجه میانگینِ کلِ سال است، شب و زمستان هم حساب است. تهران امروز زیرِ این خط است و با انتشارِ میانه در آینده‌ی دور بالای آن می‌رود.

«پس شمال و کوهستان؟»
زمستانِ یخ‌بندان تقریباً فقط در کوهستان‌هاست و با انتشارِ میانه از {p(now['freezing'])} به {p(later['freezing'])} از ایران می‌رسد. ساحلِ خزر، مثلِ رشت و ساری، معتدل می‌ماند.

«شهرِ من؟»
اسمِ شهرتان را بنویسید؛ رده‌ی اقلیمی‌اش را از داده‌ی ۱ کیلومتریِ همین مطالعه برایتان می‌گوییم. نزدیکِ مرزِ رده‌ها، پاسخ قطعی نیست.
"""
    return dict(caption=caption, first_comment=comment, replies=replies)


def main() -> None:
    social = onebit.OUT / "social"
    T = texts()
    for k, v in T.items():
        (social / f"koppen_fa_{k}_fa.txt").write_text(v, encoding="utf-8")
    c = T["caption"]
    print(f"caption: {len(c)} characters, {len(c.encode('utf-8'))} bytes (limit 2,100), {c.count('#')} hashtags")
    assert len(c.encode("utf-8")) <= 2100 and c.count("#") <= 5
    print(f"first comment: {len(T['first_comment'])} characters (limit 2,200)")
    assert len(T["first_comment"]) <= 2200
    for banned in ("رکورد", "خشک شد", "مُرد", "مقصر", "فاجعه", "میانگینِ مدل"):
        assert not any(banned in v for v in T.values()), banned
    print("\n" + c + "\n" + T["first_comment"])


if __name__ == "__main__":
    main()
