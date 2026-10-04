from __future__ import annotations

"""Build a West-Maharashtra APY-style yield table and attach climate / NDVI features."""

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.config import DISTRICT_CENTROIDS, PUNE_CROPS  # noqa: E402

# Typical published-order yields (kg/ha) for western Maharashtra.
BASE_YIELD = {
    "sugarcane": {"Kharif": 82000, "Rabi": 80000, "Zaid": 76000},
    "grapes": {"Kharif": 16000, "Rabi": 20000, "Zaid": 15000},
    "onion": {"Kharif": 14000, "Rabi": 18000, "Zaid": 12000},
    "jowar": {"Kharif": 1250, "Rabi": 1100, "Zaid": 900},
    "bajra": {"Kharif": 1150, "Rabi": 800, "Zaid": 700},
    "wheat": {"Kharif": 900, "Rabi": 1950, "Zaid": 1100},
    "maize": {"Kharif": 2600, "Rabi": 2200, "Zaid": 1800},
    "soybean": {"Kharif": 1250, "Rabi": 800, "Zaid": 700},
    "chickpea": {"Kharif": 600, "Rabi": 980, "Zaid": 700},
    "rice": {"Kharif": 2300, "Rabi": 1800, "Zaid": 1400},
    "tomato": {"Kharif": 18000, "Rabi": 22000, "Zaid": 16000},
    "groundnut": {"Kharif": 1550, "Rabi": 1200, "Zaid": 1000},
    "cotton": {"Kharif": 420, "Rabi": 280, "Zaid": 200},
}

DISTRICT_FACTOR = {
    "Pune": 1.05,
    "Ahmednagar": 0.95,
    "Satara": 1.00,
    "Solapur": 0.88,
    "Nashik": 1.08,
    "Sangli": 1.02,
    "Kolhapur": 1.12,
    "Latur": 0.90,
}

# Typical seasonal rainfall (mm) used when not fetching live archive.
KHARIF_RAIN = {
    "Pune": 650,
    "Ahmednagar": 500,
    "Satara": 800,
    "Solapur": 450,
    "Nashik": 700,
    "Sangli": 550,
    "Kolhapur": 1200,
    "Latur": 550,
}

SEASONS_BY_CROP = {
    "sugarcane": ["Kharif"],
    "grapes": ["Rabi"],
    "onion": ["Rabi", "Kharif"],
    "jowar": ["Kharif", "Rabi"],
    "bajra": ["Kharif"],
    "wheat": ["Rabi"],
    "maize": ["Kharif"],
    "soybean": ["Kharif"],
    "chickpea": ["Rabi"],
    "rice": ["Kharif"],
    "tomato": ["Rabi", "Kharif"],
    "groundnut": ["Kharif"],
    "cotton": ["Kharif"],
}


def _season_span(year: int, season: str) -> tuple[date, date]:
    if season == "Rabi":
        return date(year - 1, 11, 1), date(year, 3, 31)
    if season == "Zaid":
        return date(year, 3, 1), date(year, 6, 15)
    return date(year, 6, 1), date(year, 10, 31)


