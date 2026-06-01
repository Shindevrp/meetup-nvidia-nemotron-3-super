from __future__ import annotations

import json
import os
import re
from typing import Any, List, Optional, Tuple

import httpx

from models.schemes import (
    get_schemes_cache,
)

SCHEMES_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "schemes")

LANG_MAP = {
    "english": "en",
    "hindi": "hi",
    "telugu": "te",
    "tamil": "ta",
    "bengali": "bn",
    "marathi": "mr",
}

LANG_INSTRUCTIONS = {
    "english": "Respond in English.",
    "hindi": "Respond in Hindi (हिंदी).",
    "telugu": "Respond in Telugu (తెలుగు).",
    "tamil": "Respond in Tamil (தமிழ்).",
    "bengali": "Respond in Bengali (বাংলা).",
    "marathi": "Respond in Marathi (मराठी).",
}

_GREETING_PATTERN = re.compile(
    r"^(hi|hello|hey|namaste|नमस्ते|हाय|నమస్కారం|வணக்கம்|নমস্কার|नमस्कार|thanks|thank you|bye|goodbye|what can you do|help)$",
    re.IGNORECASE,
)

_BROAD_QUERY_PATTERN = re.compile(
    r"(what|which|all|any|every|list|show|tell).*(scheme|benefit|eligible|welfare|yojana|apply)",
    re.IGNORECASE,
)


def _call_llm(
    messages: List[dict],
    httpx_client: httpx.AsyncClient,
    api_key: str,
    api_url: str,
    model_name: str,
    app_url: str,
    app_title: str,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    response_format: Optional[dict] = None,
) -> dict:
    body = {
        "model": model_name,
        "messages": messages,
        "temperature": temperature,
        "top_p": 0.95,
        "max_tokens": max_tokens,
    }
    if response_format:
        body["response_format"] = response_format
    return {
        "model": model_name,
        "messages": messages,
        "temperature": temperature,
        "top_p": 0.95,
        "max_tokens": max_tokens,
        **(response_format or {}),
    }


async def _llm_completion(
    messages: List[dict],
    httpx_client: httpx.AsyncClient,
    api_key: str,
    api_url: str,
    model_name: str,
    app_url: str,
    app_title: str,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    response_format: Optional[dict] = None,
) -> str:
    body = {
        "model": model_name,
        "messages": messages,
        "temperature": temperature,
        "top_p": 0.95,
        "max_tokens": max_tokens,
    }
    if response_format:
        body["response_format"] = response_format

    resp = await httpx_client.post(
        f"{api_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": app_url,
            "X-Title": app_title,
        },
        json=body,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


async def decompose_query(
    message: str,
    language: str,
    httpx_client: httpx.AsyncClient,
    api_key: str,
    api_url: str,
    model_name: str,
    app_url: str,
    app_title: str,
) -> List[str]:
    lang_instr = LANG_INSTRUCTIONS.get(language, LANG_INSTRUCTIONS["english"])
    prompt = (
        f"{lang_instr}\n\n"
        "The user is asking about Indian government welfare schemes. "
        "If their question is broad (covers multiple schemes or asks 'which schemes am I eligible for'), "
        "break it into 2-4 specific sub-questions that can each be answered from a single scheme document. "
        "If the question is already specific, return only the original question.\n\n"
        "Return a JSON array of strings. Example: "
        '["What is the income limit for PM-KISAN?", "What are the eligibility criteria for Ayushman Bharat?"]\n\n'
        f"User question: {message}"
    )
    try:
        result = await _llm_completion(
            messages=[{"role": "user", "content": prompt}],
            httpx_client=httpx_client,
            api_key=api_key,
            api_url=api_url,
            model_name=model_name,
            app_url=app_url,
            app_title=app_title,
            max_tokens=512,
            response_format={"type": "json_object"},
        )
        questions = json.loads(result)
        if isinstance(questions, list) and len(questions) > 0:
            return questions
    except Exception:
        pass
    return [message]


async def summarize_history(
    history: List[dict],
    language: str,
    httpx_client: httpx.AsyncClient,
    api_key: str,
    api_url: str,
    model_name: str,
    app_url: str,
    app_title: str,
) -> str:
    lang_instr = LANG_INSTRUCTIONS.get(language, LANG_INSTRUCTIONS["english"])
    transcript = "\n".join(
        f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content'][:200]}"
        for m in history
    )
    prompt = (
        f"{lang_instr}\n\n"
        "Summarize the following conversation about Indian government welfare schemes. "
        "Include: which schemes were discussed, what eligibility questions were asked, "
        "and what information was provided. Keep it under 100 words.\n\n"
        f"CONVERSATION:\n{transcript}\n\nSUMMARY:"
    )
    try:
        return await _llm_completion(
            messages=[{"role": "user", "content": prompt}],
            httpx_client=httpx_client,
            api_key=api_key,
            api_url=api_url,
            model_name=model_name,
            app_url=app_url,
            app_title=app_title,
            max_tokens=300,
            temperature=0.5,
        )
    except Exception:
        return ""


