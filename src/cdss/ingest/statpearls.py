"""StatPearls passages from local JSONL chunks or plain-text articles."""

from __future__ import annotations

import json
from pathlib import Path

from cdss.schemas import Passage
from cdss.textutil import chunk_content


def _from_json_row(row: dict) -> list[Passage]:
    title = (row.get("title") or "StatPearls").strip()
    content = (row.get("content") or "").strip()
    snippet_id = str(row.get("id") or title)
    passages: list[Passage] = []
    for index, piece in enumerate(chunk_content(content)):
        piece_id = snippet_id if index == 0 else f"{snippet_id}#{index}"
        passages.append(
            Passage(
                id=piece_id,
                title=title,
                content=piece,
                source="statpearls",
                url="https://www.ncbi.nlm.nih.gov/books/NBK430685/",
            )
        )
    return passages


def ingest_statpearls(source_dir: Path, dest: Path, cap: int = 2000) -> int:
    """Read data/statpearls/chunk/*.jsonl and data/statpearls/raw/*.txt."""
    if not source_dir.exists():
        raise FileNotFoundError(
            f"No StatPearls files in {source_dir}. "
            "Add MedRAG-style JSONL under chunk/ or article text under raw/."
        )
    kept: list[Passage] = []
    for path in sorted(source_dir.rglob("*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                kept.extend(_from_json_row(json.loads(line)))
                if len(kept) >= cap:
                    break
        if len(kept) >= cap:
            break
    if len(kept) < cap:
        for path in sorted(source_dir.rglob("*.txt")):
            text = path.read_text(encoding="utf-8")
            kept.extend(
                _from_json_row({"id": path.stem, "title": path.stem.replace("_", " "), "content": text})
            )
            if len(kept) >= cap:
                break
    kept = kept[:cap]
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", encoding="utf-8") as handle:
        for passage in kept:
            handle.write(passage.model_dump_json() + "\n")
    return len(kept)
