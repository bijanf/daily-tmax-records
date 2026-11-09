"""THE NUMBERS OF «با این باران‌ها، سدهای تهران پر شدند؟» (damsexplain_fa): a primary-school-level answer to the
question dozens of viewers asked under the five-dam reel (106,677 views) after the storm of 14-17 Aban 1405
(5-8 Nov 2026). Official figures are "reported" (press quoting the agency), with the date they refer to; the
arithmetic is ours and says so on screen.

Sources (opened 9 Nov 2026; copies in the job's research_dams folder):
- STORAGE NOW: Behnam Bakhshi, spokesman of Tehran Province Water and Wastewater Co. (Abfa), on TV, 18 Aban 1405
  (9 Nov 2026): about 350 million m3 in the five dams, «کمتر از ۲۰ درصد» of their capacity; «اگرچه بارش‌های اخیر در
  ارتفاعات به شکل برف بوده و هنوز ذوب نشده است، اما مجموع ذخایر آبی سد‌های تهران همچنان حدود ۳۵۰ میلیون مترمکعب است»
  (IRIB News 5961620). Tehran needs 800-850 million m3 to be comfortable (Bakhshi via Hamshahri 1083787, 16 Aban).
- 1 AБAN TABLE: Tehran Regional Water Co. via Mehr 6989418 (4 Aban 1405): total 359, long-term average 548.
- CAPACITIES: Mehr 6981337 (26 Mehr 1405): Amir Kabir ~205, Latyan ~95, Lar ~960, Mamlu ~250, Taleqan ~420 (sum 1,930).
- PRECEDENT: Mehr 6677166 (12 Azar 1404): a 1-2 day rain raised the dams' inflow by only about 1.5 million m3.
- SNOW: more than 1 m of snow at Tochal station 7 (Tabnak 4200639, 17 Aban 1405).
- KARAJ INFLOW BY MONTH: Mohammadi, Eslami & Dayyani Dardashti 2005, J. Agric. Sci. Technol. 7:17-30, Fig. 2
  (1970-1999 means, digitized to about +-1 million m3); "about 60 % in April-June" is the paper's own statement.
  Catchment 764 km2 (Tehran Regional Water, thrw.ir/st/61).
- ONE RAIN ON THE KARAJ CATCHMENT (our arithmetic): 20 mm x 764 km2 = 15.3 million m3 falls; in autumn about 1 drop in
  10 reaches the dam within weeks (our estimate from the official monthly means: Karaj 7-13 %, Taleqan about 10 % from
  JICA, The study on water management in the western area of the Capital Tehran, final report, Nov 2001).
- TEHRAN'S DRAW: about 3 million m3 a day, 65 % from surface water (Bakhshi via Mehr 7000495) = about 2 a day from dams.
- GAP, LIKE FOR LIKE: on 1 Aban 1405 the five dams held 359 against a long-term average of 548 for that day: 189 short
  (Mehr 6989418); the average keeps falling through autumn (509 reported for early Azar), so after the storm the gap
  is about the same (~183, our estimate). On screen: «حدودِ ۱۹۰», 190 squares of 1 million m3 = about 63 days of the
  city's 3 million m3 a day.
- URMIA RAIN: about 30 mm on the basin in Aban to 18 Aban (57 mm since 1 Mehr, West Azerbaijan Regional Water via Mehr
  7005028, minus 26.7 mm to 1 Aban, Mehr 6987913; our subtraction); basin stations 25-67 mm in 72 h.
- LAKE URMIA: 1270.59 m, 1,971 km2, 2.55 billion m3 on 30 Mehr 1405 (West Azerbaijan Regional Water via Mehr 6988836),
  the same level and area on 13 Aban, before the storm, the newest reading on 9 Nov (DoE West Azerbaijan, Mehr 7001578);
  ecological level 1274.10 m, 14.58 billion m3 (DoE, Mehr 4494254); 15.5 billion m3 "needed" (Mehr 6988836). Basin
  51,876 km2 (Eimanifar & Mohebbi 2007, doi:10.1186/1746-1448-3-5). 30 mm: direct on the lake 0.059 billion m3 = 3 cm;
  from the basin at 1.6-15 % (river inflow over precipitation, about 8 % a year now and 15 % in 1995-2017, Schulz et
  al. 2020 doi:10.1038/s41598-019-57150-y; an autumn storm on dry soil behind ~41 reservoirs delivers less) at most
  0.233 billion m3 = 11.8 cm at today's area: at most about 15 cm in all.
- EXPERT: Kaveh Madani, UNU-INWEH director, 2026 Stockholm Water Prize (UNU-INWEH, KVA, 18 Mar 2026), to Al Jazeera,
  12 Nov 2025: "But I think with the first rain or flood, people could forget about the situation."

    python -I src/damsexplain.py     computes, asserts, writes data/damsexplain/numbers.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import onebit  # noqa: E402

DATA = onebit.ROOT / "data" / "damsexplain"
NOW_MCM, NOW_DATE = 350.0, "18 Aban 1405"
AVG_1ABAN, NOW_1ABAN = 548.0, 359.0
COMFORT = (800.0, 850.0)
CAPACITY = dict(amirkabir=205.0, latyan=95.0, lar=960.0, mamlu=250.0, taleqan=420.0)
PRECEDENT_MCM = 1.5
KARAJ_KM2 = 764.0
KARAJ_MONTH = dict(Jan=12.7, Feb=14.1, Mar=27.2, Apr=74.7, May=103.6, Jun=79.7, Jul=44.1, Aug=21.1, Sep=13.2,
                   Oct=12.3, Nov=15.8, Dec=14.9)
QUICK = (0.07, 0.13)                                   # autumn quick-response share at Karaj (our estimate)
RAIN_MM = 20.0                                         # mm: the Karaj example (log only)
URMIA_RAIN_MM = 57.0 - 26.7                            # mm: Aban rain on the Urmia basin to 18 Aban, about 30 (reported:
                                                       # 57 since 1 Mehr, Mehr 7005028; 26.7 to 1 Aban, Mehr 6987913)
TEHRAN_DAY = 3.0                                       # million m3 a day, all of Tehran's water (Bakhshi via Mehr 7000495)
TEHRAN_DRAW = TEHRAN_DAY * 0.65                        # million m3 a day from the dams (65 % surface water)
URMIA = dict(level=1270.59, area_km2=1971.0, volume_bcm=2.55, target_level=1274.10, target_bcm=14.58,
             needed_bcm=15.5, basin_km2=51876.0, basin_share=(0.016, 0.15))


def numbers() -> dict:
    cap = sum(CAPACITY.values())
    assert round(cap) == 1930
    fill = NOW_MCM / cap
    assert 0.17 < fill < 0.20, fill                     # "less than 20 %" as the spokesman said
    gap = AVG_1ABAN - NOW_MCM                           # mixes two dates (log only)
    gap_1aban = AVG_1ABAN - NOW_1ABAN                   # like for like: both on 1 Aban, the operator's table
    assert gap_1aban == 189
    total = sum(KARAJ_MONTH.values())
    seasons = dict(autumn=("Oct", "Nov", "Dec"), winter=("Jan", "Feb", "Mar"), spring=("Apr", "May", "Jun"),
                   summer=("Jul", "Aug", "Sep"))
    share = {k: sum(KARAJ_MONTH[m] for m in v) / total for k, v in seasons.items()}
    assert abs(share["spring"] - 0.60) < 0.01, share     # the paper: about 60 % in April-June
    falls = RAIN_MM / 1000 * KARAJ_KM2 * 1e6 / 1e6      # million m3
    quick = tuple(round(falls * q, 1) for q in QUICK)
    assert abs(falls - 15.3) < 0.05 and quick == (1.1, 2.0)
    u = URMIA
    gap_bcm = (u["target_bcm"] - u["volume_bcm"], u["needed_bcm"] - u["volume_bcm"])
    rain = round(URMIA_RAIN_MM)
    assert rain == 30
    direct = rain / 1000 * u["area_km2"] * 1e6 / 1e9
    basin = tuple(rain / 1000 * u["basin_km2"] * 1e6 / 1e9 * s for s in u["basin_share"])
    pct = (100 * (direct + basin[0]) / gap_bcm[1], 100 * (direct + basin[1]) / gap_bcm[0])
    assert pct[1] < 3.0, pct                            # under 3 % of its deficit even at the upper end
    depth = u["target_level"] - u["level"]
    direct_cm = 100 * direct * 1e9 / (u["area_km2"] * 1e6)          # rain on the lake raises it by its own depth
    max_cm = 100 * (direct + basin[1]) * 1e9 / (u["area_km2"] * 1e6)  # plus the rivers at the high share, at today's area
    assert round(direct_cm) == 3 and max_cm < 15.0, (direct_cm, max_cm)   # «حداکثر حدودِ ۱۵ سانتی‌متر»
    gap_days = gap_1aban / TEHRAN_DAY
    assert 60 <= gap_days <= 70 and 24 / TEHRAN_DAY == 8.0, gap_days      # «about two months»; one cube = 8 hours
    return dict(
        capacity=cap, now=NOW_MCM, now_date=NOW_DATE, fill_pct=round(100 * fill, 1), avg_1aban=AVG_1ABAN,
        gap_to_avg=round(gap), gap_1aban=gap_1aban, now_1aban=NOW_1ABAN, comfort=COMFORT, precedent=PRECEDENT_MCM,
        karaj_month=KARAJ_MONTH, karaj_total=round(total, 1),
        season_pct={k: round(100 * v) for k, v in share.items()},
        karaj_rain=dict(mm=RAIN_MM, km2=KARAJ_KM2, falls=round(falls, 1), quick=quick),
        tehran_draw=round(TEHRAN_DRAW, 2), tehran_day=TEHRAN_DAY, hours_per_mcm=24 / TEHRAN_DAY,
        gap_days=round(gap_days),
        urmia=dict(**u, rain_mm=rain, gap_bcm=[round(x, 2) for x in gap_bcm], depth_m=round(depth, 2),
                   direct_bcm=round(direct, 3), basin_bcm=[round(x, 3) for x in basin],
                   pct_of_gap=[round(x, 2) for x in pct], direct_cm=round(direct_cm, 1), max_cm=round(max_cm, 1)),
    )


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    n = numbers()
    (DATA / "numbers.json").write_text(json.dumps(n, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(n, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
