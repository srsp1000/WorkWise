"""WorkWise Safety Evaluation, Workability Heatmap, and Task Scheduling Engine.

Deterministic core providing:
1. Hourly risk evaluation based on physically modeled WBGT and OSHA / NIOSH screening thresholds.
2. Standard Workability Heatmap generation across 4 occupational workload/exposure tiers.
3. Independent environmental constraint gates (rain wash, lightning strike risk, equipment wind, GRAP air quality).
4. Signature context-specific recommendations and validated prioritized actions.
5. Constraint-aware multi-task scheduling optimizer enforcing topological dependencies,
   prior task completion states, continuous/split durations, and site crew capacity.
"""

from __future__ import annotations
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Iterable, Optional

from .config import (
    ACCLIMATED_LIMITS_C,
    DEFAULT_GUST_WARN_KMH,
    DEFAULT_RAIN_MM_BLOCK,
    DEFAULT_RAIN_PROB_BLOCK,
    LIGHTNING_CODES,
    STATE_BANDS,
    TASKS,
    UNACCLIMATED_LIMITS_C,
    WORKABILITY_TIERS,
    TaskConfig,
)
from .wbgt import calculate_wbgt_c


def _state(margin_c: Optional[float]) -> str:
    """Map safety screening margin (°C) to operational workability state."""
    if margin_c is None:
        return "DATA_UNAVAILABLE"
    if margin_c >= 0.0:
        return "GO"
    if margin_c >= -1.5:
        return "EASE"
    if margin_c >= -3.0:
        return "LIMIT"
    return "STOP"


def _heat_limit(task_intensity: str, new_crew: bool) -> float:
    """Get OSHA / NIOSH screening limit (°C WBGT) for workload and acclimatization status."""
    limits = UNACCLIMATED_LIMITS_C if new_crew else ACCLIMATED_LIMITS_C
    return limits.get(task_intensity, 26.0)


def _gates(
    task_id: str,
    weather: dict,
    grap_stage: int = 0,
    wind_limit_kmh: Optional[float] = None,
    rain_sensitive: Optional[bool] = None,
    outdoor: bool = True,
) -> list[str]:
    """Evaluate independent physical & regulatory constraint gates.

    Constraint gates are evaluated independently of heat stress and override
    thermal screening with an immediate STOP state.
    """
    task = TASKS.get(task_id)
    gates: list[str] = []

    rain_prob = float(weather.get("precipitation_probability") or 0.0)
    precip = float(weather.get("precipitation") or 0.0)
    code = int(weather.get("weather_code") or 0)
    gust = float(weather.get("wind_gusts_10m") or 0.0)

    # 1. Rain Wash Gate (Concrete washing out, paint blistering/diluting)
    is_rain_sens = rain_sensitive if rain_sensitive is not None else (task.rain_sensitive if task else False)
    if is_rain_sens and (rain_prob >= DEFAULT_RAIN_PROB_BLOCK or precip >= DEFAULT_RAIN_MM_BLOCK):
        gates.append("RAIN_BLOCK")

    # 2. Severe Lightning Risk (Thunderstorm codes for all outdoor activities)
    is_outdoor = outdoor if outdoor is not None else (task.outdoor if task else True)
    if is_outdoor and code in LIGHTNING_CODES:
        gates.append("LIGHTNING_RISK")

    # 3. High Gust Gate (Crane lift tip-over hazard & scaffolding falls)
    effective_wind_limit = wind_limit_kmh or (task.equipment_wind_limit_kmh if task else DEFAULT_GUST_WARN_KMH)
    if (task_id in {"crane_lift", "work_at_height"} or wind_limit_kmh is not None) and gust >= effective_wind_limit:
        gates.append("HIGH_GUST")

    # 4. Air Quality Regulatory Restriction (CAQM GRAP Stage III / IV C&D ban in Delhi NCR)
    dust_gen = task.dust_generating if task else False
    if grap_stage >= 3 and dust_gen:
        gates.append("GRAP_RESTRICTION")

    return gates