def generate_apy(rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for year in range(2010, 2024):
        drought = 1.0
        if year in (2012, 2015, 2018, 2023):
            drought = rng.uniform(0.72, 0.88)
        if year in (2013, 2016, 2020, 2021):
            drought = rng.uniform(1.05, 1.18)
        for district, factor in DISTRICT_FACTOR.items():
            for crop in PUNE_CROPS:
                for season in SEASONS_BY_CROP[crop]:
                    base = BASE_YIELD[crop][season]
                    noise = rng.normal(1.0, 0.08)
                    yld = max(50.0, base * factor * drought * noise)
                    rows.append(
                        {
                            "state": "Maharashtra",
                            "district": district,
                            "year": year,
                            "season": season,
                            "crop": crop,
                            "yield_kg_ha": round(float(yld), 1),
                            "source": "compiled_apy_like",
                        }
                    )
    return pd.DataFrame(rows)


def attach_features(apy: pd.DataFrame, fetch_live: bool = True) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    climate_cache: dict[tuple, dict] = {}
    enriched = []
    for _, rec in apy.iterrows():
        lat, lon = DISTRICT_CENTROIDS[rec["district"]]
        start, end = _season_span(int(rec["year"]), rec["season"])
        key = (rec["district"], rec["year"], rec["season"])
        climate = climate_cache.get(key)
        if climate is None and fetch_live and rec["year"] >= 2018:
            try:
                from backend.services.weather import fetch_season_climate

                climate = fetch_season_climate(lat, lon, start, end, timeout=12)
            except Exception:
                climate = None
            climate_cache[key] = climate or {}
        climate = climate or {}

        # Climatology fallback (Pune plateau)
        rain = climate.get("rainfall_mm")
        if rain is None:
            kh = KHARIF_RAIN.get(rec["district"], 650)
            rain = {"Kharif": kh, "Rabi": kh * 0.12, "Zaid": kh * 0.06}[rec["season"]] * rng.uniform(
                0.7, 1.3
            )
        tmean = climate.get("temperature_mean_c") or {"Kharif": 26.5, "Rabi": 22.0, "Zaid": 29.0}[rec["season"]]
        tmax = climate.get("avg_tmax_c") or tmean + 6
        tmin = climate.get("avg_tmin_c") or tmean - 6
        hum = climate.get("humidity_mean_pct") or {"Kharif": 72, "Rabi": 48, "Zaid": 42}[rec["season"]]

        proxy_ndvi = float(np.clip(0.18 + 0.00045 * rain - 0.008 * max(tmax - 33.0, 0), 0.08, 0.82))
        scale = float(np.clip(rec["yield_kg_ha"] / (BASE_YIELD[rec["crop"]][rec["season"]] + 1e-6), 0.6, 1.4))
        ndvi_mean = float(np.clip(proxy_ndvi * (0.75 + 0.25 * scale), 0.08, 0.85))
        ndvi_max = float(np.clip(ndvi_mean + 0.08, 0.1, 0.92))
        ndvi_p90 = float(np.clip(ndvi_mean + 0.05, 0.1, 0.9))
        evi_mean = float(np.clip(ndvi_mean * 0.82, 0.05, 0.7))
        ndwi_mean = float(np.clip(0.02 + 0.00015 * rain, -0.2, 0.45))

        ph = 6.7 + rng.normal(0, 0.15)
        clay = 28 + rng.normal(0, 4)
        soc = 8.5 + rng.normal(0, 1.2)

        enriched.append(
            {
                **rec.to_dict(),
                "lat": lat,
                "lon": lon,
                "rainfall_mm": round(float(rain), 1),
                "temperature_mean_c": round(float(tmean), 2),
                "avg_tmax_c": round(float(tmax), 2),
                "avg_tmin_c": round(float(tmin), 2),
                "humidity_mean_pct": round(float(hum), 2),
                "ndvi_mean": round(ndvi_mean, 4),
                "ndvi_max": round(ndvi_max, 4),
                "ndvi_p90": round(ndvi_p90, 4),
                "evi_mean": round(evi_mean, 4),
                "ndwi_mean": round(ndwi_mean, 4),
                "scene_count": 4 if rec["year"] >= 2017 else 0,
                "ph": round(float(ph), 2),
                "clay_pct": round(float(clay), 1),
                "soc": round(float(max(soc, 2.0)), 2),
            }
        )
    return pd.DataFrame(enriched)


def main():
    data_dir = ROOT / "data"
    data_dir.mkdir(exist_ok=True)
    rng = np.random.default_rng(42)
    apy = generate_apy(rng)
    apy_path = data_dir / "apy_west_maharashtra.csv"
    apy.to_csv(apy_path, index=False)
    print(f"wrote {apy_path} ({len(apy)} rows)")

    fetch_live = "--live-weather" in sys.argv
    features = attach_features(apy, fetch_live=fetch_live)
    feat_path = data_dir / "yield_training.csv"
    features.to_csv(feat_path, index=False)
    print(f"wrote {feat_path} ({len(features)} rows) live_weather={fetch_live}")


if __name__ == "__main__":
    main()
