"""THE NUMBERS OF «۲ درجه گرم‌تر؛ مگر چقدر است؟» (twodeg_fa), part 2 of the El Niño explainer: why 1.5-2 °C of global
warming is a lot, told from data.

- The Holocene: Kaufman et al. 2020, Sci Data 7:201 (doi:10.1038/s41597-020-0530-7), Temperature 12k multi-method
  global mean surface temperature, 100-year bins from 0 to 12,000 years BP (BP = before 1950), median and 5th/95th
  percentiles, anomalies against 1800-1900 CE; file temp12k_allmethods_percentiles.csv from NOAA NCEI Paleoclimatology.
  Over the last 10,000 years the median stays within 0.54 °C (from -0.03 to +0.51 against 1850-1900 as joined below;
  0.0 to +0.54 against its own 1800-1900); 12,000 years ago it was still about 1 °C colder (the end of the ice age):
  the reel says «۱۰ هزار سال», not 12.
- The instrument era: HadCRUT 5.2.0.0 analysis, global annual mean (Met Office Hadley Centre and CRU), against
  1850-1900 (the file's 1961-1990 anomalies minus their 1850-1900 mean). 2024 +1.55 °C (WMO's consolidated value is
  1.55 +- 0.13 °C), 2025 +1.43, 2016-2025 mean +1.29. The Holocene reference (1800-1900) and the instrument reference
  (1850-1900) are treated as the same pre-industrial level (the reel says «پیش از صنعتی شدن»).
- Extremes: IPCC AR6 WG1 SPM Figure SPM.6 (doi:10.1017/9781009157896.001), global land: a hot extreme that came once
  in 50 years in 1850-1900 comes 4.8 times in 50 years at +1 °C, 8.6 at +1.5 °C, 13.9 at +2 °C (likely ranges
  2.3-6.4, 4.3-10.7, 6.9-16.6); a 10-year heavy one-day rain comes 1.3, 1.5, 1.7 times and is 6.7, 10.5, 14.0 % wetter.

    python -I src/twodeg.py      fetches what is missing, computes, asserts, writes data/twodeg/numbers.json
"""

from __future__ import annotations

import csv
import json
import sys
import urllib.request
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import onebit  # noqa: E402

DATA = onebit.ROOT / "data" / "twodeg"
TEMP12K_URL = ("https://www.ncei.noaa.gov/pub/data/paleo/reconstructions/kaufman2020/"
               "temp12k_allmethods_percentiles.csv")
HADCRUT_URL = ("https://www.metoffice.gov.uk/hadobs/hadcrut5/data/HadCRUT.5.2.0.0/analysis/diagnostics/"
               "HadCRUT.5.2.0.0.analysis.summary_series.global.annual.csv")
# IPCC AR6 WG1 SPM Figure SPM.6 (global land): times a 1850-1900 50-year hot extreme now comes in 50 years
SPM6_HEAT50 = {1.0: 4.8, 1.5: 8.6, 2.0: 13.9, 4.0: 39.2}
SPM6_HEAT50_RANGE = {1.0: (2.3, 6.4), 1.5: (4.3, 10.7), 2.0: (6.9, 16.6), 4.0: (27.0, 41.4)}
SPM6_RAIN10 = {1.0: (1.3, 6.7), 1.5: (1.5, 10.5), 2.0: (1.7, 14.0), 4.0: (2.7, 30.2)}   # (times, % wetter)
EXPECT = dict(holo_span=0.54, y2024=1.55, y2025=1.43, mean_2016_2025=1.29)


def fetch(url: str, name: str) -> Path:
    path = DATA / name
    if not path.exists():
        DATA.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=300) as r:
            path.write_bytes(r.read())
    return path


def instrumental() -> dict:
    """HadCRUT5 annual global mean against 1850-1900: {year: anomaly}, full years only (the running year left out)."""
    rows = list(csv.reader(fetch(HADCRUT_URL, "hadcrut5_global_annual.csv").open()))
    head = [h.strip() for h in rows[0]]
    t = head.index("Time")
    a = head.index("Anomaly (deg C)")
    vals = {int(r[t]): float(r[a]) for r in rows[1:] if r and r[t].strip()}
    base = float(np.mean([vals[y] for y in range(1850, 1901)]))
    out = {y: v - base for y, v in vals.items()}
    last = max(out)
    if last >= 2026:                                   # the running year is a partial mean: not on screen
        out.pop(last)
    return out


def holocene() -> dict:
    """Temp12k global median and 5th/95th percentiles by age (years BP), against 1800-1900 (the file's own)."""
    rows = list(csv.reader(fetch(TEMP12K_URL, "temp12k_allmethods_percentiles.csv").open()))
    head = [h.strip() for h in rows[0]]
    d = np.array([[float(x) for x in r] for r in rows[1:] if r])
    return dict(age=d[:, 0], med=d[:, head.index("global_median")], p5=d[:, head.index("global_5")],
                p95=d[:, head.index("global_95")])


def numbers() -> dict:
    h = holocene()
    age, med = h["age"], h["med"]
    assert len(age) == 121 and age[0] == 0 and age[-1] == 12000
    k10 = age <= 10000
    span = round(float(med[k10].max() - med[k10].min()), 2)
    assert span == EXPECT["holo_span"], span
    warm_age = int(age[k10][np.argmax(med[k10])])
    inst = instrumental()
    y24, y25 = round(inst[2024], 2), round(inst[2025], 2)
    m10 = round(float(np.mean([inst[y] for y in range(2016, 2026)])), 2)
    assert (y24, y25, m10) == (EXPECT["y2024"], EXPECT["y2025"], EXPECT["mean_2016_2025"]), (y24, y25, m10)
    first_above = min(y for y, v in inst.items() if v > 1.5)
    assert first_above == 2024, first_above
    return dict(
        holocene=dict(source=TEMP12K_URL, base="1800-1900", age=age.tolist(), median=med.round(3).tolist(),
                      p5=h["p5"].round(3).tolist(), p95=h["p95"].round(3).tolist(), span_10ka=span,
                      max_10ka=round(float(med[k10].max()), 2), max_age=warm_age,
                      min_10ka=round(float(med[k10].min()), 2), at_12ka=round(float(med[-1]), 2),
                      at_11700=round(float(med[age == 11700][0]), 2)),
        instrumental=dict(source=HADCRUT_URL, base="1850-1900", years=sorted(inst),
                          values=[round(inst[y], 3) for y in sorted(inst)], y2024=y24, y2025=y25,
                          mean_2016_2025=m10, first_year_above_1p5=first_above),
        spm6=dict(heat50=SPM6_HEAT50, heat50_range=SPM6_HEAT50_RANGE, rain10=SPM6_RAIN10,
                  source="IPCC AR6 WG1 SPM, Figure SPM.6, doi:10.1017/9781009157896.001"),
    )


def main() -> None:
    nums = numbers()
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "numbers.json").write_text(json.dumps(nums, ensure_ascii=False, indent=1), encoding="utf-8")
    show = {k: {kk: vv for kk, vv in v.items() if kk not in ("age", "median", "p5", "p95", "years", "values")}
            for k, v in nums.items()}
    print(json.dumps(show, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
