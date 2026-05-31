from __future__ import annotations

import json
import logging
import os
import time
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-24s | %(levelname)-5s | %(message)s",
)
logger = logging.getLogger("cb_navigator")


# --- Config ---

class Config:
    API_KEY: str = os.getenv("API_KEY", "")
    API_URL: str = os.getenv("API_URL", "https://openrouter.ai/api/v1")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "nvidia/nemotron-3-super-120b-a12b:free")
    APP_URL: str = os.getenv("APP_URL", "")
    APP_TITLE: str = os.getenv("APP_TITLE", "Community Benefits Navigator")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    RATE_LIMIT: int = int(os.getenv("RATE_LIMIT", "30"))
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")
    ADMIN_KEY: str = os.getenv("ADMIN_KEY", "")

    @classmethod
    def validate(cls):
        if not cls.API_KEY or cls.API_KEY == "sk-or-v1-your_key_here":
            logger.warning("API_KEY not configured — chat will return error messages")
        if cls.CORS_ORIGINS == "*":
            logger.warning("CORS allows all origins — restrict in production")
        if not cls.ADMIN_KEY:
            logger.warning("ADMIN_KEY not set — admin endpoints disabled. Set ADMIN_KEY in .env")


Config.validate()


# --- Rate Limiter ---

class RateLimiter:
    def __init__(self, max_requests: int, window_sec: int = 60):
        self.max_requests = max_requests
        self.window_sec = window_sec
        self._clients: Dict[str, List[float]] = defaultdict(list)

    def check(self, client_ip: str) -> tuple[bool, int, int]:
        now = time.time()
        cutoff = now - self.window_sec
        timestamps = [t for t in self._clients[client_ip] if t > cutoff]
        self._clients[client_ip] = timestamps
        remaining = max(0, self.max_requests - len(timestamps))
        if len(timestamps) >= self.max_requests:
            return False, 0, self.window_sec
        self._clients[client_ip].append(now)
        return True, remaining, self.window_sec


rate_limiter = RateLimiter(max_requests=Config.RATE_LIMIT)


# --- Session Store ---

SESSIONS_FILE = os.path.join(os.path.dirname(__file__), "data", "sessions.json")


class SessionStore:
    def __init__(self, persistence_path: str = ""):
        self._persistence_path = persistence_path or SESSIONS_FILE
        self._sessions: Dict[str, dict] = {}
        self._load()

    def _load(self):
        if os.path.exists(self._persistence_path):
            try:
                with open(self._persistence_path) as f:
                    self._sessions = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load sessions: {e}")
        else:
            os.makedirs(os.path.dirname(self._persistence_path) or ".", exist_ok=True)
            self._save()

    def _save(self):
        try:
            with open(self._persistence_path, "w") as f:
                json.dump(self._sessions, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to persist sessions: {e}")

    def get_or_create(self, session_id: str) -> dict:
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "id": session_id,
                "title": None,
                "created_at": time.time(),
                "updated_at": time.time(),
                "message_count": 0,
                "messages": [],
                "profile": None,
                "eligibility_results": [],
                "discussed_schemes": [],
            }
            self._save()
        return self._sessions[session_id]

    def list_sessions(self) -> list:
        result = []
        for sid, data in self._sessions.items():
            raw_title = data.get("title")
            if not raw_title:
                msgs = data.get("messages", [])
                user_msgs = [m for m in msgs if m.get("role") == "user"]
                raw_title = user_msgs[0]["content"][:80].replace("\n", " ") if user_msgs else "New Chat"
            result.append({
                "id": sid,
                "title": raw_title,
                "created_at": data.get("created_at", 0),
                "updated_at": data.get("updated_at", 0),
                "message_count": data.get("message_count", 0),
            })
        result.sort(key=lambda x: x["updated_at"], reverse=True)
        return result

    def get_session(self, session_id: str) -> dict:
        return self._sessions.get(session_id, {})

    def rename_session(self, session_id: str, title: str):
        session = self.get_or_create(session_id)
        session["title"] = title
        session["updated_at"] = time.time()
        self._save()

    def delete_session(self, session_id: str):
        self._sessions.pop(session_id, None)
        self._save()

    def add_message(self, session_id: str, role: str, content: str, confidence: Optional[float] = None):
        session = self.get_or_create(session_id)
        msg: dict = {"role": role, "content": content, "timestamp": time.time()}
        if confidence is not None:
            msg["confidence"] = confidence
        session.setdefault("messages", []).append(msg)
        session["message_count"] = len(session["messages"])
        session["updated_at"] = time.time()
        if not session.get("title") and role == "user":
            session["title"] = content[:80].replace("\n", " ")
        self._save()

    def get_messages(self, session_id: str) -> list:
        session = self._sessions.get(session_id)
        return session.get("messages", []) if session else []

    def update_profile(self, session_id: str, profile: dict):
        session = self.get_or_create(session_id)
        session["profile"] = profile
        self._save()

    def update_eligibility(self, session_id: str, results: list):
        session = self.get_or_create(session_id)
        session["eligibility_results"] = results
        self._save()

    def get_context_summary(self, session_id: str) -> str:
        session = self.get_or_create(session_id)
        parts = []
        if session.get("discussed_schemes"):
            parts.append(f"Schemes the user has asked about: {', '.join(session['discussed_schemes'])}.")
        if session.get("eligibility_results"):
            names = [r["name"] for r in session["eligibility_results"]]
            parts.append(f"User recently checked eligibility for: {', '.join(names)}.")
        if session.get("profile"):
            p = session["profile"]
            bits = []
            if p.get("age"): bits.append(f"age {p['age']}")
            if p.get("annual_income"): bits.append(f"annual income ₹{p['annual_income']}")
            if p.get("occupation"): bits.append(f"occupation: {p['occupation']}")
            if p.get("gender"): bits.append(f"gender: {p['gender']}")
            if bits: parts.append(f"User profile: {', '.join(bits)}.")
        return " ".join(parts)


