import requests

SOILGRIDS_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"


def fetch_soil_data(lat: float, lon: float, timeout: int = 30) -> dict | None:
    properties = ["phh2o", "soc", "clay", "sand", "nitrogen", "cec", "bdod"]
    params: list[tuple[str, str | float]] = [
        ("lon", lon),
        ("lat", lat),
        ("depth", "0-5cm"),
        ("value", "mean"),
    ]
    for p in properties:
        params.append(("property", p))

    try:
        r = requests.get(SOILGRIDS_URL, params=params, timeout=timeout)
        r.raise_for_status()
        raw = r.json()
    except Exception:
        return None

    soil: dict[str, float | None] = {}
    try:
        layers = raw["properties"]["layers"]
        for layer in layers:
            name = layer["name"]
            depth_entry = layer["depths"][0]
            mean_val = depth_entry["values"]["mean"]
            d_factor = layer.get("unit_measure", {}).get("d_factor", 1) or 1
            if mean_val is None:
                soil[name] = None
                continue
            soil[name] = mean_val / d_factor
    except Exception:
        return None

    return {
        "ph_h2o": soil.get("phh2o"),
        "organic_carbon": soil.get("soc"),
        "clay_pct": soil.get("clay"),
        "sand_pct": soil.get("sand"),
        "nitrogen_g_per_kg": soil.get("nitrogen"),
        "cec_cmol_per_kg": soil.get("cec"),
        "bulk_density_kg_per_m3": soil.get("bdod"),
    }
