"""Embed passage JSONL files with MedCPT and write a FAISS index."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cdss.config import get_settings
from cdss.index.embed import MedCPT
from cdss.index.store import build_index, load_passages


def main() -> None:
    settings = get_settings()
    passages = load_passages(settings.passages_dir)
    print(f"Embedding {len(passages)} passages.")
    encoder = MedCPT()
    pairs = [[passage.title, passage.content] for passage in passages]
    vectors = encoder.encode_articles(pairs)
    build_index(passages, vectors, settings.index_dir)
    print(f"Index written to {settings.index_dir}")


if __name__ == "__main__":
    main()
