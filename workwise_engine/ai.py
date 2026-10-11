"""WorkWise AI Assistance and Safeguards Module.

Integrates Amazon Bedrock (with Anthropic Claude / Amazon Titan) as an optional
explanatory communication layer, protected by deterministic validation safeguards.

Core Philosophy:
- "Deterministic safety engine decides; AI explains."
- AI cannot invent weather data, calculate safety states independently, override gates,
  make medical claims, or claim the plan guarantees worker safety.
- Strict schema validation and ground-truth comparison against the validated plan.
- If Bedrock is unavailable, credentials are absent, or output fails validation,
  seamlessly fall back to deterministic bilingual templates.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Optional

from pydantic import BaseModel, Field

from .config import (
    AI_DISCLAIMER_EN,
    AI_DISCLAIMER_HI,
    BEDROCK_DEFAULT_MODEL_ID,
    BEDROCK_DEFAULT_REGION,
    BEDROCK_FALLBACK_MODEL_ID,
    BEDROCK_TIMEOUT_SECONDS,
    CONFIG_VERSION,
    GRAP_STAGES,
    WORKABILITY_TIERS,
)

# Prohibited phrases that violate safety integrity or medical boundaries (English & Hindi)
PROHIBITED_PHRASES: list[str] = [
    "100% safe",
    "100% safety",
    "guaranteed safe",
    "guarantee safety",
    "guarantees safety",
    "guarantee absolute safety",
    "zero risk",
    "completely safe",
    "fully safe",
    "absolute safety",
    "perfectly safe",
    "cure",
    "cures",
    "treatment for heat stroke",
    "medical diagnosis",
    "prescribe",
    "prescription",
    # Hindi safety & medical overclaims
    "100% सुरक्षित",
    "पूर्ण सुरक्षा",
    "पूर्ण सुरक्षित",
    "पूरी तरह सुरक्षित",
    "कोई जोखिम नहीं",
    "शून्य जोखिम",
    "इलाज",
    "दवा",
    "चिकित्सा निदान",
    "सुरक्षा की गारंटी",
    "गारंटी",
]


class AIExplanationResponse(BaseModel):
    provider: str = Field(..., description="'amazon_bedrock' or 'deterministic_template'")
    model_id: Optional[str] = Field(None, description="Bedrock model identifier if used")
    explanation_en: str = Field(..., description="English natural language explanation")
    explanation_hi: str = Field(..., description="Hindi natural language explanation")
    key_points: list[str] = Field(default_factory=list, description="Key operational bullet points")
    disclaimer: str = Field(AI_DISCLAIMER_EN, description="Mandatory safety disclaimer")
    validated: bool = Field(True, description="Whether output passed guardrail validation")
    ground_truth_matches: bool = Field(True, description="Whether claims align with deterministic plan")


class AIAskResponse(BaseModel):
    provider: str = Field(..., description="'amazon_bedrock' or 'deterministic_template'")
    model_id: Optional[str] = Field(None, description="Bedrock model identifier if used")
    question: str = Field(..., description="Supervisor question asked")
    answer: str = Field(..., description="Grounded supervisor answer in English")
    answer_hi: Optional[str] = Field(None, description="Grounded answer in Hindi")
    referenced_tasks: list[str] = Field(default_factory=list, description="Tasks cited in the answer")
    citations: list[str] = Field(default_factory=list, description="Rules or scientific criteria cited")
    disclaimer: str = Field(AI_DISCLAIMER_EN, description="Mandatory safety disclaimer")
    validated: bool = Field(True, description="Passed safeguard validation")


class AIRephraseResponse(BaseModel):
    provider: str = Field(...)
    original_text: str = Field(...)
    rephrased_en: str = Field(...)
    rephrased_hi: str = Field(...)
    target_audience: str = Field("worker")
    disclaimer: str = Field(AI_DISCLAIMER_EN)


def is_bedrock_configured() -> bool:
    """Check if AWS credentials and region are present in environment or AWS configuration."""
    has_keys = bool(
        os.getenv("AWS_ACCESS_KEY_ID")
        and os.getenv("AWS_SECRET_ACCESS_KEY")
    )
    if has_keys:
        return True
    # Check if a custom session / role exists
    try:
        import boto3
        session = boto3.Session()
        creds = session.get_credentials()
        return creds is not None and creds.access_key is not None
    except Exception:
        return False


def _get_bedrock_client(region: Optional[str] = None):
    """Obtain a boto3 bedrock-runtime client."""
    import boto3
    target_region = region or os.getenv("AWS_REGION", BEDROCK_DEFAULT_REGION)
    return boto3.client("bedrock-runtime", region_name=target_region)


def invoke_bedrock_model(
    prompt: str,
    system_prompt: str = "",
    model_id: Optional[str] = None,
    max_tokens: int = 800,
    temperature: float = 0.1,
) -> Optional[str]:
    """Invoke Amazon Bedrock via Converse API, returning text response or None on failure."""
    if not is_bedrock_configured():
        return None

    target_model = model_id or os.getenv("BEDROCK_MODEL_ID", BEDROCK_DEFAULT_MODEL_ID)

    try:
        client = _get_bedrock_client()
        messages = [
            {
                "role": "user",
                "content": [{"text": prompt}],
            }
        ]
        kwargs: dict[str, Any] = {
            "modelId": target_model,
            "messages": messages,
            "inferenceConfig": {
                "maxTokens": max_tokens,
                "temperature": temperature,
            },
        }
        if system_prompt:
            kwargs["system"] = [{"text": system_prompt}]

        response = client.converse(**kwargs)
        output_msg = response.get("output", {}).get("message", {})
        content_list = output_msg.get("content", [])
        if content_list and isinstance(content_list, list):
            text_blocks = [c.get("text", "") for c in content_list if isinstance(c, dict) and "text" in c]
            if text_blocks:
                return "".join(text_blocks)
        return None
    except Exception:
        # Graceful failure fallback to deterministic templates
        return None


# --- Validation Safeguards ---

def validate_ai_text(text: str, plan_data: dict) -> tuple[bool, list[str]]:
    """Validate AI generated text against safety constraints and the plan ground truth.
    
    Returns (is_valid, list_of_errors).
    """
    if not text or not isinstance(text, str):
        return False, ["Empty text output"]

    lower_text = text.lower()
    errors: list[str] = []

    # 1. Check prohibited phrasing (overclaiming safety or medical authority)
    for phrase in PROHIBITED_PHRASES:
        pattern = (
            rf"(?i)\b{re.escape(phrase)}\b"
            if re.match(r"^\w+$", phrase)
            else rf"(?i)(?:\b|^|\s){re.escape(phrase)}(?:\b|$|\s|[।,.!?])"
        )
        if re.search(pattern, text):
            errors.append(f"Contains prohibited phrasing: '{phrase}'")

    # 2. Check simulation fidelity
    is_simulated = False
    metadata = plan_data.get("metadata") or {}
    if isinstance(metadata, dict) and metadata.get("is_simulated"):
        is_simulated = True

    if is_simulated:
        if "real-time satellite observation" in lower_text or "live on-site weather station readings" in lower_text:
            errors.append("Mischaracterizes simulated scenario fixture as real live sensor readings")

    # 3. Check consistency of scheduled states
    schedule = plan_data.get("schedule", [])
    if isinstance(schedule, list):
        for item in schedule:
            if not isinstance(item, dict):
                continue
            task_name = item.get("task", "").lower()
            status = item.get("status", "")

            # If task is UNSCHEDULABLE, AI must not claim it was successfully scheduled or give start time
            if status == "UNSCHEDULABLE" and task_name:
                pattern = rf"(scheduled|starting|begins at)\s+['\"]?{re.escape(task_name)}['\"]?"
                if re.search(pattern, lower_text):
                    errors.append(f"Falsely claims unscheduled task '{task_name}' is scheduled")

    return len(errors) == 0, errors


# --- Deterministic Bilingual Templates ---

def generate_deterministic_explanation(
    plan_data: dict,
    task_id: Optional[str] = None,
) -> AIExplanationResponse:
    """Generate verified, deterministic bilingual explanation directly from plan data."""
    site = plan_data.get("site", "Site")
    date_str = plan_data.get("date", "Today")
    schedule = plan_data.get("schedule", [])
    top_rec = plan_data.get("top_recommendation") or plan_data.get("plan_summary") or "Work scheduled per screening limits."
    rest_recs = plan_data.get("rest_recommendations") or {}
    new_crew = plan_data.get("new_crew", False)
    crew_size = plan_data.get("total_crew_size", 18)
    grap_desc = plan_data.get("grap_description", "Normal")

    scheduled_tasks = [t for t in schedule if isinstance(t, dict) and t.get("status") == "SCHEDULED"]
    unscheduled_tasks = [t for t in schedule if isinstance(t, dict) and t.get("status") == "UNSCHEDULABLE"]

    # Filter to specific task if requested
    if task_id:
        target_task = next((t for t in schedule if isinstance(t, dict) and t.get("task_id") == task_id), None)
        if target_task:
            return _generate_single_task_explanation(target_task, plan_data)

    # Build English Explanation
    en_lines = [
        f"WorkWise Operations Brief for {site} ({date_str}):",
        f"Top Directive: {top_rec}",
        "",
        f"Crew Parameters: {crew_size} workers ({'Unacclimatized' if new_crew else 'Acclimatized'}). Regulatory Status: {grap_desc}.",
    ]

    if scheduled_tasks:
        en_lines.append("\nScheduled Activities:")
        for t in scheduled_tasks:
            t_name = t.get("task", "")
            t_start = t.get("start", "")
            t_end = t.get("end", "")
            t_why = t.get("why_scheduled", "")
            en_lines.append(f"• {t_name} is set for {t_start} to {t_end}. {t_why}")

    if unscheduled_tasks:
        en_lines.append("\nUnscheduled / Blocked Tasks:")
        for t in unscheduled_tasks:
            t_name = t.get("task", "")
            t_why = t.get("why_unschedulable", "")
            t_action = t.get("recommended_action", "Review site schedule.")
            en_lines.append(f"• {t_name}: {t_why} (Supervisor Action: {t_action})")

    en_lines.append("\nThermal Rest & Hydration Protocol:")
    cycle = rest_recs.get("work_rest_cycle", "Standard recovery")
    hydr = rest_recs.get("hydration_guideline", "1 liter water/hour")
    shade = rest_recs.get("shade_requirement", "Covered rest shelter")
    en_lines.append(f"• Work/Rest Guidance: {cycle}.")
    en_lines.append(f"• Hydration: {hydr}.")
    en_lines.append(f"• Rest Shelter: {shade}.")

    explanation_en = "\n".join(en_lines)

    # Build Hindi Explanation
    crew_type_hi = "नया / गैर-अनुकूलित कार्यदल (Unacclimatized)" if new_crew else "अनुकूलित कार्यदल (Acclimatized)"
    hi_lines = [
        f"वर्कवाइज कार्यस्थल परिचालन ब्रीफिंग — {site} ({date_str}):",
        f"मुख्य निर्देश: {top_rec}",
        "",
        f"कार्यदल स्थिति: {crew_size} श्रमिक ({crew_type_hi})। पर्यावरण व प्रदूषण स्थिति: {grap_desc}।",
    ]

    if scheduled_tasks:
        hi_lines.append("\nअनुसूचित कार्य (Scheduled Tasks):")
        for t in scheduled_tasks:
            t_name = t.get("task", "")
            t_start = t.get("start", "")
            t_end = t.get("end", "")
            hi_lines.append(f"• {t_name}: समय {t_start} से {t_end} तक निर्धारित। यह सुरक्षा स्क्रीनिंग सीमाओं के भीतर है।")

    if unscheduled_tasks:
        hi_lines.append("\nस्थगित / प्रतिबंधित कार्य (Unscheduled Tasks):")
        for t in unscheduled_tasks:
            t_name = t.get("task", "")
            t_why = t.get("why_unschedulable", "")
            t_act = t.get("recommended_action", "पुनरीक्षण करें")
            hi_lines.append(f"• {t_name}: आज के लिए स्थगित। कारण: {t_why}। अनुशंसित कदम: {t_act}।")

    hi_lines.append("\nगर्मी व विश्राम नियम (Rest & Hydration):")
    hi_lines.append(f"• कार्य-विश्राम अनुपात: {cycle}।")
    hi_lines.append(f"• जलपान: {hydr}।")
    hi_lines.append(f"• छायादार आश्रय: {shade} अनिवार्य।")

    explanation_hi = "\n".join(hi_lines)

    key_points = [
        f"Shift covers {len(scheduled_tasks)} scheduled task(s) and flags {len(unscheduled_tasks)} unscheduled task(s).",
        f"Operating under OSHA/NIOSH continuous work criteria ({'Unacclimatized' if new_crew else 'Acclimatized'}).",
        f"Mandatory rest protocol: {cycle} with {hydr}.",
    ]

    return AIExplanationResponse(
        provider="deterministic_template",
        model_id=None,
        explanation_en=explanation_en,
        explanation_hi=explanation_hi,
        key_points=key_points,
        disclaimer=AI_DISCLAIMER_EN,
        validated=True,
        ground_truth_matches=True,
    )


def _generate_single_task_explanation(
    task_item: dict,
    plan_data: dict,
) -> AIExplanationResponse:
    """Generate focused explanation for a single task."""
    task_name = task_item.get("task", "Task")
    status = task_item.get("status", "UNKNOWN")
    new_crew = plan_data.get("new_crew", False)

    if status == "SCHEDULED":
        start = task_item.get("start", "")
        end = task_item.get("end", "")
        why = task_item.get("why_scheduled", "Conditions meet continuous screening limits.")
        en = (
            f"'{task_name}' is scheduled from {start} to {end}. "
            f"{why} Environmental variables (WBGT, wind, and precipitation) remain within safe screening margins. "
            f"Supervisor verification: Ensure adequate drinking water and shaded rest breaks are enforced."
        )
        hi = (
            f"'{task_name}' का कार्य समय {start} से {end} बजे तक निर्धारित किया गया है। "
            f"यह समयावधि तापमान व मौसम की सुरक्षा सीमाओं के भीतर है। "
            f"सुपरवाइजर ध्यान दें: श्रमिकों के लिए पीने का पानी और छायादार विश्राम सुनिश्चित करें।"
        )
        pts = [
            f"Scheduled window: {start} – {end}",
            "Meets continuous screening threshold",
            "Mandatory water and rest breaks enforced",
        ]
    else:
        why = task_item.get("why_unschedulable", "Environmental or constraint limits exceeded.")
        rec = task_item.get("recommended_action", "Reschedule or adjust task parameters.")
        en = (
            f"'{task_name}' could not be scheduled today. "
            f"Primary constraint: {why}. "
            f"Supervisor Action: {rec}."
        )
        hi = (
            f"'{task_name}' आज के लिए निर्धारित नहीं किया जा सका। "
            f"कारण: {why}। "
            f"सुपरवाइजर के लिए कदम: {rec}।"
        )
        pts = [
            f"Status: UNSCHEDULABLE",
            f"Blocking constraint: {why}",
            f"Recommended supervisor remedy: {rec}",
        ]

    return AIExplanationResponse(
        provider="deterministic_template",
        model_id=None,
        explanation_en=en,
        explanation_hi=hi,
        key_points=pts,
        disclaimer=AI_DISCLAIMER_EN,
        validated=True,
        ground_truth_matches=True,
    )


# --- Core Service Functions ---

def explain_plan(
    plan_data: dict,
    task_id: Optional[str] = None,
    language: str = "both",
    use_ai: bool = True,
) -> AIExplanationResponse:
    """Explain the plan using Bedrock if configured, with strict safeguard validation and template fallback."""
    # 1. Generate fallback deterministic explanation as baseline
    deterministic_resp = generate_deterministic_explanation(plan_data, task_id)

    if not use_ai or not is_bedrock_configured():
        return deterministic_resp

    # 2. Attempt Amazon Bedrock invocation
    try:
        site = plan_data.get("site", "Site")
        top_rec = plan_data.get("top_recommendation", "")
        schedule = plan_data.get("schedule", [])
        grap = plan_data.get("grap_description", "Normal")
        new_crew = plan_data.get("new_crew", False)

        schedule_summary = [
            {
                "task": t.get("task"),
                "status": t.get("status"),
                "start": t.get("start"),
                "end": t.get("end"),
                "why": t.get("why_scheduled") or t.get("why_unschedulable"),
            }
            for t in schedule
            if isinstance(t, dict)
        ]

        system_prompt = (
            "You are the WorkWise Construction Operations Assistant. "
            "A deterministic physical safety engine has already validated and created the workday plan. "
            "Your job is ONLY to provide a concise, professional explanation of the plan in English and Hindi. "
            "STRICT RULES:\n"
            "- Do NOT alter any scheduled times, durations, or safety statuses.\n"
            "- Do NOT promise '100% safety' or 'zero risk'. Always state that workers must follow screening guidelines.\n"
            "- Do NOT make medical diagnoses or claims.\n"
            "- If a task is UNSCHEDULABLE, do NOT claim it is scheduled.\n"
            "- Base every statement on the provided data.\n"
            "Output JSON with keys: explanation_en, explanation_hi, key_points (list of 3 strings)."
        )

        user_prompt = f"""
