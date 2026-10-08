from datetime import datetime
import json

from workwise_engine.engine import build_matrix, schedule_tasks


TASKS = [
    {"id": "concrete", "duration_h": 3},
    {"id": "rebar", "duration_h": 4},
    {"id": "brickwork", "duration_h": 3},
    {"id": "material_prep", "duration_h": 2},
]

with open("sample_weather.json", encoding="utf-8") as f:
    rows = json.load(f)

for r in rows:
    r["time"] = datetime.fromisoformat(r["time"])

lat, lon = 28.6139, 77.2090
matrix = build_matrix(rows, [t["id"] for t in TASKS], False, lat, lon)
plan = schedule_tasks(matrix, TASKS, day_start=6 * 60)

print("\nWORKWISE - OFFLINE PHASE 1 DEMO\n")
for p in plan:
    print(p)

print("\n12:00 task states:")
for task in TASKS:
    cell = next(m["tasks"][task["id"]] for m in matrix if m["time"].startswith("2026-10-08T12:00"))
    print(f"- {cell['task']}: {cell['state']} | WBGT={cell['wbgt_c']} deg C | margin={cell['margin_c']} deg C")
