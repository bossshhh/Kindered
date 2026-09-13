#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/backend"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
if ! python -c "import fastapi, langgraph, sklearn" >/dev/null 2>&1; then
  python -m pip install -r requirements.txt
fi
if [ ! -f .env ]; then
  cp .env.example .env
fi
python -m uvicorn app.main:app --reload
