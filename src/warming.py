"""WHO HEATED THE PLANET: each country's share of the warming its emissions have caused so far.

One index for three gases: the change in global mean surface temperature caused by each
country's emissions of carbon dioxide, methane and nitrous oxide since 1850, from Jones et al.,
"National contributions to climate change due to historical emissions of carbon dioxide,
methane, and nitrous oxide since 1850", Scientific Data 10, 155 (2023),
doi:10.1038/s41597-023-02041-1, updated yearly; release 2025.1 (13 November 2025, 1851-2024),
doi:10.5281/zenodo.16640595. The file holds, for every country and year, the warming in that
year due to its emissions up to then (°C), split into "Fossil" (fossil fuels, cement and other
industry, waste) and "LULUCF" (land use, land-use change and forestry, which there includes
agriculture's methane and nitrous oxide).

The film uses "Fossil", the warming from fossil fuels and industry since the industrial
revolution: the UK leads until 1900, the USA from 1901, China is second since 1997. With "Total"
(fossil and land use) the USA leads every year from 1851, Brazil enters the top 10 (from 1917)
and Indonesia stays in it; the USA's share of 2024 is then 17.7 % instead of 21.7 %. A share is
the country's warming over the world's ("GLOBAL", which in this file is exactly the sum of the
countries: no separate row for international shipping and aviation). Countries in today's
borders: the Soviet Union's emissions are split among its successor states. The early years
rest on tiny amounts of warming (0.3 thousandths of a degree in 1851) and the file holds a few
negative contributions, so the film's first board is 1860. Only CO2, CH4 and N2O: no aerosols.

    python -I src/warming.py                  # the ranking, step by step
    python -I src/warming.py --component Total
"""

from __future__ import annotations

import argparse
import functools
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "data" / "warming" / "GMST_response_1851-2024.csv"
URL = "https://zenodo.org/api/records/16640595/files/GMST_response_1851-2024.csv/content"
GROUPS = {"ANNEXI", "ANNEXII", "BASIC", "EIT", "EU27", "GLOBAL", "LDC", "LMDC", "NONANNEX", "OECD"}
TOP = 10
NAMES = {"en": {"United Kingdom": "UK", "USA": "USA", "Czechia": "Czechia", "Netherlands": "Netherlands",
                "Côte d'Ivoire": "Ivory Coast"},
         "fa": {"United Kingdom": "بریتانیا", "USA": "آمریکا", "China": "چین", "Russia": "روسیه",
                "Germany": "آلمان", "India": "هند", "Japan": "ژاپن", "Canada": "کانادا", "France": "فرانسه",
                "Ukraine": "اوکراین", "Belgium": "بلژیک", "Poland": "لهستان", "Czechia": "جمهوری چک",
                "Netherlands": "هلند", "Venezuela": "ونزوئلا", "Brazil": "برزیل", "Indonesia": "اندونزی",
                "Australia": "استرالیا", "Côte d'Ivoire": "ساحل عاج", "Iran": "ایران"}}


def name(country: str, lang: str = "en") -> str:
    return NAMES[lang].get(country, country)


def download() -> Path:
    """The file, fetched once; an interrupted or failed download leaves no file behind."""
    if not FILE.exists():
        FILE.parent.mkdir(parents=True, exist_ok=True)
        part = FILE.with_suffix(".part")
        urllib.request.urlretrieve(URL, part)
        with open(part, encoding="utf-8") as f:
            assert f.readline().startswith('"CNTR_NAME","ISO3","Gas"'), "not the Jones et al. file"
        part.rename(FILE)
    return FILE


@functools.lru_cache(maxsize=2)
def shares(component: str = "Fossil") -> pd.DataFrame:
    """Per cent of the world's warming caused by each country's CO2, CH4 and N2O, every year
    from 1851 to 2024 (years x countries)."""
    d = pd.read_csv(download())
    d = d[(d["Gas"] == "3-GHG") & (d["Component"] == component)]
    p = d.pivot_table(index="Year", columns="CNTR_NAME", values="Data")
    return p.drop(columns=sorted(GROUPS & set(p.columns))).div(p["GLOBAL"], axis=0) * 100


@functools.lru_cache(maxsize=2)
def warming(component: str = "Fossil") -> pd.Series:
    """The world's warming from these emissions, °C, every year."""
    d = pd.read_csv(download())
    d = d[(d["Gas"] == "3-GHG") & (d["Component"] == component) & (d["CNTR_NAME"] == "GLOBAL")]
    return d.set_index("Year")["Data"]


def board(year: int, component: str = "Fossil") -> pd.Series:
    """The top 10 of one year, largest first."""
    return shares(component).loc[year].sort_values(ascending=False).head(TOP)


def leaders(component: str = "Fossil") -> pd.DataFrame:
    """Years in which first or second place changes hands."""
    s = shares(component)
    order = s.apply(lambda r: list(r.sort_values(ascending=False).index[:2]), axis=1)
    first, second = order.str[0], order.str[1]
    turn = (first != first.shift()) | (second != second.shift())
    return pd.DataFrame({"first": first, "second": second})[turn]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--component", default="Fossil", choices=("Fossil", "Total", "LULUCF"))
    args = ap.parse_args()
    print(f"world's warming from these emissions, 2024: {warming(args.component).loc[2024]:.2f} °C")
    print(leaders(args.component).to_string())
    for y in (1851, 1901, 1997, 2024):
        b = board(y, args.component)
        print(y, " | ".join(f"{n} {v:.1f}" for n, v in b.items()), f"(top 10: {b.sum():.0f} %)")


if __name__ == "__main__":
    main()
