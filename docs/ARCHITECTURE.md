# WorkWise — Technical Architecture & Engineering Specification

**Document Version:** 2026.2-field-ops  
**Status:** Approved Architecture Blueprint  
**Authors:** WorkWise Engineering Team  

---

## 1. System Blueprint

```
+----------------------------------------------------------------------------------------------------+
|                                    WORKWISE SYSTEM ARCHITECTURE                                    |
+----------------------------------------------------------------------------------------------------+

  [Supervisor Voice / Touch]                   [Live Weather Streams]        [Regulatory Mandates]
               |                                          |                           |
               | (Web Speech / Hindi NLP)                 | (Open-Meteo CC BY 4.0)    | (CAQM GRAP Sep 2026)
               v                                          v                           v
  +-------------------------+                 +-----------------------+   +-----------------------+
  |  Frontend PWA (React)   |                 |   Weather Client      |   |   Regulatory Gates    |
  |  - Workability Heatmap  |                 |   - 15s Timeout       |   |   - GRAP Stage 1-4    |
  |  - Signature Rec Banner |                 |   - Exponential Retry |   |   - Equipment Wind    |
  |  - 3 Prioritized Acts   |                 |   - Simulation Honesty|   |   - Precipitation     |
  +------------+------------+                 +-----------+-----------+   +-----------+-----------+
               |                                          |                           |
               +--------------------+   +-----------------+                           |
                                    |   |                                             |
                                    v   v                                             |
                     +------------------------------+                                 |
                     |  Physical WBGT Engine        |                                 |
                     |  - Liljegren (2008) Primary  |<--------------------------------+
                     |  - Stull (2011) Fallback     |
                     |  - In-Shade (SW=0, Direct=0) |
                     +--------------+---------------+
                                    |
                                    | Hourly Thermal Matrix
                                    v
                     +------------------------------+
                     |  Deterministic Scheduler     |
                     |  - OSHA / NIOSH Screening    |
                     |  - Prerequisite DAG Chain    |
                     |  - Multi-crew Concurrency    |
                     |  - Split-shift Heat Avoidance|
                     +--------------+---------------+
                                    |
                                    | Validated Plan Contract
                                    v
                     +------------------------------+
                     |  AI Safeguards & Comms Layer |
                     |  - Amazon Bedrock (Optional) |
                     |  - Guardrail Filter (Safety) |
                     |  - Deterministic Templates   |
                     |  - Amazon Polly Neural Voice |
                     +------------------------------+
```

---

## 2. Core Subsystems

### A. Physical Heat Stress Modeling (`workwise_engine/wbgt.py`)
WorkWise rejects crude dry-bulb cutoffs or arbitrary shade subtractions (such as fixed −4°C deductions). Instead:
1. **Liljegren et al. (2008) Primary Algorithm:**
   - Evaluates ambient air temperature ($T_d$), natural wet-bulb temperature ($T_w$), black globe temperature ($T_g$) derived from solar irradiance, wind speed ($v$), and barometric pressure ($p$).
   - Calculates solar zenith angle using the astronomical NOAA solar algorithm with local standard meridian correction.
2. **Physically Modeled In-Shade WBGT:**
   - Evaluates shaded and covered work areas by setting incoming direct and diffuse solar irradiance to $0\text{ W/m}^2$ ($SW = 0, \text{Direct} = 0$).
   - Calculates the physical convection and radiation equilibrium under standard shelter airflow ($0.7 T_w + 0.3 T_d$), yielding an authentic reduction of 1.5°C to 5.2°C depending on atmospheric humidity.
3. **Stull (2011) Psychrometric Fallback:**
   - A deterministic empirical approximation used if ECMWF C-libraries are unavailable.
4. **Data Integrity:**
   - If critical meteorological variables are missing or corrupted, the engine explicitly outputs `DATA_UNAVAILABLE` rather than fabricating synthetic temperatures.

---

### B. Versioned Occupational Screening Thresholds (`workwise_engine/config.py`)
Screening limits are calibrated against published **OSHA / NIOSH continuous work criteria**:

