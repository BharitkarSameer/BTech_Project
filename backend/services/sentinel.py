from __future__ import annotations

from datetime import date, timedelta

import numpy as np

from backend.services.cache import sentinel_cache
from backend.services.ndvi_utils import classify_ndvi
from backend.services.weather import fetch_season_climate

BUFFER_DEG = 0.0015  # ~150–160 m


def _season_dates(season: str, year: int | None = None) -> tuple[date, date]:
    today = date.today()
    year = year or today.year
    s = (season or "Kharif").title()
    if s == "Rabi":
        # Rabi spans calendar years: Nov (year-1) – Mar (year)
        if today.month >= 11:
            return date(year, 11, 1), min(today, date(year + 1, 3, 31))
        return date(year - 1, 11, 1), min(today, date(year, 3, 31))
    if s == "Zaid":
        start = date(year, 3, 1)
        end = date(year, 6, 15)
        return start, min(today, end)
    # Kharif / default last 90 days if off-season
    start = date(year, 6, 1)
    end = date(year, 10, 31)
    if today < start:
        start = date(year - 1, 6, 1)
        end = date(year - 1, 10, 31)
    return start, min(today - timedelta(days=2), end)


def _proxy_indices(lat: float, lon: float, start: date, end: date) -> dict:
    """Weather-based NDVI stand-in if Sentinel COGs cannot be read."""
    climate = fetch_season_climate(lat, lon, start, end) or {}
    rain = climate.get("rainfall_mm") or 400.0
    tmax = climate.get("avg_tmax_c") or 32.0
    ndvi = 0.18 + 0.00045 * rain - 0.008 * max(tmax - 33.0, 0)
    ndvi = float(np.clip(ndvi, 0.08, 0.82))
    evi = float(np.clip(ndvi * 0.85, 0.05, 0.7))
    ndwi = float(np.clip(0.05 + 0.0002 * rain - 0.01 * max(tmax - 30, 0), -0.2, 0.4))
    return {
        "ndvi_mean": round(ndvi, 4),
        "ndvi_max": round(min(ndvi + 0.08, 0.9), 4),
        "ndvi_p90": round(min(ndvi + 0.05, 0.88), 4),
        "evi_mean": round(evi, 4),
        "ndwi_mean": round(ndwi, 4),
        "scene_count": 0,
        "latest_ndvi": round(ndvi, 4),
        "latest_date": None,
        "source": "proxy",
        "interpretation": classify_ndvi(ndvi),
        "series": [],
        "start": start.isoformat(),
        "end": end.isoformat(),
        "note": "Sentinel scenes unavailable; NDVI estimated from seasonal weather.",
    }


def _read_indices_from_item(item, lat: float, lon: float) -> dict | None:
    try:
        import planetary_computer  # noqa: F401
        import rasterio
        from rasterio.windows import from_bounds
    except ImportError:
        return None

    signed = item
    try:
        import planetary_computer as pc

        signed = pc.sign(item)
    except Exception:
        pass

    assets = signed.assets
    b04 = assets.get("B04")
    b08 = assets.get("B08")
    b8a = assets.get("B8A")
    b03 = assets.get("B03")
    b11 = assets.get("B11")
    if not b04 or not (b08 or b8a):
        return None

    west, south = lon - BUFFER_DEG, lat - BUFFER_DEG
    east, north = lon + BUFFER_DEG, lat + BUFFER_DEG

    def _mean_band(asset) -> float | None:
        try:
            from rasterio.warp import transform_bounds
            import rasterio
            from rasterio.windows import from_bounds

            href = asset.href
            with rasterio.open(href) as src:
                minx, miny, maxx, maxy = transform_bounds(
                    "EPSG:4326", src.crs, west, south, east, north, densify_pts=0
                )
                window = from_bounds(minx, miny, maxx, maxy, transform=src.transform)
                data = src.read(1, window=window, boundless=True, fill_value=0).astype("float32")
                scale = src.scales[0] if src.scales else 0.0001
                if scale in (0, 1):
                    scale = 0.0001
                nodata = src.nodata
                data = data * scale
                mask = (data > 0) & (data < 1)
                if nodata is not None:
                    mask &= data != nodata * scale
                data = data[mask]
                if data.size == 0:
                    return None
                return float(np.nanmean(data))
        except Exception:
            return None

    red = _mean_band(b04)
    nir = _mean_band(b08 or b8a)
    if red is None or nir is None:
        return None
    ndvi = (nir - red) / (nir + red + 1e-6)

    green = _mean_band(b03) if b03 else None
    swir = _mean_band(b11) if b11 else None
    evi = 2.5 * (nir - red) / (nir + 6 * red - 7.5 * (green or red) + 1)
    ndwi = ((green - nir) / (green + nir + 1e-6)) if green is not None else None
    ndmi = ((nir - swir) / (nir + swir + 1e-6)) if swir is not None else None

    props = item.properties
    return {
        "date": props.get("datetime", "")[:10],
        "cloud": props.get("eo:cloud_cover"),
        "ndvi": float(ndvi),
        "evi": float(evi),
        "ndwi": float(ndwi) if ndwi is not None else None,
        "ndmi": float(ndmi) if ndmi is not None else None,
    }


