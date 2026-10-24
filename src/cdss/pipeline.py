"""End-to-end consult: chart, retrieval, draft, NLI flags, interaction note."""

from __future__ import annotations

from cdss.config import FLAG, Settings, get_settings
from cdss.generate.llm import draft_answer
from cdss.graph.query import GraphClient, query_terms
from cdss.guardrail.claims import recommendation_from_claims, split_claims, verify_claims
from cdss.guardrail.nli import NLI
from cdss.index.store import FaissStore
from cdss.patient.mimic import build_card
from cdss.schemas import Claim, ConsultResponse, Passage, PatientCard, Source
from cdss.textutil import citation_token


class MissingIndex(FileNotFoundError):
    pass


class MissingPatient(KeyError):
    pass


def _patient_lines(card: PatientCard) -> list[str]:
    return [
        f"Age {card.age}, sex {card.sex}, admission {card.admission_type}, hadm_id {card.hadm_id}.",
        "Diagnoses: " + "; ".join(card.diagnoses),
        "Prescribed drugs: " + "; ".join(card.drugs),
        "Abnormal labs: " + "; ".join(card.abnormal_labs),
    ]


def _sources(passages: list[Passage]) -> list[Source]:
    sources: list[Source] = []
    seen: set[str] = set()
    for passage in passages:
        token = citation_token(passage.id, passage.source, passage.pmid)
        if token in seen:
            continue
        seen.add(token)
        sources.append(Source(id=token, title=passage.title, url=passage.url))
    return sources


def consult(
    question: str | None = None,
    subject_id: str | None = None,
    k: int | None = None,
    settings: Settings | None = None,
) -> ConsultResponse:
    settings = settings or get_settings()
    if not question and not subject_id:
        raise ValueError("Provide a question or a MIMIC demo subject_id.")

    patient: PatientCard | None = None
    if subject_id:
        try:
            patient = build_card(settings.mimic_dir, subject_id.strip())
        except KeyError as exc:
            raise MissingPatient(str(exc)) from exc
        except FileNotFoundError as exc:
            raise MissingPatient(str(exc)) from exc

    query = (question or "").strip()
    if patient and patient.diagnoses:
        diagnosis_query = "; ".join(patient.diagnoses[:12])
        query = f"{query} {diagnosis_query}".strip() if query else diagnosis_query
    if not query:
        raise ValueError("The patient card has no diagnoses and no question was given.")

    try:
        store = FaissStore(settings.index_dir)
    except FileNotFoundError as exc:
        raise MissingIndex(str(exc)) from exc

    from cdss.index.embed import MedCPT

    encoder = MedCPT()
    hits = store.search(encoder.encode_query(query), k or settings.top_k)
    passages = [passage for passage, _score in hits]

    disease_terms = list(patient.diagnoses) if patient else [query, *query_terms(query)]
    drug_terms = list(patient.drugs) if patient else []
    graph = GraphClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password, settings.primekg_dir)
    graph_lines, interactions, missed = graph.subgraph(disease_terms, drug_terms)
    if patient is not None:
        patient = patient.model_copy(update={"unmatched_drugs": missed})

    draft = draft_answer(
        query,
        passages,
        graph_lines,
        _patient_lines(patient) if patient else [],
        settings.llm_base_url,
        settings.llm_api_key,
        settings.llm_model,
    )
    rows = split_claims(draft, settings.llm_base_url, settings.llm_api_key, settings.llm_model)
    try:
        claims = verify_claims(rows, passages, NLI())
    except Exception:
        claims = [
            Claim(text=text, citation_ids=cites, support="unsupported", flag=FLAG)
            for text, cites in rows
        ]

    return ConsultResponse(
        recommendation=recommendation_from_claims(claims),
        claims=claims,
        interactions=interactions,
        sources=_sources(passages),
        patient=patient,
        graph_context=graph_lines,
    )
