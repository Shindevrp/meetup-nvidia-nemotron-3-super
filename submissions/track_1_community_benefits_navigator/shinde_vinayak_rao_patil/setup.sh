#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================"
echo " Community Benefits Navigator - Setup"
echo "================================================"

# 1. Create .venv if not exists
if [ ! -d ".venv" ]; then
    echo "[1/4] Creating Python virtual environment..."
    python3 -m venv .venv
else
    echo "[1/4] Virtual environment already exists."
fi

source .venv/bin/activate

# 2. Install dependencies
echo "[2/4] Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r backend/requirements.txt

# 3. Configure .env
if [ ! -f "backend/.env" ]; then
    echo "[3/4] Creating backend/.env from template..."
    cp backend/.env.example backend/.env
    echo ""
    echo "  ⚠️  Open backend/.env and add your OpenRouter API key:"
    echo "      API_KEY=sk-or-v1-..."
    echo "     Get a free key at https://openrouter.ai/keys"
    echo ""
else
    echo "[3/4] backend/.env already exists."
fi

# 4. Index schemes into ChromaDB
echo "[4/4] Indexing schemes into ChromaDB..."
cd backend
python -c "
import sys
sys.path.insert(0, '.')
from rag.loader import load_and_index
load_and_index()
" 2>/dev/null || echo "  (ChromaDB indexing will run on first server start)"
cd ..

echo ""
echo "================================================"
echo " Setup complete!"
echo ""
echo " Run the server:  ./run.sh"
echo "================================================"
