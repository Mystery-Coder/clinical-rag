"""Ingest a diagnosis-matched PubMed slice of about 5,000 snippets."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cdss.config import get_settings
from cdss.ingest.pubmed import ingest_huggingface, ingest_local_jsonl
from cdss.ingest.terms import diagnosis_terms


def main() -> None:
    settings = get_settings()
    terms = diagnosis_terms(settings.mimic_dir)
    print(f"Keeping snippets that mention {len(terms)} diagnosis terms.")
    local = sorted((settings.data_dir / "pubmed" / "chunk").glob("*.jsonl"))
    dest = settings.passages_dir / "pubmed.jsonl"
    if local:
        count = ingest_local_jsonl(local, terms, dest, settings.passage_cap)
    else:
        print("Streaming MedRAG/pubmed from Hugging Face. The full corpus is not saved.")
        count = ingest_huggingface(terms, dest, settings.passage_cap)
    print(f"Wrote {count} passages to {dest}")


if __name__ == "__main__":
    main()
