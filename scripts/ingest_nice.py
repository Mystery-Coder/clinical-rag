"""Pull NICE guidance for the demo diagnosis terms into the passage store."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cdss.config import get_settings
from cdss.ingest.nice import fetch_nice, write_passages
from cdss.ingest.terms import SEED_TERMS


def main() -> None:
    settings = get_settings()
    passages = []
    seen = set()
    for term in SEED_TERMS:
        for passage in fetch_nice(settings.nice_api_base, settings.nice_api_key, term):
            if passage.id in seen:
                continue
            seen.add(passage.id)
            passages.append(passage)
    dest = settings.passages_dir / "nice.jsonl"
    write_passages(passages, dest)
    print(f"Wrote {len(passages)} NICE passages to {dest}")
    print("Rebuild the FAISS index so these passages are searchable.")


if __name__ == "__main__":
    main()