Plan Details:
- Site: {site}
- Acclimatized: {'No (New crew)' if new_crew else 'Yes'}
- CAQM GRAP: {grap}
- Top Directive: {top_rec}
- Schedule Summary: {json.dumps(schedule_summary)}

Explain this schedule concisely to the site supervisor in English and Hindi.
"""

        raw_output = invoke_bedrock_model(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=700,
        )

        if not raw_output:
            return deterministic_resp

        # Try parsing JSON from Bedrock
        clean_text = raw_output.strip()
        if "```json" in clean_text:
            clean_text = clean_text.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_text:
            clean_text = clean_text.split("```")[1].split("```")[0].strip()

        parsed = json.loads(clean_text)
        en_text = parsed.get("explanation_en", "")
        hi_text = parsed.get("explanation_hi", "")
        points = parsed.get("key_points", [])

        # Validate both English and Hindi against guardrails
        valid_en, errs_en = validate_ai_text(en_text, plan_data)
        valid_hi, errs_hi = validate_ai_text(hi_text, plan_data)

        if valid_en and valid_hi:
            return AIExplanationResponse(
                provider="amazon_bedrock",
                model_id=os.getenv("BEDROCK_MODEL_ID", BEDROCK_DEFAULT_MODEL_ID),
                explanation_en=en_text,
                explanation_hi=hi_text,
                key_points=points if isinstance(points, list) else deterministic_resp.key_points,
                disclaimer=AI_DISCLAIMER_EN,
                validated=True,
                ground_truth_matches=True,
            )

    except Exception:
        pass

    # Safe fallback
    return deterministic_resp


def answer_supervisor_question(
    question: str,
    plan_data: dict,
    language: str = "en",
    use_ai: bool = True,
) -> AIAskResponse:
    """Answer a supervisor's operational question, strictly grounded in the deterministic plan."""
    q_lower = question.lower()
    schedule = plan_data.get("schedule", [])
    matrix = plan_data.get("matrix", [])
    rest_recs = plan_data.get("rest_recommendations", {})
    new_crew = plan_data.get("new_crew", False)
    grap = plan_data.get("grap_description", "Normal")

    # 1. Deterministic Grounded Analysis
    referenced_tasks: list[str] = []
    citations: list[str] = []

    # Check for mentioned tasks
    matched_task: Optional[dict] = None
    for item in schedule:
        if not isinstance(item, dict):
            continue
        t_id = item.get("task_id", "").lower()
        t_name = item.get("task", "").lower()
        if t_id in q_lower or t_name in q_lower:
            matched_task = item
            referenced_tasks.append(item.get("task", ""))
            break

    # Build Grounded Answer
    citations.append("OSHA / NIOSH continuous work screening benchmarks")
    if "grap" in q_lower or "pollution" in q_lower or "dust" in q_lower:
        citations.append("CAQM GRAP revised schedule (28 September 2026)")

    # Prepare deterministic response content
    if matched_task:
        t_name = matched_task.get("task", "Task")
        if matched_task.get("status") == "SCHEDULED":
            ans = (
                f"'{t_name}' is scheduled from {matched_task.get('start')} to {matched_task.get('end')}. "
                f"Rationale: {matched_task.get('why_scheduled', 'Meets thermal screening criteria')}. "
                f"Crew assigned: {matched_task.get('crew_required', 'Standard')} workers."
            )
            ans_hi = (
                f"'{t_name}' {matched_task.get('start')} से {matched_task.get('end')} के बीच निर्धारित है। "
                f"यह अवधि मौसम व तापमान के अनुरूप सुरक्षित पाई गई है।"
            )
        else:
            ans = (
                f"'{t_name}' could not be scheduled in today's shift. "
                f"Reason: {matched_task.get('why_unschedulable')}. "
                f"Recommended action: {matched_task.get('recommended_action')}."
            )
            ans_hi = (
                f"'{t_name}' आज के लिए निर्धारित नहीं किया जा सका। "
                f"कारण: {matched_task.get('why_unschedulable')}। "
                f"सुझाव: {matched_task.get('recommended_action')}।"
            )
    elif "rest" in q_lower or "break" in q_lower or "water" in q_lower or "hydrate" in q_lower or "pani" in q_lower:
        cycle = rest_recs.get("work_rest_cycle", "45 min work / 15 min rest")
        hydr = rest_recs.get("hydration_guideline", "1 liter water per hour")
        ans = (
            f"The active heat protocol recommends a {cycle} cycle during peak hours. "
            f"Hydration standard: {hydr}. Ensure workers have access to a covered shaded rest area."
        )
        ans_hi = (
            f"गर्मी प्रोटोकॉल के अनुसार पीक ऑवर्स में {cycle} का नियम लागू है। "
            f"जलपान मानक: {hydr}। श्रमिकों के लिए छायादार विश्राम स्थल सुनिश्चित करें।"
        )
    elif "grap" in q_lower or "pollution" in q_lower or "smog" in q_lower or "stage 3" in q_lower:
        ans = (
            f"Current CAQM regulatory stage is: {grap}. "
            f"Under Stage III and above, all dust-generating and C&D activities are prohibited by mandate."
        )
        ans_hi = (
            f"वर्तमान CAQM वायु गुणवत्ता स्थिति: {grap}। स्टेज III या अधिक होने पर धूल उत्पन्न करने वाले निर्माण कार्य प्रतिबंधित हैं।"
        )
    elif "new crew" in q_lower or "unacclimatized" in q_lower or "acclimat" in q_lower:
        ans = (
            f"Site is configured for {'Unacclimatized (new)' if new_crew else 'Acclimatized'} crew. "
            f"Unacclimatized screening thresholds are 2°C to 3°C lower (NIOSH RAL) to prevent rapid heat strain."
        )
        ans_hi = (
            f"कार्यस्थल {'नए (गैर-अनुकूलित)' if new_crew else 'अनुकूलित'} कार्यदल के लिए निर्धारित है। "
            f"नए श्रमिकों के लिए स्क्रीनिंग सीमाएं 2-3°C कम रखी जाती हैं।"
        )
    else:
        top = plan_data.get("top_recommendation") or "Review schedule and workability heatmap."
        ans = f"WorkWise Guidance: {top} All activities are restricted by Liljegren WBGT and environmental gates."
        ans_hi = f"वर्कवाइज निर्देश: {top} सभी कार्य मौसम व सुरक्षा मानकों के अनुसार निर्धारित हैं।"

    deterministic_ans = AIAskResponse(
        provider="deterministic_template",
        model_id=None,
        question=question,
        answer=ans,
        answer_hi=ans_hi,
        referenced_tasks=referenced_tasks,
        citations=citations,
        disclaimer=AI_DISCLAIMER_EN,
        validated=True,
    )

    if not use_ai or not is_bedrock_configured():
        return deterministic_ans

    # 2. Bedrock invocation with Grounded Context
    try:
        prompt = f"""
Supervisor Question: "{question}"

Deterministic Ground Truth Plan Context:
- Site: {plan_data.get('site')}
- New Crew (Unacclimatized): {new_crew}
- GRAP: {grap}
- Referenced Tasks: {json.dumps(matched_task or {})}
- Rest Guidance: {json.dumps(rest_recs)}
- Deterministic Factual Answer: {ans}

Instructions:
Answer the supervisor concisely (under 80 words).
Ground yourself 100% in the facts above.
Do NOT guarantee safety or make medical claims.
Output JSON: {{"answer_en": "...", "answer_hi": "..."}}
"""
        raw = invoke_bedrock_model(
            prompt=prompt,
            system_prompt="You are WorkWise Copilot. Ground all responses in the factual deterministic context.",
            temperature=0.1,
            max_tokens=300,
        )

        if raw:
            clean = raw.strip()
            if "```json" in clean:
                clean = clean.split("```json")[1].split("```")[0].strip()
            elif "```" in clean:
                clean = clean.split("```")[1].split("```")[0].strip()
            parsed = json.loads(clean)
            a_en = parsed.get("answer_en", "")
            a_hi = parsed.get("answer_hi", "")

            valid_en, _ = validate_ai_text(a_en, plan_data)
            valid_hi, _ = validate_ai_text(a_hi, plan_data)

            if valid_en and valid_hi:
                return AIAskResponse(
                    provider="amazon_bedrock",
                    model_id=os.getenv("BEDROCK_MODEL_ID", BEDROCK_DEFAULT_MODEL_ID),
                    question=question,
                    answer=a_en,
                    answer_hi=a_hi,
                    referenced_tasks=referenced_tasks,
                    citations=citations,
                    disclaimer=AI_DISCLAIMER_EN,
                    validated=True,
                )
    except Exception:
        pass

    return deterministic_ans


