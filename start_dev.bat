@echo off
setlocal enabledelayedexpansion

cd /d %~dp0

echo ==^> Checking environment
if not exist .env (
  echo Creating .env from .env.example
  copy .env.example .env
)

echo ==^> Checking Python venv
if exist .venv\Scripts\activate.bat (
  call .venv\Scripts\activate.bat
) else if exist .venv\Scripts\activate (
  call .venv\Scripts\activate
) else (
  echo No venv found. Creating...
  python -m venv .venv
  call .venv\Scripts\activate.bat
  pip install -r requirements.txt
)

echo ==^> Installing Python deps if needed
pip show fastapi >nul 2>&1 || pip install -r requirements.txt

echo ==^> Checking Neo4j container
docker --version >nul 2>&1 && (
  docker ps --format "{{.Names}}" | findstr /C:"cdss-neo4j" >nul 2>&1 && (
    echo Neo4j container (cdss-neo4j) is running
  ) || (
    docker ps -a --format "{{.Names}}" | findstr /C:"cdss-neo4j" >nul 2>&1 && (
      echo Starting Neo4j container...
      docker start cdss-neo4j
      timeout /t 5 /nobreak >nul
    ) || (
      echo No cdss-neo4j container found. Create with:
      echo docker run -d --name cdss-neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/yourpassword neo4j:5
      echo Update NEO4J_PASSWORD in .env accordingly
    )
  )
)

echo ==^> Ensuring data directories
if not exist data\passages mkdir data\passages
if not exist data\index mkdir data\index
if not exist data\primekg mkdir data\primekg
if not exist data\mimic-iv-demo mkdir data\mimic-iv-demo
if not exist data\eval mkdir data\eval

echo ==^> Building index if missing
if not exist data\index\passages.faiss (
  echo Index missing - running ingest_pubmed and build_index
  if not exist data\passages\pubmed.jsonl (
    python scripts\ingest_pubmed.py
  )
  python scripts\build_index.py
) else (
  echo Index exists: data\index\passages.faiss
)

echo ==^> Loading PrimeKG slice
if not exist data\primekg\clinical_nodes.jsonl (
  python scripts\load_graph.py
) else (
  echo PrimeKG clinical slice exists
  python scripts\load_graph.py 2>nul
)

echo ==^> Starting FastAPI backend
start "CDSS API" cmd /k "cd /d %~dp0 && call .venv\Scripts\activate.bat && uvicorn cdss.api:app --app-dir src --reload --host 127.0.0.1 --port 8000"

timeout /t 3 /nobreak >nul

echo ==^> Starting Next.js frontend
cd web
if not exist node_modules (
  echo Installing npm deps...
  npm install
)
start "CDSS Web" cmd /k "npm run dev"

echo All started. Open http://127.0.0.1:3000
