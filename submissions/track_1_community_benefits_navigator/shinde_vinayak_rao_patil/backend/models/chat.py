from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx

from models.schemes import (
    Scheme,
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
        return {"reply": get_greeting_reply(language), "citations": [], "confidence": 1.0}

    from rag.retriever import retrieve, format_context

    retrieved = retrieve(message)
    context = format_context(retrieved)

    lang_instruction = LANG_INSTRUCTIONS.get(language, LANG_INSTRUCTIONS["english"])

    system_prompt = (
        "You are a Community Benefits Navigator for Indian government schemes.\n\n"
        f"{lang_instruction}\n\n"
        "RULES:\n"
        "1. ONLY answer based on the provided context documents below.\n"
        "2. Cite the exact scheme name and section for every claim you make.\n"
        "3. If the context doesn't contain the answer, say \"I don't have reliable information on this\" and suggest visiting the official portal or nearest Common Service Centre (CSC).\n"
        "4. Be helpful and concise. Use simple language that a person with basic literacy can understand.\n"
        "5. Format complex information as bullet points or numbered steps.\n"
        "6. Always end with: \"For official confirmation, please visit the scheme portal or your nearest CSC.\"\n\n"
        f"CONTEXT:\n{context}\n"
    )

    messages = [{"role": "system", "content": system_prompt}]
    for h in history[-6:]:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})

    if not api_key:
        return {
            "reply": "API key not configured. Set API_KEY in backend/.env (get one from https://openrouter.ai/keys)",
            "citations": [],
            "confidence": 0.0,
        }

    should_close = False
    if httpx_client is None:
        httpx_client = httpx.AsyncClient(timeout=60.0)
        should_close = True

    try:
        resp = await httpx_client.post(
            f"{api_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": app_url,
                "X-Title": app_title,
            },
            json={
                "model": model_name,
                "messages": messages,
                "temperature": 1.0,
                "top_p": 0.95,
                "max_tokens": 1024,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        reply = data["choices"][0]["message"]["content"]
    finally:
        if should_close:
            await httpx_client.aclose()

    citations = []
    for doc, meta, score in retrieved:
        if score > 0.3:
            citations.append({
                "scheme": meta["name"],
                "section": meta["type"],
                "confidence": round(score, 2),
                "text": doc[:200],
            })

    avg_confidence = round(sum(c["confidence"] for c in citations) / max(len(citations), 1), 2)

    return {
        "reply": reply,
        "citations": citations[:3],
        "confidence": avg_confidence,
    }
