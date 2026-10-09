from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Iterable

from .config import (
    ACCLIMATED_LIMITS_C,
    GUST_WARN_KMH,
    RAIN_MM_BLOCK,
    RAIN_PROB_BLOCK,
    TASKS,
    UNACCLIMATED_LIMITS_C,
)
from .wbgt import calculate_wbgt_c


def _state(margin_c: float) -> str:
    if margin_c >= 0:
        return "GO"
    if margin_c >= -2:
        return "EASE"
    if margin_c >= -4:
        return "LIMIT"
    return "STOP"


def _heat_limit(task_intensity: str, new_crew: bool) -> float:
    limits = UNACCLIMATED_LIMITS_C if new_crew else ACCLIMATED_LIMITS_C
    return limits[task_intensity]


def _gates(task_id: str, weather: dict, grap_stage: int = 0) -> list[str]:
    task = TASKS[task_id]
    gates: list[str] = []

    rain_prob = float(weather.get("precipitation_probability") or 0.0)
    precip = float(weather.get("precipitation") or 0.0)
    code = int(weather.get("weather_code") or 0)
    gust = float(weather.get("wind_gusts_10m") or 0.0)

    if task_id in {"concrete", "painting"} and (rain_prob >= RAIN_PROB_BLOCK or precip >= RAIN_MM_BLOCK):
        gates.append("RAIN_BLOCK")

    if task.outdoor and code in {95, 96, 97, 98, 99}:
        gates.append("LIGHTNING_RISK")

    if task_id in {"crane_lift", "work_at_height"} and gust >= GUST_WARN_KMH:
        gates.append("HIGH_GUST")

    if grap_stage >= 3 and task.dust_generating:
        gates.append("GRAP_RESTRICTION")

    return gates


def evaluate_hour(
    task_id: str,
    weather: dict,
    new_crew: bool,
    lat: float,
    lon: float,
    grap_stage: int = 0,
) -> dict:
    task = TASKS[task_id]
    dt = weather["time"]
    temp = weather.get("temperature_2m")
    rh = weather.get("relative_humidity_2m")
    wbgt_c, wbgt_method = calculate_wbgt_c(
        float(temp if temp is not None else 25.0),
        float(rh if rh is not None else 50.0),
        float(weather.get("surface_pressure") or 1013.0),
        float(weather.get("wind_speed_10m") or 0.0) / 3.6,
        float(weather.get("shortwave_radiation") or 0.0),
        float(weather.get("direct_radiation") or 0.0),
        dt,
        lat,
        lon,
    )
    limit = _heat_limit(task.intensity, new_crew)
    margin = limit - wbgt_c
    gates = _gates(task_id, weather, grap_stage=grap_stage)

    if gates:
        state = "STOP"
    elif not task.outdoor:
        # Indoor/shaded task: still expose the WBGT for transparency, but don't
        # automatically stop it on outdoor heat bands.
        state = "GO"
    else:
        state = _state(margin)

    work_rest = {
        "GO": "normal",
        "EASE": "45:15",
        "LIMIT": "30:30",
        "STOP": "swap/reschedule",
    }[state]

    why = []
    if task.outdoor:
        why.append(f"WBGT {wbgt_c:.1f}°C vs {limit:.1f}°C task limit")
    if gates:
        why.extend(gates)
    if not why:
        why.append("No configured gate triggered")

    return {
        "time": dt.isoformat(),
        "task_id": task_id,
        "task": task.label,
        "intensity": task.intensity,
        "wbgt_c": round(wbgt_c, 2),
        "wbgt_method": wbgt_method,
        "limit_c": round(limit, 2),
        "margin_c": round(margin, 2),
        "state": state,
        "work_rest": work_rest,
        "gates": gates,
        "why": why,
    }


def build_matrix(
    weather_rows: Iterable[dict],
    task_ids: list[str],
    new_crew: bool,
    lat: float,
    lon: float,
    grap_stage: int = 0,
) -> list[dict]:
    hours = []
    for weather in weather_rows:
        cells = {}
        for task_id in task_ids:
            cells[task_id] = evaluate_hour(task_id, weather, new_crew, lat, lon, grap_stage=grap_stage)
        hours.append({"time": weather["time"].isoformat(), "tasks": cells})
    return hours


def _dep_depth(tid: str, task_dict: dict) -> int:
    deps = task_dict.get(tid, {}).get("depends_on")
    if deps is None and tid in TASKS:
        deps = TASKS[tid].depends_on
    if not deps:
        return 0
    return 1 + max(_dep_depth(d, task_dict) for d in deps if d in task_dict or d in TASKS)


