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


def _gates(task_id: str, weather: dict) -> list[str]:
    task = TASKS[task_id]
    gates: list[str] = []

    rain_prob = float(weather.get("precipitation_probability") or 0.0)
    precip = float(weather.get("precipitation") or 0.0)
    code = int(weather.get("weather_code") or 0)
    gust = float(weather.get("wind_gusts_10m") or 0.0)

    if task_id in {"concrete", "painting"} and (rain_prob >= RAIN_PROB_BLOCK or precip >= RAIN_MM_BLOCK):
        gates.append("RAIN_BLOCK")

    if task_id in {"crane_lift", "electrical"} or task_id in {"rebar", "concrete"}:
        if code in {95, 96, 97, 98, 99}:
            gates.append("LIGHTNING_RISK")

    if task_id in {"crane_lift", "work_at_height"} and gust >= GUST_WARN_KMH:
        gates.append("HIGH_GUST")

    return gates


def evaluate_hour(task_id: str, weather: dict, new_crew: bool, lat: float, lon: float) -> dict:
    task = TASKS[task_id]
    dt = weather["time"]
    wbgt_c, wbgt_method = calculate_wbgt_c(
        float(weather["temperature_2m"]),
        float(weather["relative_humidity_2m"]),
        float(weather["surface_pressure"] or 1013.0),
        float(weather["wind_speed_10m"] or 0.0) / 3.6,
        float(weather["shortwave_radiation"] or 0.0),
        float(weather["direct_radiation"] or 0.0),
        dt,
        lat,
        lon,
    )
    limit = _heat_limit(task.intensity, new_crew)
    margin = limit - wbgt_c
    gates = _gates(task_id, weather)

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


def build_matrix(weather_rows: Iterable[dict], task_ids: list[str], new_crew: bool, lat: float, lon: float) -> list[dict]:
    hours = []
    for weather in weather_rows:
        cells = {}
        for task_id in task_ids:
            cells[task_id] = evaluate_hour(task_id, weather, new_crew, lat, lon)
        hours.append({"time": weather["time"].isoformat(), "tasks": cells})
    return hours


def schedule_tasks(matrix: list[dict], tasks: list[dict], day_start: int) -> list[dict]:
    """Greedy feasible scheduler for Phase 1.

    Heavier/continuous tasks are placed first. Cost prioritizes zero-stop,
    low heat exposure, and earlier starts.
    """
    order = sorted(
        tasks,
        key=lambda t: (
            not TASKS[t["id"]].continuous,
            -{"light": 1, "moderate": 2, "heavy": 3}[TASKS[t["id"]].intensity],
        ),
    )

    result = []
    occupied: set[int] = set()

    for task in order:
        tid = task["id"]
        task_config = TASKS[tid]
        duration = int(task.get("duration_h") or task_config.default_duration_h)
        best = None

        for i in range(0, len(matrix) - duration + 1):
            window_idx = list(range(i, i + duration))
            start_dt = datetime.fromisoformat(matrix[window_idx[0]]["time"])
            starts_clock = start_dt.hour * 60 + start_dt.minute

            if starts_clock < day_start:
                continue
            if any(idx in occupied for idx in window_idx):
                continue

            cells = [matrix[idx]["tasks"][tid] for idx in window_idx]
            if any(c["state"] == "STOP" for c in cells):
                continue

            # Indoor tasks are protected from outdoor WBGT heat penalties
            if task_config.outdoor:
                heat_penalty = sum(max(0.0, -float(c["margin_c"])) for c in cells)
            else:
                heat_penalty = 0.0

            ease_penalty = sum(1.0 for c in cells if c["state"] == "EASE")
            limit_penalty = sum(2.0 for c in cells if c["state"] == "LIMIT")
            cost = heat_penalty + 0.5 * ease_penalty + 1.5 * limit_penalty + 0.05 * max(0, starts_clock - day_start)

            candidate = (cost, starts_clock, window_idx, cells)
            if best is None or candidate[:2] < best[:2]:
                best = candidate

        if best is None:
            result.append({"task_id": tid, "task": TASKS[tid].label, "status": "UNSCHEDULABLE"})
            continue

        cost, starts_clock, idxs, cells = best
        occupied.update(idxs)
        start_dt = datetime.fromisoformat(matrix[idxs[0]]["time"])
        end_dt = datetime.fromisoformat(matrix[idxs[-1]]["time"]) + timedelta(hours=1)

        result.append({
            "task_id": tid,
            "task": TASKS[tid].label,
            "status": "SCHEDULED",
            "start": start_dt.strftime("%H:%M"),
            "end": end_dt.strftime("%H:%M"),
            "cost": round(cost, 2),
            "worst_state": max(cells, key=lambda c: {"GO": 0, "EASE": 1, "LIMIT": 2, "STOP": 3}[c["state"]])["state"],
        })

    return result

