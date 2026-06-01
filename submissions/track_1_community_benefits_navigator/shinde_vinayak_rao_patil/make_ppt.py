from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
import os

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

W = prs.slide_width
H = prs.slide_height

BLUE = RGBColor(0x1A, 0x73, 0xE8)
DARK = RGBColor(0x1F, 0x2A, 0x3A)
GRAY = RGBColor(0x5F, 0x6B, 0x7A)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_BG = RGBColor(0xF2, 0xF4, 0xF7)
GREEN = RGBColor(0x2E, 0x7D, 0x32)
ORANGE = RGBColor(0xE6, 0x51, 0x00)

def add_bg(slide, color=LIGHT_BG):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color

def add_rect(slide, left, top, width, height, color):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    return shape

def add_text_box(slide, left, top, width, height, text, size=18, color=DARK, bold=False, align=PP_ALIGN.LEFT, font_name="Calibri"):
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(size)
    p.font.color.rgb = color
    p.font.bold = bold
    p.font.name = font_name
    p.alignment = align
    return txBox

def add_bullet_slide(slide, left, top, width, height, items, size=16, color=DARK):
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.text = item
        p.font.size = Pt(size)
        p.font.color.rgb = color
        p.font.name = "Calibri"
        p.space_after = Pt(6)
        p.level = 0
    return txBox

# === SLIDE 1: TITLE ===
slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
add_bg(slide)
add_rect(slide, 0, 0, W, Inches(3.2), BLUE)
add_text_box(slide, Inches(0.8), Inches(0.6), Inches(11), Inches(1), "Community Benefits Navigator", 40, WHITE, True, PP_ALIGN.LEFT)
add_text_box(slide, Inches(0.8), Inches(1.6), Inches(11), Inches(0.6), "Indian Government Welfare Schemes AI Assistant", 22, RGBColor(0xBB, 0xDE, 0xFB), False, PP_ALIGN.LEFT)
add_text_box(slide, Inches(0.8), Inches(2.3), Inches(11), Inches(0.5), "Built with NVIDIA Nemotron-3-Super + Multi-Query RAG", 16, RGBColor(0xDD, 0xEE, 0xFF), False, PP_ALIGN.LEFT)
add_text_box(slide, Inches(0.8), Inches(4.0), Inches(11), Inches(0.5), "Vinayak Rao Patil Shinde", 28, DARK, True)
add_text_box(slide, Inches(0.8), Inches(4.6), Inches(11), Inches(0.4), "GitHub: @shindevrp", 16, GRAY)
add_text_box(slide, Inches(0.8), Inches(5.2), Inches(11), Inches(0.8), "Track 1: Community Benefits Navigator\nNVIDIA + DataHack Summit 2026", 14, GRAY)

# === SLIDE 2: PROBLEM ===
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_rect(slide, 0, 0, W, Inches(0.08), BLUE)
add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11), Inches(0.7), "The Problem", 32, DARK, True)
items = [
    "▸ 60+ central welfare schemes — each with different eligibility, documents, and application process",
    "▸ Farmers, women, students, and low-income families struggle to discover what they qualify for",
    "▸ Scheme information is spread across multiple government portals in different formats",
    "▸ AI assistants hallucinate or give generic answers — no source confidence",
    "▸ Language barrier: most information is English-only, excluding Hindi/bilingual users",
]
add_bullet_slide(slide, Inches(0.8), Inches(1.4), Inches(11.5), Inches(5), items, 17, DARK)

# === SLIDE 3: SOLUTION ===
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_rect(slide, 0, 0, W, Inches(0.08), BLUE)
add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11), Inches(0.7), "The Solution", 32, DARK, True)
items = [
    "▸ Multi-Query RAG: decomposes broad questions into sub-queries for complete coverage",
    "▸ Nemotron-3-Super (via OpenRouter) handles 6 distinct roles: answer, explain, compare, summarize, FAQ, recommend",
    "▸ Data-driven JSON rule engine — new schemes require zero code changes",
    "▸ Self-rated confidence scores via embedded JSON extraction",
    "▸ Full i18n: English + Hindi (Telugu/Tamil/Bengali/Marathi fallback)",
    "▸ Voice input, dark mode, session history, PDF download",
]
add_bullet_slide(slide, Inches(0.8), Inches(1.4), Inches(11.5), Inches(5), items, 17, DARK)