async def generate_followup_questions(
    message: str,
    reply: str,
    language: str,
    httpx_client: httpx.AsyncClient,
    api_key: str,
    api_url: str,
    model_name: str,
    app_url: str,
    app_title: str,
) -> List[str]:
    lang_instr = LANG_INSTRUCTIONS.get(language, LANG_INSTRUCTIONS["english"])
    prompt = (
        f"{lang_instr}\n\n"
        "Based on the following conversation about Indian government welfare schemes, "
        "suggest 3 relevant follow-up questions the user might want to ask next. "
        "Return a JSON array of strings.\n\n"
        f'User: {message}\nAssistant: {reply}\n\n'
        '["question 1?", "question 2?", "question 3?"]'
    )
    try:
        result = await _llm_completion(
            messages=[{"role": "user", "content": prompt}],
            httpx_client=httpx_client,
            api_key=api_key,
            api_url=api_url,
            model_name=model_name,
            app_url=app_url,
            app_title=app_title,
            max_tokens=512,
            response_format={"type": "json_object"},
        )
        questions = json.loads(result)
        if isinstance(questions, list) and len(questions) > 0:
            return questions[:3]
    except Exception:
        pass
    return []


async def explain_eligibility(
    profile: dict,
    results: List[dict],
    scheme_details: dict,
    language: str,
    httpx_client: httpx.AsyncClient,
    api_key: str,
    api_url: str,
    model_name: str,
    app_url: str,
    app_title: str,
) -> dict:
    lang_instr = LANG_INSTRUCTIONS.get(language, LANG_INSTRUCTIONS["english"])
    profile_str = "\n".join(f"  {k}: {v}" for k, v in profile.items() if v is not None and v != "" and v is not False)
    results_str = ""
    for r in results:
        detail = scheme_details.get(r["scheme_id"], {})
        results_str += (
            f"\n- {r['name']} (id: {r['scheme_id']})\n"
            f"  Match: {'YES' if r['match'] else 'NO'} (confidence: {r['confidence']})\n"
            f"  Ministry: {detail.get('ministry', 'N/A')}\n"
            f"  Summary: {detail.get('summary', 'N/A')[:200]}\n"
            f"  Benefits: {'; '.join(detail.get('benefits', [])[:3])}\n"
            f"  Reasons: {'; '.join(r['reasons']) if r['reasons'] else 'All criteria met'}\n"
        )

    prompt = (
        f"{lang_instr}\n\n"
        "You are an expert on Indian government welfare schemes. "
        "Based on the user's profile and the eligibility results, generate:\n"
        "1. A personalized plain-language explanation of which schemes they qualify for and why\n"
        "2. For matched schemes: what benefits they can expect and next steps to apply\n"
        "3. For unmatched schemes: what specific criteria they don't meet and whether they might qualify in future\n"
        "4. An overall recommendation on the best scheme to apply for first\n\n"
        f"USER PROFILE:\n{profile_str}\n\n"
        f"ELIGIBILITY RESULTS:\n{results_str}\n\n"
        "Return a JSON object with keys: "
        '"explanation" (string, 3-5 sentences), '
        '"best_scheme" (string, scheme name), '
        '"next_steps" (array of strings, 3 items), '
        '"improvement_tips" (array of strings, 2-3 items if any schemes were not matched).'
    )
    try:
        result = await _llm_completion(
            messages=[{"role": "user", "content": prompt}],
            httpx_client=httpx_client,
            api_key=api_key,
            api_url=api_url,
            model_name=model_name,
            app_url=app_url,
            app_title=app_title,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )
        return json.loads(result)
    except Exception:
        return {
            "explanation": f"Analysis available. You matched {len([r for r in results if r['match']])} out of {len(results)} schemes.",
            "best_scheme": "",
            "next_steps": ["Review the eligibility results above", "Visit the scheme portal for details", "Contact your nearest CSC for assistance"],
            "improvement_tips": [],
        }


