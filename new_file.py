"""
AgroVision Ambajogai - Land Characteristics & Crop Recommendation Tool
========================================================================

Purpose
-------
Krishi Vigyan Kendra (KVK), Ambajogai will hand over a GPS coordinate
(lat, lon) anywhere in the Ambajogai / Beed district area. This script
takes that coordinate and returns:

    1. Soil characteristics  -> pH, Nitrogen, Organic Carbon, Clay%, Sand%,
                                 CEC (from SoilGrids REST API, 250m res, no key)
    2. Climate snapshot       -> temperature, humidity, recent rainfall
                                 (from Open-Meteo API, no key)
    3. Vegetation / NDVI      -> optional, via EOS Data Analytics API
                                 (needs an API key) or Google Earth Engine
                                 (needs a GEE service account, as used in the
                                 AgroVision Maharashtra pipeline). Falls back
                                 gracefully to "not available" if neither is
                                 configured.
    4. Crop recommendation    -> rule-based scoring against typical Marathwada
                                 (Beed district) crop agronomic profiles:
                                 Wheat, Jowar, Gram, Soybean, Cotton, Tur, Bajra.
                                 This mirrors the logic of the Random Forest
                                 crop-recommendation stage in the AgroVision
                                 report, but works without a pre-trained model
                                 file, so it runs immediately in the field.

Data sources (all free, no key required unless noted)
------------------------------------------------------
- SoilGrids v2.0 REST API  : https://rest.isric.org/soilgrids/v2.0/
- Open-Meteo Forecast API  : https://open-meteo.com/
- EOS Data Analytics       : https://doc.eos.com/  (OPTIONAL, needs API key)
- Google Earth Engine      : https://earthengine.google.com/ (OPTIONAL, needs
                              a service account - same one used in your
                              Pune Rice Yield / AgroVision project)

Usage
-----
    pip install requests

    python ambajogai_land_report.py --lat 18.5834 --lon 76.3847

    # If you later get an EOS key:
    python ambajogai_land_report.py --lat 18.5834 --lon 76.3847 --eos-key YOUR_KEY

Output
------
Prints a full report to the console and saves:
    - <lat>_<lon>_report.json   (machine-readable)
    - <lat>_<lon>_report.png    (bar charts, if matplotlib is available)

Author: built for Mayank, EY Summer Intern / COEP Robotics & AI
"""

import argparse
import json
import os
import sys
from datetime import datetime

import requests

# ----------------------------------------------------------------------
# 0. Sanity bounds for Ambajogai / Beed district (rough bounding box)
#    Used only to warn the user if a coordinate looks out of area -
#    the tool will still run for any coordinate.
# ----------------------------------------------------------------------
AMBAJOGAI_BBOX = {
    "lat_min": 18.35, "lat_max": 18.85,
    "lon_min": 76.10, "lon_max": 76.65,
}


# ----------------------------------------------------------------------
# 1. SOIL DATA - SoilGrids v2.0 (ISRIC), 250m global resolution, free
# ----------------------------------------------------------------------
def fetch_soil_data(lat, lon, timeout=30):
    """
    Query SoilGrids REST API for the 0-5cm depth layer.
    Returns a dict of soil properties, or None on failure.
    """
    url = "https://rest.isric.org/soilgrids/v2.0/properties/query"
    properties = ["phh2o", "soc", "clay", "sand", "nitrogen", "cec", "bdod"]
    params = [("lon", lon), ("lat", lat), ("depth", "0-5cm"), ("value", "mean")]
    for p in properties:
        params.append(("property", p))

    try:
        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        raw = r.json()
    except Exception as e:
        print(f"[WARN] SoilGrids request failed: {e}")
        return None

    soil = {}
    try:
        layers = raw["properties"]["layers"]
        # SoilGrids returns scaled integer values; each property has its own
        # d_factor to convert back to conventional units.
        for layer in layers:
            name = layer["name"]
            depth_entry = layer["depths"][0]
            mean_val = depth_entry["values"]["mean"]
            d_factor = layer.get("unit_measure", {}).get("d_factor", 1)
            if mean_val is None:
                soil[name] = None
                continue
            soil[name] = mean_val / d_factor
    except Exception as e:
        print(f"[WARN] Could not parse SoilGrids response: {e}")
        return None

    # Friendly renaming + unit notes
    result = {
        "ph_h2o": soil.get("phh2o"),                      # unitless (0-14)
        "organic_carbon_pct": soil.get("soc"),             # g/kg -> treat as index
        "clay_pct": soil.get("clay"),                      # %
        "sand_pct": soil.get("sand"),                      # %
        "nitrogen_g_per_kg": soil.get("nitrogen"),          # cg/kg -> g/kg after d_factor
        "cec_cmol_per_kg": soil.get("cec"),
        "bulk_density_kg_per_m3": soil.get("bdod"),
    }
    return result


