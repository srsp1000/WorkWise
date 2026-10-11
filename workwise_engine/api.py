"""WorkWise Safety Engine REST API.

Provides structured endpoints for:
- Task catalog & CAQM GRAP definitions.
- City locations list.
- Real-time weather dashboard data.
- Live weather plan generation with full schema validation and provenance metadata.
- Pre-configured scenario simulations (normal, heatwave, cloudburst, smog_grap3, monsoon).
- Spoken audio synthesis endpoint (Amazon Polly with browser fallback).
"""

from __future__ import annotations
from datetime import date, datetime
import hashlib
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException, Path as APIPath
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .ai import (
    AIAskResponse,
    AIExplanationResponse,
    AIRephraseResponse,
    answer_supervisor_question,
    explain_plan,
    is_bedrock_configured,
    rephrase_brief_for_workers,
)
from .cities import get_cities_list
from .config import (
    CONFIG_VERSION,
    GRAP_STAGES,
    TASKS,
    WORKABILITY_TIERS,
)
from .engine import (
    build_matrix,
    build_workability_heatmap,
    generate_signature_recommendations,
    schedule_tasks,
)
from .scenarios import list_scenarios, load_scenario_rows
from .weather import DATA_ATTRIBUTION, fetch_current, fetch_hourly

