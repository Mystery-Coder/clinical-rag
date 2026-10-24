#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "==> Checking environment"
if [[ ! -f .env ]]; then
  cp .env.example .env
fi

echo "==> Setting up Python venv"
if [[ -f .venv/Scripts/activate ]]; then
  source .venv/Scripts/activate
elif [[ -f .venv/bin/activate ]]; then
  source .venv/bin/activate
else
  python -m venv .venv
  source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate
  pip install -r requirements.txt
fi

pip show fastapi >/dev/null 2>&1 || pip install -r requirements.txt

echo "==> Neo4j"
if command -v docker >/dev/null 2>&1; then
  if docker ps --format '{{.Names}}' | grep -q '^cdss-neo4j$'; then
    echo "cdss-neo4j running"
  elif docker ps -a --format '{{.Names}}' | grep -q '^cdss-neo4j$'; then
    docker start cdss-neo4j
    sleep 5
  fi
fi

mkdir -p data/passages data/index data/primekg data/mimic-iv-demo data/eval

echo "==> Index check"
if [[ ! -f data/index/passages.faiss ]]; then
  [[ ! -f data/passages/pubmed.jsonl ]] && python scripts/ingest_pubmed.py
  python scripts/build_index.py
else
  echo "Index ready"
fi

echo "==> PrimeKG check"
if [[ ! -f data/primekg/clinical_nodes.jsonl ]]; then
  python scripts/load_graph.py || true
else
  echo "PrimeKG slice ready"
  # Don't reload if already in Neo4j
  PWDENV=$(grep NEO4J_PASSWORD .env | cut -d= -f2 || true)
  if [[ -n "${PWDENV:-}" ]] && command -v docker >/dev/null 2>&1 && docker ps --format '{{.Names}}' | grep -q '^cdss-neo4j$'; then
    CNT=$(docker exec cdss-neo4j cypher-shell -u neo4j -p "$PWDENV" "MATCH (n:Disease) RETURN count(n) AS c;" 2>/dev/null | grep -E '^[0-9]+$' | tail -1 || echo 0)
    if [[ "$CNT" -gt 1000 ]]; then
      echo "Neo4j has $CNT disease nodes - skipping reload"
    else
      python scripts/load_graph.py || true
    fi
  fi
fi

echo "==> Starting services in separate windows/terminals"
# Try to start in background properly
if command -v gnome-terminal >/dev/null 2>&1; then
  gnome-terminal -- bash -c "cd '$ROOT' && source .venv/bin/activate && uvicorn cdss.api:app --app-dir src --reload --host 127.0.0.1 --port 8000; exec bash" &
  gnome-terminal -- bash -c "cd '$ROOT/web' && npm run dev; exec bash" &
elif command -v konsole >/dev/null 2>&1; then
  konsole -e bash -c "cd '$ROOT' && source .venv/bin/activate && uvicorn cdss.api:app --app-dir src --reload --host 127.0.0.1 --port 8000" &
  konsole -e bash -c "cd '$ROOT/web' && npm run dev" &
elif command -v xterm >/dev/null 2>&1; then
  xterm -e "cd '$ROOT' && source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate && uvicorn cdss.api:app --app-dir src --reload --host 127.0.0.1 --port 8000" &
  xterm -e "cd '$ROOT/web' && npm run dev" &
else
  # Windows Git Bash / WSL - use start
  if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    start "CDSS-API" bash -c "cd '$ROOT' && source .venv/Scripts/activate && uvicorn cdss.api:app --app-dir src --reload --host 127.0.0.1 --port 8000; exec bash"
    start "CDSS-WEB" bash -c "cd '$ROOT/web' && npm run dev; exec bash"
  else
    # Linux/Mac - tmux/screen or just background
    if command -v tmux >/dev/null 2>&1; then
      tmux new-session -d -s cdss-api "cd '$ROOT' && source .venv/bin/activate && uvicorn cdss.api:app --app-dir src --reload --host 127.0.0.1 --port 8000"
      tmux new-session -d -s cdss-web "cd '$ROOT/web' && npm run dev"
      echo "Started in tmux: tmux attach -t cdss-api or cdss-web"
    else
      nohup bash -c "cd '$ROOT' && source .venv/bin/activate && uvicorn cdss.api:app --app-dir src --reload --host 127.0.0.1 --port 8000" >/tmp/cdss-api.log 2>&1 &
      nohup bash -c "cd '$ROOT/web' && npm run dev" >/tmp/cdss-web.log 2>&1 &
      echo "Started in background. Logs: /tmp/cdss-api.log, /tmp/cdss-web.log"
    fi
  fi
fi

echo "Done. API: http://127.0.0.1:8000, Web: http://127.0.0.1:3000"