def evaluate_hour(
    task_id: str,
    weather: dict,
    new_crew: bool,
    lat: float,
    lon: float,
    grap_stage: int = 0,
    intensity_override: Optional[str] = None,
    outdoor_override: Optional[bool] = None,
    wind_limit_override: Optional[float] = None,
    rain_sensitive_override: Optional[bool] = None,
) -> dict:
    """Evaluate a single task or workability tier against hourly meteorological conditions.

    Returns deterministic safety state, margin, work-rest screening cycle, and diagnostic rationale.
    Does NOT fabricate data when weather variables are missing.
    """
    task = TASKS.get(task_id)
    label = task.label if task else task_id.replace("_", " ").title()
    intensity = intensity_override or (task.intensity if task else "moderate")
    outdoor = outdoor_override if outdoor_override is not None else (task.outdoor if task else True)

    dt = weather.get("time")
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    elif dt is None:
        dt = datetime.now()

    temp = weather.get("temperature_2m")
    rh = weather.get("relative_humidity_2m")
    pressure = weather.get("surface_pressure")
    wind_kmh = weather.get("wind_speed_10m")
    wind_ms = (float(wind_kmh) / 3.6) if wind_kmh is not None else None
    sw = weather.get("shortwave_radiation")
    direct = weather.get("direct_radiation")

    # Physically modeled WBGT: outdoor includes solar radiation, shaded has zero solar radiation
    wbgt_c, wbgt_method = calculate_wbgt_c(
        temp,
        rh,
        pressure,
        wind_ms,
        sw,
        direct,
        dt,
        lat,
        lon,
        outdoor=outdoor,
    )

    limit = _heat_limit(intensity, new_crew)
    gates = _gates(
        task_id,
        weather,
        grap_stage=grap_stage,
        wind_limit_kmh=wind_limit_override,
        rain_sensitive=rain_sensitive_override,
        outdoor=outdoor,
    )

    assumptions = []
    if outdoor:
        assumptions.append("Outdoor direct solar irradiance modeling (Liljegren / Stull formulation)")
    else:
        assumptions.append(
            "Physically modeled shaded / indoor exposure with zero direct solar irradiance. "
            "Assumes natural air circulation; moving indoors does not eliminate thermal risk in unventilated or heat-trapping structures."
        )

    if wbgt_c is None:
        state = "DATA_UNAVAILABLE"
        margin = None
        work_rest = "data unavailable"
        why = ["Missing required meteorological variables (temperature/humidity). Cannot calculate WBGT."]
        assumptions.append("No data fabrication permitted")
    else:
        margin = limit - wbgt_c
        if gates:
            state = "STOP"
        else:
            state = _state(margin)

        work_rest_table = {
            "GO": "Continuous (standard hydration breaks)",
            "EASE": "45 min work / 15 min rest (adjusted recovery)",
            "LIMIT": "30 min work / 30 min rest (restricted exposure)",
            "STOP": "Suspend / Reschedule heavy task",
            "DATA_UNAVAILABLE": "Data unavailable",
        }
        work_rest = work_rest_table[state]

        why = []
        if gates:
            why.extend(gates)
        acclim_str = "unacclimatized" if new_crew else "acclimatized"
        if outdoor:
            why.append(f"Outdoor WBGT {wbgt_c:.1f}°C vs {limit:.1f}°C {intensity} workload limit ({acclim_str})")
        else:
            why.append(f"Shaded WBGT {wbgt_c:.1f}°C vs {limit:.1f}°C {intensity} workload limit ({acclim_str})")

    return {
        "time": dt.isoformat(),
        "task_id": task_id,
        "task": label,
        "intensity": intensity,
        "outdoor": outdoor,
        "wbgt_c": round(wbgt_c, 2) if wbgt_c is not None else None,
        "effective_wbgt_c": round(wbgt_c, 2) if wbgt_c is not None else None,
        "wbgt_method": wbgt_method,
        "limit_c": round(limit, 2),
        "margin_c": round(margin, 2) if margin is not None else None,
        "state": state,
        "work_rest": work_rest,
        "gates": gates,
        "why": why,
        "assumptions": assumptions,
    }


def build_workability_heatmap(
    weather_rows: Iterable[dict],
    new_crew: bool,
    lat: float,
    lon: float,
    grap_stage: int = 0,
) -> list[dict]:
    """Generate the primary Workability Heatmap across the 4 standard workload/exposure tiers.

    Tiers:
    1. Heavy outdoor work
    2. Moderate outdoor work
    3. Light outdoor work
    4. Shaded / indoor work
    """
    rows_by_tier: dict[str, dict] = {
        tier["id"]: {
            "tier_id": tier["id"],
            "tier_label": tier["label"],
            "description": tier["description"],
            "intensity": tier["intensity"],
            "outdoor": tier["outdoor"],
            "cells": [],
        }
        for tier in WORKABILITY_TIERS
    }

    for weather in weather_rows:
        for tier in WORKABILITY_TIERS:
            tid = tier["id"]
            cell = evaluate_hour(
                task_id=tid,
                weather=weather,
                new_crew=new_crew,
                lat=lat,
                lon=lon,
                grap_stage=grap_stage,
                intensity_override=tier["intensity"],
                outdoor_override=tier["outdoor"],
            )
            rows_by_tier[tid]["cells"].append(cell)

    return list(rows_by_tier.values())