app = FastAPI(
    title="WorkWise Safety Engine API",
    description="Mobile-first, India-aware construction workability and scheduling assistant API",
    version=CONFIG_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Input Request Schemas ---

class TaskItem(BaseModel):
    id: str = Field(..., json_schema_extra={"example": "concrete"}, description="Task identifier from catalog")
    duration_h: Optional[int] = Field(None, json_schema_extra={"example": 3}, description="Custom duration in hours")
    intensity: Optional[str] = Field(None, description="Workload intensity: light, moderate, heavy, very_heavy")
    continuous: Optional[bool] = Field(None, description="Whether continuous execution without pause is enforced")
    completed_prior: Optional[bool] = Field(False, description="True if prerequisite work was inspected/finished in prior shift")
    depends_on: Optional[list[str]] = Field(None, description="Prerequisite task IDs")
    crew_required: Optional[int] = Field(None, description="Worker count required")
    equipment_wind_limit_kmh: Optional[float] = Field(None, description="Equipment wind gust threshold in km/h")
    rain_sensitive: Optional[bool] = Field(None, description="Whether task is blocked by precipitation wash")


class PlanRequest(BaseModel):
    lat: float = Field(28.6139, json_schema_extra={"example": 28.6139}, description="Site latitude")
    lon: float = Field(77.2090, json_schema_extra={"example": 77.2090}, description="Site longitude")
    date_str: Optional[str] = Field(None, json_schema_extra={"example": "2026-10-11"}, description="Target date in YYYY-MM-DD format")
    new_crew: bool = Field(False, description="True if crew is unacclimatized")
    grap_stage: int = Field(0, ge=0, le=4, description="CAQM GRAP stage (0-4)")
    shift_start_hour: int = Field(6, ge=0, le=23, description="Shift start hour (0-23)")
    shift_end_hour: int = Field(18, ge=1, le=24, description="Shift end hour (1-24)")
    total_crew_size: int = Field(18, ge=1, description="Total site crew capacity")
    max_concurrent_tasks: int = Field(2, ge=1, description="Max concurrent task bound")
    tasks: list[TaskItem] = Field(..., description="List of tasks to schedule")


class ScenarioPlanRequest(BaseModel):
    lat: float = Field(28.6139, description="Site latitude")
    lon: float = Field(77.2090, description="Site longitude")
    new_crew: bool = Field(False, description="True if crew is unacclimatized")
    grap_stage: Optional[int] = Field(None, ge=0, le=4, description="Override GRAP stage")
    shift_start_hour: int = Field(6, ge=0, le=23, description="Shift start hour (0-23)")
    shift_end_hour: int = Field(18, ge=1, le=24, description="Shift end hour (1-24)")
    total_crew_size: int = Field(18, ge=1, description="Total site crew capacity")
    max_concurrent_tasks: int = Field(2, ge=1, description="Max concurrent task bound")
    tasks: list[TaskItem] = Field(..., description="List of tasks to schedule")


# --- Output Response Contract Schemas ---

class TaskHourCellModel(BaseModel):
    time: str
    task_id: str
    task: str
    intensity: str
    outdoor: bool = True
    wbgt_c: Optional[float] = None
    effective_wbgt_c: Optional[float] = None
    wbgt_method: str
    limit_c: float
    margin_c: Optional[float] = None
    state: str
    work_rest: str
    gates: list[str] = []
    why: list[str] = []
    assumptions: list[str] = []


class WorkabilityHeatmapRowModel(BaseModel):
    tier_id: str
    tier_label: str
    description: str
    intensity: str
    outdoor: bool
    cells: list[TaskHourCellModel]


class HourlyMatrixRowModel(BaseModel):
    time: str
    tasks: dict[str, TaskHourCellModel]


class ScheduledTaskModel(BaseModel):
    task_id: str
    task: str
    status: str
    start: Optional[str] = None
    end: Optional[str] = None
    continuous: bool = False
    is_split: bool = False
    cost: Optional[float] = None
    crew_required: Optional[int] = None
    worst_state: Optional[str] = None
    why_scheduled: Optional[str] = None
    why_unschedulable: Optional[str] = None
    recommended_action: Optional[str] = None


class PrioritizedActionModel(BaseModel):
    id: str
    title: str
    action: str
    affected: str
    why: str
    constraint: str
    alternative: str
    can_apply: bool = False
    apply_payload: Optional[dict] = None


class PlanMetadataModel(BaseModel):
    plan_id: str
    generated_at: str
    engine_version: str = CONFIG_VERSION
    data_source: str
    is_simulated: bool = False
    attribution: str = DATA_ATTRIBUTION
    data_freshness: str
    scientific_basis: str = "Liljegren (2008) WBGT, OSHA Technical Manual Sec III Ch 4 & NIOSH (2016) Criteria"


class InputAssumptionsModel(BaseModel):
    site: str
    lat: float
    lon: float
    date: str
    shift_window: str
    total_crew_size: int
    new_crew: bool
    grap_stage: int
    grap_description: str
    max_concurrent_tasks: int


class RestRecommendationModel(BaseModel):
    heat_protocol_window: Optional[str] = None
    work_rest_cycle: str
    hydration_guideline: str
    shade_requirement: str


class PlanResponseModel(BaseModel):
    site: Optional[str] = None
    scenario_id: Optional[str] = None
    date: str
    grap_stage: int
    grap_description: str
    new_crew: bool
    total_crew_size: int
    workability_heatmap: list[WorkabilityHeatmapRowModel]
    matrix: list[HourlyMatrixRowModel]
    schedule: list[ScheduledTaskModel]
    top_recommendation: str
    prioritized_actions: list[PrioritizedActionModel]
    plan_summary: str
    metadata: PlanMetadataModel
    input_assumptions: InputAssumptionsModel
    rest_recommendations: RestRecommendationModel
    limitations_disclaimer: str = (
        "WorkWise is a planning and decision-support aid based on forecast meteorological modeling "
        "and OSHA/NIOSH screening guidelines. Meeting screening criteria does not guarantee absolute safety. "
        "It does not replace on-site calibrated WBGT instruments, certified medical supervision, "
        "or site safety officer authority."
    )


# --- Helpers ---

def _build_rest_recommendations(matrix: list[dict], new_crew: bool) -> RestRecommendationModel:
    stress_hours = []
    for row in matrix:
        for tid, cell in row.get("tasks", {}).items():
            if cell.get("state") in {"EASE", "LIMIT", "STOP"}:
                t_dt = datetime.fromisoformat(row["time"])
                stress_hours.append(t_dt.hour)
                break

    if not stress_hours:
        return RestRecommendationModel(
            heat_protocol_window="No thermal protocol required",
            work_rest_cycle="Standard continuous work with scheduled hydration breaks",
            hydration_guideline="Provide 0.5 L cool potable water per worker per hour.",
            shade_requirement="Ensure accessible shaded rest canopy adjacent to work areas.",
        )

    first_h = min(stress_hours)
    last_h = max(stress_hours) + 1
    window_str = f"{first_h:02d}:00 – {last_h:02d}:00"

    has_limit_or_stop = any(
        cell.get("state") in {"LIMIT", "STOP"} for r in matrix for cell in r.get("tasks", {}).values()
    )
    cycle = (
        "30 min work / 30 min rest screening guidance (LIMIT state)"
        if has_limit_or_stop
        else "45 min work / 15 min rest screening guidance (EASE state)"
    )

    hydration = "Mandate 1.0 L (4 cups) cool potable water per worker per hour. Schedule drinking every 15–20 minutes."
    if new_crew:
        hydration += " Closely monitor new/unacclimatized workers for early symptoms of heat illness."

    return RestRecommendationModel(
        heat_protocol_window=window_str,
        work_rest_cycle=cycle,
        hydration_guideline=hydration,
        shade_requirement="Mandatory shaded break canopy with active airflow adjacent to active work zones.",
    )


def _generate_plan_id(lat: float, lon: float, date_str: str) -> str:
    raw = f"{lat}:{lon}:{date_str}:{datetime.now().isoformat()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


# --- Endpoints ---

@app.get("/api/health", summary="Health Check")
def health_check():
    return {
        "status": "ok",
        "service": "WorkWise Safety Engine API",
        "version": CONFIG_VERSION,
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
                "depends_on": list(v.depends_on),
                "crew_required": v.crew_required,
                "equipment_wind_limit_kmh": v.equipment_wind_limit_kmh,
                "rain_sensitive": v.rain_sensitive,
                "source_reference": v.source_reference,
            }
            for k, v in TASKS.items()
        },
        "workability_tiers": WORKABILITY_TIERS,
        "grap_stages": GRAP_STAGES,
        "version": CONFIG_VERSION,
    }


