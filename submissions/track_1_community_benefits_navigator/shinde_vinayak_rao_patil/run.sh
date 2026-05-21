#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Run ./setup.sh first."
    exit 1
fi

source .venv/bin/activate

# Load .env for API keys
if [ -f "backend/.env" ]; then
    set -a; source backend/.env; set +a
fi

echo "Starting Community Benefits Navigator..."
echo "  Model: ${MODEL_NAME:-nvidia/nemotron-3-super-120b-a12b:free}"
echo "  Open:  http://localhost:${PORT:-8000}"
echo ""

cd backend
uvicorn main:app --reload --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}"
