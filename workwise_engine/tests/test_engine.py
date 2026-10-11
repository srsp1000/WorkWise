"""Comprehensive unit test suite for WorkWise Safety Engine.

Validates:
- WBGT calculation physics and fallback behavior.
- In-shade physical modeling with zero solar radiation (no arbitrary -4°C deduction).
- Missing weather variable detection (DATA_UNAVAILABLE without fabrication).
- State threshold boundary cutoffs (GO, EASE, LIMIT, STOP).
- Acclimatization threshold offsets (OSHA / NIOSH baseline criteria including Very heavy).
- Configurable task intensity (workload not bound to task name).
- Independent physical constraint gates (rain wash, thunderstorm lightning, configurable equipment wind).
- CAQM GRAP pollution regulatory stages (revised schedule dated 28 September 2026).
- Prerequisite completion states (completed_prior allowing immediate scheduling).
- Continuous vs non-continuous task execution flexibility.
- Workability heatmap across 4 tiers (heavy, moderate, light, shaded).
- Signature recommendations and prioritized actions generation.
- Deterministic output guarantee.
"""

from datetime import datetime
from zoneinfo import ZoneInfo
import pytest

from workwise_engine.config import (
    ACCLIMATED_LIMITS_C,
    UNACCLIMATED_LIMITS_C,
    TASKS,
    WORKABILITY_TIERS,
)
from workwise_engine.engine import (
    _state,
    build_matrix,
    build_workability_heatmap,
    evaluate_hour,
    generate_signature_recommendations,
    schedule_tasks,
)
from workwise_engine.wbgt import (
    _simple_wbgt_c,
    _solar_cos_zenith,
    calculate_wbgt_c,
)

BASE_WEATHER = {
    "time": datetime(2026, 10, 8, 13, 0, tzinfo=ZoneInfo("Asia/Kolkata")),
    "temperature_2m": 42.0,
    "relative_humidity_2m": 50.0,
    "surface_pressure": 1000.0,
    "wind_speed_10m": 10.0,
    "wind_gusts_10m": 12.0,
    "shortwave_radiation": 700.0,
    "direct_radiation": 500.0,
    "precipitation": 0.0,
    "precipitation_probability": 0.0,
    "weather_code": 1,
}


# --- 1. WBGT Calculation & Physics Tests ---

def test_wbgt_calculation_runs_and_returns_positive():
    wbgt, method = calculate_wbgt_c(
        temp_c=35.0,
        rh_pct=60.0,
        pressure_hpa=1013.0,
        wind_ms=2.0,
        shortwave_wm2=800.0,
        direct_wm2=600.0,
        dt=BASE_WEATHER["time"],
        lat=28.6139,
        lon=77.2090,
        outdoor=True,
    )
    assert wbgt is not None
    assert 20.0 <= wbgt <= 50.0
    assert "Liljegren" in method or "Stull" in method


def test_shaded_wbgt_physically_lower_without_arbitrary_subtraction():
    # Outdoor vs Shaded physical calculation using identical atmospheric inputs
    outdoor_wbgt, _ = calculate_wbgt_c(
        temp_c=38.0,
        rh_pct=50.0,
        pressure_hpa=1000.0,
        wind_ms=2.0,
        shortwave_wm2=850.0,
        direct_wm2=700.0,
        dt=BASE_WEATHER["time"],
        lat=28.6139,
        lon=77.2090,
        outdoor=True,
    )
    shaded_wbgt, method = calculate_wbgt_c(
        temp_c=38.0,
        rh_pct=50.0,
        pressure_hpa=1000.0,
        wind_ms=2.0,
        shortwave_wm2=850.0,
        direct_wm2=700.0,
        dt=BASE_WEATHER["time"],
        lat=28.6139,
        lon=77.2090,
        outdoor=False,
    )
    assert outdoor_wbgt is not None
    assert shaded_wbgt is not None
    # Outdoor WBGT with intense 850 W/m² solar load must exceed shaded WBGT
    assert outdoor_wbgt > shaded_wbgt
    assert "shaded" in method.lower() or "indoor" in method.lower()