# === SLIDE 4: ARCHITECTURE ===
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_rect(slide, 0, 0, W, Inches(0.08), BLUE)
add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11), Inches(0.7), "Architecture", 32, DARK, True)

# Import the architecture image
img_path = "/home/shinde/Desktop/meetup-nvidia-nemotron-3-super/submissions/track_1_community_benefits_navigator/shinde_vinayak_rao_patil/blog/request-lifecycle.png"
if os.path.exists(img_path):
    slide.shapes.add_picture(img_path, Inches(0.8), Inches(1.3), Inches(11.5), Inches(5.5))

# Simple text fallback
labels = [
    "User → FastAPI Backend → Query Decomposition → Multi-Query ChromaDB Retrieval",
    "→ Merge & Deduplicate → Nemotron-3-Super (OpenRouter) → Response + Confidence",
]
add_text_box(slide, Inches(0.8), Inches(6.8), Inches(11), Inches(0.5), " |  ".join(labels), 12, GRAY)

# === SLIDE 5: FEATURES ===
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_rect(slide, 0, 0, W, Inches(0.08), BLUE)
add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11), Inches(0.7), "Key Features", 32, DARK, True)

features = [
    ("Chat", "Multi-turn conversation with query decomposition\nSuggested question chips, voice input\nSession history sidebar", Inches(0.5)),
    ("Eligibility", "Age + income + demographics form\nRule-engine matching + AI explanation\nPDF download of results", Inches(3.8)),
    ("Schemes", "Browse/search all 60+ welfare schemes\nClick for full details (benefits, docs, portal)\nMulti-language names", Inches(7.1)),
    ("Compare", "Side-by-side table compare\nAI Compare with Nemotron recommendations\nJoint-applicability check", Inches(10.4)),
]

for title, desc, left in features:
    card = add_rect(slide, left, Inches(1.5), Inches(2.8), Inches(4.5), WHITE)
    card.shadow.inherit = False
    add_text_box(slide, left + Inches(0.2), Inches(1.7), Inches(2.4), Inches(0.5), title, 20, BLUE, True, PP_ALIGN.CENTER)
    add_text_box(slide, left + Inches(0.2), Inches(2.4), Inches(2.4), Inches(3.2), desc, 13, DARK)

# Extra features at bottom
add_text_box(slide, Inches(0.5), Inches(6.3), Inches(12), Inches(0.5), "+ CSC Locator (Leaflet map)  |  Dark Mode  |  Multi-Language (6 languages)  |  PDF Reports  |  One-Click Docker Deploy", 12, GRAY, False, PP_ALIGN.CENTER)

# === SLIDE 6: LIVE DEMO ===
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_rect(slide, 0, 0, W, Inches(0.08), BLUE)
add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11), Inches(0.7), "Live Demo Walkthrough", 32, DARK, True)

steps = [
    "1. Chat Tab — Ask \"What schemes am I eligible for?\" — see multi-query decomposition in action",
    "2. Eligibility Tab — Enter age 35, income 1.2L — see matched schemes + AI explanation button",
    "3. Schemes Tab — Browse/search, click any scheme for full details (benefits, docs, helpline)",
    "4. Compare Tab — Pick two schemes, click Compare (table) then AI Compare (Nemotron)",
    "5. Language — Switch to Hindi → all UI + responses translate instantly",
    "6. CSC Locator — Search \"Pune\" → see nearby Common Service Centres on Leaflet map",
    "7. Extra — Toggle dark mode, use voice input, download eligibility PDF, view session history",
]
add_bullet_slide(slide, Inches(0.8), Inches(1.4), Inches(11.5), Inches(5.5), steps, 16, DARK)

# === SLIDE 7: TECH STACK ===
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_rect(slide, 0, 0, W, Inches(0.08), BLUE)
add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11), Inches(0.7), "Tech Stack", 32, DARK, True)

