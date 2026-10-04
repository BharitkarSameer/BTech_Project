from functools import lru_cache

import pandas as pd

from backend.config import SERVICE_DISTRICTS, SOIL_CSV
from backend.services.bbox import nearest_district


@lru_cache(maxsize=1)
def _mh_soil() -> pd.DataFrame:
    df = pd.read_csv(SOIL_CSV)
    names = {n.lower() for n in SERVICE_DISTRICTS}
    return df[(df["state"] == "Maharashtra") & (df["district"].str.lower().isin(names))].copy()


def district_npk(district: str, season: str | None = None) -> dict:
    """District-average NPK (kg/ha) — not a laboratory soil test."""
    df = _mh_soil()
    subset = df[df["district"].str.lower() == district.lower()]
    if subset.empty:
        return {
            "N": 55.0,
            "P": 27.0,
            "K": 185.0,
            "ph": 6.8,
            "year": None,
            "season": season or "Kharif",
            "district": district,
            "source": "fallback",
        }

    if season:
        seas = subset[subset["season"].str.lower() == season.lower()]
        if not seas.empty:
            subset = seas

    latest_year = int(subset["year"].max())
    rowset = subset[subset["year"] == latest_year]
    if season:
        match = rowset[rowset["season"].str.lower() == season.lower()]
        if not match.empty:
            row = match.iloc[0]
            return {
                "N": round(float(row["N"]), 1),
                "P": round(float(row["P"]), 1),
                "K": round(float(row["K"]), 1),
                "ph": round(float(row["ph"]), 2),
                "year": latest_year,
                "season": str(row["season"]),
                "district": district,
                "source": "district",
            }

    return {
        "N": round(float(rowset["N"].mean()), 1),
        "P": round(float(rowset["P"].mean()), 1),
        "K": round(float(rowset["K"].mean()), 1),
        "ph": round(float(rowset["ph"].mean()), 2),
        "year": latest_year,
        "season": "all",
        "district": district,
        "source": "district",
    }


def npk_for_point(lat: float, lon: float, season: str | None = None) -> dict:
    name, dist_km = nearest_district(lat, lon)
    payload = district_npk(name, season)
    payload["distance_km"] = round(dist_km, 1)
    return payload


def pune_npk(season: str | None = None) -> dict:
    return district_npk("Pune", season)
