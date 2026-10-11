# WorkWise (कामवाइज़)

> **Plan smarter. Work safer.**  
> Climate-aware construction task scheduling and workforce communication platform for India.

[![Tests](https://img.shields.io/badge/pytest-48%2F48%20passing%20(100%25)-emerald?style=flat-square)](workwise_engine/tests)
[![Frontend Build](https://img.shields.io/badge/frontend-built%20in%20442ms-blue?style=flat-square)](frontend)
[![Python](https://img.shields.io/badge/python-3.13-blue?style=flat-square)](https://www.python.org/)
[![React](https://img.shields.io/badge/react-19%20%2B%20vite-61dafb?style=flat-square)](https://react.dev/)
[![AWS Serverless](https://img.shields.io/badge/aws-sam%20%7C%20lambda%20%7C%20bedrock%20%7C%20polly-ff9900?style=flat-square)](template.yaml)
[![License](https://img.shields.io/badge/data%20attribution-Open--Meteo%20(CC%20BY%204.0)-lightgrey?style=flat-square)](https://open-meteo.com/)

---

## 1. Product Vision & The Problem in India

Across India, more than **50 million construction workers** operate under severe and shifting climatic hazards:
- **Extreme Semi-Arid Heat:** Northern and central regions (Delhi NCR, Rajasthan, Nagpur) regularly exceed 45°C ambient air temperatures, with intense direct solar radiation driving Wet-Bulb Globe Temperatures (WBGT) beyond survivable continuous exertion limits.
- **Oppressive Coastal & Monsoon Humidity:** Coastal hubs (Mumbai, Chennai, Kolkata) experience 33°C–36°C dry-bulb temperatures paired with 75%–88% relative humidity, where natural evaporation fails and dangerous thermal strain occurs as early as 09:30 AM.
- **Regulatory Air Quality Lockdowns:** Delhi NCR construction is governed by the **Commission for Air Quality Management (CAQM) Graded Response Action Plan (GRAP)**, where Stage III and IV mandates enforce immediate statutory bans on dust-generating construction activities.
- **Sudden Monsoon Cloudbursts:** Severe localized thunderstorms bring lightning hazards and wind gusts exceeding 40 km/h, endangering crane operations and work at height.

### The Conventional Flaw: Rigid Clock Rules
Today, supervisors rely on crude rules of thumb — typically a **fixed clock break from 12:00 to 15:00** — or unguided intuition. 
Our empirical research audit ([`docs/HISTORICAL_WBGT_RESEARCH.md`](docs/HISTORICAL_WBGT_RESEARCH.md)) using authentic Open-Meteo ERA5 reanalysis data reveals that **80.4% of shift hours outside this fixed break already breach occupational heat safety limits** for acclimatized workers (and **95.8%** for unacclimatized workers) during summer heatwaves. Workers are exposed to severe heat strain between 10:00–12:00 and 15:00–17:00, while safe indoor/shaded tasks that could proceed between 12:00 and 15:00 are shut down indiscriminately.

### The WorkWise Solution
WorkWise gives site supervisors a **mobile-first, climate-aware scheduling and communication copilot**:
1. **Dynamic Physical WBGT Modeling:** Calculates hour-by-hour heat stress using the peer-reviewed Liljegren (2008) formulation with authentic in-shade zero-solar modeling.
2. **Deterministic Constraint Scheduling:** Evaluates task prerequisites, crew capacities, equipment wind thresholds, and regulatory gates to generate defensible, workable schedules.
3. **Multimodal Field Communication:** Features bilingual voice input (Hindi & English), a spoken morning assembly audio dispatch via Amazon Polly (neural bilingual `Kajal` voice with browser fallback), a 4-tier Workability Heatmap, and an Amazon Bedrock-powered Supervisor AI Assistant (Converse API) protected by strict deterministic guardrails.

---

## 2. Core Architectural Philosophy

```
  ┌─────────────────────────────────────────────────────────────┐
  │     DETERMINISTIC SAFETY ENGINE DECIDES; AI EXPLAINS.       │
  │     NO SAFETY GUARANTEES. NO FABRICATED WEATHER DATA.       │
  └─────────────────────────────────────────────────────────────┘
```

1. **Safety Engine Decides:** Every scheduling window, work/rest ratio, and constraint gate is computed deterministically in Python against published OSHA / NIOSH continuous work screening benchmarks and statutory CAQM schedules. The AI has **zero authority** to alter thresholds or override gates.
2. **AI Explains:** Amazon Bedrock (via the Converse API with Anthropic Claude 3.5 Haiku / Nova Lite inference profiles) translates complex thermal indices into plain Hindi and English operational briefings.
3. **Strict Guardrail Filtering:** Generated explanations are validated against the ground-truth plan. Claims promising "100% safety", "zero risk", or medical cures are automatically rejected, triggering a seamless fallback to deterministic templates.
4. **Data Integrity:** Missing meteorological variables return explicit `DATA_UNAVAILABLE` states. Simulated scenario fixtures are visibly marked with `is_simulated: true`.

---

## 3. UI/UX Hierarchy (Field Operations Design)

Built specifically for high-glare sunlight on Indian construction sites using a high-contrast, warm-neutral field palette and WCAG 2.1 AA compliant 48px touch targets:

1. **Context & Baseline Weather Banner:** Site location, shift window (e.g., 06:00–18:00), total crew headcount, acclimatization status, and active CAQM GRAP stage.
2. **One-Sentence WorkWise Signature Recommendation:** A concise, authoritative operational directive placed above the heatmap answering what should change and why.
3. **Workability Heatmap (Primary Experience):** 4 standardized workload/exposure tiers across the shift:
   - **Heavy Outdoor Work (400W):** Rebar bending, trench digging, manual wheelbarrow transport.
   - **Moderate Outdoor Work (300W):** Concrete placement, pipe fitting, structural framing.
   - **Light Outdoor Work (200W):** Site inspection, equipment supervision, traffic coordination.
   - **Shaded / Indoor Work (Covered):** Prefabrication, indoor electrical, basement masonry ($SW=0, \text{Direct}=0$).
   - *State Badges:* `GO` (Screening passed), `EASE` (45:15 rest cycle), `LIMIT` (30:30 rest cycle), `STOP` (Exceeds limits / Gate blocked), `DATA_UNAVAILABLE`.
   - *Tap-to-Explain:* Tap any cell to view the exact dry-bulb temp, wet-bulb temp, globe temp, solar irradiance, threshold margin, and decision rule.
4. **Three Prioritised Operational Actions:** Concrete decision-support cards with affected hours, constraints, feasible alternatives, and an interactive **"Apply Recommendation"** button that automatically validates and regenerates the schedule.
5. **Proposed Construction Work Schedule:** Interactive Gantt timeline displaying task execution windows, crew allocation, and prerequisite resolution.
6. **Multimodal Briefing & Supervisor AI Copilot:**
   - **Audio Dispatch:** Spoken morning assembly message in Hindi (`hi-IN`) and English (`en-IN`) using Amazon Polly's neural bilingual `Kajal` voice (with browser Web Speech API fallback), variable speed control, and pre-shift checklist.
   - **Supervisor Copilot:** Ask questions about the active plan with grounded answers citing OSHA/NIOSH benchmarks.

---

## 4. Technical Specifications & Scientific Basis

### A. Physical Heat Stress Modeling
- **Algorithm:** Liljegren et al. (2008) formulation as implemented in ECMWF `thermofeel`.
- **In-Shade Modeling:** Models covered work areas by setting incoming direct and diffuse solar irradiance to $0\text{ W/m}^2$ ($SW = 0, \text{Direct} = 0$), evaluating physical convection and radiation equilibrium rather than arbitrary subtractions.
- **Fallback:** Deterministic Stull (2011) psychrometric wet-bulb formulation.
- **Zenith Angle:** Astronomical NOAA solar position algorithm with local standard meridian correction (82.5°E for IST).

### B. Published Screening Benchmarks (Continuous Work)

| Workload Category | Metabolic Rate | Acclimatized REL | Unacclimatized RAL | Guidance |
| :--- | :--- | :--- | :--- | :--- |
| **Light** | ~200 W | **30.0°C WBGT** | **28.0°C WBGT** | Continuous work under standard hydration |
| **Moderate** | ~300 W | **28.0°C WBGT** | **25.0°C WBGT** | 45 min work / 15 min rest when margin < 0°C |
| **Heavy** | ~400 W | **26.0°C WBGT** | **23.0°C WBGT** | 30 min work / 30 min rest when margin < -1.5°C |
| **Very Heavy** | ~500 W | **25.0°C WBGT** | **21.0°C WBGT** | Suspend or reschedule when margin < -3.0°C |

*Reference: National Institute for Occupational Safety and Health (NIOSH) Criteria for a Recommended Standard: Occupational Exposure to Heat and Hot Environments (DHHS/NIOSH Pub. No. 2016-106).*

### C. Regulatory & Environmental Gates
- **CAQM GRAP Schedule (Revised 28 September 2026):** Stage III and IV mandate immediate halts on dust-generating activities (`concrete`, `brickwork`, `excavation`).
- **Equipment Wind Threshold:** Configurable gust speed limits (default: 35 km/h) for crane lifts and scaffolding work.
- **Precipitation Gate:** Rain-sensitive tasks are blocked when rainfall $\ge 0.5\text{ mm/h}$ or probability $\ge 50\%$.
- **Lightning Risk Gate:** WMO thunderstorm codes (95–99) immediately trigger outdoor stop gates.

---

## 5. AWS Cloud Serverless Architecture

```
                               ┌───────────────────────────┐
                               │    Mobile Supervisor      │
                               │ (React PWA / AWS Amplify) │
                               └─────────────┬─────────────┘
                                             │ HTTPS
                                             ▼
                               ┌───────────────────────────┐
                               │  API Gateway HTTP API v2  │
                               │   (Low Latency, CORS)     │
                               └─────────────┬─────────────┘
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │    AWS Lambda Function    │
                               │    (Python 3.12 Mangum)   │
                               └──────┬─────────────┬──────┘
                                      │             │
             ┌────────────────────────┼─────────────┼────────────────────────┐
             │                        │             │                        │
             ▼                        ▼             ▼                        ▼
     ┌──────────────┐         ┌──────────────┐┌──────────────┐        ┌──────────────┐
     │  Open-Meteo  │         │Amazon Bedrock││ Amazon Polly │        │  Amazon S3   │
     │ Weather API  │         │ Nova/Claude  ││ Neural Speech│        │Audio Briefs &│
     │ (Forecasts)  │         │ Converse API ││ (Kajal Voice)│        │ Print Reports│
     └──────────────┘         └──────────────┘└──────────────┘        └──────────────┘
```

The repository includes a production-ready **AWS SAM Template** ([`template.yaml`](template.yaml)) and **Mangum ASGI Lambda Handler** ([`workwise_engine/lambda_handler.py`](workwise_engine/lambda_handler.py)):
- **`template.yaml`**: Serverless infrastructure as code defining API Gateway HTTP API v2, Python 3.12 Lambda function with IAM policies for Bedrock and Polly, and an S3 bucket with 7-day automatic lifecycle expiration.
- **`lambda_handler.py`**: ASGI bridge with container warm-up ping preservation and structured CloudWatch logging.
- **Local Runner ([`scripts/test_lambda_local.py`](scripts/test_lambda_local.py))**: Executes API Gateway v2 payloads through the Lambda handler locally without requiring AWS credentials.

---

## 6. Pre-Configured Climate Scenario Fixtures

Pre-configured Indian climate scenarios in [`data/scenarios/`](data/scenarios) enable instant demonstration and testing:
1. **Normal Summer Day (`normal.json`):** Moderate seasonal conditions with manageable midday peak.
2. **Severe Heatwave (`heatwave.json`):** 45°C+ dry-bulb heatwave with outdoor WBGT exceeding 34°C.
3. **Monsoon Hot & Humid (`monsoon.json`):** Tropical 35°C temperature paired with 85%+ relative humidity.
4. **Cloudburst & Thunderstorm (`cloudburst.json`):** Morning storm with lightning codes (95, 97) and 45 km/h gusts.
5. **Smog & GRAP Stage III (`smog_grap3.json`):** Severe pollution triggering CAQM dust-generating bans.

---

## 7. Quickstart & Local Execution

### Prerequisites
- Python 3.10+ (tested on Python 3.13)
- Node.js 18+ & npm

### 1. Start Backend Engine
```powershell
# In repository root
py -m pip install -r requirements.txt

# Start FastAPI server on port 8008
py -m uvicorn workwise_engine.api:app --host 127.0.0.1 --port 8008 --reload
```

### 2. Start Frontend Web App
```powershell
cd frontend
npm install
npm run dev
```
Open **`http://localhost:5180`** in your browser.

---

## 8. Test & Verification Suite

WorkWise maintains an automated test suite across the backend and frontend:

```powershell
# 1. Run all 49 pytest unit and integration tests (100% passing)
py -m pytest -v

# 2. Run local AWS Lambda Mangum handler verification
py scripts/test_lambda_local.py

# 3. Run historical research WBGT audit script
py scripts/historical_wbgt_audit.py

# 4. Run frontend TypeScript & production build
cd frontend
npm run build
```

---

## 9. Environment Variables

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `AWS_REGION` | `ap-south-1` | AWS region for Bedrock, Polly, and S3 |
| `BEDROCK_MODEL_ID` | `apac.amazon.nova-lite-v1:0` | Amazon Bedrock inference profile ID (Amazon Nova Lite APAC) |
| `AWS_ACCESS_KEY_ID` | *(Optional)* | AWS credentials for cloud services (falls back cleanly to local templates) |
| `AWS_SECRET_ACCESS_KEY` | *(Optional)* | AWS credentials for cloud services |
| `S3_STORAGE_BUCKET` | `workwise-briefs-...` | S3 bucket for storing generated audio files |

---

## 10. Data Attribution & Licenses

- **Weather Data:** Provided by [Open-Meteo.com](https://open-meteo.com/) under the [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/) license.
- **Physical Thermal Modeling:** Powered by the [thermofeel](https://github.com/ecmwf/thermofeel) library by the European Centre for Medium-Range Weather Forecasts (ECMWF) under the Apache 2.0 license.
- **Occupational Health Standards:** Derived from published research by NIOSH (DHHS/NIOSH Pub. No. 2016-106) and OSHA continuous work criteria.
- **Regulatory Pollution Mandates:** Commission for Air Quality Management in NCR and Adjoining Areas (CAQM), revised schedule dated 28 September 2026.
