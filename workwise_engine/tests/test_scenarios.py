"""Unit tests verifying all pre-configured scenario fixtures."""

from workwise_engine.api import app
from workwise_engine.scenarios import list_scenarios, load_scenario_rows
from fastapi.testclient import TestClient

client = TestClient(app)


def test_all_scenarios_exist_and_load():
    scenarios = list_scenarios()
    expected_ids = {"normal", "heatwave", "cloudburst", "smog_grap3", "monsoon"}
    actual_ids = {s["id"] for s in scenarios}
    assert expected_ids.issubset(actual_ids), f"Missing expected scenarios: {expected_ids - actual_ids}"

    for s in scenarios:
        rows = load_scenario_rows(s["id"])
        # Each scenario covers a full workday shift (at least 12 hours)
        assert len(rows) >= 12, f"Scenario {s['id']} has fewer than 12 shift rows"
        for r in rows:
            assert "time" in r
            assert "temperature_2m" in r
            assert "relative_humidity_2m" in r
            assert "wind_speed_10m" in r
            assert "shortwave_radiation" in r


def test_all_scenarios_generate_valid_plans_via_api():
    payload = {
        "new_crew": False,
        "tasks": [
            {"id": "concrete", "duration_h": 3},
            {"id": "rebar", "duration_h": 4},
            {"id": "material_prep", "duration_h": 2},
        ],
    }

    scenarios = ["normal", "heatwave", "cloudburst", "smog_grap3", "monsoon"]
    for s_id in scenarios:
        resp = client.post(f"/api/scenarios/{s_id}/plan", json=payload)
        assert resp.status_code == 200, f"Failed generating plan for scenario {s_id}"
        data = resp.json()

        # Contract assertions
        assert data["scenario_id"] == s_id
        assert data["metadata"]["is_simulated"] is True
        assert len(data["workability_heatmap"]) == 4
        assert "top_recommendation" in data
        assert len(data["schedule"]) == 3
        assert len(data["matrix"]) > 0

        # Scenario-specific behavior assertions
        if s_id == "smog_grap3":
            # Concrete and Rebar dust-generating tasks must be blocked under GRAP Stage 3
            concrete_item = next(t for t in data["schedule"] if t["task_id"] == "concrete")
            assert concrete_item["status"] == "UNSCHEDULABLE"
            assert "GRAP" in concrete_item["why_unschedulable"]

        if s_id == "cloudburst":
            # In severe morning cloudburst, morning matrix cells (07:00-09:00) must have STOP states
            morning_cells = [
                row["tasks"]["rebar"]
                for row in data["matrix"]
                if "07:00" in row["time"] or "08:00" in row["time"] or "09:00" in row["time"]
            ]
            assert any(c["state"] == "STOP" for c in morning_cells)
            assert any("LIGHTNING_RISK" in c["gates"] or "RAIN_BLOCK" in c["gates"] for c in morning_cells)



def test_monsoon_scenario_humidity_stress():
    rows = load_scenario_rows("monsoon")
    # Verify tropical monsoon profile has high humidity (>75% RH)
    high_rh_rows = [r for r in rows if r["relative_humidity_2m"] >= 75]
    assert len(high_rh_rows) >= 12, "Monsoon scenario should have prolonged high humidity"