col1 = ["Backend", "FastAPI", "ChromaDB (vector store)", "Sentence Transformers (E5-small)", "OpenRouter (Nemotron-3-Super)"]
col2 = ["Frontend", "Vanilla JS + CSS", "Leaflet.js (CSC map)", "html2pdf.js (PDF export)", "Web Speech API (voice input)"]
col3 = ["Infra", "Python 3.11 + Uvicorn", "Docker + Docker Compose", "Setup.sh auto-configure", "CORS + session middleware"]

y_start = Inches(1.4)
for i, (head, *items) in enumerate([col1, col2, col3]):
    left = Inches(0.8 + i * 4.2)
    add_text_box(slide, left, y_start, Inches(3.8), Inches(0.5), head, 20, BLUE, True)
    add_bullet_slide(slide, left + Inches(0.1), y_start + Inches(0.6), Inches(3.6), Inches(4), [f"• {item}" for item in items], 14, DARK)

add_text_box(slide, Inches(0.8), Inches(5.8), Inches(11), Inches(0.6), "Why Vanilla JS: app under 1300 lines, framework overhead not justified. One model handles 6 roles via different prompts.", 12, GRAY)

# === SLIDE 8: HIGHLIGHTS ===
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_rect(slide, 0, 0, W, Inches(0.08), BLUE)
add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11), Inches(0.7), "Key Highlights", 32, DARK, True)

highlights = [
    "★ Query Decomposition: \"What am I eligible for?\" → 4 sub-queries → full coverage",
    "★ Multi-Role LLM: Same Nemotron model answers, explains, compares, recommends, summarizes",
    "★ Self-Rated Confidence: JSON regex extraction, no separate API call, transparent to user",
    "★ Data-Driven: Add a new scheme JSON → zero code changes needed anywhere",
    "★ OpenRouter Free Tier: ~$0/month during dev, switch to direct NIM for production",
    "★ SVG Mic Icons: Open-source, respects dark/light mode via currentColor",
    "★ Full i18n: 90+ UI strings translated, data-i18n attributes on all static HTML",
    "★ One-Click Deploy: Docker Compose with persistent ChromaDB volume",
]
add_bullet_slide(slide, Inches(0.8), Inches(1.3), Inches(11.5), Inches(5.5), highlights, 16, DARK)

# === SLIDE 9: LINKS ===
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_rect(slide, 0, 0, W, Inches(0.08), BLUE)
add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11), Inches(0.7), "Links & Submission", 32, DARK, True)

add_text_box(slide, Inches(0.8), Inches(1.5), Inches(11), Inches(0.5), "GitHub Repository", 22, BLUE, True)
add_text_box(slide, Inches(0.8), Inches(2.1), Inches(11), Inches(0.4), "https://github.com/shindevrp/meetup-nvidia-nemotron-3-super", 14, GRAY)

add_text_box(slide, Inches(0.8), Inches(3.0), Inches(11), Inches(0.5), "Submission Directory", 22, BLUE, True)
add_text_box(slide, Inches(0.8), Inches(3.6), Inches(11), Inches(0.4), "track_1_community_benefits_navigator/shinde_vinayak_rao_patil/", 14, GRAY)

add_text_box(slide, Inches(0.8), Inches(4.5), Inches(11), Inches(0.5), "Quick Start", 22, BLUE, True)
add_text_box(slide, Inches(0.8), Inches(5.1), Inches(11), Inches(0.8), "git clone ...  →  cd backend && cp .env.example .env && bash setup.sh  →  uvicorn main:app\nOr: docker compose up --build", 13, GRAY)

add_text_box(slide, Inches(0.8), Inches(6.2), Inches(11), Inches(0.5), "YouTube Demo  |  Blog Post  |  LinkedIn — (links in README)", 16, DARK, True, PP_ALIGN.CENTER)

