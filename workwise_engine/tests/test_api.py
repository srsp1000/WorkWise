from fastapi.testclient import TestClient

from workwise_engine.api import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_get_tasks():
    response = client.get("/api/tasks")
    assert response.status_code == 200
    data = response.json()
    assert "concrete" in data["tasks"]
    assert "grap_stages" in data


def test_get_scenarios():
    response = client.get("/api/scenarios")
    assert response.status_code == 200
    data = response.json()
    ids = [s["id"] for s in data["scenarios"]]
    assert "normal" in ids
    assert "heatwave" in ids
    assert "smog_grap3" in ids


def test_scenario_normal_plan_contract():
    payload = {
        "new_crew": False,
        "tasks": [
            {"id": "concrete", "duration_h": 3},
            {"id": "material_prep", "duration_h": 2},
        ],
    }
    response = client.post("/api/scenarios/normal/plan", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["scenario_id"] == "normal"
    assert len(data["schedule"]) == 2

    # Verify Phase 2 standardized contract fields
    assert "metadata" in data
    assert "plan_id" in data["metadata"]
    assert data["metadata"]["is_simulated"] is True
    assert "attribution" in data["metadata"]

    assert "input_assumptions" in data
    assert "shift_window" in data["input_assumptions"]

    assert "rest_recommendations" in data
    assert "hydration_guideline" in data["rest_recommendations"]
    assert "work_rest_cycle" in data["rest_recommendations"]

    assert "limitations_disclaimer" in data
    assert "NIOSH" in data["limitations_disclaimer"]


def test_grap3_blocks_dust_generating_tasks():
    payload = {
        "new_crew": False,
        "grap_stage": 3,
        "tasks": [
            {"id": "concrete", "duration_h": 3},
            {"id": "material_prep", "duration_h": 2},
        ],
    }
    response = client.post("/api/scenarios/smog_grap3/plan", json=payload)
    assert response.status_code == 200
    data = response.json()
    # concrete is dust-generating so it should be unschedulable under GRAP Stage 3
    sched = {item["task_id"]: item for item in data["schedule"]}
    assert sched["concrete"]["status"] == "UNSCHEDULABLE"
    assert sched["material_prep"]["status"] == "SCHEDULED"


def test_scenario_shift_window():
    payload = {
        "shift_start_hour": 8,
        "shift_end_hour": 14,
        "tasks": [
            {"id": "material_prep", "duration_h": 2},
        ],
    }
    response = client.post("/api/scenarios/normal/plan", json=payload)
    assert response.status_code == 200
    data = response.json()
    sched = data["schedule"][0]
    assert sched["start"] >= "08:00"
    assert sched["end"] <= "14:00"


def test_api_plan_with_dependencies_and_crew_capacity():
    payload = {
        "shift_start_hour": 6,
        "shift_end_hour": 18,
        "total_crew_size": 18,
        "max_concurrent_tasks": 2,
        "tasks": [
            {"id": "excavation", "duration_h": 2, "depends_on": []},
            {"id": "rebar", "duration_h": 2, "depends_on": ["excavation"]},
            {"id": "material_prep", "duration_h": 2, "depends_on": []},
        ],
    }
    response = client.post("/api/scenarios/normal/plan", json=payload)
    assert response.status_code == 200
    data = response.json()
    sched = {item["task_id"]: item for item in data["schedule"]}

    assert sched["excavation"]["status"] == "SCHEDULED"
    assert sched["rebar"]["status"] == "SCHEDULED"
    assert sched["material_prep"]["status"] == "SCHEDULED"

    # Rebar must start after Excavation ends
    assert sched["rebar"]["start"] >= sched["excavation"]["end"]
    # Verify diagnostic explanations
    assert "why_scheduled" in sched["rebar"]
    assert "following Excavation completion" in sched["rebar"]["why_scheduled"]


def test_audio_synthesis_fallback():
    payload = {
        "text": "Aaj 18 worker hain, concrete subah chhe baje shuru karein.",
        "language": "hi",
    }
    response = client.post("/api/audio/synthesize", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in {"success", "fallback"}
    assert "provider" in data


def test_workability_heatmap_and_recommendations_contract():
    payload = {
        "shift_start_hour": 6,
        "shift_end_hour": 18,
        "tasks": [
            {"id": "concrete", "duration_h": 3, "intensity": "very_heavy"},
            {"id": "brickwork", "duration_h": 3, "intensity": "moderate", "completed_prior": False},
        ],
    }
    response = client.post("/api/scenarios/heatwave/plan", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Verify workability_heatmap has the 4 standard tiers
    assert "workability_heatmap" in data
    assert len(data["workability_heatmap"]) == 4
    tier_ids = [t["tier_id"] for t in data["workability_heatmap"]]
    assert "heavy_outdoor" in tier_ids
    assert "shaded_indoor" in tier_ids

    # Verify top recommendation and prioritized actions
    assert "top_recommendation" in data
    assert len(data["top_recommendation"]) > 15
    assert "prioritized_actions" in data
    assert len(data["prioritized_actions"]) <= 3
    for act in data["prioritized_actions"]:
        assert "id" in act
        assert "title" in act
        assert "action" in act
        assert "affected" in act
        assert "why" in act
        assert "constraint" in act
        assert "alternative" in act


def test_live_plan_timezone_default_date():
    from zoneinfo import ZoneInfo
    from datetime import datetime
    expected_date = datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
    payload = {
        "lat": 28.6139,
        "lon": 77.2090,
        "shift_start_hour": 6,
        "shift_end_hour": 18,
        "tasks": [{"id": "material_prep", "duration_h": 2}],
    }
    response = client.post("/api/plan", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["date"] == expected_date



