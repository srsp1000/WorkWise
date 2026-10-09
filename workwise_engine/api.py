from datetime import date, datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Path as APIPath
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import GRAP_STAGES, TASKS
from .engine import build_matrix, schedule_tasks
from .scenarios import list_scenarios, load_scenario_rows
from .weather import fetch_hourly


app = FastAPI(
    title="WorkWise Safety Engine API",
    description="Climate-aware construction work scheduling & WBGT safety engine API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TaskItem(BaseModel):
    id: str = Field(..., json_schema_extra={"example": "concrete"}, description="Task identifier from task catalog")
    duration_h: Optional[int] = Field(None, json_schema_extra={"example": 3}, description="Custom duration in hours")


class PlanRequest(BaseModel):
    lat: float = Field(28.6139, json_schema_extra={"example": 28.6139}, description="Site latitude")
    lon: float = Field(77.2090, json_schema_extra={"example": 77.2090}, description="Site longitude")
    date_str: Optional[str] = Field(None, json_schema_extra={"example": "2026-10-08"}, description="Target date in YYYY-MM-DD format")
    new_crew: bool = Field(False, description="True if crew is unacclimated")
    grap_stage: int = Field(0, ge=0, le=4, description="GRAP pollution stage (0-4)")
    shift_start_hour: int = Field(6, ge=0, le=23, description="Shift start hour (0-23)")
    shift_end_hour: int = Field(18, ge=1, le=24, description="Shift end hour (1-24)")
    tasks: list[TaskItem] = Field(..., description="List of tasks to schedule")


class ScenarioPlanRequest(BaseModel):
    new_crew: bool = Field(False, description="True if crew is unacclimated")
    grap_stage: Optional[int] = Field(None, ge=0, le=4, description="Override GRAP stage")
    shift_start_hour: int = Field(6, ge=0, le=23, description="Shift start hour (0-23)")
    shift_end_hour: int = Field(18, ge=1, le=24, description="Shift end hour (1-24)")
    tasks: list[TaskItem] = Field(..., description="List of tasks to schedule")


@app.get("/api/health", summary="Health Check")
def health_check():
    return {
        "status": "ok",
        "service": "WorkWise Safety Engine API",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/tasks", summary="Get Task Catalog & GRAP Stages")
def get_task_catalog():
    return {
        "tasks": {
            k: {
                "id": v.id,
                "label": v.label,
                "intensity": v.intensity,
                "default_duration_h": v.default_duration_h,
                "outdoor": v.outdoor,
                "continuous": v.continuous,
                "dust_generating": v.dust_generating,
            }
            for k, v in TASKS.items()
        },
        "grap_stages": GRAP_STAGES,
    }


@app.post("/api/plan", summary="Generate Work Schedule from Live Forecast")
def generate_live_plan(req: PlanRequest):
    for t in req.tasks:
        if t.id not in TASKS:
            raise HTTPException(status_code=400, detail=f"Unknown task ID: '{t.id}'")

    target_date = req.date_str or date.today().isoformat()
    try:
        rows = fetch_hourly(req.lat, req.lon, target_date, target_date)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Weather API error: {str(e)}")

    rows = [r for r in rows if req.shift_start_hour <= r["time"].hour < req.shift_end_hour]
    if not rows:
        raise HTTPException(status_code=400, detail="No hourly weather data found for requested shift window")

    task_ids = [t.id for t in req.tasks]
    matrix = build_matrix(
        rows,
        task_ids,
        req.new_crew,
        req.lat,
        req.lon,
        grap_stage=req.grap_stage,
    )

    task_dicts = [{"id": t.id, "duration_h": t.duration_h} for t in req.tasks]
    plan = schedule_tasks(matrix, task_dicts, day_start=req.shift_start_hour * 60)

    return {
        "site": f"Lat {req.lat}, Lon {req.lon}",
        "date": target_date,
        "grap_stage": req.grap_stage,
        "grap_description": GRAP_STAGES.get(req.grap_stage, "Unknown"),
        "new_crew": req.new_crew,
        "matrix": matrix,
        "schedule": plan,
    }


@app.get("/api/scenarios", summary="List Pre-configured Scenarios")
def get_scenarios():
    return {"scenarios": list_scenarios()}


@app.post("/api/scenarios/{scenario_id}/plan", summary="Generate Work Schedule from Scenario Data")
def generate_scenario_plan(
    scenario_id: str = APIPath(..., description="Scenario identifier (e.g. normal, heatwave, cloudburst, smog_grap3)"),
    req: ScenarioPlanRequest = ...,
):
    for t in req.tasks:
        if t.id not in TASKS:
            raise HTTPException(status_code=400, detail=f"Unknown task ID: '{t.id}'")

    try:
        rows = load_scenario_rows(scenario_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    rows = [r for r in rows if req.shift_start_hour <= r["time"].hour < req.shift_end_hour]
    if not rows:
        raise HTTPException(status_code=400, detail="No scenario rows found for requested shift window")

    grap = req.grap_stage if req.grap_stage is not None else rows[0].get("default_grap_stage", 0)
    lat, lon = 28.6139, 77.2090
    task_ids = [t.id for t in req.tasks]

    matrix = build_matrix(
        rows,
        task_ids,
        req.new_crew,
        lat,
        lon,
        grap_stage=grap,
    )

    task_dicts = [{"id": t.id, "duration_h": t.duration_h} for t in req.tasks]
    plan = schedule_tasks(matrix, task_dicts, day_start=req.shift_start_hour * 60)

    return {
        "scenario_id": scenario_id,
        "grap_stage": grap,
        "grap_description": GRAP_STAGES.get(grap, "Unknown"),
        "new_crew": req.new_crew,
        "matrix": matrix,
        "schedule": plan,
    }