async def compare_schemes_llm(
    scheme_a: dict,
    scheme_b: dict,
    language: str,
    httpx_client: httpx.AsyncClient,
    api_key: str,
    api_url: str,
    model_name: str,
    app_url: str,
    app_title: str,
) -> dict:
    lang_instr = LANG_INSTRUCTIONS.get(language, LANG_INSTRUCTIONS["english"])

    def fmt(s):
        return (
            f"Name: {s.get('name', 'N/A')}\n"
            f"Ministry: {s.get('ministry', 'N/A')}\n"
            f"Type: {s.get('type', 'N/A')}\n"
            f"Summary: {s.get('summary', 'N/A')}\n"
            f"Benefits: {'; '.join(s.get('benefits', []))}\n"
            f"Who Can Apply: {'; '.join((s.get('eligibility') or {}).get('who_can_apply', []))}\n"
            f"Documents: {'; '.join((s.get('eligibility') or {}).get('documents_required', []))}\n"
            f"Portal: {((s.get('application_process') or {}).get('portal_url', 'N/A'))}\n"
            f"Helpline: {((s.get('application_process') or {}).get('helpline', 'N/A'))}\n"
        )

    prompt = (
        f"{lang_instr}\n\n"
        "Compare the following two Indian government welfare schemes. "
        "Focus on: who would benefit most from each, key differences in eligibility, "
        "benefit amounts, and application process.\n\n"
        f"SCHEME A:\n{fmt(scheme_a)}\n\n"
        f"SCHEME B:\n{fmt(scheme_b)}\n\n"
        "Return a JSON object with keys: "
        '"overall_comparison" (string, 3-4 sentences), '
        '"differences" (array of strings, 3-5 key differences), '
        '"recommendation" (string, 2-3 sentences on who should choose which), '
        '"can_apply_both" (boolean, whether a citizen can potentially apply to both).'
    )
    try:
        result = await _llm_completion(
            messages=[{"role": "user", "content": prompt}],
            httpx_client=httpx_client,
            api_key=api_key,
            api_url=api_url,
            model_name=model_name,
            app_url=app_url,
            app_title=app_title,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )
        return json.loads(result)
    except Exception:
        return {
            "overall_comparison": "Comparison not available at this time.",
            "differences": [],
            "recommendation": "See the detailed table below for a side-by-side comparison.",
            "can_apply_both": False,
        }


# --- Eligibility Rule Engine (unchanged) ---


def _evaluate_op(profile: dict, field: str, op: str, value: Any) -> bool:
    field_val = profile.get(field)
    if op == "eq":
        return field_val == value
    elif op == "ne":
        return field_val != value
    elif op == "gt":
        return field_val is not None and field_val > value
    elif op == "gte":
        return field_val is not None and field_val >= value
    elif op == "lt":
        return field_val is not None and field_val < value
    elif op == "lte":
        return field_val is not None and field_val <= value
    elif op == "in":
        return field_val in value
    elif op == "not_in":
        return field_val is None or field_val not in value
    elif op == "in_optional":
        return field_val is None or field_val == "" or field_val in value
    return True


def _check_rule(profile: dict, rule: dict) -> Tuple[bool, str]:
    only_if = rule.get("only_if")
    if only_if:
        for cond_field, cond_rule in only_if.items():
            cond_op = cond_rule.get("op", "eq")
            cond_val = cond_rule.get("value")
            if not _evaluate_op(profile, cond_field, cond_op, cond_val):
                return True, ""
    failed = not _evaluate_op(profile, rule["field"], rule["op"], rule["value"])
    return (not failed, rule.get("fail_msg", "")) if not failed else (False, rule.get("fail_msg", ""))


def _score_from_brackets(brackets: List[dict], income: Optional[float]) -> Optional[float]:
    if income is None:
        return None
    for bracket in sorted(brackets, key=lambda b: b.get("max_income", 0)):
        if income <= bracket["max_income"]:
            return bracket["value"]
    return None


def _compute_confidence(scoring: dict, profile: dict, reason_count: int) -> float:
    base = scoring.get("base", 0.8)
    penalty = scoring.get("penalty", 0.25)
    min_val = scoring.get("min", 0.1)

    overrides = scoring.get("overrides") or []
    for override in overrides:
        if _evaluate_op(profile, override["field"], override.get("op", "eq"), override.get("value")):
            return max(override.get("confidence", min_val), min_val)

    if_not_student = scoring.get("if_not_student")
    if if_not_student is not None and not profile.get("is_student", False):
        return max(if_not_student, min_val)

    income = profile.get("annual_income")
    brackets = scoring.get("brackets")
    if brackets and income is not None:
        bracket_score = _score_from_brackets(brackets, income)
        if bracket_score is not None:
            return max(bracket_score, min_val)

    score = base - (reason_count * penalty)
    return max(score, min_val)


# --- Public API ---


def get_available_schemes() -> dict:
    schemes = get_schemes_cache(SCHEMES_DIR)
    return {
        s.id: {
            "name": s.name,
            "name_hi": s.name_hi,
            "summary": s.summary,
            "summary_hi": s.summary_hi,
            "tags": s.tags,
        }
        for s in schemes
    }


def get_scheme_detail(scheme_id: str) -> Optional[dict]:
    schemes = get_schemes_cache(SCHEMES_DIR)
    for s in schemes:
        if s.id == scheme_id:
            return {
                "id": s.id,
                "name": s.name,
                "name_hi": s.name_hi,
                "ministry": s.ministry,
                "type": s.type,
                "summary": s.summary,
                "summary_hi": s.summary_hi,
                "benefits": s.benefits,
                "eligibility": s.eligibility,
                "application_process": s.application_process,
                "faq": [{"q": f.q, "a": f.a} for f in s.faq],
                "official_sources": s.official_sources,
            }
    return None


