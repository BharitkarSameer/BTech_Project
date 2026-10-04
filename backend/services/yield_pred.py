from __future__ import annotations

import json
from datetime import date

import joblib
import numpy as np
import pandas as pd

from backend.config import CROP_PROFILES, MODELS_DIR
from backend.services.ndvi_utils import classify_ndvi
from backend.services.sentinel import _season_dates, fetch_sentinel_indices
from backend.services.soil import fetch_soil_data
from backend.services.weather import fetch_season_climate

_model = None
_meta: dict | None = None
_crop_map: dict[str, int] | None = None
_season_map: dict[str, int] | None = None


def _load():
    global _model, _meta, _crop_map, _season_map
    if _model is not None:
        return
    path = MODELS_DIR / "yield_lgbm.joblib"
    meta_path = MODELS_DIR / "yield_meta.json"
    if not path.exists():
        raise FileNotFoundError(
            "Yield model missing. Run `python -m ml.train_yield` from the project root."
        )
    bundle = joblib.load(path)
    _model = bundle["model"]
    _crop_map = bundle["crop_map"]
    _season_map = bundle["season_map"]
    _meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}


def typical_yield(crop: str) -> float:
    """kg/ha typical western Maharashtra district yield (order-of-magnitude)."""
    table = {
        "sugarcane": 80000,
        "grapes": 18000,
        "onion": 16000,
        "jowar": 1200,
        "bajra": 1100,
        "wheat": 1800,
        "maize": 2500,
        "soybean": 1200,
        "chickpea": 900,
        "rice": 2200,
        "tomato": 20000,
        "groundnut": 1500,
        "cotton": 400,  # lint kg/ha, often reported as kg/ha
    }
    return float(table.get(crop, 2000))


def _season_name(crop: str, season: str) -> str:
    season_name = season.title() if season else "Kharif"
    if season_name not in ("Kharif", "Rabi", "Zaid"):
        season_name = CROP_PROFILES.get(crop, {}).get("season", "Kharif")
        if season_name == "Annual":
            season_name = "Kharif"
    return season_name


def _score_crop(crop: str, season_name: str, sat: dict, climate: dict, soil: dict) -> dict:
    _load()
    crop = crop.lower()
    crop_id = _crop_map.get(crop, 0) if _crop_map else 0
    season_id = _season_map.get(season_name, 0) if _season_map else 0
    year = date.today().year

    row = {
        "crop_id": crop_id,
        "season_id": season_id,
        "year": year,
        "ndvi_mean": sat.get("ndvi_mean") or 0.4,
        "ndvi_max": sat.get("ndvi_max") or 0.5,
        "ndvi_p90": sat.get("ndvi_p90") or 0.48,
        "evi_mean": sat.get("evi_mean") or 0.3,
        "ndwi_mean": sat.get("ndwi_mean") or 0.0,
        "scene_count": sat.get("scene_count") or 0,
        "rainfall_mm": climate.get("rainfall_mm") or 500.0,
        "temperature_mean_c": climate.get("temperature_mean_c") or 26.0,
        "avg_tmax_c": climate.get("avg_tmax_c") or 32.0,
        "avg_tmin_c": climate.get("avg_tmin_c") or 20.0,
        "humidity_mean_pct": climate.get("humidity_mean_pct") or 60.0,
        "ph": soil.get("ph_h2o") or 6.8,
        "clay_pct": soil.get("clay_pct") or 30.0,
        "soc": soil.get("organic_carbon") or 8.0,
    }
    feature_order = (_meta or {}).get(
        "features",
        list(row.keys()),
    )
    x = pd.DataFrame([row])[feature_order]
    yhat = float(_model.predict(x)[0])
    residual_std = float(
        (_meta or {}).get("residual_std", {}).get(
            crop, (_meta or {}).get("global_residual_std", yhat * 0.15)
        )
    )
    lo = max(0.0, yhat - 1.28 * residual_std)
    hi = yhat + 1.28 * residual_std
    ndvi = row["ndvi_mean"]
    baseline = typical_yield(crop) * (0.55 + 0.9 * ndvi)
    blended = 0.85 * yhat + 0.15 * baseline
    latest = sat.get("latest_ndvi")
    return {
        "crop": crop,
        "season": season_name,
        "yield_kg_ha": round(blended, 1),
        "interval_80pct": [round(lo, 1), round(hi, 1)],
        "model_raw_kg_ha": round(yhat, 1),
        "ndvi_baseline_kg_ha": round(baseline, 1),
        "unit": "kg/ha",
        "disclaimer": (
            "Indicative yield. The model is trained on synthetic district harvest trends "
            "(typical western Maharashtra / Latur yields by crop and year). "
            "At prediction time, NDVI comes from live Sentinel-2 and climate from Open-Meteo "
            "for this coordinate. Not a field-measured harvest."
        ),
        "satellite": sat,
        "climate": climate,
        "soil": soil,
        "ndvi_interpretation": classify_ndvi(latest if latest is not None else ndvi),
    }


def predict_yield(lat: float, lon: float, crop: str, season: str = "Kharif") -> dict:
    crop = crop.lower()
    season_name = _season_name(crop, season)
    start, end = _season_dates(season_name)
    sat = fetch_sentinel_indices(lat, lon, season=season_name, date_start=start, date_end=end)
    climate = fetch_season_climate(lat, lon, start, end) or {}
    soil = fetch_soil_data(lat, lon) or {}
    out = _score_crop(crop, season_name, sat, climate, soil)
    out["window"] = {"start": start.isoformat(), "end": end.isoformat()}
    return out


def predict_yield_batch(lat: float, lon: float, crops: list[str], season: str = "Kharif") -> dict:
    """One Sentinel + climate + soil pull, then a yield score per crop."""
    season_name = _season_name(crops[0] if crops else "wheat", season)
    start, end = _season_dates(season_name)
    sat = fetch_sentinel_indices(lat, lon, season=season_name, date_start=start, date_end=end)
    climate = fetch_season_climate(lat, lon, start, end) or {}
    soil = fetch_soil_data(lat, lon) or {}
    results = []
    for crop in crops:
        c = crop.lower().strip()
        sn = _season_name(c, season)
        item = _score_crop(c, sn, sat, climate, soil)
        item["window"] = {"start": start.isoformat(), "end": end.isoformat()}
        results.append(item)
    return {
        "lat": lat,
        "lon": lon,
        "season": season_name,
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "satellite": sat,
        "climate": climate,
        "soil": soil,
        "yields": results,
    }
