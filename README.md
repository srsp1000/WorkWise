# WorkWise (कामवाइज़)

**Mobile-First, India-Aware Construction Workability & Scheduling Assistant**

WorkWise helps construction supervisors in India make informed, defensible operational decisions under extreme weather and environmental constraints (dry heat, humid monsoons, thunderstorms, and CAQM GRAP air pollution stages).

---

## Architecture & Product Hierarchy

WorkWise separates **environmental workability screening** from **deterministic task scheduling**:

1. **Context & Environmental Baseline:** Compact site, time, crew acclimatization, and weather indicators.
2. **One-Sentence Signature Recommendation:** Clear operational directive above the heatmap answering what should change and why.
3. **Workability Heatmap (Primary Experience):** 4 standardized workload/exposure tiers across the shift:
   - Light (Indoor/Shaded)
   - Moderate (Outdoor)
   - Heavy (Outdoor)
   - Very Heavy (Demanding Masonry / Heavy Lifting)
4. **Prioritised Operational Recommendations:** 3 actionable decision-support cards with concrete alternatives and interactive one-click application.
5. **Proposed Construction Work Schedule:** Deterministic Gantt schedule honoring prerequisites, crew headcount limits, continuous placement constraints, and configurable intensity.
6. **Bilingual Dispatch & Explainability:** Multi-lingual voice briefing (Hindi / Indian English) and tap-to-explain safety rule diagnostics.

---

## Core Technical Principles & Corrections

1. **Physical Exposure Modeling (No Arbitrary Shade Offsets):**
   - Removed fixed −4°C shade adjustments. In-shade conditions are calculated physically ($SW = 0, \text{Direct} = 0$) using Liljegren / ISO 7243 algorithms.
   - Missing or null meteorological variables produce `DATA_UNAVAILABLE` rather than fabricated values.
2. **Versioned Occupational Screening Thresholds:**
   - Calibrated against published OSHA / NIOSH continuous work screening benchmarks:
     - **Light (200W):** 30.0°C (Acclimatized) / 28.0°C (Unacclimatized)
     - **Moderate (300W):** 28.0°C (Acclimatized) / 25.0°C (Unacclimatized)
     - **Heavy (400W):** 26.0°C (Acclimatized) / 23.0°C (Unacclimatized)
     - **Very Heavy (500W):** 25.0°C (Acclimatized) / 21.0°C (Unacclimatized)
   - Passing a screening tier indicates hours meeting criteria, not a guarantee of absolute safety.
3. **Decoupled Task Intensity:**
   - Supervisors can configure workload intensity (`light`, `moderate`, `heavy`, `very_heavy`) independently of task name.
4. **Configurable Regulatory & Weather Gates:**
   - CAQM GRAP dust mitigation restrictions aligned with the revised schedule dated **29 September 2026**.
   - Configurable equipment wind thresholds, task rain sensitivities, and optional continuous placement constraints.
5. **Interactive Recommendation Validation:**
   - Applying a recommendation regenerates and validates the entire daily schedule in real-time before acceptance.

---

## Quickstart

### Prerequisites
- Python 3.10+ (tested on Python 3.13)
- Node.js 18+ & npm

### 1. Backend Engine
```bash
# In repository root
pip install -r requirements.txt

# Run automated tests (25/25 passing)
py -m pytest

# Start FastAPI engine on port 8008
py -m uvicorn workwise_engine.api:app --host 127.0.0.1 --port 8008 --reload
```

### 2. Frontend Web App
```bash
cd frontend
npm install
npm run build
npm run dev
```

Visit `http://localhost:5173` to explore WorkWise in your browser or mobile viewport.

---

## Pre-Loaded Indian Scenarios

1. **Normal Summer Day:** Baseline seasonal pattern with moderate afternoon peak.
2. **Severe Heatwave:** Extreme temperatures (45°C+) testing midday heat shifts and shaded rotations.
3. **Cloudburst & Thunderstorm:** High winds and sudden precipitation triggering equipment safety gates.
4. **Smog & GRAP Stage III:** Severe winter air pollution triggering CAQM dust-generating work bans.
5. **Monsoon Hot & Humid:** Oppressive tropical humidity (35°C, 80%+ RH) generating severe wet-bulb heat stress.
