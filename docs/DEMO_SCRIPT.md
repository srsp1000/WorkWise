# WorkWise — 3-Minute Video Demo & Presentation Script

**Project:** WorkWise (कामवाइज़)  
**Tagline:** Plan smarter. Work safer.  
**Target Audience:** Construction site supervisors, project managers, safety engineers, hackathon judges.  
**Timing:** Exactly 3 Minutes (180 Seconds)

---

## Video Outline & Timestamp Guide

| Timestamp | Phase | Visual Cue | Spoken Script / Narration |
| :--- | :--- | :--- | :--- |
| **0:00 – 0:35** | **The Problem** | Opening slide & mobile browser showing Delhi construction site under 44°C sun. | *"Across India, over 50 million construction workers face extreme climate risks — from 48°C summer heatwaves in Delhi to oppressive 85% monsoon humidity in Mumbai and severe CAQM winter smog bans. Today, supervisors rely on rigid clock-time rules like 'shut down 12 to 3 PM', or pure intuition. But our historical reanalysis research reveals that over 80% to 95% of hours outside this fixed break already breach occupational heat safety limits! Workers face acute heat strain, concrete dries prematurely, and projects face massive delays. Enter WorkWise: Climate-aware construction task scheduling and worker communication. Plan smarter. Work safer."* |
| **0:35 – 1:10** | **Multimodal Input & Setup** | Screen shows `SetupPage` with Location Detector, crew sliders, and Hindi microphone button. | *"Supervisors on noisy sites cannot navigate complex dashboards. WorkWise provides seamless bilingual voice input in Hindi and English. Let's tap the microphone: '18 workers, shift 6 to 6, new unacclimatized crew, need concrete and rebar'. Watch our deterministic rule parser extract the crew size, unacclimatized status, and task durations into structured parameters with zero hallucination. The supervisor confirms with one tap. Now let's click 'CREATE TODAY'S WORK PLAN'."* |
| **1:10 – 1:55** | **Primary Experience: Workability Heatmap & Prioritized Actions** | Screen switches to `PlanPage`, showing the One-Sentence Recommendation and 4-tier Workability Heatmap. | *"In under 200 milliseconds, WorkWise's physical Liljegren WBGT engine evaluates the entire workday. Look at the primary screen: right at the top is the WorkWise Signature Recommendation. Below it is the 4-Tier Workability Heatmap — categorizing conditions into Heavy, Moderate, Light Outdoor, and Shaded Work. Green is GO, Amber is EASE with 45:15 rest, Orange is LIMIT, and Red is STOP. Notice how peak midday heat hits STOP for heavy outdoor work. Below the heatmap, WorkWise delivers 3 Prioritized Operational Actions. With one click on 'Apply Recommendation', the scheduler satisfies prerequisite constraints and reschedules concrete pour to 06:00 AM before midday peak heat."* |
| **1:55 – 2:30** | **Bilingual Dispatch & Supervisor AI Copilot** | Screen navigates to `BriefPage` and `WhyPage`. Audio plays voice brief; AI assistant responds to query. | *"Safety plans are useless if workers on site don't understand them. In the Briefing tab, WorkWise generates a localized morning assembly dispatch with audio playback in Hindi and English via Amazon Polly neural Kajal voice or browser fallback. Tap Play: 'सभी साथी ध्यान दें...'. Over on the Transparency tab, every decision is explained citing OSHA/NIOSH continuous work criteria. And our Bedrock-powered Supervisor AI Copilot answers complex site questions, like 'Why was brickwork unscheduled?'. Protected by deterministic guardrails with word-boundary and bilingual safety checks, the AI can never promise false 100% safety or alter engine limits."* |
| **2:30 – 3:00** | **Cloud Architecture & Production Validation** | Screen shows AWS architecture slide, SAM template, and test suite terminal. | *"Architected for scale, WorkWise deploys via AWS SAM: API Gateway HTTP API v2 on $default stage, Python 3.13 Lambda with Mangum ASGI, Amazon Bedrock Converse API with APAC inference profile, Polly neural Kajal voice, and S3. With 48 automated backend tests passing at 100%, frontend TypeScript verification, and an empirical research audit published, WorkWise is ready for real Indian infrastructure projects. WorkWise: Plan smarter. Work safer. Thank you!"* |

---

## Live Demo Click-Through Sequence for Evaluators

1. **Open Application:** Navigate to `http://localhost:5180` (or deployed URL).
2. **Setup Screen:**
   - Notice the pre-selected location (Delhi NCR) and baseline weather indicators.
   - Tap the **Hindi / English Voice Input** button or select the pre-loaded **Monsoon** or **Heatwave** scenario.
   - Toggle **New / Unacclimatized Crew** on to demonstrate NIOSH RAL stricter thermal thresholds.
3. **Plan Screen:**
   - Inspect the **One-Sentence Signature Directive** at the top.
   - Inspect the **4-Tier Workability Heatmap**:
     - Tap any cell to open the **Diagnostic Explainability Sheet** (inspects dry-bulb, wet-bulb, solar radiation, margin, and rule citations).
   - Scroll to **Prioritised Operational Actions** and tap **"Apply Recommendation"** to watch the schedule dynamically adapt.
   - Scroll to the **Proposed Work Schedule** Gantt view.
4. **Brief Screen:**
   - Tap **Play Spoken Briefing (Audio Dispatch)** to listen to the Hindi or English morning assembly message.
   - Inspect the **Pre-Shift Verification Checklist** and Print Layout (`Ctrl+P` preview).
5. **Why Screen & Supervisor AI Copilot:**
   - Review OSHA/NIOSH continuous work benchmarks.
   - In the **Supervisor AI Assistant** box, click the chip *"Why is Concrete pour scheduled at this time?"* to see the grounded explanation citing screening thresholds.
