import math

from backend.config import DISTRICT_CENTROIDS, SERVICE_BBOX, SERVICE_DISTRICTS


def in_region(lat: float, lon: float) -> bool:
    return (
        SERVICE_BBOX["lat_min"] <= lat <= SERVICE_BBOX["lat_max"]
        and SERVICE_BBOX["lon_min"] <= lon <= SERVICE_BBOX["lon_max"]
    )


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def nearest_district(lat: float, lon: float) -> tuple[str, float]:
    best_name, best_d = SERVICE_DISTRICTS[0], float("inf")
    for name in SERVICE_DISTRICTS:
        clat, clon = DISTRICT_CENTROIDS[name]
        d = haversine_km(lat, lon, clat, clon)
        if d < best_d:
            best_name, best_d = name, d
    return best_name, best_d


def bbox_error(lat: float, lon: float) -> str | None:
    if in_region(lat, lon):
        return None
    names = ", ".join(SERVICE_DISTRICTS)
    return (
        f"This app covers {names} only "
        f"(lat {SERVICE_BBOX['lat_min']}–{SERVICE_BBOX['lat_max']}, "
        f"lon {SERVICE_BBOX['lon_min']}–{SERVICE_BBOX['lon_max']})."
    )