def schedule_tasks(
    matrix: list[dict],
    tasks: list[dict],
    day_start: int,
    total_crew_size: int = 18,
    max_concurrent_tasks: int = 2,
) -> list[dict]:
    """Advanced multi-constraint scheduler.

    Enforces topological dependency order, multi-crew site capacity,
    parallel task execution bounds, and explainable diagnostics.
    """
    task_map = {t["id"]: t for t in tasks}

    order = sorted(
        tasks,
        key=lambda t: (
            _dep_depth(t["id"], task_map),
            not TASKS[t["id"]].continuous if t["id"] in TASKS else True,
            -{"light": 1, "moderate": 2, "heavy": 3}[TASKS[t["id"]].intensity] if t["id"] in TASKS else 0,
        ),
    )

    result = []
    hourly_crew_used: dict[int, int] = {i: 0 for i in range(len(matrix))}
    hourly_task_count: dict[int, int] = {i: 0 for i in range(len(matrix))}
    scheduled_end_indices: dict[str, int] = {}
    scheduled_end_times_str: dict[str, str] = {}

    for task in order:
        tid = task["id"]
        task_config = TASKS.get(tid)
        duration = int(task.get("duration_h") or (task_config.default_duration_h if task_config else 2))
        outdoor = task_config.outdoor if task_config else True
        
        raw_deps = task.get("depends_on")
        if raw_deps is None and task_config:
            raw_deps = task_config.depends_on
        depends_on = list(raw_deps) if raw_deps else []

        crew_req = int(task.get("crew_required") or (task_config.crew_required if task_config else 4))

        # Check if any prerequisite is unschedulable
        unmet_dep = next((d for d in depends_on if d in task_map and d not in scheduled_end_indices), None)
        if unmet_dep:
            dep_label = TASKS[unmet_dep].label if unmet_dep in TASKS else unmet_dep
            result.append({
                "task_id": tid,
                "task": task_config.label if task_config else tid,
                "status": "UNSCHEDULABLE",
                "why_unschedulable": f"Prerequisite task '{dep_label}' was not scheduled.",
            })
            continue

        min_start_idx = 0
        if depends_on:
            min_start_idx = max(
                (scheduled_end_indices[d] for d in depends_on if d in scheduled_end_indices),
                default=0,
            )

        best = None

        for i in range(min_start_idx, len(matrix) - duration + 1):
            window_idx = list(range(i, i + duration))
            start_dt = datetime.fromisoformat(matrix[window_idx[0]]["time"])
            starts_clock = start_dt.hour * 60 + start_dt.minute

            if starts_clock < day_start:
                continue
            if any(hourly_crew_used[idx] + crew_req > total_crew_size for idx in window_idx):
                continue
            if any(hourly_task_count[idx] >= max_concurrent_tasks for idx in window_idx):
                continue

            cells = [matrix[idx]["tasks"][tid] for idx in window_idx]
            if any(c["state"] == "STOP" for c in cells):
                continue

            if outdoor:
                heat_penalty = sum(max(0.0, -float(c["margin_c"])) for c in cells)
            else:
                heat_penalty = 0.0

            ease_penalty = sum(1.0 for c in cells if c["state"] == "EASE")
            limit_penalty = sum(2.0 for c in cells if c["state"] == "LIMIT")
            start_delay_hours = max(0.0, (starts_clock - day_start) / 60.0)
            cost = heat_penalty + 0.5 * ease_penalty + 1.5 * limit_penalty + 0.05 * start_delay_hours

            candidate = (cost, starts_clock, window_idx, cells)
            if best is None or candidate[:2] < best[:2]:
                best = candidate

        if best is None:
            result.append({
                "task_id": tid,
                "task": task_config.label if task_config else tid,
                "status": "UNSCHEDULABLE",
                "why_unschedulable": "No available shift window meeting heat safety and crew capacity bounds.",
            })
            continue

        cost, starts_clock, idxs, cells = best
        for idx in idxs:
            hourly_crew_used[idx] += crew_req
            hourly_task_count[idx] += 1

        end_idx = idxs[-1] + 1
        scheduled_end_indices[tid] = end_idx

        start_dt = datetime.fromisoformat(matrix[idxs[0]]["time"])
        end_dt = datetime.fromisoformat(matrix[idxs[-1]]["time"]) + timedelta(hours=1)
        start_str = start_dt.strftime("%H:%M")
        end_str = end_dt.strftime("%H:%M")
        scheduled_end_times_str[tid] = end_str

        peak_crew_used = max(hourly_crew_used[idx] for idx in idxs)

        if depends_on:
            dep_names = ", ".join(TASKS[d].label if d in TASKS else d for d in depends_on)
            why_diag = f"Scheduled {start_str}-{end_str} following {dep_names} completion ({peak_crew_used}/{total_crew_size} crew utilized)."
        else:
            why_diag = f"Scheduled {start_str}-{end_str} during optimal thermal window ({peak_crew_used}/{total_crew_size} crew utilized)."

        result.append({
            "task_id": tid,
            "task": task_config.label if task_config else tid,
            "status": "SCHEDULED",
            "start": start_str,
            "end": end_str,
            "cost": round(cost, 2),
            "crew_required": crew_req,
            "worst_state": max(cells, key=lambda c: {"GO": 0, "EASE": 1, "LIMIT": 2, "STOP": 3}[c["state"]])["state"],
            "why_scheduled": why_diag,
        })

    return result

