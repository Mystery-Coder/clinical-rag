#!/usr/bin/env bash
# Run API and web in two separate terminal tabs/windows
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate
# API
gnome-terminal --tab -- bash -c "cd '$ROOT' && source .venv/bin/activate && uvicorn cdss.api:app --app-dir src --reload --host 127.0.0.1 --port 8000; exec bash" 2>/dev/null || \
xterm -e "cd '$ROOT' && source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate && uvicorn cdss.api:app --app-dir src --reload --host 127.0.0.1 --port 8000" 2>/dev/null || \
start bash -c "cd '$ROOT' && source .venv/Scripts/activate && uvicorn cdss.api:app --app-dir src --reload --host 127.0.0.1 --port 8000"
sleep 2
gnome-terminal --tab -- bash -c "cd '$ROOT/web' && npm run dev; exec bash" 2>/dev/null || \
xterm -e "cd '$ROOT/web' && npm run dev" 2>/dev/null || \
start bash -c "cd '$ROOT/web' && npm run dev"
