"""Local consult API and the single clinician page."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from cdss.config import get_settings
from cdss.patient.mimic import list_patients
from cdss.pipeline import MissingIndex, MissingPatient, consult
from cdss.schemas import ConsultRequest

app = FastAPI(title="Clinical decision support")
_PAGE = Path(__file__).resolve().parents[2] / "static" / "index.html"


@app.get("/")
def page():
    return FileResponse(_PAGE)


@app.get("/patients")
def patients_endpoint():
    try:
        patients = list_patients(get_settings().mimic_dir)
        return {"patients": [patient.model_dump() for patient in patients]}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/consult")
def consult_endpoint(body: ConsultRequest):
    try:
        result = consult(body.question, body.subject_id, body.k)
    except MissingPatient as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MissingIndex as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result