def check_eligibility(profile: dict) -> List[dict]:
    schemes = get_schemes_cache(SCHEMES_DIR)
    results = []

    for s in schemes:
        if not s.eligibility_rules:
            results.append({
                "scheme_id": s.id,
                "name": s.name,
                "confidence": 0.5,
                "match": False,
                "reasons": ["Eligibility rules not configured for this scheme"],
            })
            continue

        reasons = []
        for rule in s.eligibility_rules:
            rule_dict = {
                "field": rule.field,
                "op": rule.op,
                "value": rule.value,
                "fail_msg": rule.fail_msg,
            }
            if rule.only_if:
                rule_dict["only_if"] = rule.only_if
            passes, msg = _check_rule(profile, rule_dict)
            if not passes:
                reasons.append(msg)

        scoring = {
            "base": s.confidence_scoring.base if s.confidence_scoring else 0.8,
            "penalty": s.confidence_scoring.penalty if s.confidence_scoring else 0.25,
            "min": s.confidence_scoring.min if s.confidence_scoring else 0.1,
            "brackets": s.confidence_scoring.brackets if s.confidence_scoring else None,
            "overrides": s.confidence_scoring.overrides if s.confidence_scoring else None,
            "if_not_student": s.confidence_scoring.if_not_student if s.confidence_scoring else None,
        }
        confidence = _compute_confidence(scoring, profile, len(reasons))

        results.append({
            "scheme_id": s.id,
            "name": s.name,
            "confidence": round(confidence, 2),
            "match": len(reasons) == 0,
            "reasons": reasons,
        })

    results.sort(key=lambda x: x["confidence"], reverse=True)
    return results


def extract_scheme_names(text: str) -> List[str]:
    schemes = get_schemes_cache(SCHEMES_DIR)
    found = []
    text_lower = text.lower()
    for s in schemes:
        if s.name.lower() in text_lower or s.id.replace("_", " ") in text_lower:
            if s.name not in found:
                found.append(s.name)
    return found


def is_greeting(message: str) -> bool:
    return bool(_GREETING_PATTERN.match(message.strip().rstrip(".!?")))


def is_broad_query(message: str) -> bool:
    return bool(_BROAD_QUERY_PATTERN.search(message))


