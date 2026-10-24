"""Stream MedRAG PubMed snippets and keep a diagnosis-matched college slice."""

from __future__ import annotations

import json
from pathlib import Path

from cdss.schemas import Passage
from cdss.textutil import chunk_content


def pubmed_url(pmid: str | None, snippet_id: str) -> str:
    if pmid:
        return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
    return f"https://pubmed.ncbi.nlm.nih.gov/?term={snippet_id}"


def passages_from_row(row: dict, max_chars: int = 1800) -> list[Passage]:
    title = (row.get("title") or "").strip()
    content = (row.get("content") or "").strip()
    snippet_id = str(row.get("id") or row.get("PMID") or "")
    pmid = str(row.get("PMID") or row.get("pmid") or "").strip() or None
    pieces = chunk_content(content, max_chars=max_chars)
    passages: list[Passage] = []
    for index, piece in enumerate(pieces):
        piece_id = snippet_id if len(pieces) == 1 else f"{snippet_id}#{index}"
        passages.append(
            Passage(
                id=piece_id,
                title=title,
                content=piece,
                source="pubmed",
                pmid=pmid,
                url=pubmed_url(pmid, snippet_id),
            )
        )
    return passages


def _matches(row: dict, terms: list[str]) -> bool:
    blob = f"{row.get('title', '')} {row.get('content', '')}".lower()
    return any(term in blob for term in terms)


def _write(passages: list[Passage], dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", encoding="utf-8") as handle:
        for passage in passages:
            handle.write(passage.model_dump_json() + "\n")


def ingest_local_jsonl(paths: list[Path], terms: list[str], dest: Path, cap: int) -> int:
    kept: list[Passage] = []
    for path in sorted(paths, reverse=True):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                if not _matches(row, terms):
                    continue
                kept.extend(passages_from_row(row))
                if len(kept) >= cap:
                    _write(kept[:cap], dest)
                    return cap
    _write(kept, dest)
    return len(kept)


def ingest_huggingface(terms: list[str], dest: Path, cap: int) -> int:
    from huggingface_hub import HfFileSystem

    fs = HfFileSystem()
    paths = sorted(fs.glob("datasets/MedRAG/pubmed/chunk/*.jsonl"), reverse=True)
    if not paths:
        raise FileNotFoundError("No JSONL files under datasets/MedRAG/pubmed/chunk")
    kept: list[Passage] = []
    for path in paths:
        with fs.open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                if not _matches(row, terms):
                    continue
                kept.extend(passages_from_row(row))
                if len(kept) >= cap:
                    _write(kept[:cap], dest)
                    return cap
    _write(kept, dest)
    return len(kept)