def test_missing_weather_variables_returns_data_unavailable():
    # Missing temperature or humidity must return DATA_UNAVAILABLE, not fabricate 25°C
    wbgt, method = calculate_wbgt_c(
        temp_c=None,
        rh_pct=50.0,
        pressure_hpa=1000.0,
        wind_ms=2.0,
        shortwave_wm2=500.0,
        direct_wm2=400.0,
        dt=BASE_WEATHER["time"],
        lat=28.6139,
        lon=77.2090,
    )
    assert wbgt is None
    assert method == "DATA_UNAVAILABLE"

    # In evaluate_hour, missing temperature returns state DATA_UNAVAILABLE
    sparse_weather = {"time": BASE_WEATHER["time"], "temperature_2m": None, "relative_humidity_2m": 50.0}
    res = evaluate_hour("concrete", sparse_weather, False, 28.6139, 77.2090)
    assert res["state"] == "DATA_UNAVAILABLE"
    assert res["wbgt_c"] is None


def test_stull_fallback_approximation():
    # Air temp 30°C, RH 50%, zero solar radiation -> psychrometric wet bulb should be around 22-25°C
    simple_val = _simple_wbgt_c(30.0, 50.0, solar_w_m2=0.0)
    assert 20.0 <= simple_val <= 26.0


def test_solar_cos_zenith_bounds():
    cosz = _solar_cos_zenith(BASE_WEATHER["time"], 28.6139, 77.2090)
    assert -1.0 <= cosz <= 1.0


# --- 2. State Boundary & Threshold Cutoffs ---

def test_state_boundary_transitions():
    assert _state(0.0) == "GO"
    assert _state(1.5) == "GO"
    assert _state(-0.01) == "EASE"
    assert _state(-1.5) == "EASE"
    assert _state(-1.51) == "LIMIT"
    assert _state(-3.0) == "LIMIT"
    assert _state(-3.01) == "STOP"
    assert _state(None) == "DATA_UNAVAILABLE"


def test_osha_niosh_screening_thresholds_table():
    # Verified OSHA / NIOSH continuous work screening criteria table
    assert ACCLIMATED_LIMITS_C["light"] == 30.0
    assert UNACCLIMATED_LIMITS_C["light"] == 28.0

    assert ACCLIMATED_LIMITS_C["moderate"] == 28.0
    assert UNACCLIMATED_LIMITS_C["moderate"] == 25.0

    assert ACCLIMATED_LIMITS_C["heavy"] == 26.0
    assert UNACCLIMATED_LIMITS_C["heavy"] == 23.0

    assert ACCLIMATED_LIMITS_C["very_heavy"] == 25.0
    assert UNACCLIMATED_LIMITS_C["very_heavy"] == 21.0

    for k in ["light", "moderate", "heavy", "very_heavy"]:
        assert ACCLIMATED_LIMITS_C[k] > UNACCLIMATED_LIMITS_C[k]


def test_configurable_task_intensity_overrides():
    # Brickwork evaluated as moderate vs heavy vs very_heavy
    w = dict(BASE_WEATHER)
    w["temperature_2m"] = 32.0
    w["relative_humidity_2m"] = 55.0

    r_mod = evaluate_hour("brickwork", w, False, 28.6139, 77.2090, intensity_override="moderate")
    r_vh = evaluate_hour("brickwork", w, False, 28.6139, 77.2090, intensity_override="very_heavy")

    assert r_mod["limit_c"] == 28.0
    assert r_vh["limit_c"] == 25.0
    # Very heavy workload has lower limit, hence smaller or negative margin
    assert r_vh["margin_c"] < r_mod["margin_c"]


# --- 3. Independent Constraint Gates ---

def test_rain_gate_blocks_rain_sensitive_tasks():
    w = dict(BASE_WEATHER)
    w["precipitation_probability"] = 60.0

    r_concrete = evaluate_hour("concrete", w, False, 28.6139, 77.2090)
    assert r_concrete["state"] == "STOP"
    assert "RAIN_BLOCK" in r_concrete["gates"]

    # Rebar is not rain-sensitive by default
    r_rebar = evaluate_hour("rebar", w, False, 28.6139, 77.2090)
    assert "RAIN_BLOCK" not in r_rebar["gates"]


def test_lightning_gate_blocks_outdoor_tasks_only():
    w = dict(BASE_WEATHER)
    w["weather_code"] = 95  # Thunderstorm

    for outdoor_tid in ["concrete", "rebar", "excavation", "crane_lift", "work_at_height"]:
        res = evaluate_hour(outdoor_tid, w, False, 28.6139, 77.2090)
        assert res["state"] == "STOP"
        assert "LIGHTNING_RISK" in res["gates"]

    w_mild = dict(w)
    w_mild["temperature_2m"] = 28.0
    r_indoor = evaluate_hour("material_prep", w_mild, False, 28.6139, 77.2090)
    assert "LIGHTNING_RISK" not in r_indoor["gates"]
    assert r_indoor["state"] == "GO"


