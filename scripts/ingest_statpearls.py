"""Add local StatPearls text to the passage store."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cdss.config import get_settings
from cdss.ingest.statpearls import ingest_statpearls


def main() -> None:
    settings = get_settings()
    count = ingest_statpearls(settings.data_dir / "statpearls", settings.passages_dir / "statpearls.jsonl")
    print(f"Wrote {count} StatPearls passages.")
    print("Rebuild the FAISS index so these passages are searchable.")


if __name__ == "__main__":
    main()
