"""MedCPT encoders. Article encoder for indexing, query encoder at question time."""

from __future__ import annotations

import numpy as np

_ARTICLE = "ncbi/MedCPT-Article-Encoder"
_QUERY = "ncbi/MedCPT-Query-Encoder"


class MedCPT:
    def __init__(self) -> None:
        import torch
        from transformers import AutoModel, AutoTokenizer

        self.torch = torch
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.article_tokenizer = AutoTokenizer.from_pretrained(_ARTICLE)
        self.article_model = AutoModel.from_pretrained(_ARTICLE).to(self.device).eval()
        self.query_tokenizer = AutoTokenizer.from_pretrained(_QUERY)
        self.query_model = AutoModel.from_pretrained(_QUERY).to(self.device).eval()

    def _cls(self, model, tokenizer, batch, max_length: int) -> np.ndarray:
        encoded = tokenizer(
            batch,
            truncation=True,
            padding=True,
            return_tensors="pt",
            max_length=max_length,
        )
        encoded = {key: value.to(self.device) for key, value in encoded.items()}
        with self.torch.no_grad():
            hidden = model(**encoded).last_hidden_state[:, 0, :]
        return hidden.detach().cpu().numpy().astype("float32")

    def encode_articles(self, pairs: list[list[str]], batch_size: int = 8) -> np.ndarray:
        if not pairs:
            return np.zeros((0, 768), dtype="float32")
        parts: list[np.ndarray] = []
        for start in range(0, len(pairs), batch_size):
            parts.append(self._cls(self.article_model, self.article_tokenizer, pairs[start : start + batch_size], 512))
        return np.vstack(parts)

    def encode_query(self, text: str) -> np.ndarray:
        return self._cls(self.query_model, self.query_tokenizer, [text], 64)
