"""Diagnosis phrases used to keep a college-sized PubMed slice."""

from __future__ import annotations

from pathlib import Path

from cdss.patient.mimic import diagnosis_titles, mimic_available

SEED_TERMS = (
    "sepsis",
    "heart failure",
    "diabetes",
    "pneumonia",
    "kidney injury",
    "acute kidney",
    "atrial fibrillation",
    "hypertension",
    "copd",
    "myocardial infarction",
    "respiratory failure",
    "pulmonary embolism",
    "stroke",
    "cirrhosis",
    "anemia",
    "gastrointestinal",
)

_SKIP = {
    "unspecified",
    "other",
    "without",
    "not",
    "elsewhere",
    "classified",
    "personal",
    "history",
}


def _heads(titles: list[str]) -> list[str]:
    heads: list[str] = []
    for title in titles:
        head = title.split(",")[0].strip().lower()
        words = head.split()
        if len(head) < 6 or len(head) > 48:
            continue
        if words and words[0] in _SKIP:
            continue
        if head not in heads:
            heads.append(head)
        if len(heads) >= 40:
            break
    return heads


def diagnosis_terms(mimic_dir: Path) -> list[str]:
    """Seed terms, narrowed to phrases that actually appear in the demo when it is present."""
    if not mimic_available(mimic_dir):
        return list(SEED_TERMS)
    titles = [title.lower() for title in diagnosis_titles(mimic_dir)]
    blob = "\n".join(titles)
    terms = [term for term in SEED_TERMS if term in blob]
    for head in _heads(titles):
        if head not in terms:
            terms.append(head)
    return terms or list(SEED_TERMS)
