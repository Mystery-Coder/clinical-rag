"""FAISS inner-product index plus a metadata JSONL aligned by row id."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from cdss.schemas import Passage


class FaissStore:
    def __init__(self, index_dir: Path) -> None:
        import faiss

        index_path = index_dir / "passages.faiss"
        meta_path = index_dir / "meta.jsonl"
        if not index_path.exists() or not meta_path.exists():
            raise FileNotFoundError(
                f"No index in {index_dir}. Run scripts/build_index.py after ingestion."
            )
        self.index = faiss.read_index(str(index_path))
        self.meta = [json.loads(line) for line in meta_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def search(self, vector: np.ndarray, k: int) -> list[tuple[Passage, float]]:
        if self.index.ntotal == 0:
            return []
        query = np.asarray(vector, dtype="float32")
        if query.ndim == 1:
            query = query.reshape(1, -1)
        scores, ids = self.index.search(query, min(k, self.index.ntotal))
        hits: list[tuple[Passage, float]] = []
        for score, row_id in zip(scores[0], ids[0]):
            if row_id < 0:
                continue
            hits.append((Passage.model_validate(self.meta[int(row_id)]), float(score)))
        return hits


def build_index(passages: list[Passage], vectors: np.ndarray, index_dir: Path) -> None:
    import faiss

    if len(passages) != len(vectors):
        raise ValueError("Passage count and vector count differ")
    index_dir.mkdir(parents=True, exist_ok=True)
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(np.asarray(vectors, dtype="float32"))
    faiss.write_index(index, str(index_dir / "passages.faiss"))
    with (index_dir / "meta.jsonl").open("w", encoding="utf-8") as handle:
        for passage in passages:
            handle.write(passage.model_dump_json() + "\n")


def load_passages(passages_dir: Path) -> list[Passage]:
    passages: list[Passage] = []
    files = sorted(passages_dir.glob("*.jsonl"))
    if not files:
        raise FileNotFoundError(f"No passage files in {passages_dir}")
    for path in files:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                passages.append(Passage.model_validate_json(line))
    return passages
