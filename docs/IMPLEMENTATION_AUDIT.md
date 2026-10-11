# WorkWise — Implementation Audit & Failure Diagnostics

**Date:** 2026-10-11  
**Target:** WorkWise Construction Workability & Scheduling Assistant  
**Auditor:** WorkWise Engineering Team  
**Status:** Phase A Audit Complete — Baseline Findings  

---

## 1. Executive Summary

This audit thoroughly investigates the current React frontend, Python safety engine (`workwise_engine`), weather client, task configuration, scenario fixtures, and automated test suite. 

The application currently has a solid foundation for physical WBGT modeling (Liljegren 2008 & Stull 2011) and constraint gates. However, the existing scheduling pipeline and user interface suffer from architectural flaws:
1. **False scheduling failures** caused by inappropriate continuous-work assumptions and rigid sequential prerequisite chains.
2. **UI hierarchy inversion**, where the Plan screen prioritizes dark dashboard cards, Gantt bars, and client-side statistical percentages over the primary decision tool: the **Workability Heatmap**.
3. **Client-side calculation drift**, where the frontend calculates its own "safe percentages" and heuristic time windows rather than reflecting authoritative backend engine outputs.
4. **Missing-data fabrication**, where absent weather inputs default silently to 25°C instead of exposing an explicit missing-data state.

---

## 2. Root Cause Analysis: Why Sample Tasks Report as Unschedulable

In sample runs (`demo.py` / `phase1_output.json`), tasks such as **Brickwork** consistently report as `UNSCHEDULABLE`:
```json
{
  "task_id": "brickwork",
  "task": "Brickwork",
  "status": "UNSCHEDULABLE",
  "why_unschedulable": "Prerequisite 'Concrete pour' finishes at 17:00, leaving insufficient remaining shift time (3h required).",
  "recommended_action": "Start 'Concrete pour' earlier or reduce shift duration of Brickwork."
}
```

Our technical investigation reveals five distinct root causes that explain scheduling failures across different conditions:

### Root Cause 1: Rigid Same-Day Prerequisite Chains vs Real Construction Reality
- **Current logic:** `config.py` hardcodes `concrete -> rebar -> excavation` and `brickwork -> concrete -> painting`. In `demo.py`, 4 selected tasks (`material_prep`, `rebar` (4h), `concrete` (3h), `brickwork` (3h)) create a sequential dependency: `rebar` (4h) + `concrete` (3h) + `brickwork` (3h) = 10 sequential hours.
- **Physical/operational flaw:** In actual construction, masonry brickwork is **never** laid on freshly poured wet concrete on the same afternoon; concrete requires curing time (24 hours to 28 days). Brickwork scheduled on a given workday is typically situated on an already cured slab, or in a different structural zone.
- **Missing feature:** The engine lacked a mechanism to indicate that a prerequisite task was **already completed** in a prior shift or applies to a separate site zone. Consequently, selecting both Concrete and Brickwork forced an artificial 10-hour same-day critical path that left zero buffer within a 12-hour shift (06:00–18:00).

### Root Cause 2: Inappropriate "Continuous Work" Constraints
- **Current logic:** `config.py` flags `continuous: True` on almost every task (`rebar`, `brickwork`, `painting`, `excavation`, `crane_lift`, `work_at_height`). In `engine.py`, the sliding window optimizer mandates a single unbroken block of consecutive hours:
  ```python
  window_idx = list(range(i, i + duration))
  if any(c["state"] == "STOP" for c in cells):
      continue
  ```
- **Operational reality:** Only **concrete pouring** has an immutable engineering constraint requiring uninterrupted placement (to prevent cold joints). In contrast, tasks like rebar tying, bricklaying, and painting can easily be paused during midday peak thermal stress (e.g., 12:00–14:00) and resumed in cooler afternoon hours (15:00–18:00), or paused while crews rotate into shaded material prep.
- **Impact:** When midday hours hit `STOP`, any task with `duration_h >= 3` that is marked `continuous: True` fails to find a continuous window, even when there are 6+ hours of workable conditions across the shift.