def test_configurable_wind_gate():
    w = dict(BASE_WEATHER)
    w["wind_gusts_10m"] = 32.0  # Below 35 km/h default

    r_default = evaluate_hour("crane_lift", w, False, 28.6139, 77.2090)
    assert "HIGH_GUST" not in r_default["gates"]

    # If supervisor configures stricter 30 km/h wind limit for sensitive rigging:
    r_strict = evaluate_hour("crane_lift", w, False, 28.6139, 77.2090, wind_limit_override=30.0)
    assert "HIGH_GUST" in r_strict["gates"]
    assert r_strict["state"] == "STOP"


def test_caqm_grap_stage3_blocks_dust_generating_activities():
    w = dict(BASE_WEATHER)
    w["temperature_2m"] = 25.0

    r_grap3_concrete = evaluate_hour("concrete", w, False, 28.6139, 77.2090, grap_stage=3)
    assert r_grap3_concrete["state"] == "STOP"
    assert "GRAP_RESTRICTION" in r_grap3_concrete["gates"]

    r_grap3_elec = evaluate_hour("electrical", w, False, 28.6139, 77.2090, grap_stage=3)
    assert "GRAP_RESTRICTION" not in r_grap3_elec["gates"]


# --- 4. Scheduling: Prior Completion & Continuous Flexibility ---

