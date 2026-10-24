"""Grounded draft. Uses an OpenAI-compatible chat model when a key is set."""

from __future__ import annotations

from cdss.schemas import Passage
from cdss.textutil import citation_token, split_sentences


def _context(passages: list[Passage], graph_lines: list[str], patient_lines: list[str]) -> str:
    blocks = []
    if patient_lines:
        blocks.append("Patient chart (context only, not a citation source):\n" + "\n".join(patient_lines))
    passage_lines = []
    for passage in passages:
        token = citation_token(passage.id, passage.source, passage.pmid)
        passage_lines.append(f"[{token}] {passage.title}\n{passage.content}")
    blocks.append("Passages:\n" + "\n\n".join(passage_lines))
    if graph_lines:
        blocks.append("Graph rows:\n" + "\n".join(graph_lines))
    return "\n\n".join(blocks)


def extractive_draft(passages: list[Passage]) -> str:
    lines = []
    for passage in passages[:5]:
        sentence = split_sentences(passage.content)[0].rstrip()
        if sentence.endswith("."):
            sentence = sentence[:-1].rstrip()
        token = citation_token(passage.id, passage.source, passage.pmid)
        lines.append(f"{sentence} [{token}].")
    return " ".join(lines)


def draft_answer(
    question: str,
    passages: list[Passage],
    graph_lines: list[str],
    patient_lines: list[str],
    base_url: str,
    api_key: str,
    model: str,
) -> str:
    if not passages:
        return "No retrieved passages were available for this question."
    if not api_key:
        return extractive_draft(passages)
    from openai import OpenAI

    client = OpenAI(base_url=base_url, api_key=api_key)
    prompt = (
        "You draft clinical decision support. Use only the passages and graph rows. "
        "Do not add medical facts from memory. Write 4 to 8 short claims. "
        "End every claim with a citation token copied from the context, such as [PMID:123456] or [NICE:NG28]. "
        "Patient chart facts may be acknowledged, and they are not citations.\n\n"
        f"{_context(passages, graph_lines, patient_lines)}\n\nQuestion:\n{question}"
    )
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": "You only state what the supplied context supports."},
            {"role": "user", "content": prompt},
        ],
    )
    return (response.choices[0].message.content or "").strip()