def fetch_sentinel_indices(
    lat: float,
    lon: float,
    season: str = "Kharif",
    year: int | None = None,
    date_start: date | None = None,
    date_end: date | None = None,
) -> dict:
    if date_start is None or date_end is None:
        date_start, date_end = _season_dates(season, year)

    key = f"{round(lat, 4)}:{round(lon, 4)}:{date_start}:{date_end}"
    cached = sentinel_cache.get(key)
    if cached:
        return cached

    try:
        import planetary_computer
        import pystac_client
    except ImportError:
        result = _proxy_indices(lat, lon, date_start, date_end)
        sentinel_cache.set(key, result)
        return result

    try:
        catalog = pystac_client.Client.open(
            "https://planetarycomputer.microsoft.com/api/stac/v1",
            modifier=planetary_computer.sign_inplace,
        )
        search = catalog.search(
            collections=["sentinel-2-l2a"],
            bbox=[lon - BUFFER_DEG, lat - BUFFER_DEG, lon + BUFFER_DEG, lat + BUFFER_DEG],
            datetime=f"{date_start.isoformat()}/{date_end.isoformat()}",
            max_items=20,
        )
        items = [
            it
            for it in search.items()
            if (it.properties.get("eo:cloud_cover") or 100) < 45
        ]
        items.sort(key=lambda it: it.properties.get("eo:cloud_cover") or 100)
    except Exception:
        result = _proxy_indices(lat, lon, date_start, date_end)
        sentinel_cache.set(key, result)
        return result

    series = []
    for item in items[:8]:
        row = _read_indices_from_item(item, lat, lon)
        if row and row["ndvi"] == row["ndvi"]:
            series.append(row)

    if not series:
        result = _proxy_indices(lat, lon, date_start, date_end)
        sentinel_cache.set(key, result)
        return result

    ndvis = np.array([s["ndvi"] for s in series], dtype=float)
    evis = np.array([s["evi"] for s in series], dtype=float)
    ndwis = np.array([s["ndwi"] for s in series if s.get("ndwi") is not None], dtype=float)
    latest = sorted(series, key=lambda s: s["date"] or "")[-1]

    result = {
        "ndvi_mean": round(float(np.mean(ndvis)), 4),
        "ndvi_max": round(float(np.max(ndvis)), 4),
        "ndvi_p90": round(float(np.percentile(ndvis, 90)), 4),
        "evi_mean": round(float(np.mean(evis)), 4),
        "ndwi_mean": round(float(np.mean(ndwis)), 4) if ndwis.size else None,
        "scene_count": len(series),
        "latest_ndvi": round(float(latest["ndvi"]), 4),
        "latest_date": latest["date"],
        "source": "sentinel-2-l2a",
        "interpretation": classify_ndvi(float(latest["ndvi"])),
        "series": series,
        "start": date_start.isoformat(),
        "end": date_end.isoformat(),
        "note": None,
    }
    sentinel_cache.set(key, result)
    return result