@app.get("/api/cities", summary="Get list of Indian cities")
def get_cities():
    return {"cities": get_cities_list()}


@app.get("/api/weather/current", summary="Get current weather for location")
def get_current_weather(lat: float, lon: float):
    try:
        return fetch_current(lat, lon)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch current weather: {str(e)}")


@app.post("/api/plan", response_model=PlanResponseModel, summary="Generate Work Schedule from Live Forecast")
def generate_live_plan(req: PlanRequest):
    for t in req.tasks:
        if t.id not in TASKS:
            raise HTTPException(status_code=400, detail=f"Unknown task ID: '{t.id}'")

    target_date = req.date_str or datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
    try:
        rows = fetch_hourly(req.lat, req.lon, target_date, target_date, use_fallback_on_failure=True)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Weather API error: {str(e)}")

    rows = [r for r in rows if req.shift_start_hour <= r["time"].hour < req.shift_end_hour]
    if not rows:
        raise HTTPException(status_code=400, detail="No hourly weather data found for requested shift window")

    task_dicts = [
        {
            "id": t.id,
            "duration_h": t.duration_h,
            "intensity": t.intensity,
            "continuous": t.continuous,
            "completed_prior": t.completed_prior,
            "depends_on": t.depends_on,
            "crew_required": t.crew_required,
            "equipment_wind_limit_kmh": t.equipment_wind_limit_kmh,
            "rain_sensitive": t.rain_sensitive,
        }
        for t in req.tasks
    ]

    try:
        # 1. Primary Workability Heatmap across 4 tiers
        workability_heatmap = build_workability_heatmap(
            rows,
            req.new_crew,
            req.lat,
            req.lon,
            grap_stage=req.grap_stage,
        )

        # 2. Specific Task Matrix
        matrix = build_matrix(
            rows,
            task_dicts,
            req.new_crew,
            req.lat,
            req.lon,
            grap_stage=req.grap_stage,
        )

        # 3. Constraint-aware Task Schedule
        plan = schedule_tasks(
            matrix,
            task_dicts,
            day_start=req.shift_start_hour * 60,
            total_crew_size=req.total_crew_size,
            max_concurrent_tasks=req.max_concurrent_tasks,
        )

        # 4. Signature Recommendations
        top_rec, prioritized_actions = generate_signature_recommendations(
            matrix=matrix,
            workability_heatmap=workability_heatmap,
            schedule=plan,
            weather_rows=rows,
            city_name="Site Location",
            new_crew=req.new_crew,
        )

        plan_id = _generate_plan_id(req.lat, req.lon, target_date)
        rest_recs = _build_rest_recommendations(matrix, req.new_crew)

        is_fallback = any(r.get("is_sample_fallback") for r in rows) if rows else False

        metadata = PlanMetadataModel(
            plan_id=plan_id,
            generated_at=datetime.now().isoformat(),
            engine_version=CONFIG_VERSION,
            data_source="Offline Sample Fixture (Open-Meteo fallback)" if is_fallback else "Open-Meteo Forecast API",
            is_simulated=is_fallback,
            attribution="Offline Sample Weather Fixture" if is_fallback else DATA_ATTRIBUTION,
            data_freshness="Offline sample fallback" if is_fallback else f"Hourly forecast retrieved for {target_date}",
        )


        input_assumptions = InputAssumptionsModel(
            site=f"Lat {req.lat:.4f}, Lon {req.lon:.4f}",
            lat=req.lat,
            lon=req.lon,
            date=target_date,
            shift_window=f"{req.shift_start_hour:02d}:00 – {req.shift_end_hour:02d}:00",
            total_crew_size=req.total_crew_size,
            new_crew=req.new_crew,
            grap_stage=req.grap_stage,
            grap_description=GRAP_STAGES.get(req.grap_stage, "Unknown"),
            max_concurrent_tasks=req.max_concurrent_tasks,
        )

        return PlanResponseModel(
            site=f"Lat {req.lat:.4f}, Lon {req.lon:.4f}",
            scenario_id=None,
            date=target_date,
            grap_stage=req.grap_stage,
            grap_description=GRAP_STAGES.get(req.grap_stage, "Unknown"),
            new_crew=req.new_crew,
            total_crew_size=req.total_crew_size,
            workability_heatmap=workability_heatmap,
            matrix=matrix,
            schedule=plan,
            top_recommendation=top_rec,
            prioritized_actions=prioritized_actions,
            plan_summary=top_rec,
            metadata=metadata,
            input_assumptions=input_assumptions,
            rest_recommendations=rest_recs,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate live plan: {str(e)}")


@app.get("/api/scenarios", summary="List Pre-configured Scenarios")
def get_scenarios():
    try:
        return {"scenarios": list_scenarios()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list scenarios: {str(e)}")


@app.post("/api/scenarios/{scenario_id}/plan", response_model=PlanResponseModel, summary="Generate Work Schedule from Scenario Data")
def generate_scenario_plan(
    scenario_id: str = APIPath(..., description="Scenario identifier"),
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

    task_dicts = [
        {
            "id": t.id,
            "duration_h": t.duration_h,
            "intensity": t.intensity,
            "continuous": t.continuous,
            "completed_prior": t.completed_prior,
            "depends_on": t.depends_on,
            "crew_required": t.crew_required,
            "equipment_wind_limit_kmh": t.equipment_wind_limit_kmh,
            "rain_sensitive": t.rain_sensitive,
        }
        for t in req.tasks
    ]

    try:
        # 1. Primary Workability Heatmap across 4 tiers
        workability_heatmap = build_workability_heatmap(
            rows,
            req.new_crew,
            req.lat,
            req.lon,
            grap_stage=grap,
        )

        # 2. Specific Task Matrix
        matrix = build_matrix(
            rows,
            task_dicts,
            req.new_crew,
            req.lat,
            req.lon,
            grap_stage=grap,
        )

        # 3. Constraint-aware Task Schedule
        plan = schedule_tasks(
            matrix,
            task_dicts,
            day_start=req.shift_start_hour * 60,
            total_crew_size=req.total_crew_size,
            max_concurrent_tasks=req.max_concurrent_tasks,
        )

        scenario_name = scenario_id.replace("_", " ").title()

        # 4. Signature Recommendations
        top_rec, prioritized_actions = generate_signature_recommendations(
            matrix=matrix,
            workability_heatmap=workability_heatmap,
            schedule=plan,
            weather_rows=rows,
            city_name=scenario_name,
            new_crew=req.new_crew,
        )

        target_date = rows[0]["time"].strftime("%Y-%m-%d") if hasattr(rows[0]["time"], "strftime") else "2026-10-11"
        plan_id = f"scenario-{scenario_id}-{_generate_plan_id(req.lat, req.lon, target_date)}"
        rest_recs = _build_rest_recommendations(matrix, req.new_crew)

        metadata = PlanMetadataModel(
            plan_id=plan_id,
            generated_at=datetime.now().isoformat(),
            engine_version=CONFIG_VERSION,
            data_source=f"Pre-configured Scenario: {scenario_id}",
            is_simulated=True,
            attribution="Simulated environmental testing fixture (WorkWise Research)",
            data_freshness="Deterministic historical/scenario fixture",
        )

        input_assumptions = InputAssumptionsModel(
            site=f"Scenario: {scenario_name}",
            lat=req.lat,
            lon=req.lon,
            date=target_date,
            shift_window=f"{req.shift_start_hour:02d}:00 – {req.shift_end_hour:02d}:00",
            total_crew_size=req.total_crew_size,
            new_crew=req.new_crew,
            grap_stage=grap,
            grap_description=GRAP_STAGES.get(grap, "Unknown"),
            max_concurrent_tasks=req.max_concurrent_tasks,
        )

        return PlanResponseModel(
            site=f"Scenario: {scenario_name}",
            scenario_id=scenario_id,
            date=target_date,
            grap_stage=grap,
            grap_description=GRAP_STAGES.get(grap, "Unknown"),
            new_crew=req.new_crew,
            total_crew_size=req.total_crew_size,
            workability_heatmap=workability_heatmap,
            matrix=matrix,
            schedule=plan,
            top_recommendation=top_rec,
            prioritized_actions=prioritized_actions,
            plan_summary=top_rec,
            metadata=metadata,
            input_assumptions=input_assumptions,
            rest_recommendations=rest_recs,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate scenario plan: {str(e)}")


class AudioSynthesisRequest(BaseModel):
    text: str = Field(..., max_length=1500)
    language: str = Field("hi-IN", description="'hi-IN' or 'en-IN'")
    voice_id: Optional[str] = Field(None, description="Amazon Polly voice ID (defaults to 'Kajal' for neural bilingual Hindi/English)")


@app.post("/api/audio/synthesize", summary="Synthesize Spoken Brief Audio")
def synthesize_audio(req: AudioSynthesisRequest):
    """Audio synthesis endpoint supporting Amazon Polly with browser fallback."""
    import os
    aws_region = os.getenv("AWS_REGION", "ap-south-1")

    try:
        import boto3
        import base64

        # Validate that boto3 has credentials (environment or IAM execution role)
        session = boto3.Session()
        creds = session.get_credentials()
        if creds is None:
            return {
                "status": "fallback",
                "provider": "browser_fallback",
                "mode": "browser_fallback",
                "audio_base64": None,
                "text": req.text,
                "language": req.language,
                "notice": "Amazon Polly credentials not configured. Using client-side Web Speech API.",
            }

        polly = session.client("polly", region_name=aws_region)
        voice = req.voice_id or "Kajal"
        response = polly.synthesize_speech(
            Text=req.text,
            OutputFormat="mp3",
            VoiceId=voice,
            Engine="neural",
        )
        audio_stream = response.get("AudioStream")
        if audio_stream:
            audio_bytes = audio_stream.read()
            b64_audio = base64.b64encode(audio_bytes).decode("utf-8")

            # Persist to S3 bucket if configured in environment
            s3_bucket = os.getenv("S3_STORAGE_BUCKET")
            s3_key = None
            if s3_bucket:
                try:
                    s3 = session.client("s3", region_name=aws_region)
                    text_hash = hashlib.sha256(req.text.encode("utf-8")).hexdigest()[:16]
                    s3_key = f"audio-briefs/{req.language}/{text_hash}.mp3"
                    s3.put_object(
                        Bucket=s3_bucket,
                        Key=s3_key,
                        Body=audio_bytes,
                        ContentType="audio/mpeg",
                    )
                except Exception:
                    pass

            return {
                "status": "success",
                "provider": "amazon_polly",
                "mode": "polly_neural",
                "audio_base64": b64_audio,
                "s3_key": s3_key,
                "text": req.text,
                "language": req.language,
                "voice": voice,
            }
    except Exception as e:
        return {
            "status": "fallback",
            "provider": "browser_fallback",
            "mode": "browser_fallback",
            "audio_base64": None,
            "text": req.text,
            "language": req.language,
            "notice": f"Polly service exception: {str(e)}. Using browser Web Speech API.",
        }


# --- AI Assistance & Safeguards Endpoints (Phase 6) ---

class AIExplainRequest(BaseModel):
    plan: dict = Field(..., description="Full PlanResponse dictionary")
    task_id: Optional[str] = Field(None, description="Optional task ID")
    language: str = Field("both", description="'en', 'hi', or 'both'")
    use_ai: bool = Field(True, description="Whether to query Bedrock if configured")


class AIAskRequest(BaseModel):
    question: str = Field(..., max_length=500, description="Supervisor question")
    plan: dict = Field(..., description="Plan response context")
    language: str = Field("en", description="'en' or 'hi'")
    use_ai: bool = Field(True, description="Whether to query Bedrock if configured")


class AIRephraseRequest(BaseModel):
    text: str = Field(..., max_length=1500)
    target_audience: str = Field("worker", description="'worker' or 'supervisor'")
    language: str = Field("both")
    use_ai: bool = Field(True)


@app.get("/api/ai/status", summary="AI Assistant Service Status")
def get_ai_status():
    """Returns whether Amazon Bedrock is configured or running in deterministic template mode."""
    import os
    configured = is_bedrock_configured()
    return {
        "status": "ready",
        "bedrock_configured": configured,
        "mode": "amazon_bedrock" if configured else "deterministic_template",
        "default_model": os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0"),
        "region": os.getenv("AWS_REGION", "ap-south-1"),
        "safeguards_active": True,
    }


@app.post("/api/ai/explain", response_model=AIExplanationResponse, summary="Explain Work Plan")
def explain_plan_endpoint(req: AIExplainRequest):
    """Generates a concise, safeguarded bilingual explanation for a plan or task."""
    try:
        return explain_plan(
            plan_data=req.plan,
            task_id=req.task_id,
            language=req.language,
            use_ai=req.use_ai,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate explanation: {str(e)}")


@app.post("/api/ai/ask", response_model=AIAskResponse, summary="Supervisor Q&A Assistant")
def ask_ai_endpoint(req: AIAskRequest):
    """Answers supervisor questions strictly grounded in the deterministic plan."""
    try:
        return answer_supervisor_question(
            question=req.question,
            plan_data=req.plan,
            language=req.language,
            use_ai=req.use_ai,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to answer question: {str(e)}")


@app.post("/api/ai/rephrase", response_model=AIRephraseResponse, summary="Rephrase Technical Brief")
def rephrase_ai_endpoint(req: AIRephraseRequest):
    """Rephrases technical safety parameters into plain worker briefing language."""
    try:
        return rephrase_brief_for_workers(
            text=req.text,
            target_audience=req.target_audience,
            language=req.language,
            use_ai=req.use_ai,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rephrase brief: {str(e)}")