# ----------------------------------------------------------------------
# 2. CLIMATE DATA - Open-Meteo, free, no key
# ----------------------------------------------------------------------
def fetch_weather_data(lat, lon, timeout=30):
    """
    Query Open-Meteo for current conditions + last 30 days rainfall.
    Returns a dict, or None on failure.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,precipitation",
        "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min",
        "past_days": 30,
        "forecast_days": 1,
        "timezone": "auto",
    }
    try:
        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        raw = r.json()
    except Exception as e:
        print(f"[WARN] Open-Meteo request failed: {e}")
        return None

    try:
        current = raw.get("current", {})
        daily = raw.get("daily", {})
        rainfall_30d = sum(v for v in daily.get("precipitation_sum", []) if v is not None)
        tmax_list = [v for v in daily.get("temperature_2m_max", []) if v is not None]
        tmin_list = [v for v in daily.get("temperature_2m_min", []) if v is not None]

        result = {
            "temperature_now_c": current.get("temperature_2m"),
            "humidity_now_pct": current.get("relative_humidity_2m"),
            "rainfall_last_30_days_mm": round(rainfall_30d, 1),
            "avg_tmax_30d_c": round(sum(tmax_list) / len(tmax_list), 1) if tmax_list else None,
            "avg_tmin_30d_c": round(sum(tmin_list) / len(tmin_list), 1) if tmin_list else None,
        }
        return result
    except Exception as e:
        print(f"[WARN] Could not parse Open-Meteo response: {e}")
        return None


# ----------------------------------------------------------------------
# 3. VEGETATION / NDVI - optional EOS API or Earth Engine
# ----------------------------------------------------------------------
def fetch_ndvi_eos(lat, lon, api_key, date_start=None, date_end=None,
                    buffer_deg=0.002, timeout=30, poll_interval=5, max_poll_attempts=60):
    """
    Query the real EOS Data Analytics Statistics API for NDVI over a small
    square (~200m) around the point, using the documented async task flow:

        1. POST /api/gdw/api            -> creates a task, returns task_id
        2. GET  /api/gdw/api/{task_id}   -> poll until "result" is populated

    Docs: https://doc.eos.com/docs/statistics/vegetation-indices-analytics/

    Returns the raw `result` list from EOS (one entry per available scene
    in the date range), or None if the key is missing / the request fails /
    the task times out.
    """
    if not api_key:
        return None

    import time
    from datetime import date, timedelta

    if date_end is None:
        date_end = date.today().isoformat()
    if date_start is None:
        # Default to the last 60 days so we have a good chance of a
        # cloud-free Sentinel-2 scene
        date_start = (date.today() - timedelta(days=60)).isoformat()

    polygon = {
        "type": "Polygon",
        "coordinates": [[
            [lon - buffer_deg, lat - buffer_deg],
            [lon + buffer_deg, lat - buffer_deg],
            [lon + buffer_deg, lat + buffer_deg],
            [lon - buffer_deg, lat + buffer_deg],
            [lon - buffer_deg, lat - buffer_deg],
        ]]
    }

    create_url = f"https://api-connect.eos.com/api/gdw/api?api_key={api_key}"
    payload = {
        "type": "mt_stats",
        "params": {
            "bm_type": ["NDVI"],
            "date_start": date_start,
            "date_end": date_end,
            "geometry": polygon,
            "reference": f"ambajogai_{lat:.4f}_{lon:.4f}",
            "sensors": ["sentinel2"],
        }
    }

    # Step 1: create the task
    try:
        r = requests.post(create_url, json=payload, headers={"Content-Type": "application/json"}, timeout=timeout)
        r.raise_for_status()
        task = r.json()
        task_id = task.get("task_id")
        if not task_id:
            print(f"[WARN] EOS task creation returned no task_id: {task}")
            return None
        print(f"[INFO] EOS task created: {task_id} (timeout {task.get('task_timeout', '?')}s)")
    except Exception as e:
        print(f"[WARN] EOS task creation failed: {e}")
        return None

    # Step 2: poll for the result
    result_url = f"https://api-connect.eos.com/api/gdw/api/{task_id}"
    for attempt in range(1, max_poll_attempts + 1):
        try:
            r = requests.get(result_url, headers={"x-api-key": api_key}, timeout=timeout)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"[WARN] EOS polling failed (attempt {attempt}): {e}")
            return None

        if data.get("errors"):
            print(f"[WARN] EOS returned errors: {data['errors']}")

        result = data.get("result")
        if result:
            print(f"[OK] EOS task complete - {len(result)} scene(s) returned")
            return result

        time.sleep(poll_interval)

    print(f"[WARN] EOS task {task_id} did not complete within {max_poll_attempts * poll_interval}s")
    return None


def extract_latest_ndvi(eos_result):
    """
    From the EOS `result` list (one entry per Sentinel-2 scene), pick the
    most recent, least-cloudy scene and return (ndvi_average, scene_date).
    Returns (None, None) if nothing usable is found.
    """
    if not eos_result:
        return None, None

    def sort_key(scene):
        return (scene.get("date", ""), -scene.get("cloud", 1.0))

    for scene in sorted(eos_result, key=sort_key, reverse=True):
        ndvi_stats = scene.get("indexes", {}).get("NDVI")
        if ndvi_stats and ndvi_stats.get("average") is not None:
            return ndvi_stats["average"], scene.get("date")

    return None, None


def fetch_ndvi_gee(lat, lon):
    """
    OPTIONAL: pull recent Sentinel-2 NDVI via Google Earth Engine, the same
    approach used in the AgroVision Maharashtra pipeline (Section III.C of
    your report). Requires the `earthengine-api` package and an
    authenticated GEE service account.

    This is left as a template - uncomment and configure if you want to
    reuse the GEE credentials from your Pune Rice Yield project instead of
    an EOS key.
    """
    try:
        import ee
    except ImportError:
        return None

    try:
        # ee.Initialize(credentials=...)  # configure with your service account
        point = ee.Geometry.Point([lon, lat])
        collection = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(point)
            .filterDate(ee.Date(datetime.utcnow().strftime("%Y-%m-%d")).advance(-30, "day"),
                        ee.Date(datetime.utcnow().strftime("%Y-%m-%d")))
            .sort("CLOUDY_PIXEL_PERCENTAGE")
        )
        image = collection.first()
        ndvi = image.normalizedDifference(["B8", "B4"])
        value = ndvi.reduceRegion(ee.Reducer.mean(), point, 10).get("nd")
        return value.getInfo()
    except Exception as e:
        print(f"[INFO] GEE NDVI request not completed: {e}")
        return None


def classify_ndvi(ndvi):
    """Map an NDVI float to the interpretation scale from your report (Table 1)."""
    if ndvi is None:
        return "Not available (configure EOS key or Earth Engine credentials)"
    if ndvi < 0.0:
        return "Water bodies / snow / clouds - non-agricultural surface"
    if ndvi < 0.1:
        return "Bare soil / fallow land - no crop present"
    if ndvi < 0.3:
        return "Sparse / emerging vegetation - early seedling stage"
    if ndvi < 0.6:
        return "Moderate vegetation cover - active vegetative growth"
    if ndvi < 0.8:
        return "Good crop condition - healthy, well-developed canopy"
    return "Dense, highly productive crop - peak canopy closure"


# ----------------------------------------------------------------------
# 4. CROP RECOMMENDATION - rule-based agronomic scoring
#    (stand-in for the trained Random Forest classifier until a model
#    file is available; ranges are typical for Marathwada / Beed district)
# ----------------------------------------------------------------------
CROP_PROFILES = {
    "Wheat":    {"ph": (6.0, 7.5), "n_g_kg": (1.0, 3.0), "rain_mm": (300, 600),  "temp_c": (15, 25), "season": "Rabi"},
    "Gram":     {"ph": (6.0, 7.5), "n_g_kg": (0.5, 2.0), "rain_mm": (250, 500),  "temp_c": (18, 28), "season": "Rabi"},
    "Jowar":    {"ph": (6.0, 7.8), "n_g_kg": (0.5, 2.0), "rain_mm": (400, 700),  "temp_c": (25, 32), "season": "Kharif/Rabi"},
    "Soybean":  {"ph": (6.0, 7.5), "n_g_kg": (1.0, 2.5), "rain_mm": (600, 1000), "temp_c": (20, 30), "season": "Kharif"},
    "Cotton":   {"ph": (6.0, 8.0), "n_g_kg": (1.0, 2.5), "rain_mm": (600, 1200), "temp_c": (21, 30), "season": "Kharif"},
    "Tur (Pigeon Pea)": {"ph": (6.0, 7.5), "n_g_kg": (0.5, 2.0), "rain_mm": (600, 1000), "temp_c": (20, 30), "season": "Kharif"},
    "Bajra":    {"ph": (6.5, 8.5), "n_g_kg": (0.3, 1.5), "rain_mm": (400, 600),  "temp_c": (25, 35), "season": "Kharif"},
}


def _range_score(value, low, high):
    """
    Score 0-100 for how well `value` fits inside [low, high].
    Full marks inside the range; linear decay outside it.
    """
    if value is None:
        return 50.0  # neutral score if data missing
    if low <= value <= high:
        return 100.0
    span = high - low if high > low else 1.0
    if value < low:
        dist = (low - value) / span
    else:
        dist = (value - high) / span
    return max(0.0, 100.0 - dist * 100.0)


def recommend_crops(soil, weather):
    """
    Score every crop profile against the fetched soil pH, nitrogen,
    30-day rainfall, and average temperature. Returns a ranked list of
    (crop_name, score, season) tuples, highest score first.
    """
    ph = soil.get("ph_h2o") if soil else None
    n = soil.get("nitrogen_g_per_kg") if soil else None
    rain = weather.get("rainfall_last_30_days_mm") if weather else None
    temp = weather.get("avg_tmax_30d_c") if weather else None

    ranked = []
    for crop, profile in CROP_PROFILES.items():
        s_ph = _range_score(ph, *profile["ph"])
        s_n = _range_score(n, *profile["n_g_kg"])
        s_rain = _range_score(rain, *profile["rain_mm"])
        s_temp = _range_score(temp, *profile["temp_c"])
        overall = round((s_ph + s_n + s_rain + s_temp) / 4, 1)
        ranked.append((crop, overall, profile["season"]))

    ranked.sort(key=lambda x: x[1], reverse=True)
    return ranked


# ----------------------------------------------------------------------
# 5. REPORT GENERATION
# ----------------------------------------------------------------------
def generate_report(lat, lon, soil, weather, ndvi, crops, ndvi_date=None):
    in_bbox = (
        AMBAJOGAI_BBOX["lat_min"] <= lat <= AMBAJOGAI_BBOX["lat_max"]
        and AMBAJOGAI_BBOX["lon_min"] <= lon <= AMBAJOGAI_BBOX["lon_max"]
    )

    lines = []
    lines.append("=" * 68)
    lines.append("  AGROVISION - LAND CHARACTERISTICS REPORT (Ambajogai / KVK)")
    lines.append("=" * 68)
    lines.append(f"Coordinate            : {lat:.5f}, {lon:.5f}")
    lines.append(f"Within Ambajogai area  : {'Yes' if in_bbox else 'No (outside expected bounding box - check coordinate)'}")
    lines.append(f"Generated on           : {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("-" * 68)

    lines.append("SOIL CHARACTERISTICS  (SoilGrids, 0-5cm, 250m resolution)")
    if soil:
        lines.append(f"  Soil pH               : {soil.get('ph_h2o')}")
        lines.append(f"  Nitrogen (g/kg)       : {soil.get('nitrogen_g_per_kg')}")
        lines.append(f"  Organic Carbon        : {soil.get('organic_carbon_pct')}")
        lines.append(f"  Clay %                : {soil.get('clay_pct')}")
        lines.append(f"  Sand %                : {soil.get('sand_pct')}")
        lines.append(f"  CEC (cmol/kg)         : {soil.get('cec_cmol_per_kg')}")
    else:
        lines.append("  Not available (SoilGrids request failed - check internet connection)")

    lines.append("-" * 68)
    lines.append("CLIMATE SNAPSHOT  (Open-Meteo)")
    if weather:
        lines.append(f"  Current temperature   : {weather.get('temperature_now_c')} C")
        lines.append(f"  Current humidity      : {weather.get('humidity_now_pct')} %")
        lines.append(f"  Rainfall (last 30 d)  : {weather.get('rainfall_last_30_days_mm')} mm")
        lines.append(f"  Avg max temp (30 d)   : {weather.get('avg_tmax_30d_c')} C")
        lines.append(f"  Avg min temp (30 d)   : {weather.get('avg_tmin_30d_c')} C")
    else:
        lines.append("  Not available (Open-Meteo request failed - check internet connection)")

    lines.append("-" * 68)
    lines.append("VEGETATION STATUS  (NDVI)")
    lines.append(f"  NDVI value            : {ndvi if ndvi is not None else 'N/A'}")
    if ndvi_date:
        lines.append(f"  From satellite scene  : {ndvi_date}")
    lines.append(f"  Interpretation        : {classify_ndvi(ndvi)}")
    if ndvi is None:
        lines.append("  (Enable with --eos-key, or configure Earth Engine, for a live value)")

    lines.append("-" * 68)
    lines.append("CROP RECOMMENDATION  (rule-based scoring, Marathwada agronomic ranges)")
    for i, (crop, score, season) in enumerate(crops, start=1):
        lines.append(f"  {i}. {crop:<20s} score: {score:5.1f}/100   season: {season}")

    lines.append("=" * 68)
    report_text = "\n".join(lines)
    print(report_text)

    return {
        "lat": lat,
        "lon": lon,
        "within_ambajogai_bbox": in_bbox,
        "generated_on": datetime.now().isoformat(),
        "soil": soil,
        "weather": weather,
        "ndvi": ndvi,
        "ndvi_date": ndvi_date,
        "ndvi_interpretation": classify_ndvi(ndvi),
        "crop_recommendation": [
            {"crop": c, "score": s, "season": season} for c, s, season in crops
        ],
    }


def plot_report(report, out_path):
    """Save a simple 2-panel chart: crop scores + NDVI scale marker."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("[INFO] matplotlib not installed - skipping chart. `pip install matplotlib` to enable.")
        return

    crops = report["crop_recommendation"]
    names = [c["crop"] for c in crops]
    scores = [c["score"] for c in crops]

    fig, ax = plt.subplots(1, 1, figsize=(8, 5))
    ax.barh(names[::-1], scores[::-1], color="#3a7d44")
    ax.set_xlabel("Suitability score (0-100)")
    ax.set_title(f"Crop Suitability - {report['lat']:.4f}, {report['lon']:.4f}")
    ax.set_xlim(0, 100)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"[OK] Saved chart to {out_path}")


