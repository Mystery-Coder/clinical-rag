#!/usr/bin/env bash
# One consult with the pieces that exist today.
# Builds the PubMed index the first time. Does not load Neo4j.
set -euo pipefail
cd "$(dirname "$0")"

if [[ -f .venv/Scripts/activate ]]; then
  # Git Bash on Windows
  source .venv/Scripts/activate
elif [[ -f .venv/bin/activate ]]; then
  source .venv/bin/activate
else
  echo "No .venv. Run: python -m venv .venv && pip install -r requirements.txt"
  exit 1
fi

if [[ ! -f data/passages/pubmed.jsonl ]]; then
  echo "Streaming PubMed abstracts into data/passages/pubmed.jsonl (PASSAGE_CAP)"
  python scripts/ingest_pubmed.py
fi

if [[ ! -f data/index/passages.faiss ]]; then
  echo "Embedding passages with MedCPT and writing data/index/passages.faiss"
  python scripts/build_index.py
fi

if [[ $# -eq 0 ]]; then
  set -- "treatment considerations in sepsis with kidney injury"
fi

python scripts/ask.py "$@"