_GREETING_REPLIES = {
    "english": (
        "Namaste! I'm your Community Benefits Navigator. I can help you:\n\n"
        "\u2022 Find which government welfare schemes you may qualify for\n"
        "\u2022 Explain how to apply for schemes like PM-KISAN, Ayushman Bharat, etc.\n"
        "\u2022 Check your eligibility for different schemes\n"
        "\u2022 List required documents and application steps\n\n"
        "What would you like help with?"
    ),
    "hindi": (
        "\u0928\u092e\u0938\u094d\u0924\u0947! \u092e\u0948\u0902 \u0906\u092a\u0915\u093e \u0938\u093e\u092e\u0941\u0926\u093e\u092f\u093f\u0915 \u0932\u093e\u092d \u0928\u0947\u0935\u093f\u0917\u0947\u091f\u0930 \u0939\u0942\u0902\u0964 \u092e\u0948\u0902 \u0906\u092a\u0915\u0940 \u092e\u0926\u0926 \u0915\u0930 \u0938\u0915\u0924\u093e \u0939\u0942\u0902:\n\n"
        "\u2022 \u0906\u092a \u0915\u093f\u0928 \u0938\u0930\u0915\u093e\u0930\u0940 \u0915\u0932\u094d\u092f\u093e\u0923 \u092f\u094b\u091c\u0928\u093e\u0913\u0902 \u0915\u0947 \u092a\u093e\u0924\u094d\u0930 \u0939\u0948\u0902, \u092f\u0939 \u091c\u093e\u0928\u0928\u0947 \u092e\u0947\u0902\n"
        "\u2022 \u092a\u0940\u090f\u092e-\u0915\u093f\u0938\u093e\u0928, \u0906\u092f\u0941\u0937\u094d\u092e\u093e\u0928 \u092d\u093e\u0930\u0924 \u0906\u0926\u093f \u092f\u094b\u091c\u0928\u093e\u0913\u0902 \u0915\u0947 \u0932\u093f\u090f \u0906\u0935\u0947\u0926\u0928 \u0915\u0948\u0938\u0947 \u0915\u0930\u0947\u0902\n"
        "\u2022 \u0935\u093f\u092d\u093f\u0928\u094d\u0928 \u092f\u094b\u091c\u0928\u093e\u0913\u0902 \u0915\u0947 \u0932\u093f\u090f \u0905\u092a\u0928\u0940 \u092a\u093e\u0924\u094d\u0930\u0924\u093e \u091c\u093e\u0902\u091a\u0928\u0947 \u092e\u0947\u0902\n"
        "\u2022 \u0906\u0935\u0936\u094d\u092f\u0915 \u0926\u0938\u094d\u0924\u093e\u0935\u0947\u091c \u0914\u0930 \u0906\u0935\u0947\u0926\u0928 \u091a\u0930\u0923\u094b\u0902 \u0915\u0940 \u0938\u0942\u091a\u0940\n\n"
        "\u0906\u092a \u0915\u093f\u0938 \u092c\u093e\u0930\u0947 \u092e\u0947\u0902 \u091c\u093e\u0928\u0928\u093e \u091a\u093e\u0939\u0947\u0902\u0917\u0947?"
    ),
    "telugu": (
        "\u0c28\u0c2e\u0c38\u0c4d\u0c15\u0c3e\u0c30\u0c02! \u0c28\u0c47\u0c28\u0c41 \u0c2e\u0c40 \u0c15\u0c2e\u0c4d\u0c2f\u0c42\u0c28\u0c3f\u0c1f\u0c40 \u0c2c\u0c46\u0c28\u0c3f\u0c2b\u0c3f\u0c1f\u0c4d\u0c38\u0c4d \u0c28\u0c47\u0c35\u0c3f\u0c17\u0c47\u0c1f\u0c30\u0c4d. \u0c28\u0c47\u0c28\u0c41 \u0c38\u0c39\u0c3e\u0c2f\u0c2a\u0c21\u0c17\u0c32\u0c28\u0c41:\n\n"
        "\u2022 \u0c2e\u0c40\u0c30\u0c41 \u0c0f \u0c2a\u0c4d\u0c30\u0c2d\u0c41\u0c24\u0c4d\u0c35 \u0c38\u0c4d\u0c25\u0c3e\u0c2a\u0c28 \u0c2a\u0c02\u0c26\u0c41\u0c17\u0c32\u0c15\u0c41 \u0c05\u0c30\u0c4d\u0c39\u0c41\u0c32\u0c4b \u0c09\u0c02\u0c21\u0c35\u0c1a\u0c4d\u0c1a\u0c41\n"
        "\u2022 PM-KISAN, Ayushman Bharat \u0c2e\u0c4a\u0c26\u0c32\u0c41 \u0c2a\u0c02\u0c26\u0c41\u0c17\u0c32\u0c15\u0c41 \u0c0e\u0c32\u0c3e \u0c26\u0c30\u0c4d\u0c16\u0c3e\u0c38\u0c4d\u0c24\u0c41 \u0c1a\u0c47\u0c2f\u0c3e\u0c32\u0c4b\n"
        "\u2022 \u0c2e\u0c40 \u0c05\u0c30\u0c4d\u0c39\u0c24\u0c3e\u0c28\u0c4d\u0c28\u0c3f \u0c24\u0c28\u0c3f\u0c16\u0c40 \u0c1a\u0c47\u0c2f\u0c21\u0c02\n"
        "\u2022 \u0c05\u0c35\u0c38\u0c30\u0c2e\u0c48\u0c28 \u0c21\u0c4a\u0c15\u0c41\u0c2e\u0c46\u0c02\u0c1f\u0c4d\u0c32\u0c41 \u0c2e\u0c30\u0c3f\u0c2f\u0c41 \u0c26\u0c30\u0c4d\u0c16\u0c3e\u0c38\u0c4d\u0c24\u0c41 \u0c26\u0c36\u0c32\u0c41\n\n"
        "\u0c2e\u0c40\u0c30\u0c41 \u0c0f\u0c2e\u0c3f\u0c1f\u0c4d\u0c32\u0c4b \u0c38\u0c39\u0c3e\u0c2f\u0c02 \u0c15\u0c4b\u0c30\u0c41\u0c15\u0c41\u0c02\u0c26\u0c3f?"
    ),
    "tamil": (
        "\u0bb5\u0ba3\u0b95\u0bcd\u0b95\u0bae\u0bcd! \u0ba8\u0bbe\u0ba9\u0bcd \u0b89\u0b99\u0bcd\u0b95\u0bb3\u0bcd \u0b9a\u0bae\u0bc2\u0b95 \u0ba8\u0ba9\u0bcd\u0bae\u0bc8 \u0bb5\u0bb4\u0bbf\u0b95\u0bbe\u0b9f\u0bcd\u0b9f\u0bbf. \u0ba8\u0bbe\u0ba9\u0bcd \u0b89\u0ba4\u0bb5\u0bb2\u0bbe\u0bae\u0bcd:\n\n"
        "\u2022 \u0b8e\u0ba8\u0bcd\u0ba4 \u0b85\u0bb0\u0b9a\u0bc1 \u0ba8\u0bb2\u0ba9\u0bcd\u0bae\u0bc8\u0ba4\u0bcd \u0ba4\u0bbf\u0b9f\u0bcd\u0b9f\u0b99\u0bcd\u0b95\u0bb3\u0bc1\u0b95\u0bcd\u0b95\u0bc1 \u0ba8\u0bc0\u0b99\u0bcd\u0b95\u0bb3\u0bcd \u0ba4\u0b95\u0bc1\u0ba4\u0bbf \u0baa\u0bc6\u0bb1\u0bcd\u0bb1\u0bc1\u0bb3\u0bcd\u0bb3\u0bc0\u0bb0\u0bcd\u0b95\u0bb3\u0bcd \u0b8e\u0ba9\u0bcd\u0baa\u0ba4\u0bc8 \u0b95\u0ba3\u0bcd\u0b9f\u0bb1\u0bbf\u0baf\u0bb2\u0bbe\u0bae\u0bcd\n"
        "\u2022 PM-KISAN, Ayushman Bharat \u0baa\u0bcb\u0ba9\u0bcd\u0bb1 \u0ba4\u0bbf\u0b9f\u0bcd\u0b9f\u0b99\u0bcd\u0b95\u0bb3\u0bc1\u0b95\u0bcd\u0b95\u0bc1 \u0b8e\u0baa\u0bcd\u0baa\u0b9f\u0bbf \u0bb5\u0bbf\u0ba3\u0bcd\u0ba3\u0baa\u0bcd\u0baa\u0bbf\u0b95\u0bcd\u0b95\u0bb5\u0bc1\u0bae\u0bcd\n"
        "\u2022 \u0bb5\u0bbf\u0bb5\u0bbf\u0ba4\u0bcd\u0ba4 \u0ba4\u0bbf\u0b9f\u0bcd\u0b9f\u0b99\u0bcd\u0b95\u0bb3\u0bc1\u0b95\u0bcd\u0b95\u0bc1 \u0b89\u0b99\u0bcd\u0b95\u0bb3\u0bcd \u0ba4\u0b95\u0bc1\u0ba4\u0bbf\u0baf\u0bc8 \u0b9a\u0bb0\u0bbf\u0baa\u0bbe\u0bb0\u0bcd\u0b95\u0bcd\u0b95\u0bb2\u0bbe\u0bae\u0bcd\n"
        "\u2022 \u0ba4\u0bc7\u0bb5\u0bc8\u0baf\u0bbe\u0ba9 \u0b86\u0bb5\u0ba3\u0b99\u0bcd\u0b95\u0bb3\u0bcd \u0bae\u0bb1\u0bcd\u0bb1\u0bc1\u0bae\u0bcd \u0bb5\u0bbf\u0ba3\u0bcd\u0ba3\u0baa\u0bcd\u0baa \u0baa\u0b9f\u0bbf\u0b95\u0bb3\u0bbf\u0ba9\u0bcd \u0baa\u0b9f\u0bcd\u0b9f\u0bbf\u0baf\u0bb2\u0bcd\n\n"
        "\u0b8e\u0ba4\u0bc1 \u0baa\u0bb1\u0bcd\u0bb1\u0bbf \u0ba8\u0bc0\u0b99\u0bcd\u0b95\u0bb3\u0bcd \u0b85\u0bb1\u0bbf\u0baf \u0bb5\u0bbf\u0bb0\u0bc1\u0bae\u0bcd\u0baa\u0bc1\u0b95\u0bbf\u0bb1\u0bc0\u0bb0\u0bcd\u0b95\u0bb3\u0bcd?"
    ),
    "bengali": (
        "\u09a8\u09ae\u09b8\u09cd\u0995\u09be\u09b0! \u0986\u09ae\u09bf \u0986\u09aa\u09a8\u09be\u09b0 \u0995\u09ae\u09cd\u09af\u09c1\u09a8\u09bf\u099f\u09bf \u09ac\u09c7\u09a8\u09bf\u09ab\u09bf\u099f\u09b8\u09cd \u09a8\u09cd\u09af\u09be\u09ad\u09bf\u0997\u09c7\u099f\u09b0\u0964 \u0986\u09ae\u09bf \u09b8\u09b9\u09be\u09af\u09bc\u09a4\u09be \u0995\u09b0\u09a4\u09c7 \u09aa\u09be\u09b0\u09bf:\n\n"
        "\u2022 \u0986\u09aa\u09a8\u09bf \u0995\u09cb\u09a8 \u09b8\u09b0\u0995\u09be\u09b0\u09bf \u0995\u09b2\u09cd\u09af\u09be\u09a3 \u0987\u09af\u09bc\u09cb\u099c\u09a8\u09be\u09b0 \u099c\u09a8\u09cd\u09af \u09af\u09cb\u0997\u09cd\u09af\u09a4\u09be \u09aa\u09c7\u09a4\u09c7 \u09aa\u09be\u09b0\u09c7\u09a8\n"
        "\u2022 PM-KISAN, Ayushman Bharat \u0987\u09a4\u09cd\u09af\u09be\u09a6\u09bf \u0987\u09af\u09bc\u09cb\u099c\u09a8\u09be\u09b0 \u099c\u09a8\u09cd\u09af \u0995\u09bf\u09ad\u09be\u09ac\u09c7 \u0986\u09ac\u09c7\u09a6\u09a8 \u0995\u09b0\u09ac\u09c7\u09a8\n"
        "\u2022 \u09ac\u09bf\u09ad\u09bf\u09a8\u09cd\u09a8 \u0987\u09af\u09bc\u09cb\u099c\u09a8\u09be\u09b0 \u099c\u09a8\u09cd\u09af \u0986\u09aa\u09a8\u09be\u09b0 \u09af\u09cb\u0997\u09cd\u09af\u09a4\u09be \u09af\u09be\u099a\u09be\u0987 \u0995\u09b0\u09be\n"
        "\u2022 \u09aa\u09cd\u09b0\u09af\u09bc\u09cb\u099c\u09a8\u09c0\u09af\u09bc \u09a1\u0995\u09c1\u09ae\u09c7\u09a8\u09cd\u099f \u0993 \u0986\u09ac\u09c7\u09a6\u09a8 \u09aa\u09a6\u09cd\u09a7\u09a4\u09bf\u09b0 \u09a4\u09be\u09b2\u09bf\u0995\u09be\n\n"
        "\u0986\u09aa\u09a8\u09bf \u0995\u09bf \u09ac\u09bf\u09b7\u09af\u09bc\u09c7 \u099c\u09be\u09a8\u09a4\u09c7 \u099a\u09be\u09a8?"
    ),
    "marathi": (
        "\u0928\u092e\u0938\u094d\u0915\u093e\u0930! \u092e\u0940 \u0924\u0941\u092e\u091a\u093e \u0938\u093e\u092e\u0941\u0926\u093e\u092f\u093f\u0915 \u0932\u093e\u092d \u0928\u0947\u0935\u093f\u0917\u0947\u091f\u0930. \u092e\u0940 \u092e\u0926\u0924 \u0915\u0930\u0942 \u0936\u0915\u0924\u094b:\n\n"
        "\u2022 \u0924\u0941\u092e\u094d\u0939\u0940 \u0915\u094b\u0923\u0924\u094d\u092f\u093e \u0938\u0930\u0915\u093e\u0930\u0940 \u0915\u0932\u094d\u092f\u093e\u0923 \u092f\u094b\u091c\u0928\u093e\u0902\u0938\u093e\u0920\u0940 \u092a\u093e\u0924\u094d\u0930 \u0906\u0939\u093e\u0924\n"
        "\u2022 PM-KISAN, Ayushman Bharat \u0907\u0924\u094d\u092f\u093e\u0926\u0940 \u092f\u094b\u091c\u0928\u093e\u0902\u0938\u093e\u0920\u0940 \u0905\u0930\u094d\u091c \u0915\u0938\u0947 \u0915\u0930\u093e\u0935\u093e\n"
        "\u2022 \u0935\u0947\u0917\u0935\u0947\u0917\u0933\u094d\u092f\u093e \u092f\u094b\u091c\u0928\u093e\u0902\u0938\u093e\u0920\u0940 \u0924\u0941\u092e\u091a\u0940 \u092a\u093e\u0924\u094d\u0930\u0924\u093e \u0924\u092a\u093e\u0938\u0923\u0947\n"
        "\u2022 \u0906\u0935\u0936\u094d\u092f\u0915 \u0915\u093e\u0917\u0926\u092a\u0924\u094d\u0930\u0947 \u0906\u0923\u093f \u0905\u0930\u094d\u091c \u092a\u0926\u094d\u0927\u0924\u0940\u091a\u0940 \u092f\u093e\u0926\u0940\n\n"
        "\u0924\u0941\u092e\u094d\u0939\u093e\u0932\u093e \u0915\u093e\u092f \u092e\u093e\u0939\u093f\u0924 \u0939\u0935\u094d\u092f\u093e\u090f?"
    ),
}


