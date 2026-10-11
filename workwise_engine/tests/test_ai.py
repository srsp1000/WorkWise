from fastapi.testclient import TestClient

from workwise_engine.ai import (
    generate_deterministic_explanation,
    validate_ai_text,
)
from workwise_engine.api import app

client = TestClient(app)

SAMPLE_PLAN_PAYLOAD = {
    "site": "Delhi Construction Site",
    "date": "2026-10-11",
    "grap_stage": 0,
    "grap_description": "Normal (No Restrictions)",
    "new_crew": False,
    "total_crew_size": 18,
    "schedule": [
        {
            "task_id": "concrete",
            "task": "Concrete pour",
            "status": "SCHEDULED",
            "start": "06:00",
            "end": "09:00",
            "crew_required": 8,
            "why_scheduled": "Conditions meet continuous screening criteria (WBGT 24.2°C <= 26.0°C).",
        },
        {
            "task_id": "brickwork",
            "task": "Brickwork",
            "status": "UNSCHEDULABLE",
            "why_unschedulable": "Exceeds thermal threshold of 26.0°C during available midday window.",
            "recommended_action": "Reschedule to early morning or night shift.",
        },
    ],
    "top_recommendation": "Concrete pour must start at 06:00 to avoid afternoon thermal stress.",
    "rest_recommendations": {
        "work_rest_cycle": "45 min work / 15 min rest",
        "hydration_guideline": "1 liter water every 20-30 minutes",
        "shade_requirement": "Covered shaded rest shelter with cross-ventilation",
    },
    "metadata": {
        "plan_id": "test-plan-001",
        "is_simulated": True,
        "engine_version": "2026.2-field-ops",
    },
}


def test_ai_status_endpoint():
    response = client.get("/api/ai/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["safeguards_active"] is True
    assert "bedrock_configured" in data
    assert data["mode"] in ["amazon_bedrock", "deterministic_template"]


def test_ai_explain_plan_deterministic():
    response = client.post("/api/ai/explain", json={"plan": SAMPLE_PLAN_PAYLOAD, "language": "both"})
    assert response.status_code == 200
    data = response.json()
    assert data["validated"] is True
    assert data["ground_truth_matches"] is True
    assert "Concrete pour" in data["explanation_en"]
    assert "Brickwork" in data["explanation_en"]
    assert "06:00" in data["explanation_en"]
    # Check Hindi explanation
    assert "कंक्रीट" in data["explanation_hi"] or "कार्य" in data["explanation_hi"]
    assert len(data["key_points"]) > 0
    assert "AI is an explanatory communication layer" in data["disclaimer"]


def test_ai_explain_single_task():
    response = client.post(
        "/api/ai/explain",
        json={"plan": SAMPLE_PLAN_PAYLOAD, "task_id": "concrete", "language": "both"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "Concrete pour" in data["explanation_en"]
    assert "06:00 to 09:00" in data["explanation_en"]


def test_ai_ask_supervisor_question_task():
    response = client.post(
        "/api/ai/ask",
        json={"question": "Why is brickwork unscheduled?", "plan": SAMPLE_PLAN_PAYLOAD},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["validated"] is True
    assert "Brickwork" in data["referenced_tasks"]
    assert "Exceeds thermal threshold" in data["answer"] or "could not be scheduled" in data["answer"]


def test_ai_ask_supervisor_question_rest_guidance():
    response = client.post(
        "/api/ai/ask",
        json={"question": "What is the recommended rest and hydration rule?", "plan": SAMPLE_PLAN_PAYLOAD},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["validated"] is True
    assert "45 min work / 15 min rest" in data["answer"]
    assert "hydration" in data["answer"].lower() or "water" in data["answer"].lower()


def test_ai_rephrase_brief():
    text = "WBGT reached 28.5°C using Liljegren (2008) formula, requiring 45:15 cycle."
    response = client.post(
        "/api/ai/rephrase",
        json={"text": text, "target_audience": "worker", "language": "both"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "rephrased_en" in data
    assert "rephrased_hi" in data


def test_ai_safeguard_validator_prohibits_false_safety_claims():
    # 1. Prohibited safety claims
    is_valid, errors = validate_ai_text("This plan is 100% safe and guarantees zero risk for workers.", SAMPLE_PLAN_PAYLOAD)
    assert is_valid is False
    assert any("100% safe" in e or "zero risk" in e for e in errors)

    # 2. Medical claims
    is_valid, errors = validate_ai_text("This hydration drink is a cure for severe heat stroke.", SAMPLE_PLAN_PAYLOAD)
    assert is_valid is False
    assert any("cure" in e for e in errors)

    # 3. Falsely claiming an unschedulable task is scheduled
    is_valid, errors = validate_ai_text("Starting Brickwork at 12:00 for the afternoon shift.", SAMPLE_PLAN_PAYLOAD)
    assert is_valid is False
    assert any("unscheduled task" in e for e in errors)

    # 4. Valid explanation text passes cleanly, including words containing 'cure' like secure, procure, curing
    valid_text = (
        "Concrete pour is scheduled from 06:00 to 09:00 following OSHA/NIOSH continuous work screening criteria. "
        "Please secure all equipment and follow proper concrete curing protocols before leaving."
    )
    is_valid, errors = validate_ai_text(valid_text, SAMPLE_PLAN_PAYLOAD)
    assert is_valid is True
    assert len(errors) == 0

    # 5. Hindi prohibited claims are rejected
    is_valid_hi, errors_hi = validate_ai_text("यह कार्य योजना 100% सुरक्षित है और कोई जोखिम नहीं।", SAMPLE_PLAN_PAYLOAD)
    assert is_valid_hi is False
    assert any("100% सुरक्षित" in e or "कोई जोखिम नहीं" in e for e in errors_hi)

    is_valid_med_hi, errors_med_hi = validate_ai_text("यह पेय लू का इलाज है।", SAMPLE_PLAN_PAYLOAD)
    assert is_valid_med_hi is False
    assert any("इलाज" in e for e in errors_med_hi)
