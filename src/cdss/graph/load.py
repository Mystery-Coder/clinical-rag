"""Filter PrimeKG down to the symptom, disease, drug, and contraindication slice."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from urllib.request import urlretrieve

from cdss.textutil import norm_name

NODES_URL = "https://dataverse.harvard.edu/api/access/datafile/6180617"
EDGES_URL = "https://dataverse.harvard.edu/api/access/datafile/6180616"

_NODE_LABEL = {
    "disease": "Disease",
    "drug": "Drug",
    "phenotype": "Phenotype",
    "effect/phenotype": "Phenotype",
    "effect": "Phenotype",
}

_EDGE_TYPE = {
    "indication": "INDICATION",
    "contraindication": "CONTRAINDICATION",
    "disease_phenotype_positive": "HAS_SYMPTOM",
    "phenotype present": "HAS_SYMPTOM",
    "drug_drug": "DRUG_DRUG",
    "drug-drug": "DRUG_DRUG",
    "drug drug": "DRUG_DRUG",
}

DRUG_DRUG_CAP = 200_000


def _download(url: str, dest: Path) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    urlretrieve(url, dest)


def ensure_source_files(primekg_dir: Path) -> tuple[Path, Path]:
    nodes = primekg_dir / "nodes.tab"
    edges = primekg_dir / "edges.csv"
    _download(NODES_URL, nodes)
    _download(EDGES_URL, edges)
    return nodes, edges


def _edge_type(relation: str, display: str) -> str | None:
    for raw in (display, relation):
        key = (raw or "").strip().lower().replace("_", " ")
        key_us = key.replace(" ", "_")
        if key in _EDGE_TYPE:
            return _EDGE_TYPE[key]
        if key_us in _EDGE_TYPE:
            return _EDGE_TYPE[key_us]
        if key.replace("-", " ") in _EDGE_TYPE:
            return _EDGE_TYPE[key.replace("-", " ")]
    return None


def filter_primekg(nodes_path: Path, edges_path: Path, dest: Path) -> dict:
    nodes: dict[str, dict] = {}
    with nodes_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            label = _NODE_LABEL.get((row.get("node_type") or "").strip().lower())
            if label is None:
                continue
            index = row["node_index"].strip()
            name = (row.get("node_name") or "").strip()
            nodes[index] = {
                "node_index": index,
                "label": label,
                "name": name,
                "name_norm": norm_name(name),
                "source_db": (row.get("node_source") or "").strip(),
            }

    clinical: list[dict] = []
    clinical_drugs: set[str] = set()
    with edges_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            kind = _edge_type(row.get("relation", ""), row.get("display_relation", ""))
            if kind is None or kind == "DRUG_DRUG":
                continue
            src = str(row.get("x_index") or row.get(":START_ID") or "").strip()
            dst = str(row.get("y_index") or row.get(":END_ID") or "").strip()
            if src not in nodes or dst not in nodes:
                continue
            src_node, dst_node = nodes[src], nodes[dst]
            if kind == "HAS_SYMPTOM":
                if src_node["label"] == "Phenotype" and dst_node["label"] == "Disease":
                    src, dst = dst, src
                elif not (src_node["label"] == "Disease" and dst_node["label"] == "Phenotype"):
                    continue
            elif kind in {"INDICATION", "CONTRAINDICATION"}:
                if src_node["label"] == "Disease" and dst_node["label"] == "Drug":
                    src, dst = dst, src
                    src_node, dst_node = nodes[src], nodes[dst]
                elif not (src_node["label"] == "Drug" and dst_node["label"] == "Disease"):
                    continue
            display = (row.get("display_relation") or row.get("relation") or kind).strip()
            clinical.append({"src": src, "dst": dst, "type": kind, "display_relation": display})
            if kind in {"INDICATION", "CONTRAINDICATION"} and nodes[src]["label"] == "Drug":
                clinical_drugs.add(src)

    drug_drug: list[dict] = []
    seen_pairs: set[tuple[str, str]] = set()
    with edges_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            kind = _edge_type(row.get("relation", ""), row.get("display_relation", ""))
            if kind != "DRUG_DRUG":
                continue
            src = str(row.get("x_index") or "").strip()
            dst = str(row.get("y_index") or "").strip()
            if src not in clinical_drugs or dst not in clinical_drugs or src == dst:
                continue
            if nodes.get(src, {}).get("label") != "Drug" or nodes.get(dst, {}).get("label") != "Drug":
                continue
            pair = (src, dst) if src < dst else (dst, src)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            display = (row.get("display_relation") or "drug_drug").strip()
            drug_drug.append({"src": pair[0], "dst": pair[1], "type": "DRUG_DRUG", "display_relation": display})
            if len(drug_drug) >= DRUG_DRUG_CAP:
                break

    used = {edge["src"] for edge in clinical + drug_drug} | {edge["dst"] for edge in clinical + drug_drug}
    kept_nodes = [node for index, node in nodes.items() if index in used]
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "clinical_nodes.jsonl").write_text(
        "".join(json.dumps(node) + "\n" for node in kept_nodes), encoding="utf-8"
    )
    (dest / "clinical_edges.jsonl").write_text(
        "".join(json.dumps(edge) + "\n" for edge in clinical + drug_drug), encoding="utf-8"
    )
    names = {
        "Disease": sorted({node["name_norm"] for node in kept_nodes if node["label"] == "Disease" and node["name_norm"]}),
        "Drug": sorted({node["name_norm"] for node in kept_nodes if node["label"] == "Drug" and node["name_norm"]}),
    }
    (dest / "names.json").write_text(json.dumps(names), encoding="utf-8")
    summary = {
        "nodes": len(kept_nodes),
        "clinical_edges": len(clinical),
        "drug_drug_edges": len(drug_drug),
        "drug_drug_capped": len(drug_drug) >= DRUG_DRUG_CAP,
    }
    (dest / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def load_into_neo4j(clinical_dir: Path, uri: str, user: str, password: str) -> None:
    from neo4j import GraphDatabase

    nodes = [json.loads(line) for line in (clinical_dir / "clinical_nodes.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    edges = [json.loads(line) for line in (clinical_dir / "clinical_edges.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session() as session:
            for label in ("Disease", "Drug", "Phenotype"):
                session.run(f"CREATE CONSTRAINT {label.lower()}_index IF NOT EXISTS FOR (n:{label}) REQUIRE n.node_index IS UNIQUE")
                batch = [node for node in nodes if node["label"] == label]
                for start in range(0, len(batch), 1000):
                    session.run(
                        f"""
                        UNWIND $rows AS row
                        MERGE (n:{label} {{node_index: row.node_index}})
                        SET n.name = row.name, n.name_norm = row.name_norm, n.source_db = row.source_db
                        """,
                        rows=batch[start : start + 1000],
                    )
            for label in ("Disease", "Drug"):
                session.run(f"CREATE INDEX {label.lower()}_name IF NOT EXISTS FOR (n:{label}) ON (n.name_norm)")
            for edge_type in ("INDICATION", "CONTRAINDICATION", "HAS_SYMPTOM", "DRUG_DRUG"):
                batch = [edge for edge in edges if edge["type"] == edge_type]
                for start in range(0, len(batch), 1000):
                    session.run(
                        f"""
                        UNWIND $rows AS row
                        MATCH (a {{node_index: row.src}})
                        MATCH (b {{node_index: row.dst}})
                        MERGE (a)-[r:{edge_type}]->(b)
                        SET r.display_relation = row.display_relation
                        """,
                        rows=batch[start : start + 1000],
                    )
    finally:
        driver.close()