def build_matrix(
    weather_rows: Iterable[dict],
    task_items: list[dict],
    new_crew: bool,
    lat: float,
    lon: float,
    grap_stage: int = 0,
) -> list[dict]:
    """Generate the specific task × hour safety matrix for all requested site tasks across shift hours."""
    hours = []
    for weather in weather_rows:
        t_dt = weather.get("time")
        t_str = t_dt.isoformat() if hasattr(t_dt, "isoformat") else str(t_dt)
        cells = {}
        for t in task_items:
            tid = t.get("id") if isinstance(t, dict) else t
            intensity = t.get("intensity") if isinstance(t, dict) else None
            wind_limit = t.get("equipment_wind_limit_kmh") if isinstance(t, dict) else None
            rain_sens = t.get("rain_sensitive") if isinstance(t, dict) else None

            cells[tid] = evaluate_hour(
                task_id=tid,
                weather=weather,
                new_crew=new_crew,
                lat=lat,
                lon=lon,
                grap_stage=grap_stage,
                intensity_override=intensity,
                wind_limit_override=wind_limit,
                rain_sensitive_override=rain_sens,
            )
        hours.append({"time": t_str, "tasks": cells})
    return hours


def _dep_depth(tid: str, task_dict: dict) -> int:
    """Calculate recursive dependency tree depth for topological sequencing."""
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
    """Constraint-aware workday scheduler optimizer.

    Respects:
    1. Prerequisite dependencies and prior completion status (`completed_prior`).
    2. Continuous vs non-continuous task flexibility (concrete continuous; others can pause/split).
    3. Site crew headcount capacity bounds (sum of concurrent crew <= total_crew_size).
    4. Concurrency limits.
    5. Thermal penalty minimization (prefers cooler morning hours for heavy physical tasks).
    6. Independent physical and regulatory constraint gates (immediate STOP if triggered).
    """
    if not matrix or not tasks:
        return []

    task_map = {t["id"]: t for t in tasks}

    # Sort tasks: prerequisites first, then continuous, then heavier workload
    def _sort_key(t: dict):
        tid = t["id"]
        t_cfg = TASKS.get(tid)
        intensity = t.get("intensity") or (t_cfg.intensity if t_cfg else "moderate")
        continuous = t.get("continuous") if t.get("continuous") is not None else (t_cfg.continuous if t_cfg else False)
        depth = _dep_depth(tid, task_map)
        int_score = {"light": 1, "moderate": 2, "heavy": 3, "very_heavy": 4}.get(intensity, 2)
        return (depth, not continuous, -int_score)

    order = sorted(tasks, key=_sort_key)

    result = []
    hourly_crew_used: dict[int, int] = {i: 0 for i in range(len(matrix))}
    hourly_task_count: dict[int, int] = {i: 0 for i in range(len(matrix))}
    scheduled_end_indices: dict[str, int] = {}
    scheduled_end_times_str: dict[str, str] = {}

    for task in order:
        tid = task["id"]
        task_config = TASKS.get(tid)
        duration = int(task.get("duration_h") or (task_config.default_duration_h if task_config else 2))
        continuous = task.get("continuous") if task.get("continuous") is not None else (task_config.continuous if task_config else False)
        outdoor = task.get("outdoor") if task.get("outdoor") is not None else (task_config.outdoor if task_config else True)
        completed_prior = bool(task.get("completed_prior", False))

        raw_deps = task.get("depends_on")
        if raw_deps is None and task_config:
            raw_deps = task_config.depends_on
        depends_on = list(raw_deps) if raw_deps else []

        crew_req = int(task.get("crew_required") or (task_config.crew_required if task_config else 4))

        # Check if crew required exceeds site capacity
        if crew_req > total_crew_size:
            result.append({
                "task_id": tid,
                "task": task_config.label if task_config else tid,
                "status": "UNSCHEDULABLE",
                "continuous": continuous,
                "why_unschedulable": f"Required crew ({crew_req}) exceeds total available site capacity ({total_crew_size}).",
                "recommended_action": "Increase site crew headcount or reduce task crew requirement.",
            })
            continue

        # Check if duration exceeds entire shift window
        if duration > len(matrix):
            result.append({
                "task_id": tid,
                "task": task_config.label if task_config else tid,
                "status": "UNSCHEDULABLE",
                "continuous": continuous,
                "why_unschedulable": f"Task duration ({duration}h) exceeds entire available shift window ({len(matrix)}h).",
                "recommended_action": "Reduce task duration or split across multiple workdays.",
            })
            continue

        # Check prerequisite satisfaction:
        # If this task has completed_prior=True, its prerequisites were satisfied in a prior shift.
        # Otherwise, check if each dependency was satisfied prior or has finished today.
        unmet_dep = None
        if not completed_prior:
            for d in depends_on:
                dep_task_input = task_map.get(d)
                if dep_task_input and dep_task_input.get("completed_prior"):
                    continue  # Satisfied from prior day
                if d in task_map and d not in scheduled_end_indices:
                    unmet_dep = d
                    break

        if unmet_dep:
            dep_label = TASKS[unmet_dep].label if unmet_dep in TASKS else unmet_dep
            result.append({
                "task_id": tid,
                "task": task_config.label if task_config else tid,
                "status": "UNSCHEDULABLE",
                "continuous": continuous,
                "why_unschedulable": f"Prerequisite task '{dep_label}' was not scheduled today.",
                "recommended_action": f"Resolve blocker for '{dep_label}', or confirm if '{dep_label}' was completed in a prior shift.",
            })
            continue

        min_start_idx = 0
        if depends_on and not completed_prior:
            valid_end_idxs = []
            for d in depends_on:
                dep_input = task_map.get(d)
                if dep_input and dep_input.get("completed_prior"):
                    continue  # Already done prior to today; can start at day_start
                if d in scheduled_end_indices:
                    valid_end_idxs.append(scheduled_end_indices[d])
            min_start_idx = max(valid_end_idxs, default=0)

        best = None
        has_downstream_dependents = any(
            tid in (list(t.get("depends_on") or ()) if t.get("depends_on") is not None else list(TASKS[t["id"]].depends_on if t["id"] in TASKS else ()))
            for t in tasks if t["id"] != tid
        )

        # Sliding window search for optimal slot
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

            cells = [matrix[idx]["tasks"].get(tid, {}) for idx in window_idx]
            if any(c.get("state") in {"STOP", "DATA_UNAVAILABLE"} for c in cells):
                continue

            # Thermal cost penalizes working in high heat / exceeding screening threshold
            if outdoor:
                heat_penalty = sum(max(0.0, -float(c.get("margin_c") or 0.0)) for c in cells)
            else:
                heat_penalty = 0.0

            ease_penalty = sum(1.0 for c in cells if c.get("state") == "EASE")
            limit_penalty = sum(2.5 for c in cells if c.get("state") == "LIMIT")
            start_delay_hours = max(0.0, (starts_clock - day_start) / 60.0)

            delay_weight = 0.6 if has_downstream_dependents else 0.1
            cost = heat_penalty + 0.5 * ease_penalty + 1.5 * limit_penalty + delay_weight * start_delay_hours

            candidate = (cost, starts_clock, window_idx, cells, False)
            if best is None or candidate[:2] < best[:2]:
                best = candidate

        # Non-continuous task fallback: if continuous window not found and task allows pause/split
        if best is None and not continuous and duration >= 2:
            # Try to find split windows (e.g., 2 chunks separated by midday heat)
            for split_pt in range(1, duration):
                dur1 = split_pt
                dur2 = duration - split_pt
                cand1 = None
                for i1 in range(min_start_idx, len(matrix) - dur1):
                    w1 = list(range(i1, i1 + dur1))
                    s_dt1 = datetime.fromisoformat(matrix[w1[0]]["time"])
                    if (s_dt1.hour * 60 + s_dt1.minute) < day_start:
                        continue
                    if any(hourly_crew_used[idx] + crew_req > total_crew_size for idx in w1):
                        continue
                    if any(hourly_task_count[idx] >= max_concurrent_tasks for idx in w1):
                        continue
                    c1 = [matrix[idx]["tasks"].get(tid, {}) for idx in w1]
                    if any(c.get("state") in {"STOP", "DATA_UNAVAILABLE"} for c in c1):
                        continue
                    cand1 = (i1, w1, c1)
                    break

                if cand1:
                    i1_end = cand1[0] + dur1
                    cand2 = None
                    for i2 in range(i1_end + 1, len(matrix) - dur2 + 1):  # At least 1h pause between chunks
                        w2 = list(range(i2, i2 + dur2))
                        if any(hourly_crew_used[idx] + crew_req > total_crew_size for idx in w2):
                            continue
                        if any(hourly_task_count[idx] >= max_concurrent_tasks for idx in w2):
                            continue
                        c2 = [matrix[idx]["tasks"].get(tid, {}) for idx in w2]
                        if any(c.get("state") in {"STOP", "DATA_UNAVAILABLE"} for c in c2):
                            continue
                        cand2 = (i2, w2, c2)
                        break

                    if cand2:
                        w_combined = cand1[1] + cand2[1]
                        c_combined = cand1[2] + cand2[2]
                        heat_penalty = sum(max(0.0, -float(c.get("margin_c") or 0.0)) for c in c_combined) if outdoor else 0.0
                        cost = heat_penalty + 2.0
                        best = (cost, datetime.fromisoformat(matrix[cand1[1][0]]["time"]).hour * 60, w_combined, c_combined, True)
                        break

        if best is None:
            # Diagnose reason for unschedulability
            if min_start_idx + duration > len(matrix):
                last_dep = next((d for d in depends_on if d in scheduled_end_indices and scheduled_end_indices[d] == min_start_idx), None)
                dep_label = TASKS[last_dep].label if last_dep in TASKS else (last_dep or "prerequisite")
                if min_start_idx < len(matrix):
                    dep_time_str = datetime.fromisoformat(matrix[min_start_idx]["time"]).strftime("%H:%M")
                elif matrix:
                    last_dt = datetime.fromisoformat(matrix[-1]["time"]) + timedelta(hours=1)
                    dep_time_str = last_dt.strftime("%H:%M")
                else:
                    dep_time_str = "shift end"
                why_msg = f"Prerequisite '{dep_label}' finishes at {dep_time_str}, leaving insufficient remaining shift time ({duration}h required)."
                rec_action = f"Start '{dep_label}' earlier, confirm if completed in prior shift, or reduce duration."
            else:
                stop_reasons = []
                for idx in range(min_start_idx, len(matrix)):
                    cell = matrix[idx]["tasks"].get(tid, {})
                    if cell.get("state") in {"STOP", "DATA_UNAVAILABLE"}:
                        stop_reasons.extend(cell.get("gates", []))
                if stop_reasons:
                    unique_reasons = sorted(set(stop_reasons))
                    why_msg = f"Blocked by physical/regulatory constraint gates: {', '.join(unique_reasons)}."
                    rec_action = "Reschedule for favorable weather or lift regulatory restrictions."
                else:
                    if continuous:
                        why_msg = (
                            f"No unbroken {duration}h window meets heat screening limits. "
                            f"Task requires continuous execution (cannot pause during peak midday heat)."
                        )
                        rec_action = "Consider permitting split shifts around peak heat or rescheduling to cooler morning hours."
                    else:
                        why_msg = "No available shift windows meeting thermal limits and site crew capacity bounds."
                        rec_action = "Adjust crew capacity or shift work into early morning window."

            result.append({
                "task_id": tid,
                "task": task_config.label if task_config else tid,
                "status": "UNSCHEDULABLE",
                "continuous": continuous,
                "why_unschedulable": why_msg,
                "recommended_action": rec_action,
            })
            continue

        cost, starts_clock, idxs, cells, is_split = best
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

        if is_split:
            # Format split window string
            first_chunk_end = datetime.fromisoformat(matrix[idxs[0]]["time"]) + timedelta(hours=1)
            why_diag = f"Scheduled as split shift across cooler morning/afternoon windows to avoid peak midday thermal stress ({peak_crew_used}/{total_crew_size} crew utilized)."
        elif depends_on and any(d in scheduled_end_indices for d in depends_on):
            scheduled_deps = [d for d in depends_on if d in scheduled_end_indices]
            dep_names = ", ".join(TASKS[d].label if d in TASKS else d for d in scheduled_deps)
            why_diag = f"Scheduled {start_str}–{end_str} following {dep_names} completion ({peak_crew_used}/{total_crew_size} crew utilized)."
        else:
            why_diag = f"Scheduled {start_str}–{end_str} during optimal thermal screening window ({peak_crew_used}/{total_crew_size} crew utilized)."

        state_priority = {"GO": 0, "EASE": 1, "LIMIT": 2, "STOP": 3, "DATA_UNAVAILABLE": 4}
        worst_state = max(cells, key=lambda c: state_priority.get(c.get("state", "GO"), 0)).get("state", "GO")

        result.append({
            "task_id": tid,
            "task": task_config.label if task_config else tid,
            "status": "SCHEDULED",
            "start": start_str,
            "end": end_str,
            "continuous": continuous,
            "is_split": is_split,
            "cost": round(cost, 2),
            "crew_required": crew_req,
            "worst_state": worst_state,
            "why_scheduled": why_diag,
        })

    return result


