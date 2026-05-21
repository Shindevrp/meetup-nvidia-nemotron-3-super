# Data models for scheme documents loaded from JSON files
# Provides typed dataclasses and loader utilities

import json
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class FAQ:
    q: str
    a: str


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


def load_scheme(filepath: str) -> Scheme:
    """Load a single scheme from a JSON file and return a typed Scheme object."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    faqs = [FAQ(**faq) for faq in data.get("faq", [])]
    data["faq"] = faqs
    return Scheme(**data)


def load_all_schemes(schemes_dir: str) -> List[Scheme]:
    """Load all scheme JSON files from a directory."""
    import os, glob
    schemes = []
    for fp in glob.glob(os.path.join(schemes_dir, "*.json")):
        schemes.append(load_scheme(fp))
    return schemes
