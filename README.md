# Clinical decision support

College-scale RAG CDSS. PubMed supplies cited passages. PrimeKG supplies the symptom, disease, and drug graph. The MIMIC-IV demo supplies a 100-patient chart. Unsupported claims stay in the answer with a visible flag.

## Setup

```bash
python -m venv .venv
source .venv/Scripts/activate  # Git Bash on Windows
pip install -r requirements.txt
cp .env.example .env
```

Put the MIMIC-IV demo 2.2 hosp tables under `data/mimic-iv-demo/`. The reader finds `patients.csv` or `patients.csv.gz` in any subfolder.

## Run order

```bash
# 1) Start the FastAPI backend
uvicorn cdss.api:app --app-dir src --reload

# 2) Start the Next.js frontend (in a separate terminal)
cd web
npm install
npm run dev
```

Open the clinician UI at `http://127.0.0.1:3000`. The original static page remains available at `http://127.0.0.1:8000` when using uvicorn.

```bash
python scripts/ingest_pubmed.py
python scripts/build_index.py
python scripts/ask.py "treatment considerations in sepsis with kidney injury"
python scripts/load_graph.py
python scripts/ingest_nice.py
python scripts/ingest_statpearls.py
python scripts/ask.py --subject-id 10000032
python scripts/eval_pubmedqa.py
```

`ingest_pubmed.py` keeps about 5,000 abstracts that mention the demo diagnoses. It streams MedRAG PubMed and does not download the 23.9 million snippet corpus.

`load_graph.py` downloads PrimeKG nodes and edges, writes the clinical slice, and loads Neo4j when `NEO4J_PASSWORD` is set.

`ingest_nice.py` needs `NICE_API_KEY`. `ingest_statpearls.py` reads `data/statpearls/chunk/*.jsonl` or `data/statpearls/raw/*.txt`. Rebuild the index after either one.

Without `LLM_API_KEY`, the draft quotes retrieved sentences and still runs the NLI check. With a key, an OpenAI-compatible chat model writes the draft and splits the claims.