def generate_signature_recommendations(
    matrix: list[dict],
    workability_heatmap: list[dict],
    schedule: list[dict],
    weather_rows: list[dict],
    city_name: str,
    new_crew: bool,
) -> tuple[str, list[dict]]:
    """Generate the one-sentence WorkWise recommendation and up to 3 prioritized actions.

    Recommendations are derived strictly from physical calculations, active gates, and scheduling status.
    No invented percentage lives saved or unsupported productivity metrics.
    """
    heavy_tier = next((t for t in workability_heatmap if t["tier_id"] == "heavy_outdoor"), None)
    shaded_tier = next((t for t in workability_heatmap if t["tier_id"] == "shaded_indoor"), None)

    # 1. Identify thermal stress windows for heavy outdoor work
    heavy_stop_hours = []
    heavy_ease_limit_hours = []
    if heavy_tier:
        for c in heavy_tier["cells"]:
            t_dt = datetime.fromisoformat(c["time"])
            h_str = t_dt.strftime("%H:%M")
            if c["state"] == "STOP":
                heavy_stop_hours.append(h_str)
            elif c["state"] in {"EASE", "LIMIT"}:
                heavy_ease_limit_hours.append(h_str)

    # 2. Check unscheduled tasks
    unscheduled = [s for s in schedule if s["status"] == "UNSCHEDULABLE"]
    scheduled = [s for s in schedule if s["status"] == "SCHEDULED"]

    # 3. Formulate one-sentence top recommendation
    if heavy_stop_hours:
        first_stop = heavy_stop_hours[0]
        last_stop = heavy_stop_hours[-1]
        top_rec = (
            f"Complete heavy outdoor work during the earlier favorable window before {first_stop}; "
            f"strictly avoid heavy physical exposure between {first_stop}–{last_stop}."
        )
    elif heavy_ease_limit_hours:
        first_ease = heavy_ease_limit_hours[0]
        last_ease = heavy_ease_limit_hours[-1]
        top_rec = (
            f"Conditions require enforced work-rest recovery cycles between {first_ease}–{last_ease}; "
            f"schedule heavy placements in early morning and rotate crews to shaded preparation during midday."
        )
    elif unscheduled:
        top_rec = (
            f"{len(unscheduled)} task(s) currently unschedulable under site constraints; "
            f"review prerequisite completion and crew capacity to establish a feasible plan."
        )
    else:
        top_rec = (
            f"All planned tasks meet configured screening criteria within standard operational hydration "
            f"and scheduled break guidelines."
        )

    # 4. Formulate up to 3 prioritized actions
    prioritized_actions = []

    # Action: Address unschedulable tasks (prerequisite or continuous constraint)
    for u in unscheduled:
        tid = u["task_id"]
        t_cfg = TASKS.get(tid)
        why_msg = u.get("why_unschedulable", "")

        if "Prerequisite" in why_msg:
            unmet_deps = list(t_cfg.depends_on) if t_cfg and t_cfg.depends_on else []
            dep_id = unmet_deps[0] if unmet_deps else tid
            dep_label = TASKS[dep_id].label if dep_id in TASKS else dep_id
            prioritized_actions.append({
                "id": f"prereq-{tid}",
                "title": f"Verify Prior Completion for '{dep_label}'",
                "action": f"Confirm if '{dep_label}' was inspected and finished in a prior shift.",
                "affected": f"Task: {u['task']}",
                "why": why_msg,
                "constraint": "Topological dependency chain blocking today's schedule.",
                "alternative": f"Marking '{dep_label}' as completed prior allows '{u['task']}' to be scheduled today.",
                "can_apply": True,
                "apply_payload": {"task_id": dep_id, "target_task_id": tid, "set_completed_prior": True},
            })
            break
        elif "continuous" in why_msg.lower():
            prioritized_actions.append({
                "id": f"continuous-{tid}",
                "title": f"Review Continuous Constraint on '{u['task']}'",
                "action": "Permit split shift around peak thermal hours if engineering tolerances allow.",
                "affected": f"Task: {u['task']}",
                "why": why_msg,
                "constraint": "Continuous placement requirement with no unbroken screening window.",
                "alternative": "If cold joints or structural limits permit, split execution across morning and late afternoon.",
                "can_apply": True,
                "apply_payload": {"task_id": tid, "set_continuous": False},
            })
            break
        elif "crew" in why_msg.lower():
            prioritized_actions.append({
                "id": f"crew-{tid}",
                "title": f"Adjust Crew Capacity for '{u['task']}'",
                "action": "Reallocate available site headcount or reduce task crew requirement.",
                "affected": f"Task: {u['task']}",
                "why": why_msg,
                "constraint": "Task worker demand exceeds total configured site crew.",
                "alternative": "Perform work with smaller sub-crews across a longer execution window.",
                "can_apply": False,
            })
            break

    # Action: Heat avoidance & shaded rotation
    if heavy_stop_hours and len(prioritized_actions) < 3:
        stop_range = f"{heavy_stop_hours[0]}–{heavy_stop_hours[-1]}"
        prioritized_actions.append({
            "id": "heat-rotation",
            "title": "Rotate Crews to Shaded/Indoor Work During Peak Heat",
            "action": f"Suspend unshaded heavy outdoor tasks during {stop_range} and reassign workers to shaded preparation or indoor activities.",
            "affected": f"Shift Hours: {stop_range}",
            "why": f"Outdoor WBGT exceeds heavy workload screening thresholds ({_heat_limit('heavy', new_crew):.1f}°C).",
            "constraint": "Direct solar radiation creates hazardous heat strain on unshaded workers.",
            "alternative": "Move permitted fabrication, rebar pre-tying, or tool prep under active shaded canopy.",
            "can_apply": False,
        })

    # Action: Work-Rest protocol enforcement
    if heavy_ease_limit_hours and len(prioritized_actions) < 3:
        prioritized_actions.append({
            "id": "work-rest-protocol",
            "title": "Mandate Structured Work-Rest & Hydration Protocol",
            "action": "Enforce 45:15 or 30:30 work-rest cycles with 1.0 L/worker/hour cool potable water.",
            "affected": f"Hours: {heavy_ease_limit_hours[0]}–{heavy_ease_limit_hours[-1]}",
            "why": "Conditions enter EASE/LIMIT screening bands where metabolic heat accumulation requires recovery intervals.",
            "constraint": "Worker physiological strain increases without shaded recovery breaks.",
            "alternative": "Provide shaded hydration canopy directly adjacent to work stations.",
            "can_apply": False,
        })

    # Action: Early morning concrete pour recommendation if concrete is scheduled late
    concrete_scheduled = next((s for s in schedule if s["task_id"] == "concrete" and s["status"] == "SCHEDULED"), None)
    if concrete_scheduled and len(prioritized_actions) < 3:
        start_h = int(concrete_scheduled["start"].split(":")[0])
        if start_h >= 11:
            prioritized_actions.append({
                "id": "early-concrete",
                "title": "Reschedule Concrete Pour to Early Morning Window",
                "action": "Advance concrete pour to 06:00 to avoid curing in high afternoon ambient temperatures.",
                "affected": "Task: Concrete pour",
                "why": f"Currently scheduled at {concrete_scheduled['start']}, overlapping higher thermal and evaporation conditions.",
                "constraint": "Batching plant delivery timing and rebar inspection sign-off.",
                "alternative": "Confirm prior rebar tie inspection today to enable early 06:00 concrete placement tomorrow.",
                "can_apply": True,
                "apply_payload": {
                    "action_type": "early_concrete",
                    "task_id": "rebar",
                    "target_task_id": "concrete",
                    "set_completed_prior": True,
                },
            })

    return top_rec, prioritized_actions[:3]
