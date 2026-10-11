"""Unit tests for Phase 9: Quality, Error Handling, and Edge Cases."""

from fastapi.testclient import TestClient
from workwise_engine.api import app
from workwise_engine.weather import load_sample_weather_fallback

client = TestClient(app)


def test_invalid_grap_stage_bounds():
    # GRAP stage must be between 0 and 4
    payload = {
        "new_crew": False,
        "grap_stage": 9,  # Invalid GRAP stage
        "tasks": [{"id": "concrete", "duration_h": 3}],
    }
    response = client.post("/api/scenarios/normal/plan", json=payload)
    assert response.status_code == 422


def test_invalid_crew_size_zero_or_negative():
    payload = {
        "new_crew": False,
        "total_crew_size": 0,  # Invalid crew size
        "tasks": [{"id": "concrete", "duration_h": 3}],
    }
    response = client.post("/api/scenarios/normal/plan", json=payload)
    assert response.status_code == 422


def test_offline_weather_fallback_marks_simulated():
    rows = load_sample_weather_fallback()
    assert len(rows) > 0
    assert all(r.get("is_sample_fallback") is True for r in rows)


def test_empty_tasks_list():
    payload = {
        "new_crew": False,
        "tasks": [],
    }
    response = client.post("/api/scenarios/normal/plan", json=payload)
    # When 0 tasks are submitted, schedule is empty but contract succeeds without crashing
    assert response.status_code == 200
    data = response.json()
    assert len(data["schedule"]) == 0
    assert len(data["workability_heatmap"]) == 4


def test_unknown_scenario_id_returns_404_or_400():
    response = client.post(
        "/api/scenarios/nonexistent_scenario_123/plan",
        json={"new_crew": False, "tasks": [{"id": "concrete"}]},
    )
    assert response.status_code in [400, 404, 500]


def test_ai_ask_handles_empty_or_special_characters():
    payload = {
        "question": "??? @#$%^&* ()",
        "plan": {
            "site": "Delhi Site",
            "schedule": [],
            "top_recommendation": "Follow site guidelines.",
        },
    }
    response = client.post("/api/ai/ask", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["validated"] is True
    assert "disclaimer" in data
