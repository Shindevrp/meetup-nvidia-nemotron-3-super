from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, List, Optional


@dataclass
class FAQ:
    q: str
    a: str


@dataclass
class EligibilityRule:
    field: str
    op: str
    value: Any
    fail_msg: str = ""
    only_if: Optional[dict] = None

    @classmethod
    def from_dict(cls, d: dict) -> EligibilityRule:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ConfidenceScoring:
    base: float = 0.8
    penalty: float = 0.25
    min: float = 0.1
    brackets: Optional[List[dict]] = None
    overrides: Optional[List[dict]] = None
    if_not_student: Optional[float] = None

    @classmethod
    def from_dict(cls, d: dict) -> ConfidenceScoring:
        if d is None:
            return cls()
        valid_fields = cls.__dataclass_fields__
        kwargs = {k: v for k, v in d.items() if k in valid_fields}
        return cls(**kwargs)


@dataclass
class Scheme:
    id: str
    name: str
    name_hi: str
    ministry: str
    type: str
    summary: str
    summary_hi: str
    benefits: List[str]
    eligibility: dict
    application_process: dict
    faq: List[FAQ]
    official_sources: List[str]
    last_updated: str
    tags: List[str]
    eligibility_rules: List[EligibilityRule] = field(default_factory=list)
    confidence_scoring: Optional[ConfidenceScoring] = None


def load_scheme(filepath: str) -> Scheme:
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    faqs = [FAQ(**faq) for faq in data.get("faq", [])]
    data["faq"] = faqs
    rules_raw = data.pop("eligibility_rules", [])
    cs_raw = data.pop("confidence_scoring", None)
    scheme = Scheme(**data)
    scheme.eligibility_rules = [EligibilityRule.from_dict(r) for r in rules_raw]
    scheme.confidence_scoring = ConfidenceScoring.from_dict(cs_raw)
    return scheme


@lru_cache(maxsize=1)
def load_all_schemes_cached(schemes_dir: str) -> List[Scheme]:
    import glob
    schemes = []
    for fp in glob.glob(os.path.join(schemes_dir, "*.json")):
        schemes.append(load_scheme(fp))
    schemes.sort(key=lambda s: s.id)
    return schemes


def get_schemes_cache(schemes_dir: str) -> List[Scheme]:
    return load_all_schemes_cached(schemes_dir)


def clear_schemes_cache():
    load_all_schemes_cached.cache_clear()


def reload_schemes(schemes_dir: str) -> List[Scheme]:
    clear_schemes_cache()
    return get_schemes_cache(schemes_dir)