# === SLIDE 10: THANK YOU ===
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide)
add_rect(slide, 0, 0, W, Inches(0.08), BLUE)
add_text_box(slide, Inches(0.8), Inches(2.0), Inches(11), Inches(1), "Thank You", 48, DARK, True, PP_ALIGN.CENTER)
add_text_box(slide, Inches(0.8), Inches(3.2), Inches(11), Inches(0.6), "Questions? Feedback?", 24, GRAY, False, PP_ALIGN.CENTER)
add_text_box(slide, Inches(0.8), Inches(4.2), Inches(11), Inches(0.5), "Vinayak Rao Patil Shinde  |  @shindevrp  |  NVIDIA + DataHack Summit 2026", 16, GRAY, False, PP_ALIGN.CENTER)

# === ADD SPEAKER NOTES ===
notes_data = {
    0: "Welcome everyone. Today I'm presenting the Community Benefits Navigator — an AI assistant for Indian government welfare schemes built with NVIDIA Nemotron-3-Super."
       "\n\nThis app helps farmers, students, women, and low-income families discover what welfare schemes they qualify for, how to apply, and compare options — all in their preferred language.",
    1: "The problem: India has 60+ central welfare schemes spread across different portals. Each has different eligibility criteria, required documents, and application processes. Most information is English-only. People don't know what they qualify for or where to start.",
    2: "Our solution: A multi-query RAG system using Nemotron-3-Super. The app decomposes broad questions into targeted sub-queries, retrieves relevant documents from ChromaDB, and generates responses with confidence scores."
       "\n\nKey features: 6 LLM roles, data-driven rule engine, full i18n, voice input, dark mode.",
    3: "Here's the architecture. User sends a query → FastAPI backend → query decomposition (2-4 sub-questions) → multi-query ChromaDB retrieval → merge & deduplicate → Nemotron generates final answer with confidence score."
       "\n\nThe LLM has 6 distinct roles via different prompts: answering, eligibility checking, comparison, recommendation, FAQ, and summarization.",
    4: "Let me walk through the key features. Chat tab for conversation, Eligibility tab with form + AI explanation, Schemes browser with search, Compare tab with both table and AI comparison, and CSC Locator for finding help centers."
       "\n\nPlus dark mode, 6 languages, voice input, PDF download, and Docker one-click deploy.",
    5: "Now let me show you the live demo. I'll start with a chat query, show eligibility checking, browse schemes, compare two schemes, switch to Hindi to show i18n, and finally search for a CSC on the map."
       "\n\nI'll also toggle dark mode and show voice input briefly.",
    6: "Tech stack: FastAPI backend with ChromaDB vector store, Sentence Transformers for embeddings, OpenRouter for Nemotron-3-Super access. Frontend is vanilla JS under 1300 lines."
       "\n\nDocker Compose for one-command deployment. Setup.sh for auto-configuration.",
    7: "Key highlights: The same LLM handles 6 roles via different prompts. Query decomposition ensures complete coverage. Self-rated confidence is transparent. Adding a new scheme requires zero code changes."
       "\n\nOpenRouter free tier saved ~$100/month during development. For production, switch to direct NVIDIA NIM deployment.",
    8: "Here are the links to the GitHub repository and submission directory. The README has full documentation including the architecture diagram."
       "\n\nQuick start: clone the repo, run setup.sh, and start with uvicorn. Or use Docker Compose for a fully containerized setup.",
    9: "Thank you for watching! Happy to answer any questions. This project was built for the NVIDIA + DataHack Summit 2026 hackathon."
}

with open("/home/shinde/Desktop/meetup-nvidia-nemotron-3-super/submissions/track_1_community_benefits_navigator/shinde_vinayak_rao_patil/make_ppt.py", "r") as f:
    pass

for i, slide in enumerate(prs.slides):
    if i in notes_data:
        notes_slide = slide.notes_slide
        notes_slide.notes_text_frame.text = notes_data[i]

output_path = "/home/shinde/Desktop/meetup-nvidia-nemotron-3-super/submissions/track_1_community_benefits_navigator/shinde_vinayak_rao_patil/presentation.pptx"
prs.save(output_path)
print(f"Saved to {output_path}")
print(f"Total slides: {len(prs.slides)}")