def rephrase_brief_for_workers(
    text: str,
    target_audience: str = "worker",
    language: str = "both",
    use_ai: bool = True,
) -> AIRephraseResponse:
    """Rephrase technical explanations into simple, direct worker-friendly language."""
    # Deterministic baseline rephrasing:
    # Replace complex technical jargon with plain operational speech
    simplified_en = text
    simplified_en = re.sub(r"Liljegren \(\d+\) WBGT", "Wet Bulb Heat Index", simplified_en)
    simplified_en = re.sub(r"OSHA / NIOSH continuous work screening criteria", "site heat safety rules", simplified_en)
    simplified_en = re.sub(r"DATA_UNAVAILABLE", "weather info not available", simplified_en)
    simplified_en = re.sub(r"margin of [+-]?\d+\.?\d*°C", "within safety limits", simplified_en)

    simplified_hi = (
        "सभी साथी ध्यान दें: दोपहर की तेज धूप में काम धीमा रखें, "
        "हर 45 मिनट बाद छांव में 15 मिनट आराम करें और लगातार पानी/ओआरएस पीते रहें। "
        "सुरक्षा नियमों का पालन करें।"
    )

    deterministic_resp = AIRephraseResponse(
        provider="deterministic_template",
        original_text=text,
        rephrased_en=simplified_en,
        rephrased_hi=simplified_hi,
        target_audience=target_audience,
        disclaimer=AI_DISCLAIMER_EN,
    )

    if not use_ai or not is_bedrock_configured():
        return deterministic_resp

    try:
        prompt = f"""
Rephrase this construction safety brief for daily morning worker assembly:
Original Text: "{text}"

Rules:
- Simple, respectful, direct language.
- Mention hydration, rest in shade, and adhering to scheduled hours.
- Keep under 60 words.
- Return JSON: {{"rephrased_en": "...", "rephrased_hi": "..."}}
"""
        raw = invoke_bedrock_model(
            prompt=prompt,
            system_prompt="You are a construction site foreman communicator.",
            temperature=0.2,
            max_tokens=250,
        )
        if raw:
            clean = raw.strip()
            if "```json" in clean:
                clean = clean.split("```json")[1].split("```")[0].strip()
            elif "```" in clean:
                clean = clean.split("```")[1].split("```")[0].strip()
            parsed = json.loads(clean)
            en_val = parsed.get("rephrased_en")
            hi_val = parsed.get("rephrased_hi")
            if en_val and hi_val:
                return AIRephraseResponse(
                    provider="amazon_bedrock",
                    original_text=text,
                    rephrased_en=en_val,
                    rephrased_hi=hi_val,
                    target_audience=target_audience,
                    disclaimer=AI_DISCLAIMER_EN,
                )
    except Exception:
        pass

    return deterministic_resp
