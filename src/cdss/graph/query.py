"""Two-hop PrimeKG lookup. Name misses are recorded and not guessed."""

from __future__ import annotations

import json
import re
from pathlib import Path

from cdss.schemas import Interaction
from cdss.textutil import norm_name

_WORD = re.compile(r"[a-z0-9][a-z0-9+/\-]{3,}")
_GENERIC_DISEASES = {
    "injury",
    "disease",
    "syndrome",
    "disorder",
    "failure",
    "infection",
    "cancer",
    "tumor",
    "tumour",
    "fever",
    "shock",
    "pain",
}


def _names(path: Path) -> dict[str, list[str]]:
    file = path / "names.json"
    if not file.exists():
        return {"Disease": [], "Drug": []}
    return json.loads(file.read_text(encoding="utf-8"))


def _covered_by_longer(name: str, longer_names: list[str]) -> bool:
    return any(
        re.search(rf"(?<![a-z0-9]){re.escape(name)}(?![a-z0-9])", longer)
        for longer in longer_names
    )


def match_diseases(titles: list[str], disease_names: list[str], limit: int = 20) -> list[str]:
    ordered = sorted(disease_names, key=len, reverse=True)
    hits: list[str] = []
    for title in titles:
        text = norm_name(title)
        if not text:
            continue
        if text in disease_names and text not in hits and text not in _GENERIC_DISEASES:
            hits.append(text)
        for name in ordered:
            if len(name) < 5 or name in _GENERIC_DISEASES:
                continue
            if re.search(rf"(?<![a-z0-9]){re.escape(name)}(?![a-z0-9])", text) and name not in hits:
                hits.append(name)
            if len(hits) >= limit:
                break
        if len(hits) >= limit:
            break
    kept: list[str] = []
    for name in sorted(hits, key=len, reverse=True):
        if _covered_by_longer(name, kept):
            continue
        kept.append(name)
    return kept[:limit]


def match_drugs(drugs: list[str], drug_names: list[str]) -> tuple[list[str], list[str]]:
    exact = set(drug_names)
    ordered = sorted((name for name in drug_names if len(name) >= 4), key=len, reverse=True)
    matched: list[str] = []
    missed: list[str] = []
    for drug in drugs:
        text = norm_name(drug)
        found = None
        if text in exact:
            found = text
        else:
            for name in ordered:
                if re.search(rf"(?<![a-z0-9]){re.escape(name)}(?![a-z0-9])", text):
                    found = name
                    break
        if found and found not in matched:
            matched.append(found)
        elif found is None:
            missed.append(drug)
    return matched, missed


def query_terms(question: str) -> list[str]:
    return list(dict.fromkeys(_WORD.findall(norm_name(question))))


class GraphClient:
    def __init__(self, uri: str, user: str, password: str, primekg_dir: Path) -> None:
        self.uri = uri
        self.user = user
        self.password = password
        self.primekg_dir = primekg_dir
        self._names = _names(primekg_dir)

    def available(self) -> bool:
        if not self.password:
            return False
        try:
            from neo4j import GraphDatabase

            driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            driver.verify_connectivity()
            driver.close()
            return True
        except Exception:
            return False

    def subgraph(self, disease_terms: list[str], drug_terms: list[str]) -> tuple[list[str], list[Interaction], list[str]]:
        diseases = match_diseases(disease_terms, self._names.get("Disease", []))
        drugs, missed = match_drugs(drug_terms, self._names.get("Drug", []))
        if not diseases and not drugs:
            return [], [], missed
        if not self.available():
            return [], [], missed
        from neo4j import GraphDatabase

        driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        lines: list[str] = []
        interactions: list[Interaction] = []
        try:
            with driver.session() as session:
                rows = session.run(
                    """
                    UNWIND $diseases AS name
                    MATCH (d:Disease {name_norm: name})
                    OPTIONAL MATCH (d)-[:HAS_SYMPTOM]->(ph:Phenotype)
                    OPTIONAL MATCH (drug:Drug)-[rel:INDICATION|CONTRAINDICATION]->(d)
                    RETURN d.name AS disease, ph.name AS symptom, drug.name AS drug,
                           type(rel) AS rel_type, rel.display_relation AS rel_label
                    LIMIT 80
                    """,
                    diseases=diseases,
                )
                for row in rows:
                    if row["symptom"]:
                        lines.append(f"{row['disease']} -[:HAS_SYMPTOM]-> {row['symptom']}")
                    if row["drug"] and row["rel_type"]:
                        label = row["rel_label"] or row["rel_type"]
                        via = f"{row['drug']} -[:{row['rel_type']}]-> {row['disease']}"
                        lines.append(via)
                        if row["rel_type"] == "CONTRAINDICATION":
                            interactions.append(
                                Interaction(
                                    drug_a=row["drug"],
                                    drug_b=row["disease"],
                                    relation=label,
                                    via=via,
                                )
                            )
                if len(drugs) >= 2:
                    pairs = session.run(
                        """
                        UNWIND $drugs AS left
                        UNWIND $drugs AS right
                        WITH left, right WHERE left < right
                        MATCH (a:Drug {name_norm: left})-[rel:DRUG_DRUG]-(b:Drug {name_norm: right})
                        RETURN a.name AS drug_a, b.name AS drug_b, rel.display_relation AS rel_label
                        LIMIT 40
                        """,
                        drugs=drugs,
                    )
                    seen: set[tuple[str, str]] = set()
                    for row in pairs:
                        key = tuple(sorted((row["drug_a"], row["drug_b"])))
                        if key in seen:
                            continue
                        seen.add(key)
                        label = row["rel_label"] or "drug_drug"
                        via = f"{row['drug_a']} -[:DRUG_DRUG]-> {row['drug_b']}"
                        lines.append(via)
                        interactions.append(
                            Interaction(
                                drug_a=row["drug_a"],
                                drug_b=row["drug_b"],
                                relation=label,
                                via=via,
                            )
                        )
        finally:
            driver.close()
        unique_lines = list(dict.fromkeys(lines))
        return unique_lines, interactions, missed
