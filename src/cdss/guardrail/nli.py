"""Local MNLI check. Entailment is supported. Neutral and contradiction are flagged."""

from __future__ import annotations

_MODEL = "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli"


class NLI:
    def __init__(self) -> None:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self.torch = torch
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = AutoTokenizer.from_pretrained(_MODEL)
        self.model = AutoModelForSequenceClassification.from_pretrained(_MODEL).to(self.device).eval()
        self.labels = {int(key): value.lower() for key, value in self.model.config.id2label.items()}

    def label(self, premise: str, hypothesis: str) -> str:
        encoded = self.tokenizer(
            premise,
            hypothesis,
            truncation="only_first",
            max_length=512,
            return_tensors="pt",
        )
        encoded = {key: value.to(self.device) for key, value in encoded.items()}
        with self.torch.no_grad():
            pred = int(self.model(**encoded).logits.argmax(dim=-1).item())
        return self.labels.get(pred, "neutral")
