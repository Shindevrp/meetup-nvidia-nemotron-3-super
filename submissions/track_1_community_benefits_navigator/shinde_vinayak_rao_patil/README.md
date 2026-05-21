# Project Name: Community Benefits Navigator

**Track:** Track 1 - Community Benefits Navigator

**Team Name:** shinde_vinayak_rao_patil

---

### 🔗 Project Links
- **YouTube Demo:** *[Link to be added after recording]*
- **Blog Post:** *[Link to be added after publishing]*
- **LinkedIn Post:** *[Link to be added after posting]*

---

### 🏗 Architecture

![Architecture Diagram](architecture.png)

The system follows a **RAG (Retrieval-Augmented Generation)** pattern:

1. **Frontend** (HTML/CSS/JS) — Mobile-first, accessible web UI with chat, eligibility checker, and scheme browser
2. **Backend** (FastAPI) — Python API server handling chat, eligibility logic, and scheme data
3. **RAG Pipeline** (ChromaDB + Sentence Transformers) — Embeds scheme documents and retrieves relevant context for every query
4. **LLM** (NVIDIA Nemotron-3-Super via NIM API) — Generates grounded responses using retrieved context with citations
5. **Data Layer** — Structured JSON files for 5 central government schemes

---

### 📖 Description

**How it uses Nemotron-3-Super:**

The Community Benefits Navigator helps Indian citizens discover, understand, and apply for central government welfare schemes. It leverages **NVIDIA Nemotron-3-Super** (via NVIDIA NIM API) as the reasoning engine:

- **Grounded Generation:** Every user query first triggers a RAG retrieval step that pulls relevant scheme documents from ChromaDB. The Nemotron model receives this context as part of the system prompt and is instructed to **only answer from the provided documents**, ensuring faithfulness to official sources.
- **Citation Tracking:** Each response includes confidence-badged citations showing exactly which scheme document section was used.
- **Eligibility Reasoning:** For the eligibility checker, a rules-based engine pre-filters schemes, but Nemotron handles nuanced eligibility questions through the chat interface.
- **Multilingual Support:** Nemotron's multilingual capabilities enable English/Hindi toggle without separate translation models.
- **Safety by Prompt Design:** The system prompt includes strong grounding constraints, a "don't know" fallback instruction, and mandatory CSC (Common Service Centre) referral for uncertain answers.

**Schemes supported (MVP):**
1. **PM-KISAN** — Income support for farmers (₹6,000/year)
2. **Ayushman Bharat (PM-JAY)** — Health insurance (₹5L/family/year)
3. **PM Awas Yojana** — Housing subsidy for EWS/LIG/MIG
4. **NSP Scholarships** — Multiple education scholarships for SC/ST/OBC/Minority students
5. **PM Ujjwala Yojana** — Free LPG connections for BPL women

---

### 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML, CSS, Vanilla JavaScript |
| Backend | Python, FastAPI |
| LLM | NVIDIA Nemotron-3-Super (NVIDIA NIM API) |
| Vector DB | ChromaDB |
| Embeddings | `intfloat/multilingual-e5-small` (Hugging Face) |
| PDF/Reporting | html2pdf.js (client-side) |

---

### 🚀 How to Run

**Prerequisites:**
- Python 3.10+
- NVIDIA NIM API key (get one at [build.nvidia.com](https://build.nvidia.com))
- 4GB+ RAM for ChromaDB + Sentence Transformers

**Setup:**
```bash
# 1. Navigate to the project
cd submissions/track_1_community_benefits_navigator/shinde_vinayak_rao_patil

# 2. Set up Python environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r backend/requirements.txt

# 4. Configure API key
cp backend/.env.example backend/.env
# Edit backend/.env and add your NIM_API_KEY

# 5. Run the server
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Open:** `http://localhost:8000` in your browser.

The first run will index scheme documents into ChromaDB (takes ~30 seconds).

---

### ✅ Judging Criteria Mapping

| Criterion | How We Address It |
|---|---|
| **Community Value** | Solves real problem — 40%+ Indians seek help with welfare schemes but face language, literacy, and awareness barriers |
| **Grounded Accuracy** | RAG pipeline ensures every answer cites official scheme documents; model instructed to refuse ungrounded queries |
| **Actionability** | Generates checklists, step-by-step application guides, document lists, and eligibility assessments |
| **Safety** | Confidence indicators (green/yellow/red), mandatory disclaimers, CSC referral fallback, rate limiting |
| **Equity/Accessibility** | English/Hindi bilingual, mobile-first responsive UI, simple conversational interface, works on low bandwidth |
| **Operational Efficiency** | ChromaDB retrieval <200ms; NIM API generates responses in 1-3s; lightweight frontend loads instantly |

---

### 📁 Project Structure

```
submissions/track_1_community_benefits_navigator/shinde_vinayak_rao_patil/
├── README.md
├── architecture.png
├── backend/
│   ├── main.py              # FastAPI app with all routes
│   ├── requirements.txt     # Python dependencies
│   ├── .env.example         # API key configuration template
│   ├── rag/
│   │   ├── embedder.py      # Document embedding & ChromaDB indexing
│   │   ├── retriever.py     # Semantic search retrieval
│   │   └── loader.py        # Data loading script
│   ├── models/
│   │   ├── chat.py          # NIM API client + prompt templates
│   │   └── schemes.py       # Scheme data models & loader
│   └── data/
│       ├── schemes/         # JSON files for 5 schemes
│       └── faqs.json        # General FAQ data
└── frontend/
    ├── index.html           # Single-page application
    ├── style.css            # Mobile-first responsive styles
    └── app.js               # Frontend logic
```

---

### 📅 Timeline

- **Data Collection & Structuring:** 2 days
- **Backend (FastAPI + RAG + NIM):** 3 days
- **Frontend (UI + Integration):** 3 days
- **Safety & Polish:** 2 days
- **Documentation & Demo:** 2 days

---

### 📜 License

This project is submitted as part of the Nemotron 3 Super Meetup Contest by HydPy Community.