session_store = SessionStore()


from models.chat import (
    chat_with_nemotron,
    check_eligibility,
    get_available_schemes,
    get_scheme_detail,
)
from models.schemes import clear_schemes_cache, reload_schemes
from rag.retriever import clear_retrieve_cache
from rag.embedder import delete_and_reindex
from rag.loader import load_and_index

INDEXED_FLAG = os.path.join(os.path.dirname(__file__), ".indexed")
SCHEMES_DIR = os.path.join(os.path.dirname(__file__), "data", "schemes")


def _reindex_all():
    import shutil
    clear_schemes_cache()
    clear_retrieve_cache()
    if os.path.exists(INDEXED_FLAG):
        os.remove(INDEXED_FLAG)
    load_and_index()
    with open(INDEXED_FLAG, "w") as f:
        f.write("1")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Community Benefits Navigator...")
    if not os.path.exists(INDEXED_FLAG):
        load_and_index()
        with open(INDEXED_FLAG, "w") as f:
            f.write("1")
    async with httpx.AsyncClient(timeout=60.0) as client:
        app.state.httpx_client = client
        logger.info(f"Server ready — listening on {Config.HOST}:{Config.PORT}")
        yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Community Benefits Navigator",
    description="AI-powered assistant for Indian government welfare schemes using Nemotron-3-Super. Supports English, Hindi, Telugu, Tamil, Bengali, and Marathi.",
    version="2.1.0",
    lifespan=lifespan,
    contact={
        "name": "Team shinde_vinayak_rao_patil",
        "url": "https://github.com/shindevrp/meetup-nvidia-nemotron-3-super",
    },
    license_info={
        "name": "MIT",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.CORS_ORIGINS.split(",") if Config.CORS_ORIGINS != "*" else ["*"],
    allow_credentials=Config.CORS_ORIGINS != "*",
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pydantic Models ---

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="User's question or message")
    language: str = Field(default="english", pattern="^(english|hindi|telugu|tamil|bengali|marathi)$", description="Response language")
    history: Optional[List[dict]] = Field(None, description="Previous chat messages for context")
    session_id: Optional[str] = Field(None, description="Anonymous session ID for context persistence")


class ChatResponse(BaseModel):
    reply: str = Field(..., description="AI-generated response")
    citations: list = Field(..., description="Source citations with confidence scores")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence score")


