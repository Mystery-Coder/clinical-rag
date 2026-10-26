# Clinical RAG CDSS - Setup Guide

This guide will walk you through setting up and running the Clinical Decision Support System from scratch.

## Prerequisites

Before starting, ensure you have the following installed:

- [Python 3.10+](https://www.python.org/downloads/)
- [Node.js 18+](https://nodejs.org/) and npm
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (for Neo4j graph database)
- [Git](https://git-scm.com/)

## 1. Clone and Navigate

```bash
git clone <repo-url>
cd "Clinical RAG COE/clinical-rag"
```

## 2. Set Up Python Environment

### Windows (Git Bash)

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

### Windows (Command Prompt)

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Linux/Mac

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your preferred settings:

```env
# LLM Configuration (Optional - works without API key using extractive mode)
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=
LLM_MODEL=gpt-4o-mini

# Neo4j Configuration
NEO4J_URI=bolt://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=cdss-college-local

# NICE API (Optional)
NICE_API_KEY=
NICE_API_BASE=https://syndication.nice.org.uk/services

# Data Configuration
PASSAGE_CAP=500
TOP_K=5
DATA_DIR=data
```

## 4. Set Up Neo4j with Docker

Start the Neo4j container. The container `cdss-neo4j` is likely already running, but if not:

```bash
docker run -d \
  --name cdss-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/cdss-college-local \
  neo4j:5
```

Verify it's running:

```bash
docker ps | grep neo4j
```

You can also access Neo4j Browser at http://localhost:7474 (login: neo4j/cdss-college-local)

## 5. Prepare Data

### MIMIC-IV Demo Data

Place MIMIC-IV demo 2.2 hospital tables under `data/mimic-iv-demo/hosp/`. The files should include:

- `patients.csv` or `patients.csv.gz`
- `admissions.csv` or `admissions.csv.gz`
- `diagnoses_icd.csv` or `diagnoses_icd.csv.gz`
- `d_icd_diagnoses.csv`
- `prescriptions.csv`
- `labevents.csv`
- `d_labitems.csv`

The code will find them regardless of compression.

### Existing Data

The repo may already have:

- `data/index/passages.faiss` and `data/index/meta.jsonl` (pre-built index)
- `data/passages/pubmed.jsonl` (PubMed passages)
- `data/primekg/` (filtered PrimeKG data)
- `data/mimic-iv-demo/hosp/` (MIMIC tables)

If these exist, you can skip rebuilding.

## 6. Build Index and Load Graph (If Needed)

If the index or graph isn't built:

```bash
# Activate venv first
source .venv/Scripts/activate  # Windows Git Bash

# Ingest PubMed passages filtered by MIMIC diagnoses
python scripts/ingest_pubmed.py

# Build FAISS index with MedCPT embeddings
python scripts/build_index.py

# Download PrimeKG, filter to clinical slice, and load into Neo4j
python scripts/load_graph.py
```

**Note:**

- `load_graph.py` will download PrimeKG files if missing (can take a few minutes)
- Loading into Neo4j will take several minutes for ~200k drug-drug edges
- If Neo4j password isn't set, it will skip Neo4j loading but save the filtered data to disk

## 7. Run the Application

You need two terminals running simultaneously.

### Terminal 1: FastAPI Backend (Port 8000)

```bash
# Activate venv
source .venv/Scripts/activate  # Windows Git Bash
# or .venv\Scripts\activate on CMD

# Start server
uvicorn cdss.api:app --app-dir src --reload --host 127.0.0.1 --port 8000
```

Backend will be available at:

- API: http://127.0.0.1:8000
- API Docs: http://127.0.0.1:8000/docs
- Fallback UI: http://127.0.0.1:8000

### Terminal 2: Next.js Frontend (Port 3000)

```bash
cd web
npm install  # Only needed first time
npm run dev
```

Frontend will be available at: http://127.0.0.1:3000

## 8. Quick Start Script (Alternative)

For convenience, use the startup script:

**Windows Git Bash:**

```bash
./start_dev.sh
```

**Windows CMD:**

```cmd
run_all.bat
```

This will handle venv activation, dependency checks, index verification, and start both services.

## Testing

### Via Web UI

1. Open http://127.0.0.1:3000
2. Select a patient from the left panel or enter a question
3. Click "Consult" to get results

### Via CLI

```bash
source .venv/Scripts/activate
python scripts/ask.py "treatment considerations in sepsis with kidney injury"
python scripts/ask.py --subject-id 10000032
```

### Via API

```bash
curl -X POST http://127.0.0.1:8000/consult \
  -H "Content-Type: application/json" \
  -d '{"question": "treatment considerations in sepsis"}'
```

## Troubleshooting

| Issue                                         | Solution                                                                                                                      |
| --------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `ModuleNotFoundError: No module named 'cdss'` | Make sure you're running with `--app-dir src` or have activated venv and installed deps                                       |
| Index not found                               | Run `python scripts/build_index.py` after ingesting passages                                                                  |
| Neo4j connection fails                        | Check if container is running: `docker ps`. Verify password in `.env` matches container auth                                  |
| Graph features missing                        | Neo4j must be running and loaded. Check `docker exec cdss-neo4j cypher-shell -u neo4j -p <pass> "MATCH (n) RETURN count(n);"` |
| Next.js won't start                           | Run `cd web && npm install` again                                                                                             |
| Port already in use                           | Kill existing processes or use different ports                                                                                |

## Architecture Notes

- **Without LLM API key**: Uses extractive drafting from retrieved passages
- **Without Neo4j**: Graph context and interactions won't appear, but core RAG still works
- **MIMIC data required**: For patient cards and diagnosis-based PubMed filtering
- **All data stays local**: No external calls except optional LLM API and PrimeKG/NICE downloads
