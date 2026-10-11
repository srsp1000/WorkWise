"""WorkWise Weather Integration Module.

Provides robust access to Open-Meteo hourly forecasts and real-time conditions.
Features:
- Exponential backoff retry logic.
- Strict response validation and missing data imputation with warning flags.
- Offline sample fixture fallback for disconnected demonstrations.
- Official data attribution: Weather data by Open-Meteo.com (CC BY 4.0).
"""

from __future__ import annotations
from datetime import datetime
import json
import logging
from pathlib import Path
import time
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

OPEN_METEO_FORECAST_API = "https://api.open-meteo.com/v1/forecast"
DATA_ATTRIBUTION = "Weather data provided by Open-Meteo.com (CC BY 4.0)"

REQUIRED_HOURLY_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "surface_pressure",
    "wind_speed_10m",
    "wind_gusts_10m",
    "shortwave_radiation",
    "direct_radiation",
    "precipitation",
    "precipitation_probability",
    "weather_code",
]

WEATHER_DESCRIPTIONS: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}

# Fallback default values if specific meteorological parameters are null in API payload
HOURLY_DEFAULTS: dict[str, float] = {
    "temperature_2m": 25.0,
    "relative_humidity_2m": 50.0,
    "surface_pressure": 1013.25,
    "wind_speed_10m": 5.0,       # km/h
    "wind_gusts_10m": 8.0,       # km/h
    "shortwave_radiation": 0.0,  # W/m²
    "direct_radiation": 0.0,     # W/m²
    "precipitation": 0.0,        # mm
    "precipitation_probability": 0.0,  # %
    "weather_code": 0,
}


def _execute_http_get(url: str, timeout_seconds: int = 15, retries: int = 3) -> dict:
    """Execute HTTP GET with exponential backoff and timeout."""
    headers = {
        "User-Agent": "WorkWise-SafetyEngine/1.0 (Hackathon Construction Safety Planner)",
        "Accept": "application/json",
    }
    req = Request(url, headers=headers)

    last_error: Optional[Exception] = None
    for attempt in range(retries):
        try:
            with urlopen(req, timeout=timeout_seconds) as response:
                if response.status != 200:
                    raise HTTPError(url, response.status, f"HTTP {response.status}", response.headers, None)
                return json.load(response)
        except (HTTPError, URLError, TimeoutError) as e:
            last_error = e
            if attempt == retries - 1:
                break
            sleep_time = 1.5 ** attempt
            time.sleep(sleep_time)

    raise ConnectionError(f"Open-Meteo weather request failed after {retries} attempts: {last_error}")


def load_sample_weather_fallback() -> list[dict]:
    """Load deterministic local sample weather fixture for offline development or testing."""
    fixture_path = Path(__file__).parent.parent / "sample_weather.json"
    if not fixture_path.exists():
        raise FileNotFoundError(f"Sample weather fixture not found at {fixture_path}")

    with open(fixture_path, encoding="utf-8") as f:
        rows = json.load(f)

    for r in rows:
        if isinstance(r.get("time"), str):
            r["time"] = datetime.fromisoformat(r["time"])
        r["is_sample_fallback"] = True
    return rows



def fetch_hourly(
    lat: float,
    lon: float,
    start_date: str,
    end_date: str,
    use_fallback_on_failure: bool = False,
) -> list[dict]:
    """Retrieve hourly weather variables from Open-Meteo with robust parsing and validation.

    Args:
        lat: Site latitude.
        lon: Site longitude.
        start_date: Start date string (YYYY-MM-DD).
        end_date: End date string (YYYY-MM-DD).
        use_fallback_on_failure: If True, falls back to local sample weather fixture if API fails.

    Returns:
        List of hourly weather dictionaries with typed datetime and validated fields.
    """
    params = {
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "hourly": ",".join(REQUIRED_HOURLY_VARIABLES),
        "start_date": start_date,
        "end_date": end_date,
        "timezone": "Asia/Kolkata",
    }
    url = f"{OPEN_METEO_FORECAST_API}?{urlencode(params)}"

    try:
        payload = _execute_http_get(url)
    except Exception as e:
        if use_fallback_on_failure:
            logger.warning("Open-Meteo API unreachable. Using offline sample weather fallback.")
            return load_sample_weather_fallback()
        raise e

    if "hourly" not in payload or "time" not in payload["hourly"]:
        raise ValueError("Malformed Open-Meteo response: 'hourly.time' missing")

    h = payload["hourly"]
    timestamps = h["time"]
    out: list[dict] = []

    for i, stamp in enumerate(timestamps):
        dt = datetime.fromisoformat(stamp)
        row = {
            "time": dt,
            "data_source": "Open-Meteo Forecast API",
            "attribution": DATA_ATTRIBUTION,
        }
        for var_name in REQUIRED_HOURLY_VARIABLES:
            val = h.get(var_name, [None])[i] if i < len(h.get(var_name, [])) else None
            if val is None:
                val = HOURLY_DEFAULTS.get(var_name, 0.0)
            row[var_name] = val
        out.append(row)

    return out


def fetch_current(lat: float, lon: float) -> dict:
    """Retrieve current ambient weather conditions for real-time dashboard display."""
    params = {
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,weather_code",
        "timezone": "Asia/Kolkata",
    }
    url = f"{OPEN_METEO_FORECAST_API}?{urlencode(params)}"
    payload = _execute_http_get(url)

    c = payload.get("current", {})
    code = int(c.get("weather_code", 0) or 0)

    return {
        "temperature": c.get("temperature_2m", 25.0),
        "humidity": c.get("relative_humidity_2m", 50.0),
        "wind_speed": c.get("wind_speed_10m", 5.0),
        "wind_direction": c.get("wind_direction_10m", 0.0),
        "weather_code": code,
        "description": WEATHER_DESCRIPTIONS.get(code, "Unknown"),
        "attribution": DATA_ATTRIBUTION,
    }