def get_greeting_reply(language: str) -> str:
    return _GREETING_REPLIES.get(language, _GREETING_REPLIES["english"])


async def chat_with_nemotron(
    message: str,
    language: str = "english",
    history: Optional[List[dict]] = None,
    httpx_client: Optional[httpx.AsyncClient] = None,
    api_key: str = "",
    api_url: str = "https://openrouter.ai/api/v1",
    model_name: str = "nvidia/nemotron-3-super-120b-a12b:free",
    app_url: str = "",
    app_title: str = "",
) -> dict:
    if history is None:
        history = []

    if is_greeting(message):
        return {"reply": get_greeting_reply(language), "citations": [], "confidence": 1.0, "suggested_questions": []}

    from rag.retriever import retrieve, format_context

    # --- Query Decomposition ---
    sub_queries = [message]
    if is_broad_query(message) and api_key:
        try:
            sub_queries = await decompose_query(
                message=message,
                language=language,
                httpx_client=httpx_client,
                api_key=api_key,
                api_url=api_url,
                model_name=model_name,
                app_url=app_url,
                app_title=app_title,
            )
        except Exception:
            sub_queries = [message]

    # --- Multi-query retrieval ---
    all_retrieved = []
    seen_chunks = set()
    for q in sub_queries:
        retrieved = retrieve(q)
        for doc, meta, score in retrieved:
            chunk_key = doc[:100]
            if chunk_key not in seen_chunks:
                seen_chunks.add(chunk_key)
                all_retrieved.append((doc, meta, score))
    all_retrieved.sort(key=lambda x: x[2], reverse=True)
    context = format_context(all_retrieved[:10])

    lang_instruction = LANG_INSTRUCTIONS.get(language, LANG_INSTRUCTIONS["english"])

    # --- Session Summarization ---
    session_summary = ""
    if len(history) > 6 and api_key:
        try:
            session_summary = await summarize_history(
                history=history[:-4],
                language=language,
                httpx_client=httpx_client,
                api_key=api_key,
                api_url=api_url,
                model_name=model_name,
                app_url=app_url,
                app_title=app_title,
            )
        except Exception:
            pass

    system_prompt = (
        "You are a Community Benefits Navigator for Indian government schemes.\n\n"
        f"{lang_instruction}\n\n"
        "RULES:\n"
        "1. ONLY answer based on the provided context documents below.\n"
        "2. Cite the exact scheme name and section for every claim you make.\n"
        "3. If the context doesn't contain the answer, say \"I don't have reliable information on this\" and suggest visiting the official portal or nearest Common Service Centre (CSC).\n"
        "4. Be helpful and concise. Use simple language that a person with basic literacy can understand.\n"
        "5. Format complex information as bullet points or numbered steps.\n"
        "6. Always end with: \"For official confirmation, please visit the scheme portal or your nearest CSC.\"\n"
        "7. At the very end of your response, rate your confidence in this answer from 0.0 to 1.0 "
        "as a JSON object on its own line like: {\"confidence\": 0.85}\n"
        "8. Before your closing, suggest 3 follow-up questions the user might want to ask next. "
        "Put them in a bullet list under \"You might also ask:\"\n\n"
        f"CONTEXT:\n{context}\n"
    )

    messages = [{"role": "system", "content": system_prompt}]
    if session_summary:
        messages.append({"role": "system", "content": f"Earlier conversation summary: {session_summary}"})
    for h in history[-6:]:
        messages.append({"role": h["role"], "content": h["content"][:1000]})
    messages.append({"role": "user", "content": message})

    if not api_key:
        return {
            "reply": "API key not configured. Set API_KEY in backend/.env (get one from https://openrouter.ai/keys)",
            "citations": [],
            "confidence": 0.0,
            "suggested_questions": [],
        }

    should_close = False
    if httpx_client is None:
        httpx_client = httpx.AsyncClient(timeout=60.0)
        should_close = True

    try:
        reply = await _llm_completion(
            messages=messages,
            httpx_client=httpx_client,
            api_key=api_key,
            api_url=api_url,
            model_name=model_name,
            app_url=app_url,
            app_title=app_title,
            temperature=0.7,
            max_tokens=2048,
        )
    finally:
        if should_close:
            await httpx_client.aclose()

    # --- Extract confidence from reply ---
    llm_confidence = None
    clean_reply = reply
    conf_match = re.search(r'\{[^{}]*"confidence"\s*:\s*([0-9.]+)[^{}]*\}', reply)
    if conf_match:
        try:
            llm_confidence = float(conf_match.group(1))
            clean_reply = reply[:conf_match.start()].rstrip()
        except (ValueError, IndexError):
            pass

    # --- Extract follow-up questions from reply ---
    suggested_questions = []
    fq_match = re.search(r"You might also ask:\n((?:.*\n)*)", reply)
    if fq_match:
        questions_text = fq_match.group(1)
        suggested_questions = [
            q.strip().lstrip("- ").lstrip('"').rstrip('"')
            for q in questions_text.strip().split("\n")
            if q.strip()
        ][:3]
        clean_reply = reply[:fq_match.start()].rstrip()

    citations = []
    for doc, meta, score in all_retrieved[:10]:
        if score > 0.3:
            citations.append({
                "scheme": meta["name"],
                "section": meta["type"],
                "confidence": round(score, 2),
                "text": doc[:200],
            })

    avg_confidence = round(sum(c["confidence"] for c in citations) / max(len(citations), 1), 2)
    final_confidence = llm_confidence if llm_confidence is not None else avg_confidence

    return {
        "reply": clean_reply,
        "citations": citations[:3],
        "confidence": final_confidence,
        "suggested_questions": suggested_questions,
    }
