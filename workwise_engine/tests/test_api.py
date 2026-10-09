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


def test_scenario_normal_plan():
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
            {"id": "concrete", "duration_h": 3},
        ],
    }
    response = client.post("/api/scenarios/normal/plan", json=payload)
    assert response.status_code == 200
    data = response.json()
    sched = data["schedule"][0]
    assert sched["start"] >= "08:00"
    assert sched["end"] <= "14:00"