# ----------------------------------------------------------------------
# 6. MAIN
# ----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="AgroVision Ambajogai land characteristics tool")
    parser.add_argument("--lat", type=float, required=True, help="Latitude of the point")
    parser.add_argument("--lon", type=float, required=True, help="Longitude of the point")
    parser.add_argument("--eos-key", type=str, default=os.environ.get("EOS_API_KEY"),
                         help="EOS Data Analytics API key (optional; or set EOS_API_KEY env var)")
    parser.add_argument("--outdir", type=str, default=".", help="Directory to save report files")
    args = parser.parse_args()

    lat, lon = args.lat, args.lon

    print(f"Fetching data for ({lat}, {lon}) ...\n")
    soil = fetch_soil_data(lat, lon)
    weather = fetch_weather_data(lat, lon)

    ndvi, ndvi_date = None, None
    if args.eos_key:
        print("Requesting NDVI from EOS (this can take up to a couple of minutes) ...")
        eos_result = fetch_ndvi_eos(lat, lon, args.eos_key)
        ndvi, ndvi_date = extract_latest_ndvi(eos_result)
    if ndvi is None:
        ndvi = fetch_ndvi_gee(lat, lon)

    crops = recommend_crops(soil or {}, weather or {})
    report = generate_report(lat, lon, soil, weather, ndvi, crops, ndvi_date=ndvi_date)

    os.makedirs(args.outdir, exist_ok=True)
    tag = f"{lat:.4f}_{lon:.4f}".replace(".", "p").replace("-", "m")
    json_path = os.path.join(args.outdir, f"{tag}_report.json")
    png_path = os.path.join(args.outdir, f"{tag}_report.png")

    with open(json_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n[OK] Saved JSON report to {json_path}")

    plot_report(report, png_path)


if __name__ == "__main__":
    main()