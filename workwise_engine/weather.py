from __future__ import annotations

from datetime import datetime
from urllib.parse import urlencode
from urllib.request import urlopen
import json


API = "https://api.open-meteo.com/v1/forecast"
HOURLY = [
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
    "cape",
]


def fetch_hourly(lat: float, lon: float, start: str, end: str) -> list[dict]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(HOURLY),
        "start_date": start,
        "end_date": end,
        "timezone": "Asia/Kolkata",
    }
    url = f"{API}?{urlencode(params)}"
    with urlopen(url, timeout=15) as r:
        payload = json.load(r)

    h = payload["hourly"]
    out = []
    for i, stamp in enumerate(h["time"]):
        row = {"time": datetime.fromisoformat(stamp)}
        for k in HOURLY:
            row[k] = h[k][i]
        out.append(row)
    return out
