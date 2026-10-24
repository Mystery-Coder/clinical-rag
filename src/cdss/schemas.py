"""Shared records for passages, the chart, and the clinician response."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from cdss.config import NOTICE


class Passage(BaseModel):
    id: str
    title: str
    content: str
    source: Literal["pubmed", "nice", "statpearls"]
    pmid: str | None = None
    url: str


class PatientCard(BaseModel):
    subject_id: str
    hadm_id: str
    age: int | None = None
    sex: str | None = None
    admission_type: str | None = None
    diagnoses: list[str] = Field(default_factory=list)
    drugs: list[str] = Field(default_factory=list)
    abnormal_labs: list[str] = Field(default_factory=list)
    unmatched_drugs: list[str] = Field(default_factory=list)


class PatientSummary(BaseModel):
    subject_id: str
    hadm_id: str
    age: int | None = None
    sex: str | None = None
    admission_type: str | None = None
    diagnoses: list[str] = Field(default_factory=list)


class Claim(BaseModel):
    text: str
    citation_ids: list[str] = Field(default_factory=list)
    support: Literal["supported", "unsupported"]
    flag: str | None = None


class Interaction(BaseModel):
    drug_a: str
    drug_b: str
    relation: str
    via: str


class Source(BaseModel):
    id: str
    title: str
    url: str


class ConsultResponse(BaseModel):
    notice: str = NOTICE
    recommendation: str
    claims: list[Claim]
    interactions: list[Interaction]
    sources: list[Source]
    patient: PatientCard | None = None
    graph_context: list[str] = Field(default_factory=list)


class ConsultRequest(BaseModel):
    question: str | None = None
    subject_id: str | None = None
    k: int = 5
