import os
import json
from typing import List, Optional

import httpx

from ..rag.retriever import retrieve, format_context
from ..models.schemes import load_all_schemes

NIM_API_URL = os.getenv("NIM_API_URL", "https://integrate.api.nvidia.com/v1")
NIM_API_KEY = os.getenv("NIM_API_KEY", "")
MODEL_NAME = os.getenv("NIM_MODEL", "nvidia/nemotron-3-super-120b-a12b")
SCHEMES_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "schemes")


def get_available_schemes() -> dict:
    schemes = load_all_schemes(SCHEMES_DIR)
    return {s.id: {"name": s.name, "name_hi": s.name_hi, "summary": s.summary, "summary_hi": s.summary_hi} for s in schemes}


def get_scheme_detail(scheme_id: str) -> Optional[dict]:
    schemes = load_all_schemes(SCHEMES_DIR)
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
    schemes = load_all_schemes(SCHEMES_DIR)
    results = []
    for s in schemes:
        reasons = []
        income = profile.get("annual_income", 0)
        age = profile.get("age", 0)
        occupation = profile.get("occupation", "").lower()
        landowner = profile.get("landowner", False)

        if s.id == "pm_kisan":
            if occupation not in ("farmer", "agriculture", ""):
                reasons.append("PM-KISAN is for farmers with landholding")
            if not landowner:
                reasons.append("Must own cultivable land")
            if income > 0 and occupation != "farmer" and age >= 18:
                reasons.append("IT payers/professionals may not be eligible")
            crop = max(0.0, 0.8)
            if reasons:
                crop = max(0.1, 1.0 - len(reasons) * 0.25)
            results.append({"scheme_id": s.id, "name": s.name, "confidence": round(crop, 2),
                            "match": len(reasons) == 0, "reasons": reasons})

        elif s.id == "ayushman_bharat":
            if income is not None and income > 300000:
                reasons.append("Family income may exceed threshold")
            if occupation in ("doctor", "engineer", "lawyer", "chartered accountant", "government"):
                reasons.append("Professional/government employees may not be eligible")
            crop = 0.7 if income and income < 250000 else (0.3 if income and income < 500000 else 0.1)
            results.append({"scheme_id": s.id, "name": s.name, "confidence": round(crop, 2),
                            "match": len(reasons) == 0, "reasons": reasons})

        elif s.id == "pm_awas_yojana":
            has_house = profile.get("owns_pucca_house", False)
            if has_house:
                reasons.append("Should not own a pucca house")
            if income is not None and income > 1800000:
                reasons.append("Family income exceeds MIG-II limit of ₹18L/year")
            if income and income < 300000:
                crop = 0.9
            elif income and income < 600000:
                crop = 0.7
            elif income and income < 1200000:
                crop = 0.4
            elif income and income < 1800000:
                crop = 0.2
            else:
                crop = 0.1
            if has_house:
                crop = 0.05
            results.append({"scheme_id": s.id, "name": s.name, "confidence": round(crop, 2),
                            "match": len(reasons) == 0, "reasons": reasons})

        elif s.id == "nsp_scholarships":
            is_student = profile.get("is_student", False)
            if not is_student:
                reasons.append("NSP is for enrolled students only")
            crop = 0.9 if is_student else 0.1
            results.append({"scheme_id": s.id, "name": s.name, "confidence": round(crop, 2),
                            "match": len(reasons) == 0, "reasons": reasons})

        elif s.id == "ujjwala":
            if profile.get("gender", "").lower() not in ("female", "woman", ""):
                reasons.append("PMUY is for women of the household")
            if profile.get("has_lpg", False):
                reasons.append("Household already has LPG connection")
            if income is not None and income > 200000:
                reasons.append("May be above poverty line threshold")
            crop = 0.8 if (income is None or income < 150000) else 0.3
            if profile.get("gender", "").lower() not in ("female", "woman", ""):
                crop = 0.1
            if profile.get("has_lpg", False):
                crop = 0.05
            results.append({"scheme_id": s.id, "name": s.name, "confidence": round(crop, 2),
                            "match": len(reasons) == 0, "reasons": reasons})

    results.sort(key=lambda x: x["confidence"], reverse=True)
    return results


async def chat_with_nemotron(
    message: str,
    language: str = "english",
    history: List[dict] = None,
) -> dict:
    if history is None:
        history = []

    retrieved = retrieve(message)
    context = format_context(retrieved)

    lang_instruction = "Respond in English." if language == "english" else f"Respond in Hindi (हिंदी)."

    system_prompt = f"""You are a Community Benefits Navigator for Indian government schemes.

{lang_instruction}

RULES:
1. ONLY answer based on the provided context documents below.
2. Cite the exact scheme name and section for every claim you make.
3. If the context doesn't contain the answer, say "I don't have reliable information on this" and suggest visiting the official portal or nearest Common Service Centre (CSC).
4. Be helpful and concise. Use simple language that a person with basic literacy can understand.
5. Format complex information as bullet points or numbered steps.
6. Always end with: "For official confirmation, please visit the scheme portal or your nearest CSC."

CONTEXT:
{context}
"""

    messages = [{"role": "system", "content": system_prompt}]
    for h in history[-6:]:  # keep last 6 messages for context window
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})

    if not NIM_API_KEY:
        return {
            "reply": "NVIDIA NIM API key not configured. Set NIM_API_KEY environment variable.",
            "citations": [],
            "confidence": 0.0,
        }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{NIM_API_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {NIM_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL_NAME,
                "messages": messages,
                "temperature": 1.0,
                "top_p": 0.95,
                "max_tokens": 1024,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        reply = data["choices"][0]["message"]["content"]

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
