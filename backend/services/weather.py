from datetime import date, timedelta

import requests

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def fetch_current_weather(lat: float, lon: float, timeout: int = 20) -> dict | None:
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,precipitation",
        "timezone": "auto",
    }
    try:
        r = requests.get(FORECAST_URL, params=params, timeout=timeout)
        r.raise_for_status()
        current = r.json().get("current", {})
        return {
            "temperature_now_c": current.get("temperature_2m"),
            "humidity_now_pct": current.get("relative_humidity_2m"),
            "precipitation_now_mm": current.get("precipitation"),
        }
    except Exception:
        return None


def fetch_annual_climate(lat: float, lon: float, timeout: int = 30) -> dict | None:
    """Last 365 days from the archive API — matches crop-model rainfall units (mm/year)."""
    end = date.today() - timedelta(days=2)
    start = end - timedelta(days=364)
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": "temperature_2m_mean,temperature_2m_max,temperature_2m_min,"
        "relative_humidity_2m_mean,precipitation_sum",
        "timezone": "auto",
    }
    try:
        r = requests.get(ARCHIVE_URL, params=params, timeout=timeout)
        r.raise_for_status()
        daily = r.json().get("daily", {})
    except Exception:
        return None

    def _vals(key: str) -> list[float]:
        return [v for v in daily.get(key, []) if v is not None]

    rain = _vals("precipitation_sum")
    tmean = _vals("temperature_2m_mean")
    tmax = _vals("temperature_2m_max")
    tmin = _vals("temperature_2m_min")
    hum = _vals("relative_humidity_2m_mean")

    if not rain and not tmean:
        return None

    def _avg(xs: list[float]) -> float | None:
        return round(sum(xs) / len(xs), 1) if xs else None

    return {
        "rainfall_12m_mm": round(sum(rain), 1) if rain else None,
        "temperature_mean_c": _avg(tmean),
        "avg_tmax_c": _avg(tmax),
        "avg_tmin_c": _avg(tmin),
        "humidity_mean_pct": _avg(hum),
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
    }


def fetch_season_climate(
    lat: float,
    lon: float,
    start: date,
    end: date,
    timeout: int = 30,
) -> dict | None:
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": "temperature_2m_mean,temperature_2m_max,temperature_2m_min,"
        "relative_humidity_2m_mean,precipitation_sum",
        "timezone": "auto",
    }
    try:
        r = requests.get(ARCHIVE_URL, params=params, timeout=timeout)
        r.raise_for_status()
        daily = r.json().get("daily", {})
    except Exception:
        return None

    def _vals(key: str) -> list[float]:
        return [v for v in daily.get(key, []) if v is not None]

    rain = _vals("precipitation_sum")
    tmean = _vals("temperature_2m_mean")
    tmax = _vals("temperature_2m_max")
    tmin = _vals("temperature_2m_min")
    hum = _vals("relative_humidity_2m_mean")

    def _avg(xs: list[float]) -> float | None:
        return round(sum(xs) / len(xs), 2) if xs else None

    return {
        "rainfall_mm": round(sum(rain), 1) if rain else None,
        "temperature_mean_c": _avg(tmean),
        "avg_tmax_c": _avg(tmax),
        "avg_tmin_c": _avg(tmin),
        "humidity_mean_pct": _avg(hum),
    }
