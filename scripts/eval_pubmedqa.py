"""Score a 50-row RAGBench PubMedQA sample for retrieval overlap and support agreement."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cdss.config import get_settings
from cdss.guardrail.nli import NLI
from cdss.index.embed import MedCPT
from cdss.index.store import FaissStore

_TOKEN = re.compile(r"[a-z0-9]+")
_SAMPLE = 50


def _tokens(text: str) -> set[str]:
    return set(_TOKEN.findall((text or "").lower()))


def _jaccard(left: str, right: str) -> float:
    a, b = _tokens(left), _tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _sentence(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(_sentence(part) for part in value)
    return str(value)


def main() -> None:
    from datasets import load_dataset

    settings = get_settings()
    dataset = load_dataset("galileo-ai/ragbench", "pubmedqa", split="test")
    rows = list(dataset.select(range(min(_SAMPLE, len(dataset)))))
    nli = NLI()
    store = None
    encoder = None
    index_note = None
    try:
        store = FaissStore(settings.index_dir)
        encoder = MedCPT()
    except FileNotFoundError as exc:
        index_note = str(exc)

    retrieval_hits = []
    agreements = []
    entailment_hits = 0
    entailment_total = 0
    for row in rows:
        documents = row["documents"] or []
        if store is not None and encoder is not None:
            hits = store.search(encoder.encode_query(row["question"]), settings.top_k)
            retrieved = [passage.content for passage, _score in hits]
            matched = 0
            for document in documents:
                if any(_jaccard(document, passage) >= 0.15 for passage in retrieved):
                    matched += 1
            retrieval_hits.append(matched / len(documents) if documents else 0.0)

        premise = "\n".join(documents)[:4000]
        sentences = [_sentence(item) for item in (row["response_sentences"] or [])]
        support_rows = row["sentence_support_information"] or []
        for sentence, info in zip(sentences, support_rows):
            if not sentence.strip():
                continue
            predicted = nli.label(premise, sentence) == "entailment"
            expected = bool(info.get("fully_supported"))
            agreements.append(predicted == expected)
            entailment_total += 1
            entailment_hits += int(predicted)

    metrics = {
        "sample_size": len(rows),
        "retrieval_overlap": None if not retrieval_hits else sum(retrieval_hits) / len(retrieval_hits),
        "nli_entailment_rate": None if not entailment_total else entailment_hits / entailment_total,
        "support_label_agreement": None if not agreements else sum(agreements) / len(agreements),
        "index_note": index_note,
    }
    settings.eval_dir.mkdir(parents=True, exist_ok=True)
    dest = settings.eval_dir / "pubmedqa_metrics.json"
    dest.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
