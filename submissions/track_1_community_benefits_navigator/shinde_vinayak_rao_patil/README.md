# Project Name: Community Benefits Navigator

**Track:** Track 1 - Community Benefits Navigator

**Team Name:** shinde_vinayak_rao_patil

---

### Project Links
- **YouTube Demo:** *[Link to be added after recording]*
- **Blog Post:** *[Link to be added after publishing]*
- **LinkedIn Post:** *[Link to be added after posting]*

---

### Architecture

![Architecture Diagram](architecture.svg)

The system follows a **RAG (Retrieval-Augmented Generation)** pattern with 5 layers:

1. **Frontend** (HTML/CSS/JS) — 5-tab SPA with chat, eligibility checker, scheme browser, comparison tool, and CSC Locator (Leaflet.js map). Includes **chat history sidebar**, voice input (SpeechRecognition), dark mode, PDF export, and a **6-language UI** (English, Hindi, Telugu, Tamil, Bengali, Marathi).
2. **Backend** (FastAPI) — Python API server with **16+ REST endpoints**, config management, rate limiting (30 req/min), structured logging, JSON-persisted **session store** with 7 CRUD endpoints, data-driven **eligibility rule engine**, and admin cache management.
3. **RAG Pipeline** (ChromaDB + intfloat/multilingual-e5-small) — Embeds scheme documents and retrieves top-5 relevant chunks per query. Query results are **LRU-cached** for performance.
4. **LLM** (NVIDIA Nemotron-3-Super via OpenRouter free tier) — Generates grounded responses using retrieved context with multi-language prompt engineering and citation tracking.
5. **Data Layer** — Structured JSON files for 5 central government schemes, each with **data-driven `eligibility_rules`** and **`confidence_scoring`** objects evaluated by a generic rule engine.

---

### Description

**How it uses Nemotron-3-Super:**

The Community Benefits Navigator helps Indian citizens discover, understand, and apply for central government welfare schemes. It leverages **NVIDIA Nemotron-3-Super** (via OpenRouter API) as the reasoning engine:

- **Grounded Generation:** Every user query first triggers a RAG retrieval step that pulls relevant scheme documents from ChromaDB. The Nemotron model receives this context as part of the system prompt and is instructed to **only answer from the provided documents**, ensuring faithfulness to official sources.
- **Citation Tracking:** Each response includes confidence-badged citations showing exactly which scheme document section was used.
- **Eligibility Reasoning:** A data-driven rule engine evaluates eligibility against profile information — rules are stored in scheme JSON files, making the system extensible without code changes.
- **Smart Query Handling:** Greeting detection skips RAG for casual messages, reducing latency and API costs.
- **6-Language Support:** Nemotron's multilingual capabilities enable 6 languages (English, Hindi, Telugu, Tamil, Bengali, Marathi) with per-language greeting replies and Noto Sans fonts for each script.
- **Voice Input:** Mic button using SpeechRecognition API with language-aware recognition for accessibility.
- **Chat History Sidebar:** ChatGPT-style slide-out panel with grouped conversations (Today/Yesterday/Last 7 Days/Earlier), search, rename, delete, and server-side JSON persistence.
- **Safety by Prompt Design:** The system prompt includes strong grounding constraints, a "don't know" fallback instruction, and mandatory CSC referral for uncertain answers.

**Key features:**
- **5-tab SPA** — Chat (with history sidebar), Eligibility Checker, Scheme Browser, Compare (side-by-side), CSC Locator (Leaflet.js map with Nominatim geocoding)
- **Data-driven eligibility rules engine** — Rules stored in scheme JSONs (no hardcoded if/elif chains)
- **Session management** — Anonymous session IDs with server-side persistence, auto-titling from first message
- **Scheme data caching** — `@lru_cache` for scheme data and RAG query results
- **Singleton embedding model** — Loaded once at startup, shared across requests
- **HTTP connection pooling** — Shared `httpx.AsyncClient` via `app.state`
- **Rate limiting** — 30 requests/minute per client with `X-RateLimit-*` headers
- **Config validation** — On startup with structured logging
- **Greeting detection** — Regex skips RAG for casual messages, reducing latency and API costs
- **PDF export** — Download eligibility results via html2pdf.js
- **Scheme comparison** — Side-by-side comparison of any two schemes
- **CSC Locator** — Interactive map with search, geocoding, markers for 10 major cities
- **Dark mode** — CSS variable override, respects `prefers-color-scheme`
- **Admin endpoints** — `POST /api/admin/refresh` for cache invalidation and re-indexing (guarded by `ADMIN_KEY`)
- **6-language UI** — Full UI translation with Noto Sans Devanagari/Telugu/Tamil/Bengali fonts
- **Auto-resizing chat input** — Textarea grows with content