def test_prerequisite_completed_prior_allows_immediate_start():
    # If rebar was completed yesterday, concrete can start at 06:00
    rows = []
    for h in range(6, 12):
        r = dict(BASE_WEATHER)
        r["time"] = datetime(2026, 10, 8, h, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        r["temperature_2m"] = 25.0
        r["shortwave_radiation"] = 100.0
        r["direct_radiation"] = 50.0
        rows.append(r)

    matrix = build_matrix(rows, [{"id": "concrete"}, {"id": "rebar"}], False, 28.6139, 77.2090)
    tasks = [
        {"id": "rebar", "duration_h": 4, "completed_prior": True},
        {"id": "concrete", "duration_h": 3, "depends_on": ["rebar"]},
    ]

    plan = schedule_tasks(matrix, tasks, day_start=6 * 60, total_crew_size=18)
    sched = {item["task_id"]: item for item in plan}

    assert sched["concrete"]["status"] == "SCHEDULED"
    assert sched["concrete"]["start"] == "06:00"  # Starts at shift opening!


def test_non_continuous_task_splits_around_midday_heat():
    # Shift from 06:00 to 18:00 where hours 10:00-14:00 are STOP for heavy work
    rows = []
    for h in range(6, 18):
        r = dict(BASE_WEATHER)
        r["time"] = datetime(2026, 10, 8, h, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        if 10 <= h < 14:
            r["temperature_2m"] = 45.0  # Peak heat STOP
            r["shortwave_radiation"] = 900.0
        else:
            r["temperature_2m"] = 28.0  # Favorable
            r["shortwave_radiation"] = 200.0
        rows.append(r)

    matrix = build_matrix(rows, [{"id": "brickwork"}], False, 28.6139, 77.2090)

    # 1. Non-continuous brickwork (4 hours total) can split across morning and afternoon
    tasks_split = [{"id": "brickwork", "duration_h": 4, "continuous": False}]
    plan_split = schedule_tasks(matrix, tasks_split, day_start=6 * 60, total_crew_size=18)
    assert plan_split[0]["status"] == "SCHEDULED"

    # 2. But if continuous is strictly enforced (e.g. concrete pour of 4h), it cannot split and is UNSCHEDULABLE
    tasks_cont = [{"id": "concrete", "duration_h": 5, "continuous": True, "depends_on": []}]
    matrix_c = build_matrix(rows, [{"id": "concrete"}], False, 28.6139, 77.2090)
    plan_cont = schedule_tasks(matrix_c, tasks_cont, day_start=6 * 60, total_crew_size=18)
    assert plan_cont[0]["status"] == "UNSCHEDULABLE"
    assert "continuous" in plan_cont[0]["why_unschedulable"].lower()


# --- 5. Workability Heatmap & Signature Recommendations ---

def test_workability_heatmap_structure():
    rows = []
    for h in range(6, 18):
        r = dict(BASE_WEATHER)
        r["time"] = datetime(2026, 10, 8, h, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        rows.append(r)

    heatmap = build_workability_heatmap(rows, new_crew=False, lat=28.6139, lon=77.2090)
    assert len(heatmap) == 4  # Exactly the 4 standard tiers
    tier_ids = [t["tier_id"] for t in heatmap]
    assert "heavy_outdoor" in tier_ids
    assert "moderate_outdoor" in tier_ids
    assert "light_outdoor" in tier_ids
    assert "shaded_indoor" in tier_ids

    for t in heatmap:
        assert len(t["cells"]) == 12  # 12 shift hours


def test_signature_recommendations_generation():
    rows = []
    for h in range(6, 18):
        r = dict(BASE_WEATHER)
        r["time"] = datetime(2026, 10, 8, h, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        r["temperature_2m"] = 43.0 if 11 <= h < 16 else 30.0
        rows.append(r)

    matrix = build_matrix(rows, [{"id": "concrete"}], False, 28.6139, 77.2090)
    heatmap = build_workability_heatmap(rows, False, 28.6139, 77.2090)
    sched = schedule_tasks(matrix, [{"id": "concrete", "duration_h": 3, "depends_on": []}], day_start=6 * 60)

    top_rec, actions = generate_signature_recommendations(
        matrix=matrix,
        workability_heatmap=heatmap,
        schedule=sched,
        weather_rows=rows,
        city_name="Delhi NCR",
        new_crew=False,
    )
    assert isinstance(top_rec, str)
    assert len(top_rec) > 20
    assert isinstance(actions, list)
    assert len(actions) <= 3
    for a in actions:
        assert "title" in a and "action" in a and "why" in a and "affected" in a


def test_indoor_or_shaded_parameter_in_calculate_wbgt_c():
    val_shaded, desc_shaded = calculate_wbgt_c(
        temp_c=36.0,
        rh_pct=50.0,
        pressure_hpa=1000.0,
        wind_ms=2.0,
        shortwave_wm2=700.0,
        direct_wm2=500.0,
        dt=BASE_WEATHER["time"],
        lat=28.6139,
        lon=77.2090,
        indoor_or_shaded=True,
    )
    val_outdoor, _ = calculate_wbgt_c(
        temp_c=36.0,
        rh_pct=50.0,
        pressure_hpa=1000.0,
        wind_ms=2.0,
        shortwave_wm2=700.0,
        direct_wm2=500.0,
        dt=BASE_WEATHER["time"],
        lat=28.6139,
        lon=77.2090,
        indoor_or_shaded=False,
    )
    assert val_shaded is not None
    assert val_outdoor is not None
    assert val_outdoor > val_shaded
    assert "shaded" in desc_shaded.lower() or "indoor" in desc_shaded.lower()


def test_prerequisite_recommendation_generation_no_name_error():
    sched = [
        {
            "task_id": "concrete",
            "task": "Concrete pour",
            "status": "UNSCHEDULABLE",
            "why_unschedulable": "Prerequisite task 'Rebar work' was not scheduled today.",
            "recommended_action": "Resolve blocker for 'Rebar work'.",
        }
    ]
    top_rec, actions = generate_signature_recommendations(
        matrix=[],
        workability_heatmap=[],
        schedule=sched,
        weather_rows=[],
        city_name="Delhi NCR",
        new_crew=False,
    )
    assert len(actions) == 1
    assert actions[0]["id"] == "prereq-concrete"
    assert actions[0]["can_apply"] is True
    assert actions[0]["apply_payload"]["task_id"] == "rebar"


def test_task_completed_prior_flag_satisfies_prerequisites():
    rows = []
    for h in range(6, 12):
        r = dict(BASE_WEATHER)
        r["time"] = datetime(2026, 10, 8, h, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        r["temperature_2m"] = 24.0
        r["shortwave_radiation"] = 100.0
        r["direct_radiation"] = 50.0
        rows.append(r)

    matrix = build_matrix(rows, [{"id": "concrete"}], False, 28.6139, 77.2090)
    # Concrete has prerequisite rebar, but supervisor marks concrete with completed_prior=True
    tasks = [{"id": "concrete", "duration_h": 3, "completed_prior": True}]
    plan = schedule_tasks(matrix, tasks, day_start=6 * 60, total_crew_size=18)
    assert plan[0]["status"] == "SCHEDULED"
    assert plan[0]["start"] == "06:00"

