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


from workwise_engine.engine import build_matrix, evaluate_hour, schedule_tasks


def test_lightning_gate_blocks_all_outdoor_tasks():
    x = dict(BASE)
    x["weather_code"] = 95
    for task_id in ["excavation", "brickwork", "rebar", "work_at_height"]:
        r = evaluate_hour(task_id, x, False, 28.6139, 77.2090)
        assert r["state"] == "STOP"
        assert "LIGHTNING_RISK" in r["gates"]


def test_task_dependency_precedence():
    # Construct 6-hour test matrix with mild weather
    rows = []
    for h in range(6, 12):
        r = dict(BASE)
        r["time"] = datetime(2026, 10, 8, h, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        r["temperature_2m"] = 25
        r["shortwave_radiation"] = 100
        r["direct_radiation"] = 50
        rows.append(r)
    
    matrix = build_matrix(rows, ["excavation", "rebar", "concrete"], False, 28.6139, 77.2090)
    tasks = [
        {"id": "concrete", "duration_h": 2},
        {"id": "rebar", "duration_h": 2},
        {"id": "excavation", "duration_h": 2},
    ]
    
    plan = schedule_tasks(matrix, tasks, day_start=6 * 60, total_crew_size=18, max_concurrent_tasks=2)
    sched = {item["task_id"]: item for item in plan}
    
    assert sched["excavation"]["status"] == "SCHEDULED"
    assert sched["rebar"]["status"] == "SCHEDULED"
    assert sched["concrete"]["status"] == "SCHEDULED"
    
    # Excavation (06:00-08:00) -> Rebar (08:00-10:00) -> Concrete (10:00-12:00)
    assert sched["excavation"]["end"] <= sched["rebar"]["start"]
    assert sched["rebar"]["end"] <= sched["concrete"]["start"]
    assert "why_scheduled" in sched["concrete"]


def test_multi_crew_parallel_scheduling():
    rows = []
    for h in range(6, 10):
        r = dict(BASE)
        r["time"] = datetime(2026, 10, 8, h, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        r["temperature_2m"] = 25
        r["shortwave_radiation"] = 100
        r["direct_radiation"] = 50
        rows.append(r)
    
    matrix = build_matrix(rows, ["material_prep", "crane_lift"], False, 28.6139, 77.2090)
    # Non-dependent tasks material_prep (3 crew) and crane_lift (4 crew) can run in parallel if max_concurrent_tasks >= 2
    tasks = [
        {"id": "material_prep", "duration_h": 2, "depends_on": []},
        {"id": "crane_lift", "duration_h": 2, "depends_on": []},
    ]
    
    plan = schedule_tasks(matrix, tasks, day_start=6 * 60, total_crew_size=18, max_concurrent_tasks=2)
    sched = {item["task_id"]: item for item in plan}
    
    assert sched["material_prep"]["status"] == "SCHEDULED"
    assert sched["crane_lift"]["status"] == "SCHEDULED"
    # Both start at 06:00 in parallel
    assert sched["material_prep"]["start"] == "06:00"
    assert sched["crane_lift"]["start"] == "06:00"


def test_crew_capacity_exceeded():
    rows = []
    for h in range(6, 10):
        r = dict(BASE)
        r["time"] = datetime(2026, 10, 8, h, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        r["temperature_2m"] = 25
        rows.append(r)
    
    matrix = build_matrix(rows, ["concrete"], False, 28.6139, 77.2090)
    # Task requiring 25 workers on a site with only 10 workers available
    tasks = [{"id": "concrete", "duration_h": 2, "crew_required": 25, "depends_on": []}]
    
    plan = schedule_tasks(matrix, tasks, day_start=6 * 60, total_crew_size=10, max_concurrent_tasks=2)
    assert plan[0]["status"] == "UNSCHEDULABLE"
    assert "why_unschedulable" in plan[0]