class EligibilityProfile(BaseModel):
    age: Optional[int] = Field(None, ge=0, le=150, description="Age in years")
    annual_income: Optional[float] = Field(None, ge=0, description="Annual family income in INR")
    occupation: Optional[str] = Field(None, description="Occupation type")
    gender: Optional[str] = Field(None, description="Gender")
    landowner: bool = Field(False, description="Owns agricultural land")
    owns_pucca_house: bool = Field(False, description="Family owns a pucca house")
    is_student: bool = Field(False, description="Currently enrolled as a student")
    has_lpg: bool = Field(False, description="Already has an LPG connection")
    session_id: Optional[str] = Field(None, description="Anonymous session ID")


class EligibilityResult(BaseModel):
    scheme_id: str = Field(..., description="Unique scheme identifier")
    name: str = Field(..., description="Scheme name")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Eligibility confidence score")
    match: bool = Field(..., description="Whether user likely qualifies")
    reasons: List[str] = Field(..., description="Reasons for disqualification if not matching")


class SessionListItem(BaseModel):
    id: str = Field(..., description="Session ID")
    title: Optional[str] = Field(None, description="Auto-generated or custom title")
    created_at: float = Field(..., description="Unix timestamp of creation")
    updated_at: float = Field(..., description="Unix timestamp of last activity")
    message_count: int = Field(0, description="Number of messages in session")


class SessionMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$", description="Message sender")
    content: str = Field(..., min_length=1, description="Message text")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score for assistant messages")


class SessionRename(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="New session title")


class RefreshResponse(BaseModel):
    status: str = Field(..., description="Operation status")
    schemes_loaded: int = Field(..., description="Number of schemes indexed")


tags_metadata = [
    {
        "name": "Chat",
        "description": "Conversational AI assistant using Nemotron-3-Super with RAG for grounded scheme information. Supports 6 Indian languages.",
    },
    {
        "name": "Eligibility",
        "description": "Rule-based eligibility checker that evaluates user profile against data-driven rules stored in each scheme's JSON.",
    },
    {
        "name": "Schemes",
        "description": "Browse and search government welfare scheme details including benefits, eligibility, documents, and application process.",
    },
    {
        "name": "Admin",
        "description": "Administrative endpoints for cache management and re-indexing. Requires ADMIN_KEY set in .env.",
    },
    {
        "name": "Health",
        "description": "Server health check and status information.",
    },
]

app.openapi_tags = tags_metadata


# --- Middleware ---

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/") and request.url.path != "/api/health":
        client_ip = request.client.host if request.client else "unknown"
        allowed, remaining, window = rate_limiter.check(client_ip)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please wait before sending more requests."},
                headers={
                    "X-RateLimit-Limit": str(Config.RATE_LIMIT),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(window),
                    "Retry-After": str(window),
                },
            )
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(Config.RATE_LIMIT)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
    return await call_next(request)


# --- API Endpoints ---

@app.get("/api/health", tags=["Health"], summary="Server health check")
async def health():
    """Returns server status, model info, and whether schemes are indexed."""
    return {
        "status": "ok",
        "schemes_indexed": os.path.exists(INDEXED_FLAG),
        "model": Config.MODEL_NAME,
        "languages": ["english", "hindi", "telugu", "tamil", "bengali", "marathi"],
    }


@app.get("/api/schemes", tags=["Schemes"], summary="List all available schemes")
async def list_schemes():
    """Returns a lightweight list of all supported schemes with id, name, summary, and tags."""
    return get_available_schemes()