| Workload Category | Metabolic Rate (W) | Acclimatized REL (°C WBGT) | Unacclimatized RAL (°C WBGT) | Typical Site Activities |
| :--- | :--- | :--- | :--- | :--- |
| **Light** | ~200 W | **30.0°C** | **28.0°C** | Site inspection, traffic control, tower supervision |
| **Moderate** | ~300 W | **28.0°C** | **25.0°C** | Concrete finishing, carpentry, pipe fitting |
| **Heavy** | ~400 W | **26.0°C** | **23.0°C** | Rebar bending, trench digging, manual wheelbarrows |
| **Very Heavy** | ~500 W | **25.0°C** | **21.0°C** | Dense masonry block laying, heavy structural lifting |

**Workability State Bands (Margin = Limit − WBGT):**
- **`GO` ($\text{Margin} \ge 0.0\text{°C}$):** Continuous work permissible under standard hydration.
- **`EASE` ($0.0 > \text{Margin} \ge -1.5\text{°C}$):** Adjusted recovery; 45 min work / 15 min rest cycle recommended.
- **`LIMIT` ($-1.5 > \text{Margin} \ge -3.0\text{°C}$):** Restricted exposure; 30 min work / 30 min rest cycle recommended.
- **`STOP` ($\text{Margin} < -3.0\text{°C}$ or Gate Active):** Exceeds continuous work safety threshold; reschedule or suspend task.

---

### C. Constraint Gates & Regulatory Compliance (`workwise_engine/engine.py`)
Independent safety gates evaluate before scheduling:
1. **CAQM GRAP (Revised Schedule: 28 September 2026):**
   - Stage III and IV automatically trigger `GRAP_RESTRICTION` for all dust-generating tasks (`concrete`, `brickwork`, `excavation`).
2. **Equipment Wind Limit Gate:**
   - Crane lifts and work at height enforce equipment-specific wind limits (default: 35 km/h gusts).
3. **Precipitation Gate:**
   - Tasks flagged `rain_sensitive: true` enforce wash-out blocks when rainfall $\ge 0.5\text{ mm/h}$ or probability $\ge 50\%$.
4. **Lightning Risk Gate:**
   - WMO thunderstorm codes (95–99) block all outdoor activities immediately.

---

### D. Deterministic Task Scheduler (`workwise_engine/engine.py`)
The scheduler employs a multi-pass optimization engine:
1. **Prerequisite Graph (DAG):**
   - Respects dependencies (`rebar -> concrete`).
   - Supports `completed_prior: true` so prior shifts do not artificially block same-day activities.
2. **Continuous vs Non-Continuous Flexibility:**
   - Tasks like `concrete` enforce continuous placement (preventing cold joints).
   - Tasks like `rebar` or `brickwork` can pause during peak midday thermal stress (12:00–14:00) and resume in cooler afternoon hours.
3. **Crew Sizing & Concurrency Bounds:**
   - Enforces hour-by-hour crew availability: $\sum \text{Crew}_{\text{active}} \le \text{Crew}_{\text{total}}$.
   - Enforces maximum concurrent task limit across the site.
4. **Penalty Cost Minimization:**
   - Evaluates candidate windows: $\text{Cost} = \sum_{\text{window}} (\text{Thermal Penalty} + \text{Delay Penalty})$.

---

### E. AI Safeguards & Communication Layer (`workwise_engine/ai.py`)
1. **Separation of Concerns:**
   - The deterministic safety engine makes 100% of the planning and safety decisions.
   - Amazon Bedrock and deterministic templates serve solely as an **explanatory communication layer**.
2. **Guardrail Validation (`validate_ai_text`):**
   - Strictly rejects prohibited phrasing (*"100% safe"*, *"guaranteed safe"*, *"zero risk"*).
   - Rejects medical claims (*"cure for heat stroke"*).
   - Verifies that referenced task states and times match the deterministic plan ground truth.
   - If validation fails or credentials are absent, falls back seamlessly to deterministic bilingual templates.

---

### F. AWS Serverless Deployment Topology (`template.yaml`)
1. **Frontend:** React 19 PWA hosted on AWS Amplify with offline service worker.
2. **API Gateway HTTP API v2:** Routes requests with low latency and CORS support.
3. **Lambda Execution:** Python 3.13 running Mangum ASGI adapter with container warmup handler.
4. **Amazon Bedrock:** Converse API with Anthropic Claude 3.5 Haiku / Amazon Nova Lite inference profiles (`apac.*`) for grounded supervisor explanations.
5. **Amazon Polly:** Synthesizes neural bilingual Hindi and Indian English dispatches using voice `Kajal` (with browser Web Speech API fallback).
6. **Amazon S3:** Persists shift audio dispatches and checklists with a 7-day automatic lifecycle expiration.
