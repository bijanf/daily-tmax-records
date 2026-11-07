"""EL NIÑO 2026 AND IRAN'S RAIN: the numbers and the clock of the reel «النینوی بسیار قوی آمده؛ یعنی طوفانِ نوح؟».

- This year's El Niño: NOAA CPC's Oceanic Niño Index (ONI, ERSSTv5, 3-month mean Niño-3.4 sea-surface temperature
  anomaly); its latest value (ASO 2026) and its rank among all ASO values since 1950 (data/enso/oni.ascii.txt).
- The picture of the Pacific: NOAA OISST v2.1 daily anomaly (0.25°, vs 1991-2020), the mean of 16-22 Oct 2026
  (CoastWatch ERDDAP, data/enso_rain/oisst_anom_20261022.nc); illustration only, no number is read from it.
- Iran's rain: src/enso.py (CRU TS 4.10, 621 cells inside Iran, 1951-2024): El Niño seasons by NOAA's +0.5 °C ONI
  of the same 3-month season; "wetter" = above that season's 1951-2024 median. Autumn = October-December (OND),
  winter = January-March (JFM); strong = ONI >= 1.5.

The clock: 30 s at 30 frames a second; frame 0 = the end state (the warm Pacific, the hook); the ONI lands at
6.0 s; the globe turns to Iran (8.5-12.5 s); the autumns at 12.5 s, the strong ones at 16.0 s, the winters at
19.5 s, the verdict at 23.0 s, the question at 26.5 s; the globe returns to the Pacific by 30 s (a loop).

    python -I src/elnino26.py > outputs/elnino26_log.txt
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import enso  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "elnino26"
DURATION, FPS = 30.0, 30
LAND, TURN, AUTUMN, STRONG, WINTER, VERDICT, QUESTION = 6.0, (8.5, 12.5), 12.5, 16.0, 19.5, 23.0, 26.5
STRONG_AT = 1.5
EXPECT = dict(oni_now=(2.3, 2.7), autumn=(21, 26), winter=(11, 22), strong_autumn=(4, 6))


def main() -> None:
    o = enso.oni("oni")
    last = o.iloc[-1]
    assert (last.season, int(last.year)) == ("ASO", 2026), (last.season, last.year)
    aso = o.query("season == 'ASO'").sort_values("oni", ascending=False)
    rank = int((aso.oni > last.oni).sum()) + 1
    print(f"ONI {last.season} {last.year}: {last.oni:+.2f} °C, rank {rank} of {len(aso)} ASO values since 1950; "
          f"next: " + ", ".join(f"{int(r.year)} {r.oni:+.2f}" for r in aso.iloc[1:4].itertuples()))
    au, wi = enso.result("OND"), enso.result("JFM")
    strong = [y for y in au["years"] if au["oni"][y] >= STRONG_AT]
    s_wet = [y for y in strong if au["wetter"][y]]
    w_strong = [y for y in wi["years"] if wi["oni"][y] >= STRONG_AT]
    print(f"autumn (OND) 1951-2024: {au['n_wetter']} of {len(au['years'])} El Niño autumns wetter than the median "
          f"({au['median']:.1f} mm); El Niño {au['pct']['El Niño']:+.1f} % vs neutral {au['pct']['neutral']:+.1f} %, "
          f"p {au['p']:.3f}")
    print(f"  strong (ONI >= {STRONG_AT}): {len(s_wet)} of {len(strong)}: " +
          ", ".join(f"{y} ({au['oni'][y]:+.1f}, {au['rain'][y]:.0f} mm, {'wetter' if au['wetter'][y] else 'drier'})" for y in strong))
    print(f"winter (JFM) 1951-2024: {wi['n_wetter']} of {len(wi['years'])} El Niño winters wetter; strong "
          f"{sum(wi['wetter'][y] for y in w_strong)} of {len(w_strong)}")
    v = dict(oni_now=float(last.oni), autumn=au["n_wetter"], winter=wi["n_wetter"], strong_autumn=len(s_wet))
    for k, (a, b) in EXPECT.items():
        assert a <= v[k] <= b, (k, v[k])
    assert rank == 1 and len(au["years"]) == 26 and len(wi["years"]) == 22 and len(strong) == 6
    assert not au["wetter"][2023], "autumn 2023 (1402) was drier: the reel says so"
    tl = dict(duration=DURATION, fps=FPS, land=LAND, turn=list(TURN), autumn_at=AUTUMN, strong_at=STRONG,
              winter_at=WINTER, verdict_at=VERDICT, question_at=QUESTION, oni_now=round(float(last.oni), 2),
              oni_shown=round(float(last.oni), 1), oni_rank=rank, oni_season="ASO 2026",
              autumn=dict(n=len(au["years"]), wetter=au["n_wetter"], years=au["years"],
                          wet={str(y): au["wetter"][y] for y in au["years"]}, strong=strong, strong_wetter=len(s_wet)),
              winter=dict(n=len(wi["years"]), wetter=wi["n_wetter"], years=wi["years"],
                          wet={str(y): wi["wetter"][y] for y in wi["years"]}),
              pct_autumn_en=au["pct"]["El Niño"], pct_autumn_neutral=au["pct"]["neutral"], p_autumn=au["p"])
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "timeline.json").write_text(json.dumps(tl, indent=1))
    print("saved", DATA / "timeline.json")


if __name__ == "__main__":
    main()
