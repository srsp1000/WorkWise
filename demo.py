from datetime import date, timedelta
import json

from workwise_engine.engine import build_matrix, schedule_tasks
from workwise_engine.weather import fetch_hourly


DELHI = {"lat": 28.6139, "lon": 77.2090}
TASKS = [
    {"id": "concrete", "duration_h": 3},
    {"id": "rebar", "duration_h": 4},
    {"id": "brickwork", "duration_h": 3},
    {"id": "material_prep", "duration_h": 2},
]


def main():
    d = date.today().isoformat()
    rows = fetch_hourly(DELHI["lat"], DELHI["lon"], d, d)
    rows = [r for r in rows if 6 <= r["time"].hour < 18]
    matrix = build_matrix(rows, [t["id"] for t in TASKS], False, DELHI["lat"], DELHI["lon"])
    plan = schedule_tasks(matrix, TASKS, day_start=6 * 60)

    print("\nWORKWISE - PHASE 1\n")
    for p in plan:
        print(p)

    out = {"site": "Delhi", "matrix": matrix, "schedule": plan}
    with open("phase1_output.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("\nWrote phase1_output.json")


if __name__ == "__main__":
    main()
