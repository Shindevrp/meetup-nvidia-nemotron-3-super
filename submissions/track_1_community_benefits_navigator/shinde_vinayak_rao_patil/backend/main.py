# FastAPI server for Community Benefits Navigator
# Serves frontend static files and exposes REST APIs for chat, eligibility, and scheme data
# Uses Nemotron-3-Super via OpenRouter for grounded RAG-powered responses

import os
import sys
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Ensure backend/ is on sys.path so subpackages are importable
sys.path.insert(0, os.path.dirname(__file__))

# Load .env file from backend/ directory so API keys are available via os.getenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Optional

from models.chat import (
    chat_with_nemotron,
    get_available_schemes,
    get_scheme_detail,
    check_eligibility,
)
from rag.loader import load_and_index

# Flag file to track whether ChromaDB has been indexed (avoids re-indexing on every restart)
INDEXED_FLAG = os.path.join(os.path.dirname(__file__), ".indexed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run once at startup: index scheme documents into ChromaDB if not already done
    if not os.path.exists(INDEXED_FLAG):
        load_and_index()
        with open(INDEXED_FLAG, "w") as f:
            f.write("1")
    yield


app = FastAPI(
    title="Community Benefits Navigator",
    description="AI-powered assistant for Indian government welfare schemes using Nemotron-3-Super",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow all origins for demo purposes (restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request/Response Models ---

class ChatRequest(BaseModel):
    message: str
    language: str = Field(default="english", pattern="^(english|hindi)$")
    history: Optional[List[dict]] = None


class ChatResponse(BaseModel):
    reply: str
    citations: list
    confidence: float


class EligibilityProfile(BaseModel):
    age: Optional[int] = None
    annual_income: Optional[float] = None
    occupation: Optional[str] = None
    gender: Optional[str] = None
    landowner: bool = False
    owns_pucca_house: bool = False
    is_student: bool = False
    has_lpg: bool = False


class EligibilityResult(BaseModel):
    scheme_id: str
    name: str
    confidence: float
    match: bool
    reasons: List[str]


# --- API Endpoints ---

@app.get("/api/health")
async def health():
    return {"status": "ok", "schemes_indexed": os.path.exists(INDEXED_FLAG)}


@app.get("/api/schemes")
async def list_schemes():
    return get_available_schemes()


@app.get("/api/schemes/{scheme_id}")
async def scheme_detail(scheme_id: str):
    detail = get_scheme_detail(scheme_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Scheme '{scheme_id}' not found")
    return detail


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    result = await chat_with_nemotron(
        message=req.message,
        language=req.language,
        history=req.history or [],
    )
    return result


@app.post("/api/eligibility", response_model=List[EligibilityResult])
async def eligibility(profile: EligibilityProfile):
    return check_eligibility(profile.model_dump())


# Serve frontend static files (HTML/CSS/JS) at the root
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
