# Contributing

Thank you for your interest in the Community Benefits Navigator. This guide explains how to extend the system with new schemes, languages, and eligibility rules.

## Adding a New Welfare Scheme

No code changes needed. Create a JSON file in `backend/data/schemes/`.

**Template:**

```json
{
  "id": "your_scheme_id",
  "name": "Scheme Full Name",
  "name_hi": "Scheme Name in Hindi",
  "ministry": "Ministry Name",
  "type": "Category",
  "summary": "One-paragraph description in English.",
  "summary_hi": "One-paragraph description in Hindi.",
  "benefits": ["Benefit 1", "Benefit 2"],
  "eligibility": {
    "who_can_apply": ["Criteria 1"],
    "who_cannot_apply": ["Exclusion 1"],
    "documents_required": ["Doc 1"]
  },
  "eligibility_rules": [
    {"field": "annual_income", "op": "lt", "value": 250000, "fail_msg": "Income too high"}
  ],
  "confidence_scoring": {
    "base": 0.7,
    "penalty": 0.2,
    "min": 0.1
  },
  "application_process": {
    "how_to_apply": ["Step 1", "Step 2"],
    "portal_url": "https://example.com",
    "helpline": "1800-xxx-xxxx"
  },
  "faq": [
    {"q": "Question?", "a": "Answer."}
  ],
  "official_sources": ["https://example.com"],
  "last_updated": "2026-06-01",
  "tags": ["tag1", "tag2"]
}
```

**Steps:**
1. Create `backend/data/schemes/<scheme_id>.json`
2. Restart the server or call `POST /api/admin/refresh` (requires `ADMIN_KEY`)
3. The scheme appears in the Scheme Browser, Chat, and Eligibility Checker automatically

## Adding a New Language

### 1. Backend (`backend/models/chat.py`)

Add entries to both maps:

```python
LANG_MAP["french"] = "fr"
LANG_INSTRUCTIONS["french"] = "Respond in French."
```

Update the ChatRequest validation regex to include the new language.

### 2. Frontend Language Names (`frontend/app.js`)

```javascript
const LANG_NAMES = {
  ...existing,
  french: 'Français',
};
```

### 3. UI Translations (`frontend/app.js`)

Add translations for all ~140 UI keys. Each key needs your new language:

```javascript
sidebar_title: {
  english: 'Chat History',
  hindi: 'चैट इतिहास',
  french: 'Historique des discussions',
},
```

### 4. Language Selector (`frontend/index.html`)

```html
<option value="french">Français</option>
```

### 5. Noto Sans Font (`frontend/index.html`)

Add the Google Fonts link for your script:

```html
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+FR:wght@400;700&display=swap" rel="stylesheet">
```

### 6. Voice Recognition (`frontend/app.js`)

```javascript
const langMap = { ...existing, french: 'fr-FR' };
```

## Extending Eligibility Rules

Rules live in each scheme's JSON file under `eligibility_rules`. No code changes required.

**Supported operators:**

| op | Behavior |
|---|---|
| `eq` | Field equals value |
| `ne` | Field does not equal value |
| `gt` | Field is greater than value |
| `gte` | Field is greater than or equal |
| `lt` | Field is less than value |
| `lte` | Field is less than or equal |
| `in` | Field is one of the listed values |
| `not_in` | Field is none or not in listed values |
| `in_optional` | Field is none, empty, or in listed values |

**Conditional rules** with `only_if`:

```json
{
  "field": "annual_income",
  "op": "gt",
  "value": 0,
  "only_if": {"occupation": {"op": "not_in", "value": ["farmer", "agriculture"]}},
  "fail_msg": "IT payers may not be eligible"
}
```

The rule is only evaluated when the `only_if` condition matches.

## Development Setup

```bash
git clone https://github.com/Shindevrp/meetup-nvidia-nemotron-3-super
cd submissions/track_1_community_benefits_navigator/shinde_vinayak_rao_patil
./setup.sh
./run.sh
```

## Code Style

- Backend: ruff + mypy (run `ruff check backend/ && mypy backend/`)
- Frontend: standard JavaScript (ES6+)
