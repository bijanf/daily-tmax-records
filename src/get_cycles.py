"""The data of the ice-age film (cycles_fa, src/cycles.py), fetched once into data/paleo/ (downloaded 23 Nov 2026).

    osman2021/     Osman et al. 2021, Nature 599, 239 (LGMR): global mean temperature, 500 members, 200-year bins (NOAA NCEI)
    bereiter2015/  Bereiter et al. 2015, GRL 42, 542: Antarctic CO2 composite, 805,669 years (NOAA NCEI)
    mlo/           NOAA GML Mauna Loa annual mean CO2
    hadcrut5/      HadCRUT 5.1.0.0 global annual summary series (Met Office)
    tsi/           NOAA total solar irradiance climate data record v3, yearly 1610-2025
    ice6g/         ICE-6G_C (VM5a) 1-degree slices, 0 to 21 thousand years ago (Peltier, Argus and Drummond 2015, Univ. of
                   Toronto). The server sends no intermediate certificate: the Sectigo intermediate named in its own
                   certificate is fetched and the chain is verified against the system's roots with it.
    etopo/         ETOPO1 (etopo180 on NOAA CoastWatch ERDDAP), every 6th point = 0.1 degree, 85 S to 85 N

    python -I src/get_cycles.py
"""

from __future__ import annotations

import gzip
import shutil
import ssl
import subprocess
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "paleo"
NCEI = "https://www.ncei.noaa.gov"
FILES = {
    "osman2021/LGMR_GMST_ens.nc": f"{NCEI}/pub/data/paleo/reconstructions/osman2021/LGMR_GMST_ens.nc",
    "osman2021/readme-osman2021.txt": f"{NCEI}/pub/data/paleo/reconstructions/osman2021/readme-osman2021.txt",
    "bereiter2015/antarctica2015co2composite.txt": f"{NCEI}/pub/data/paleo/icecore/antarctica/antarctica2015co2composite.txt",
    "mlo/co2_annmean_mlo.txt": "https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_annmean_mlo.txt",
    "hadcrut5/global_annual.csv": "https://www.metoffice.gov.uk/hadobs/hadcrut5/data/HadCRUT.5.1.0.0/analysis/diagnostics/"
                                  "HadCRUT.5.1.0.0.analysis.summary_series.global.annual.csv",
    "tsi/tsi_v03r00_yearly_s1610_e2025_c20260305.nc": f"{NCEI}/data/total-solar-irradiance/access/yearly/tsi_v03r00_yearly_s1610_e2025_c20260305.nc",
    "etopo/etopo_0p1.nc": "https://coastwatch.pfeg.noaa.gov/erddap/griddap/etopo180.nc?altitude%5B(-85):6:(85)%5D%5B(-180):6:(180)%5D",
}
ICE6G = "https://www.atmosp.physics.utoronto.ca/~peltier/datasets/Ice6G_C_VM5a/I6_C.VM5a_1deg.{k}.nc.gz"
SECTIGO = "http://crt.sectigo.com/SectigoPublicServerAuthenticationCAOVR36.crt"


def fetch(url: str, out: Path, ctx: ssl.SSLContext | None = None) -> None:
    if out.exists():
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    part = out.with_suffix(out.suffix + ".part")
    with urllib.request.urlopen(url, timeout=600, context=ctx) as r, open(part, "wb") as f:
        shutil.copyfileobj(r, f)
    part.rename(out)
    print("saved", out)


def toronto() -> ssl.SSLContext:
    """The system's roots plus the Sectigo intermediate, itself verified against the system's roots first."""
    with tempfile.TemporaryDirectory() as d:
        der, pem = Path(d) / "inter.crt", Path(d) / "inter.pem"
        urllib.request.urlretrieve(SECTIGO, der)
        subprocess.run(["openssl", "x509", "-inform", "DER", "-in", der, "-out", pem], check=True)
        subprocess.run(["openssl", "verify", pem], check=True, capture_output=True)
        ctx = ssl.create_default_context()
        ctx.load_verify_locations(cafile=str(pem))
    return ctx


def main() -> None:
    for name, url in FILES.items():
        fetch(url, P / name)
    ctx = toronto()
    for k in range(22):
        nc = P / "ice6g" / f"I6_C.VM5a_1deg.{k}.nc"
        if not nc.exists():
            gz = nc.with_suffix(".nc.gz")
            fetch(ICE6G.format(k=k), gz, ctx)
            with gzip.open(gz) as a, open(nc, "wb") as b:
                shutil.copyfileobj(a, b)
            gz.unlink()


if __name__ == "__main__":
    main()
