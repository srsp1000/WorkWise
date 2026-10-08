from datetime import datetime
from zoneinfo import ZoneInfo

from workwise_engine.engine import evaluate_hour


BASE = {
    "time": datetime(2026, 10, 8, 13, 0, tzinfo=ZoneInfo("Asia/Kolkata")),
    "temperature_2m": 42,
    "relative_humidity_2m": 50,
    "surface_pressure": 1000,
    "wind_speed_10m": 10,
    "wind_gusts_10m": 10,
    "shortwave_radiation": 700,
    "direct_radiation": 500,
    "precipitation": 0,
    "precipitation_probability": 0,
    "weather_code": 1,
    "cape": 0,
}


def test_heavy_can_stop_on_heat():
    r = evaluate_hour("concrete", BASE, False, 28.6139, 77.2090)
    assert r["state"] in {"LIMIT", "STOP"}
    assert r["wbgt_c"] > r["limit_c"]


def test_light_indoor_prep_remains_available():
    r = evaluate_hour("material_prep", BASE, False, 28.6139, 77.2090)
    assert r["state"] == "GO"


def test_rain_gate_blocks_concrete():
    x = dict(BASE)
    x["precipitation_probability"] = 80
    r = evaluate_hour("concrete", x, False, 28.6139, 77.2090)
    assert r["state"] == "STOP"
    assert "RAIN_BLOCK" in r["gates"]


def test_lightning_gate_blocks_crane():
    x = dict(BASE)
    x["weather_code"] = 95
    r = evaluate_hour("crane_lift", x, False, 28.6139, 77.2090)
    assert r["state"] == "STOP"
    assert "LIGHTNING_RISK" in r["gates"]


def test_work_at_height_high_gust_gate():
    x = dict(BASE)
    x["wind_gusts_10m"] = 40.0
    r = evaluate_hour("work_at_height", x, False, 28.6139, 77.2090)
    assert r["state"] == "STOP"
    assert "HIGH_GUST" in r["gates"]

