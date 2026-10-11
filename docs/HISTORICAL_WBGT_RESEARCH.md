# WorkWise Research Report: Fixed Clock Break vs. Dynamic WBGT Screening

**Research Study Target:** Empirical Meteorological Evaluation of Construction Heat Stress Governance  
**Data Source:** Open-Meteo Historical Archive API (ERA5 Reanalysis, May 18–24, 2024 Heatwave)  
**Subject:** 12-Hour Work Shifts (06:00–18:00) Across 3 Representative Indian Climate Hubs  
**Author:** WorkWise Safety Engineering & Climate Research Team  
**Date:** 2026-10-11  

---

## 1. Executive Summary & Core Hypothesis Test

### Research Question:
Does a conventional fixed clock rule (*"Mandatory site shutdown / break from 12:00 to 15:00"*) adequately protect outdoor construction workers from heat strain, and does it unnecessarily curtail safe productive hours?

### Empirical Findings:
1. **Severe Under-Protection (The Danger Window):**
   - Out of **189 shift hours** occurring outside the conventional fixed break (06:00–12:00 and 15:00–18:00):
     - **152 hours (80.4%)** exceeded the OSHA/NIOSH continuous screening threshold for heavy work (26.0°C WBGT) for **acclimatized** workers.
     - **181 hours (95.8%)** exceeded the continuous screening threshold (23.0°C WBGT) for **unacclimatized** workers.
   - **Critical Vulnerability Hours:** In both dry and humid climates, outdoor WBGT regularly breaches 26.0°C by **10:00–11:00 AM** and remains hazardous until **16:30–17:00 PM**. Under a rigid fixed clock rule, workers are expected to perform heavy exertion during these hazardous morning and afternoon periods under an ungrounded assumption of safety.

2. **Divergence of Humid Heat (The Tropical Trap):**
   - In coastal Mumbai, ambient dry-bulb temperatures peaked at ~35.4°C, but combined with 60%–78% relative humidity, natural evaporative cooling was severely restricted, driving peak outdoor WBGT above safety limits earlier in the day.
   - In dry continental heat (Delhi & Nagpur), high direct solar irradiance drove black globe temperatures above 50°C during mid-morning, causing WBGT to peak **2 to 3 hours before** peak dry-bulb temperature.

3. **Productive Opportunity (Shaded Reallocation):**
   - Inside the mandatory 12:00–15:00 shutdown window (63 hours), **17 hours (27.0%)** met safe continuous screening limits when reallocated to **shaded / indoor tasks** (e.g., covered prefabrication, material sorting, basement conduit installation).
   - A rigid clock rule shuts down all activity indiscriminately, whereas dynamic WBGT scheduling enables safe rotational task execution.

---

## 2. City-by-City Comparative Metrics

| Climate Zone & City | Peak Ambient (°C) | Peak WBGT (°C) | Peak WBGT Hour | Hazard Hours Outside Break (Acclimatized >26.0°C) | Hazard Hours Outside Break (Unacclimatized >23.0°C) | Shaded Workable Hours During Break |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Delhi NCR (Dry Heat)** | 44.9°C (Hour 9:00) | 42.9°C (Hour 6:00) | 6:00 | **45 hrs** | **56 hrs** | 9 hrs |
| **Mumbai (Tropical Humid)** | 35.4°C (Hour 7:00) | 38.5°C (Hour 7:00) | 7:00 | **63 hrs** | **63 hrs** | 0 hrs |
| **Nagpur (Central Heat Belt)** | 43.7°C (Hour 8:00) | 53.3°C (Hour 6:00) | 6:00 | **44 hrs** | **62 hrs** | 8 hrs |

---

## 3. Scientific Methodology & Calculations

1. **Thermal Index Calculation:**
   - Evaluated using Liljegren et al. (2008) formulation as implemented in ECMWF `thermofeel`.
   - Models ambient dry-bulb temperature ($T_d$), natural wet-bulb temperature ($T_w$), black globe temperature ($T_g$) derived from direct and diffuse solar irradiance, wind speed at 10m ($v$), and surface pressure ($p$).
   - In-shade modeling sets direct solar irradiance to 0 W/m², evaluating physical convection and radiation equilibrium rather than empirical subtractions.

2. **Screening Thresholds:**
   - Benchmarked against published **OSHA / NIOSH criteria for continuous work**:
     - Light (200W): 30°C / 28°C
     - Moderate (300W): 28°C / 25°C
     - Heavy (400W): 26°C / 23°C
     - Very Heavy (500W): 25°C / 21°C
     - *[Acclimatized / Unacclimatized]*

---

## 4. Methodological Limitations & Assumptions

1. **Meteorological Grid Resolution:**
   - ERA5 reanalysis and Open-Meteo archive data provide hourly regional reanalysis. Microclimates on specific construction sites (e.g., thermal reflection from unpainted concrete, enclosed excavation pits, or localized wind shadowing from scaffolding) can elevate local heat stress beyond ambient figures.
2. **Individual Worker Physiology:**
   - Screening thresholds represent population-level benchmarks for healthy workers with adequate hydration. They do not substitute for individual biometric monitoring or clinical evaluation.
3. **Clothing Ensemble:**
   - Assumes standard lightweight construction coveralls (Clothing Adjustment Factor approximately 0°C). Specialized vapor-impermeable PPE or heavy welding leathers require downward threshold adjustments of 2 to 11°C.