### Root Cause 3: Midday Heat Penalties and Cascading Delays
- In `demo.py`, `rebar` was scheduled 06:00–10:00 (4h). 
- At 10:00, outdoor WBGT reached 28.2°C (heavy work limit is 26.0°C, so `LIMIT` state with safety margin -2.19°C).
- Between 10:00 and 13:00, WBGT peaked at 29.6°C. Because `rebar` occupied the morning slot (06:00–10:00), `concrete` could only start at 10:00 or later.
- The optimizer calculated that starting `concrete` at 10:00 had a higher thermal penalty than starting at 14:00 (when solar radiation begins dropping). Thus, `concrete` was placed at 14:00–17:00.
- This left only 1 hour (17:00–18:00) before shift end at 18:00. Since `brickwork` required 3 hours, it was marked `UNSCHEDULABLE` due to shift-window truncation.

### Root Cause 4: Crew-Count Arithmetic & Max Concurrency Bottlenecks
- In `engine.py`, each task checks:
  ```python
  if crew_req > total_crew_size:  # Immediate failure
  if any(hourly_crew_used[idx] + crew_req > total_crew_size for idx in window_idx): continue
  if any(hourly_task_count[idx] >= max_concurrent_tasks for idx in window_idx): continue
  ```
- If a site supervisor sets total crew to 10 workers, and concrete requires 8 while brickwork requires 5:
  - Concrete + Brickwork = 13 > 10 workers. They cannot overlap at all.
  - Furthermore, `max_concurrent_tasks` defaults to 2. Even on a large site with 40 workers, the scheduler artificially forbids running 3 light/moderate tasks concurrently in the morning.

### Root Cause 5: Regulatory Environmental Gates (GRAP & Weather)
- In the `smog_grap3` scenario, CAQM GRAP Stage III is active.
- `engine.py` evaluates:
  ```python
  if grap_stage >= 3 and task.dust_generating:
      gates.append("GRAP_RESTRICTION")
  ```
- `concrete`, `brickwork`, and `excavation` are flagged `dust_generating: True`. They are immediately assigned `STOP` for all 24 hours of the day.
- In `cloudburst.json`, severe thunderstorm codes (95, 96) and high precipitation (>0.5 mm/h or prob >= 50%) trigger `LIGHTNING_RISK` and `RAIN_BLOCK`.
- These are legitimate safety blocks, but supervisors need clear diagnostic differentiation between regulatory pollution bans, weather washouts, and thermal capacity limits.

---

## 3. Systematic Checklist Audit

| Audit Area | Findings | Remediation Required |
| :--- | :--- | :--- |
| **1. Task Prerequisite Correctness** | Hardcoded chains (`rebar` -> `concrete` -> `brickwork`) create unrealistic same-day critical paths. | Allow explicit dependency configuration and marking prerequisites as "Already Completed". |
| **2. Prerequisite Selection State** | If prerequisite is not selected today, engine allows task to proceed, but offers no supervisor verification for whether prior work was inspected. | Support explicit prerequisite status: `Completed Prior`, `Scheduled Today`, `None/Independent`. |
| **3. Continuous Work Assumptions** | 6 of 8 tasks flagged `continuous: True`. Tasks cannot split across peak heat hours. | Only `concrete` should be strictly continuous by default. Allow non-continuous tasks to pause and resume. |
| **4. Crew-Count Arithmetic** | Concurrency strictly capped at 2 tasks regardless of crew size. Crew sums checked per hour correctly but lack flexible multi-crew rotation. | Make concurrency responsive to site capacity and allow task crew sizing adjustments. |
| **5. Work/Rest Calculations** | `work_rest` cycle ("45:15", "30:30") is reported as text but does not adjust task duration or effective output. | Incorporate work-rest rest allowances into scheduling windows and explicit recommendation copy. |
| **6. Threshold Configuration** | NIOSH 2016 REL (acclimatized: 26/28/30°C) and RAL (unacclimatized: 24/26/28°C) are well-sourced. STOP margin threshold (-4°C) is sensible. | Retain versioned thresholds. Add clear documentation that IMD heatwave criteria serve as meteorological context, not occupational limits. |
| **7. Scenario Consistency** | Pre-configured scenarios (`normal`, `heatwave`, `cloudburst`, `smog_grap3`) have valid time series. Missing specific Indian summer dry heat vs humid monsoon cases. | Refine scenarios to cover: May North India Dry Heat (45°C), Coastal Monsoon (34°C, 85% RH), Lightning/Rain, High Wind, and Missing Data. |
| **8. Weather Input Alignment** | Backend uses identical weather rows for matrix and scheduler. However, SetupPage `WeatherDashboard` fetches current weather independently of selected scenario. | Align weather context on Plan screen with the exact plan payload (scenario or target date). |
| **9. Displayed Value Provenance** | Frontend computes `safePercentage`, `optimalWindowText`, and `heatAvoidanceText` in TypeScript, duplicating engine logic. | All plan recommendations, optimal windows, and state metrics must originate deterministically from the backend. |

