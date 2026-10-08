# WorkWise — Phase 1

Climate-aware construction work scheduling engine.

Phase 1 goal:

> Given a construction site, crew type, tasks, and hourly weather, generate a task × hour safety matrix and a feasible work schedule.

This phase intentionally has **no React UI, no Bedrock, and no voice**. The engine must be correct and testable before we add the communication layer.

## Safety note

WorkWise is a prototype planning aid, not medical advice, legal compliance advice, or a replacement for site-specific WBGT measurement and a qualified safety professional. Thresholds in `config.py` are explicit prototype assumptions derived from occupational-heat guidance; production use requires expert validation and site-specific controls.

## Data sources

- Open-Meteo hourly weather forecast.
- NIOSH occupational heat guidance for the conceptual relationship between workload, WBGT, acclimatization, and work/rest controls.
- `thermofeel` Liljegren WBGT is the preferred calculation when installed; a clearly labeled simple fallback exists so the engine remains runnable during development.

## Run

```bash
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
python demo.py
```

## Phase 1 API shape

Input:

```json
{
  "lat": 28.6139,
  "lon": 77.2090,
  "crew_size": 18,
  "new_crew": false,
  "start": "06:00",
  "end": "18:00",
  "tasks": [
    {"id": "concrete", "duration_h": 3},
    {"id": "rebar", "duration_h": 4},
    {"id": "brickwork", "duration_h": 3},
    {"id": "material_prep", "duration_h": 2}
  ]
}
```

Output contains hourly weather, WBGT, state/gates per task, and the auto-scheduled tasks.

## Phase 1 rules

1. Physics/rules first; AI is not part of the decision path.
2. Gates beat heat score.
3. Every task gets a task-specific limit and an explainable margin.
4. A schedule is only valid if every hour in a task's window is feasible.
5. Prototype thresholds are assumptions until reviewed by a qualified occupational-safety/civil-engineering expert.

## Local/offline development

`demo_offline.py` runs from `sample_weather.json`, so development does not depend on a live API.
