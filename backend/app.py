from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

from backend.config import (
    CROP_EMOJI,
    CROP_INFO,
    CROP_PROFILES,
    PUNE_CROPS,
    REGION_CENTER,
    ROOT,
    SERVICE_BBOX,
    SERVICE_DISTRICTS,
)
from backend.services.bbox import bbox_error, nearest_district
from backend.services.cache import autofill_cache
from backend.services.npk import npk_for_point
from backend.services.recommend import recommend_crops
from backend.services.soil import fetch_soil_data
from backend.services.weather import fetch_annual_climate, fetch_current_weather
from backend.services.llm import analyze_farm, llm_configured
from backend.services.yield_pred import predict_yield, predict_yield_batch

app = FastAPI(title="Maharashtra Crop AI", version="1.1.0")
api = APIRouter()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LatLon(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    season: str | None = None


class RecommendBody(BaseModel):
    lat: float | None = None
    lon: float | None = None
    season: str | None = None
    N: float | None = None
    P: float | None = None
    K: float | None = None
    temperature: float | None = None
    humidity: float | None = None
    ph: float | None = None
    rainfall: float | None = None


class YieldBody(BaseModel):
    lat: float
    lon: float
    crop: str
    season: str = "Kharif"


class YieldBatchBody(BaseModel):
    lat: float
    lon: float
    crops: list[str]
    season: str = "Kharif"


class AnalyzeBody(BaseModel):
    lat: float | None = None
    lon: float | None = None
    district: str | None = None
    crop: str
    season: str = "Kharif"
    yield_kg_ha: float | None = None
    interval_80pct: list[float] | None = None
    confidence_pct: float | None = None
    N: float | None = None
    P: float | None = None
    K: float | None = None
    ph: float | None = None
    temperature: float | None = None
    humidity: float | None = None
    rainfall: float | None = None
    ndvi: float | None = None
    ndvi_interpretation: str | None = None
    climate: dict | None = None
    soil: dict | None = None


def _guard(lat: float, lon: float) -> None:
    err = bbox_error(lat, lon)
    if err:
        raise HTTPException(status_code=400, detail=err)


def _autofill(lat: float, lon: float, season: str | None) -> dict:
    key = f"{round(lat, 4)}:{round(lon, 4)}:{season or 'all'}"
    cached = autofill_cache.get(key)
    if cached:
        return cached

    npk = npk_for_point(lat, lon, season)
    soil = fetch_soil_data(lat, lon)
    annual = fetch_annual_climate(lat, lon)
    current = fetch_current_weather(lat, lon)

    ph_value = None
    ph_source = "district"
    if soil and soil.get("ph_h2o") is not None:
        ph_value = round(float(soil["ph_h2o"]), 2)
        ph_source = "api"
    else:
        ph_value = npk["ph"]
        ph_source = npk["source"]

    temp = None
    hum = None
    rain = None
    clim_source = "fallback"
    if annual:
        temp = annual.get("temperature_mean_c")
        hum = annual.get("humidity_mean_pct")
        rain = annual.get("rainfall_12m_mm")
        clim_source = "api"
    if current:
        if temp is None:
            temp = current.get("temperature_now_c")
        if hum is None:
            hum = current.get("humidity_now_pct")

    if temp is None:
        temp = 25.0
        clim_source = "fallback"
    if hum is None:
        hum = 60.0
    if rain is None:
        rain = 750.0
        clim_source = "fallback"

    district_name, dist_km = nearest_district(lat, lon)
    payload = {
        "lat": lat,
        "lon": lon,
        "in_region": True,
        "district": district_name,
        "district_distance_km": round(dist_km, 1),
        "N": npk["N"],
        "P": npk["P"],
        "K": npk["K"],
        "ph": ph_value,
        "temperature": temp,
        "humidity": hum,
        "rainfall": rain,
        "soil": soil,
        "weather_annual": annual,
        "weather_current": current,
        "npk_meta": {
            "source": npk["source"],
            "year": npk["year"],
            "season": npk["season"],
            "district": npk.get("district", district_name),
            "note": (
                f"N-P-K kg/ha is the {npk.get('district', district_name)} district average "
                "(not a laboratory soil test). pH/texture come from SoilGrids when available. "
                "Climate is live Open-Meteo for this coordinate."
            ),
        },
        "sources": {
            "N": npk["source"],
            "P": npk["source"],
            "K": npk["source"],
            "ph": ph_source,
            "temperature": clim_source,
            "humidity": clim_source,
            "rainfall": clim_source,
        },
    }
    autofill_cache.set(key, payload)
    return payload


@api.get("/health")
def health():
    return {
        "ok": True,
        "region": "Maharashtra-8",
        "districts": SERVICE_DISTRICTS,
        "llm_configured": llm_configured(),
    }


@api.get("/crops")
def crops():
    return {
        "crops": [
            {
                "id": c,
                "emoji": CROP_EMOJI.get(c, "🌱"),
                "info": CROP_INFO.get(c, ""),
                "season": CROP_PROFILES[c]["season"],
            }
            for c in PUNE_CROPS
        ],
        "bbox": SERVICE_BBOX,
        "center": REGION_CENTER,
        "districts": SERVICE_DISTRICTS,
    }


@api.post("/autofill")
def autofill(body: LatLon):
    _guard(body.lat, body.lon)
    return _autofill(body.lat, body.lon, body.season)


@api.post("/recommend")
def recommend(body: RecommendBody):
    values = {
        "N": body.N,
        "P": body.P,
        "K": body.K,
        "temperature": body.temperature,
        "humidity": body.humidity,
        "ph": body.ph,
        "rainfall": body.rainfall,
    }
    autofill_data = None
    if body.lat is not None and body.lon is not None:
        _guard(body.lat, body.lon)
        autofill_data = _autofill(body.lat, body.lon, body.season)
        for k in values:
            if values[k] is None:
                values[k] = autofill_data[k]

    missing = [k for k, v in values.items() if v is None]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing fields: {missing}")

    try:
        ranked = recommend_crops(
            float(values["N"]),
            float(values["P"]),
            float(values["K"]),
            float(values["temperature"]),
            float(values["humidity"]),
            float(values["ph"]),
            float(values["rainfall"]),
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    return {"inputs": values, "autofill": autofill_data, "recommendations": ranked}


@api.post("/yield")
def yield_endpoint(body: YieldBody):
    _guard(body.lat, body.lon)
    crop = body.crop.lower().strip()
    if crop not in PUNE_CROPS:
        raise HTTPException(status_code=400, detail=f"Unsupported crop. Choose from {PUNE_CROPS}")
    try:
        return predict_yield(body.lat, body.lon, crop, body.season)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@api.post("/yield/batch")
def yield_batch(body: YieldBatchBody):
    _guard(body.lat, body.lon)
    if not body.crops:
        raise HTTPException(status_code=400, detail="crops list is empty")
    crops = []
    for c in body.crops:
        name = c.lower().strip()
        if name not in PUNE_CROPS:
            raise HTTPException(status_code=400, detail=f"Unsupported crop: {c}")
        crops.append(name)
    try:
        return predict_yield_batch(body.lat, body.lon, crops, body.season)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@api.post("/analyze")
def analyze_endpoint(body: AnalyzeBody):
    if not llm_configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "LLM_API_KEY is missing. Copy .env.example to .env in the project root, "
                "paste your Gemini AI Studio key, and restart the server."
            ),
        )
    try:
        text = analyze_farm(body.model_dump())
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return {"analysis": text, "model": os.environ.get("LLM_MODEL", "gemini-3.6-flash")}


app.include_router(api)
app.include_router(api, prefix="/api")

DIST = ROOT / "frontend" / "dist"
if DIST.exists():
    assets = DIST / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        target = DIST / full_path
        if full_path and target.is_file():
            return FileResponse(target)
        return FileResponse(DIST / "index.html")
