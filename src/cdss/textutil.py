"""Small text helpers shared by ingest, retrieval, and the guardrail."""

from __future__ import annotations

import re

_SENTENCE = re.compile(r"(?<=[.!?])\s+")
_NON_NAME = re.compile(r"[^a-z0-9+/\-\s]")
_PAREN = re.compile(r"\([^)]*\)")
_SPACE = re.compile(r"\s+")


def norm_name(value: str) -> str:
    text = value.lower()
    text = _PAREN.sub(" ", text)
    text = _NON_NAME.sub(" ", text)
    return _SPACE.sub(" ", text).strip()


def split_sentences(text: str) -> list[str]:
    parts = [part.strip() for part in _SENTENCE.split(text or "") if part.strip()]
    return parts or ([text.strip()] if text and text.strip() else [])


def chunk_content(content: str, max_chars: int = 1800, overlap: int = 200) -> list[str]:
    text = (content or "").strip()
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return chunks


def citation_token(passage_id: str, source: str, pmid: str | None) -> str:
    if source == "pubmed" and pmid:
        return f"PMID:{pmid}"
    if source == "nice":
        return f"NICE:{passage_id.split('#')[0]}"
    return passage_id


def parse_citation_ids(text: str) -> list[str]:
    found = re.findall(r"\[(PMID:\d+|NICE:[A-Za-z0-9.]+)\]", text)
    extra = re.findall(r"\b(PMID:\d+|NICE:[A-Za-z0-9.]+)\b", text)
    seen: list[str] = []
    for item in found + extra:
        if item not in seen:
            seen.append(item)
    return seen
