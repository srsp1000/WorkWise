from datetime import datetime
import json
from pathlib import Path


SCENARIOS_DIR = Path(__file__).parent.parent / "data" / "scenarios"

SCENARIO_METADATA = {
    "normal": {
        "id": "normal",
        "title": "Normal Summer Day",
        "description": "Standard seasonal weather with moderate afternoon heat.",
        "default_grap_stage": 0,
    },
    "heatwave": {
        "id": "heatwave",
        "title": "Severe Heatwave",
        "description": "Extreme peak temperature (45°C+) with WBGT exceeding safety limits.",
        "default_grap_stage": 0,
    },
    "cloudburst": {
        "id": "cloudburst",
        "title": "Cloudburst & Thunderstorm",
        "description": "Heavy rainfall and lightning risk triggering safety gates.",
        "default_grap_stage": 0,
    },
    "smog_grap3": {
        "id": "smog_grap3",
        "title": "Smog & GRAP Stage III",
        "description": "Severe air pollution triggering GRAP Stage III dust construction ban.",
        "default_grap_stage": 3,
    },
}


def list_scenarios() -> list[dict]:
    return list(SCENARIO_METADATA.values())


def load_scenario_rows(scenario_id: str) -> list[dict]:
    if scenario_id not in SCENARIO_METADATA:
        raise ValueError(f"Unknown scenario ID: {scenario_id}")

    filepath = SCENARIOS_DIR / f"{scenario_id}.json"
    with open(filepath, encoding="utf-8") as f:
        rows = json.load(f)

    for r in rows:
        r["time"] = datetime.fromisoformat(r["time"])

    return rows
