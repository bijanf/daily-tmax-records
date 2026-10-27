"""Iran on a reel: a Mercator pixel grid, the country's pixels and border, city tags.

The first second of a reel decides whether a viewer stays; a map of Iran says at once what the
reel is about. Built without cartopy or shapely (enso.country_mask: pyshp and matplotlib), so a
film can open netCDF files in the same process. The frame is onebit_snowloss's for Iran.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from scipy import ndimage  # noqa: E402

import enso  # noqa: E402

EXTENT = (43.5, 63.8, 24.8, 40.2)                 # W, E, S, N
CITIES = (("تهران", 51.39, 35.69), ("تبریز", 46.29, 38.08), ("مشهد", 59.61, 36.30), ("شیراز", 52.53, 29.59))


def mercator_y(lat):
    return np.log(np.tan(np.pi / 4 + np.deg2rad(lat) / 2))


class Map:
    """`width` px wide; the height follows from the extent. inside: the countries' pixels;
    border: their outline, two pixels wide."""

    def __init__(self, width: int, countries=("Iran",), extent=EXTENT):
        W, E, S, N = self.extent = extent
        y0, y1 = mercator_y(S), mercator_y(N)
        self.w = width
        self.h = round(width * (y1 - y0) / np.deg2rad(E - W))
        lon = W + (np.arange(self.w) + 0.5) / self.w * (E - W)
        lat = np.rad2deg(np.arctan(np.sinh(y1 - (np.arange(self.h) + 0.5) / self.h * (y1 - y0))))
        self.lon, self.lat = np.meshgrid(lon, lat)
        self.inside = enso.country_mask(list(countries), self.lat, self.lon)
        self.border = self.inside & ~ndimage.binary_erosion(self.inside, iterations=2)

    def place(self, lon: float, lat: float) -> tuple[float, float]:
        W, E, S, N = self.extent
        y0, y1 = mercator_y(S), mercator_y(N)
        return (lon - W) / (E - W) * self.w, (y1 - mercator_y(lat)) / (y1 - y0) * self.h

    def sample(self, field) -> np.ndarray:
        """A field on a regular lat/lon grid (xarray with lat, lon) at each pixel, nearest cell; a
        coastal pixel whose nearest cell is sea (NaN) takes the nearest land cell's value."""
        lat, lon = field["lat"].values, field["lon"].values
        vals = field.values
        nan = ~np.isfinite(vals)
        if nan.any():
            idx = ndimage.distance_transform_edt(nan, return_distances=False, return_indices=True)
            vals = vals[idx[0], idx[1]]
        i = np.clip(np.searchsorted(lat, self.lat) - 1, 0, len(lat) - 1)
        i = np.where(np.abs(lat[np.minimum(i + 1, len(lat) - 1)] - self.lat) < np.abs(lat[i] - self.lat),
                     np.minimum(i + 1, len(lat) - 1), i)
        j = np.clip(np.searchsorted(lon, self.lon) - 1, 0, len(lon) - 1)
        j = np.where(np.abs(lon[np.minimum(j + 1, len(lon) - 1)] - self.lon) < np.abs(lon[j] - self.lon),
                     np.minimum(j + 1, len(lon) - 1), j)
        return vals[i, j]