@app.get("/api/schemes/{scheme_id}", tags=["Schemes"], summary="Get full scheme details")
async def scheme_detail(scheme_id: str):
    """Returns complete details for a single scheme including benefits, eligibility, documents, FAQ, and application process."""
    detail = get_scheme_detail(scheme_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Scheme '{scheme_id}' not found")
    return detail


@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"], summary="Send a chat message")
async def chat(req: ChatRequest, request: Request):
    """Send a message to the AI assistant. Uses RAG retrieval + Nemotron-3-Super for grounded responses.
    Supports 6 languages: english, hindi, telugu, tamil, bengali, marathi.
    Optionally accepts session_id for context persistence."""
    session_context = ""
    if req.session_id:
        session_store.get_or_create(req.session_id)
        session_context = session_store.get_context_summary(req.session_id)

    message = req.message
    if session_context:
        message = f"[Context: {session_context}]\n\n{req.message}"

    result = await chat_with_nemotron(
        message=message,
        language=req.language,
        history=req.history or [],
        httpx_client=request.app.state.httpx_client,
        api_key=Config.API_KEY,
        api_url=Config.API_URL,
        model_name=Config.MODEL_NAME,
        app_url=Config.APP_URL,
        app_title=Config.APP_TITLE,
    )

    if req.session_id:
        from models.chat import extract_scheme_names
        discussed = extract_scheme_names(req.message + result["reply"])
        session = session_store.get_or_create(req.session_id)
        for name in discussed:
            if name not in session["discussed_schemes"]:
                session["discussed_schemes"].append(name)

    return result


@app.post("/api/eligibility", response_model=List[EligibilityResult], tags=["Eligibility"], summary="Check scheme eligibility")
async def eligibility(profile: EligibilityProfile):
    """Evaluate user profile against data-driven eligibility rules for all schemes.
    Returns ranked results with confidence scores and reasons for disqualification."""
    results = check_eligibility(profile.model_dump())
    if profile.session_id:
        session_store.update_profile(profile.session_id, profile.model_dump())
        session_store.update_eligibility(profile.session_id, [
            {"scheme_id": r["scheme_id"], "name": r["name"], "match": r["match"], "confidence": r["confidence"]}
            for r in results
        ])
    return results


@app.post("/api/admin/refresh", tags=["Admin"], summary="Refresh scheme cache and re-index ChromaDB")
async def admin_refresh(request: Request):
    """Clears all caches (schemes, RAG queries), re-reads scheme JSONs, and re-indexes ChromaDB.
    Requires ADMIN_KEY to be passed as X-Admin-Key header."""
    admin_key = request.headers.get("X-Admin-Key", "")
    if not Config.ADMIN_KEY or admin_key != Config.ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing admin key. Set ADMIN_KEY in .env")
    try:
        _reindex_all()
        schemes = reload_schemes(SCHEMES_DIR)
        return RefreshResponse(status="ok", schemes_loaded=len(schemes))
    except Exception as e:
        logger.error(f"Admin refresh failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Session / History Endpoints ---


@app.get("/api/sessions", tags=["Chat"], summary="List all chat sessions")
async def list_sessions():
    """Returns all sessions for the current client, ordered by most recent activity."""
    return session_store.list_sessions()


@app.post("/api/sessions", tags=["Chat"], summary="Create a new session")
async def create_session():
    """Creates a new empty session and returns its ID."""
    sid = "sess_" + str(uuid.uuid4()).replace("-", "")[:16]
    session_store.get_or_create(sid)
    return {"id": sid}


@app.get("/api/sessions/{sid}", tags=["Chat"], summary="Get session metadata")
async def get_session(sid: str):
    """Returns metadata for a specific session (without full message history)."""
    s = session_store.get_session(sid)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "id": s.get("id"),
        "title": s.get("title"),
        "created_at": s.get("created_at"),
        "updated_at": s.get("updated_at"),
        "message_count": s.get("message_count", 0),
    }


@app.patch("/api/sessions/{sid}", tags=["Chat"], summary="Rename a session")
async def rename_session(sid: str, body: SessionRename):
    """Renames a session. Requires the session to exist."""
    s = session_store.get_session(sid)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    session_store.rename_session(sid, body.title)
    return {"status": "ok"}


@app.delete("/api/sessions/{sid}", tags=["Chat"], summary="Delete a session and its messages")
async def delete_session_endpoint(sid: str):
    """Permanently deletes a session and all its messages."""
    session_store.delete_session(sid)
    return {"status": "ok"}


@app.get("/api/sessions/{sid}/messages", tags=["Chat"], summary="Get all messages for a session")
async def get_session_messages(sid: str):
    """Returns the full message history for a session."""
    return session_store.get_messages(sid)


@app.post("/api/sessions/{sid}/messages", tags=["Chat"], summary="Add a message to a session")
async def add_session_message(sid: str, body: SessionMessage):
    """Appends a user or assistant message to the session history."""
    session_store.add_message(sid, body.role, body.content, body.confidence)
    return {"status": "ok"}


FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
