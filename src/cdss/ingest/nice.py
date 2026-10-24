"""NICE guidance passages. The dense index still runs if this key is absent."""

from __future__ import annotations

import json
from pathlib import Path

import httpx

from cdss.schemas import Passage
from cdss.textutil import chunk_content

_ACCEPT = "application/vnd.nice.syndication.services+json"


def _texts(node, found: list[tuple[str, str, str]]) -> None:
    if isinstance(node, dict):
        title = str(node.get("Title") or node.get("title") or "").strip()
        nice_id = str(
            node.get("GuidanceNumber")
            or node.get("NiceGuidanceNumber")
            or node.get("Id")
            or node.get("id")
            or ""
        ).strip()
        content = node.get("Content") or node.get("content") or node.get("Summary") or ""
        if isinstance(content, str) and title and len(content.strip()) > 80:
            found.append((nice_id or title, title, content.strip()))
        for value in node.values():
            _texts(value, found)
    elif isinstance(node, list):
        for item in node:
            _texts(item, found)


def fetch_nice(api_base: str, api_key: str, keyword: str) -> list[Passage]:
    if not api_key:
        raise RuntimeError("NICE_API_KEY is empty. PubMed retrieval still works without NICE.")
    headers = {"API-Key": api_key, "Accept": _ACCEPT}
    url = api_base.rstrip("/") + "/guidance-by-date"
    response = httpx.get(url, headers=headers, params={"keyword": keyword}, timeout=60.0)
    response.raise_for_status()
    payload = response.json()
    found: list[tuple[str, str, str]] = []
    _texts(payload, found)
    passages: list[Passage] = []
    seen: set[str] = set()
    for nice_id, title, content in found:
        for index, piece in enumerate(chunk_content(content)):
            piece_id = nice_id if index == 0 else f"{nice_id}#{index}"
            if piece_id in seen:
                continue
            seen.add(piece_id)
            passages.append(
                Passage(
                    id=piece_id,
                    title=title,
                    content=piece,
                    source="nice",
                    url=f"https://www.nice.org.uk/guidance/{nice_id}",
                )
            )
    return passages


def write_passages(passages: list[Passage], dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", encoding="utf-8") as handle:
        for passage in passages:
            handle.write(json.dumps(passage.model_dump()) + "\n")