**Schemes supported:**
1. **PM-KISAN** (`pm_kisan`) — Income support for farmers (₹6,000/year)
2. **Ayushman Bharat / PM-JAY** (`ayushman_bharat`) — Health insurance (₹5L/family/year)
3. **PM Awas Yojana** (`pm_awas_yojana`) — Housing subsidy for EWS/LIG/MIG
4. **National Scholarship Portal** (`nsp_scholarships`) — Education scholarships for SC/ST/OBC/Minority students
5. **PM Ujjwala Yojana** (`ujjwala`) — Free LPG connections for BPL women

*Each scheme JSON includes `eligibility_rules` and `confidence_scoring` — add new schemes by dropping in a JSON file, no code changes needed.*

---

### Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML, CSS, Vanilla JavaScript, Leaflet.js (map), html2pdf.js (PDF) |
| Backend | Python, FastAPI, httpx |
| LLM | NVIDIA Nemotron-3-Super via [OpenRouter](https://openrouter.ai/nvidia/nemotron-3-super-120b-a12b:free) (free tier) |
| Vector DB | ChromaDB |
| Embeddings | `intfloat/multilingual-e5-small` (Hugging Face) |
| Session Store | JSON file persistence (`backend/data/sessions.json`) |
| Maps | OpenStreetMap + Nominatim (free geocoding) |
| Voice | Web SpeechRecognition API |
| Code Quality | ruff, mypy, pytest |

---

### How to Run

**Prerequisites:**
- Python 3.10+
- OpenRouter API key (free tier) — get one at [openrouter.ai/keys](https://openrouter.ai/keys)
- 4GB+ RAM for ChromaDB + Sentence Transformers

**Quick Setup:**
```bash
./setup.sh
```
This creates a virtual environment, installs dependencies, and configures your .env file.

**Run the Server:**
```bash
./run.sh
```

**Or Manual Setup:**
```bash
cd submissions/track_1_community_benefits_navigator/shinde_vinayak_rao_patil
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
# Edit backend/.env and add your OpenRouter API key
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Open:** `http://localhost:8000` in your browser.

---

### Judging Criteria Mapping

| Criterion | How We Address It |
|---|---|
| **Community Value** | Solves real problem — 40%+ Indians seek help with welfare schemes but face language, literacy, and awareness barriers. 6 languages cover ~80% of Indian population. CSC Locator connects users to help centres. |
| **Grounded Accuracy** | RAG pipeline ensures every answer cites official scheme documents; model instructed to refuse ungrounded queries; confidence-badged citations; LRU-cached retrieval. |
| **Actionability** | Generates checklists, step-by-step guides, document lists, eligibility assessments, scheme comparisons, downloadable PDF reports, and CSC centre locations on an interactive map. |
| **Safety** | Confidence indicators (green/yellow/red), mandatory disclaimers, CSC referral fallback, rate limiting (30 req/min), input validation, admin-protected refresh endpoint. |
| **Equity/Accessibility** | 6-language UI (en/hi/te/ta/bn/mr), voice input for low-literacy users, mobile-first responsive design, dark mode, Noto Sans fonts for all scripts. |
| **Operational Efficiency** | ChromaDB retrieval ~200ms; scheme data LRU-cached; singleton embedding model; HTTP connection pooling; query result caching; JSON-persisted session store; lightweight frontend loads instantly. |

---

### Project Structure

```
submissions/track_1_community_benefits_navigator/shinde_vinayak_rao_patil/
├── README.md
├── architecture.svg
├── setup.sh                    # One-click setup script
├── run.sh                      # Server launcher
├── pyproject.toml              # Python project metadata
├── backend/
│   ├── main.py                 # FastAPI app: 16+ endpoints, config, rate limiter, session store
│   ├── requirements.txt        # Python dependencies
│   ├── .env.example            # API key configuration template
│   ├── rag/
│   │   ├── embedder.py         # Document embedding & ChromaDB indexing (singleton model)
│   │   ├── retriever.py        # Semantic search retrieval with LRU cache
│   │   └── loader.py           # Data loading & indexing entry point
│   ├── models/
│   │   ├── chat.py             # Chat orchestration, eligibility rule engine, greeting detection
│   │   └── schemes.py          # Scheme data models, caching, rule evaluation
│   └── data/
│       ├── schemes/            # JSON files for 5 schemes with eligibility_rules
│       ├── sessions.json       # Persisted chat sessions (auto-created)
│       └── faqs.json           # General FAQ data
└── frontend/
    ├── index.html              # 5-tab SPA: Chat, Eligibility, Schemes, Compare, CSC
    ├── style.css               # Mobile-first responsive styles + dark mode
    └── app.js                  # Frontend logic (sidebar, voice, PDF, map, compare)
```

---

### Timeline

- **Data Collection & Structuring:** 2 days
- **Backend (FastAPI + RAG + NIM):** 3 days
- **Frontend (UI + Integration):** 3 days
- **Safety & Polish:** 2 days
- **v2.0 Performance & Architecture:** 1 day
- **v2.1 Multi-language + Voice + CSC Locator:** 1 day
- **v2.2 Chat History Sidebar:** 1 day
- **Documentation & Demo:** 2 days

---

### License

This project is submitted as part of the Nemotron 3 Super Meetup Contest by HydPy Community.
