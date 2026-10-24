"""Split a draft into claims and keep unsupported ones visible."""

from __future__ import annotations

import json
import re

from cdss.config import FLAG
from cdss.schemas import Claim, Passage
from cdss.textutil import citation_token, parse_citation_ids, split_sentences


def _llm_claims(draft: str, base_url: str, api_key: str, model: str) -> list[dict] | None:
    if not api_key:
        return None
    from openai import OpenAI

    client = OpenAI(base_url=base_url, api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "Split the draft into individual clinical claims. "
                    'Return JSON {"claims": [{"text": "...", "citation_ids": ["PMID:1"]}]}. '
                    "Do not add claims that are not in the draft."
                ),
            },
            {"role": "user", "content": draft},
        ],
    )
    raw = response.choices[0].message.content or ""
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return None
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    claims = payload.get("claims")
    return claims if isinstance(claims, list) else None


_LEADING_CITE = re.compile(r"^(?:\[(?:PMID:\d+|NICE:[A-Za-z0-9.]+)\]\s*)+")
_CITE_TOKEN = re.compile(r"\[(?:PMID:\d+|NICE:[A-Za-z0-9.]+)\]|\b(?:PMID:\d+|NICE:[A-Za-z0-9.]+)\b")


def _claim_body(text: str) -> str:
    body = _CITE_TOKEN.sub(" ", text)
    return re.sub(r"\s+", " ", body).strip(" .")


def split_claims(draft: str, base_url: str, api_key: str, model: str) -> list[tuple[str, list[str]]]:
    parsed = _llm_claims(draft, base_url, api_key, model)
    rows: list[tuple[str, list[str]]] = []
    if parsed:
        for item in parsed:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or "").strip()
            if not text:
                continue
            cites = [str(cite) for cite in item.get("citation_ids") or []]
            cites = cites or parse_citation_ids(text)
            rows.append((text, cites))
    if not rows:
        rows = [(sentence, parse_citation_ids(sentence)) for sentence in split_sentences(draft)]
    fixed: list[tuple[str, list[str]]] = []
    for text, cites in rows:
        leading = parse_citation_ids(_LEADING_CITE.match(text).group(0)) if _LEADING_CITE.match(text) else []
        if leading and fixed and not fixed[-1][1]:
            previous, previous_cites = fixed[-1]
            fixed[-1] = (previous, previous_cites + leading)
            text = _LEADING_CITE.sub("", text).strip()
            cites = [cite for cite in cites if cite not in leading]
        if not _claim_body(text):
            continue
        fixed.append((text, cites))
    return fixed


def verify_claims(rows: list[tuple[str, list[str]]], passages: list[Passage], nli) -> list[Claim]:
    by_token = {}
    for passage in passages:
        token = citation_token(passage.id, passage.source, passage.pmid)
        by_token[token] = passage
        by_token[passage.id] = passage
    claims: list[Claim] = []
    for text, cites in rows:
        entailed: list[str] = []
        body = _claim_body(text)
        targets = [by_token[cite] for cite in cites if cite in by_token] or passages
        for passage in targets:
            token = citation_token(passage.id, passage.source, passage.pmid)
            premise = re.sub(r"\s+", " ", f"{passage.title} {passage.content}")
            if len(body) > 20 and body.lower() in premise.lower():
                entailed.append(token)
                continue
            try:
                label = nli.label(f"{passage.title}. {passage.content}", body or text)
            except Exception:
                label = "neutral"
            if label == "entailment":
                entailed.append(token)
        if entailed:
            claims.append(Claim(text=text, citation_ids=list(dict.fromkeys(entailed)), support="supported"))
        else:
            claims.append(
                Claim(
                    text=text,
                    citation_ids=cites,
                    support="unsupported",
                    flag=FLAG,
                )
            )
    return claims


def recommendation_from_claims(claims: list[Claim]) -> str:
    lines = []
    for claim in claims:
        line = claim.text
        if claim.citation_ids and not any(cite in line for cite in claim.citation_ids):
            line = f"{line} [{', '.join(claim.citation_ids)}]"
        if claim.flag:
            line = f"{line} — {claim.flag}"
        lines.append(line)
    return "\n".join(lines)