---

## 4. UI/UX & Field Operations Gap Analysis

1. **Dashboard Overload:** Current UI uses heavy dark glassmorphism, glowing borders, and card-heavy layouts that are difficult to read under harsh sunlight on Indian construction sites.
2. **Heatmap Demoted:** The Workability Heatmap is buried under banner statistics, rest cards, and Gantt charts. The brief requires the **Workability Heatmap as the main feature (Primary Experience)**.
3. **Heatmap Rows:** Currently rows are individual task IDs. The brief specifies that the primary heatmap rows must be the **4 Workability Tiers**:
   - Heavy outdoor work
   - Moderate outdoor work
   - Light outdoor work
   - Shaded/indoor work (with documented -4°C attenuation)
4. **Recommendations Missing Signature Presence:** Recommendations must appear as:
   - One concise recommendation **above** the heatmap.
   - Up to three prioritised actions **below** the heatmap with explanations (What, Which task/hours, Why, Constraints, Alternatives, and an "Apply recommendation" action).
5. **Aesthetics:** Transition to a clean, warm-neutral/light field-operations theme with strong typography, high contrast, legible badges, and zero decorative AI fluff.

---

## 5. Architectural Action Plan

1. **Safety Engine & Scheduler (`engine.py`, `config.py`):**
   - Refactor task defaults: make `concrete` the sole continuous task; allow `brickwork`, `rebar`, `painting` to split across high-heat hours if needed.
   - Add prerequisite status support: enable marking prerequisites as already completed.
   - Add first-class Workability Heatmap generation for the 4 standard intensity tiers across the shift.
   - Implement missing-data detection: if critical weather variables are null, return explicit `DATA_UNAVAILABLE` rather than fabricating values.
   - Implement signature recommendation engine: generate the single top recommendation and 3 prioritized actions with structured fields.
2. **API Contract (`api.py`, `types/api.ts`):**
   - Extend `PlanResponseModel` with `workability_heatmap` (4 tiers × shift hours), `top_recommendation`, and `prioritized_actions`.
3. **Frontend Re-Architecture (`frontend/src/`):**
   - Redesign `PlanPage.tsx` following the exact Phase F hierarchy:
     1. Compact site/time/weather context banner.
     2. One-sentence WorkWise recommendation.
     3. Large, legible Workability Heatmap (4 tiers, clear GO/EASE/LIMIT/STOP badges).
     4. Three prioritised recommended actions with "Apply recommendation" triggers.
     5. Proposed construction work schedule (Gantt timeline + task cards).
     6. Task diagnostics & explainability panel (tap-to-explain modal).
   - Apply warm neutral / light field-operations styling with crisp typography and high sunlight contrast in `index.css`.
   - Update `VoiceBrief.tsx` and `BriefPage.tsx` to align with the revised plan contract.
4. **Verification & Testing (`test_engine.py`, `test_api.py`):**
   - Comprehensive test suite covering ordinary weather, dry heat, hot/humid monsoon, severe heat, unacclimatized crew, missing weather, lightning/rain, wind limits, GRAP bans, prerequisite completion, crew constraints, impossible schedules, and non-continuous task execution.
