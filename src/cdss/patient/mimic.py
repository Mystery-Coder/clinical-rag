"""MIMIC-IV demo 2.2 patient cards. The chart is context, never a citation."""

from __future__ import annotations

import csv
import gzip
from pathlib import Path

from cdss.schemas import PatientCard, PatientSummary

_TABLES = (
    "patients",
    "admissions",
    "diagnoses_icd",
    "d_icd_diagnoses",
    "prescriptions",
    "labevents",
    "d_labitems",
)


def find_table(root: Path, name: str) -> Path | None:
    if not root.exists():
        return None
    matches = sorted(root.rglob(f"{name}.csv")) + sorted(root.rglob(f"{name}.csv.gz"))
    return matches[0] if matches else None


def mimic_available(root: Path) -> bool:
    return find_table(root, "patients") is not None and find_table(root, "admissions") is not None


def _open(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", newline="", encoding="utf-8")
    return path.open("r", newline="", encoding="utf-8")


def _rows(path: Path):
    with _open(path) as handle:
        yield from csv.DictReader(handle)


def _require(root: Path, name: str) -> Path:
    found = find_table(root, name)
    if found is None:
        raise FileNotFoundError(
            f"Missing {name}.csv under {root}. Unzip the MIMIC-IV demo 2.2 hosp tables there."
        )
    return found


def diagnosis_titles(root: Path) -> list[str]:
    """Long titles for codes that appear in the demo, in file order."""
    codes: set[tuple[str, str]] = set()
    for row in _rows(_require(root, "diagnoses_icd")):
        codes.add((row["icd_code"].strip(), str(row["icd_version"]).strip()))
    titles: list[str] = []
    seen: set[str] = set()
    for row in _rows(_require(root, "d_icd_diagnoses")):
        key = (row["icd_code"].strip(), str(row["icd_version"]).strip())
        if key not in codes:
            continue
        title = row["long_title"].strip()
        if title and title not in seen:
            seen.add(title)
            titles.append(title)
    return titles


def _latest_admission(root: Path, subject_id: str) -> dict[str, str]:
    chosen: dict[str, str] | None = None
    for row in _rows(_require(root, "admissions")):
        if row["subject_id"].strip() != subject_id:
            continue
        if chosen is None or row.get("admittime", "") > chosen.get("admittime", ""):
            chosen = row
    if chosen is None:
        raise KeyError(f"No admission for subject_id {subject_id}")
    return chosen


def _patient_row(root: Path, subject_id: str) -> dict[str, str]:
    for row in _rows(_require(root, "patients")):
        if row["subject_id"].strip() == subject_id:
            return row
    raise KeyError(f"No patient {subject_id}")


def _diagnoses_for_admission(root: Path, subject_id: str, hadm_id: str) -> list[str]:
    wanted: list[tuple[int, str, str]] = []
    for row in _rows(_require(root, "diagnoses_icd")):
        if row["subject_id"].strip() != subject_id or row["hadm_id"].strip() != hadm_id:
            continue
        try:
            seq = int(row.get("seq_num") or 0)
        except ValueError:
            seq = 0
        wanted.append((seq, row["icd_code"].strip(), str(row["icd_version"]).strip()))
    lookup = {
        (row["icd_code"].strip(), str(row["icd_version"]).strip()): row["long_title"].strip()
        for row in _rows(_require(root, "d_icd_diagnoses"))
    }
    titles: list[str] = []
    for _, code, version in sorted(wanted):
        title = lookup.get((code, version))
        if title and title not in titles:
            titles.append(title)
    return titles


def _drugs_for_admission(root: Path, subject_id: str, hadm_id: str) -> list[str]:
    drugs: list[str] = []
    for row in _rows(_require(root, "prescriptions")):
        if row["subject_id"].strip() != subject_id or row["hadm_id"].strip() != hadm_id:
            continue
        name = (row.get("drug") or "").strip()
        if name and name not in drugs:
            drugs.append(name)
    return drugs


def _number(value: str | None) -> float | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _abnormal_labs(root: Path, subject_id: str, hadm_id: str, limit: int = 8) -> list[str]:
    items = {
        row["itemid"].strip(): row.get("label", "").strip()
        for row in _rows(_require(root, "d_labitems"))
    }
    hits: list[tuple[str, str]] = []
    for row in _rows(_require(root, "labevents")):
        if row["subject_id"].strip() != subject_id or row.get("hadm_id", "").strip() != hadm_id:
            continue
        value = _number(row.get("valuenum") or row.get("value"))
        low = _number(row.get("ref_range_lower"))
        high = _number(row.get("ref_range_upper"))
        if value is None or (low is None and high is None):
            continue
        if low is not None and value < low:
            side = "low"
        elif high is not None and value > high:
            side = "high"
        else:
            continue
        label = items.get(row["itemid"].strip(), f"item {row['itemid']}")
        unit = (row.get("valueuom") or "").strip()
        ref = f"{low if low is not None else ''}-{high if high is not None else ''}"
        text = f"{label} {value:g} {unit} ({side}; ref {ref})".strip()
        hits.append((row.get("charttime") or "", text))
    hits.sort(key=lambda item: item[0], reverse=True)
    chosen: list[str] = []
    for _, text in hits:
        if text not in chosen:
            chosen.append(text)
        if len(chosen) >= limit:
            break
    return chosen


def _sex(code: str | None) -> str | None:
    if not code:
        return None
    return {"M": "male", "F": "female"}.get(code.strip().upper(), code.strip())


def list_patients(root: Path, diagnosis_limit: int = 3) -> list[PatientSummary]:
    """One pass over the demo tables. Each row is the latest admission."""
    for name in ("patients", "admissions", "diagnoses_icd", "d_icd_diagnoses"):
        _require(root, name)

    people: dict[str, dict[str, str]] = {}
    for row in _rows(_require(root, "patients")):
        subject_id = row["subject_id"].strip()
        if subject_id:
            people[subject_id] = row

    latest: dict[str, dict[str, str]] = {}
    for row in _rows(_require(root, "admissions")):
        subject_id = row["subject_id"].strip()
        if subject_id not in people:
            continue
        current = latest.get(subject_id)
        if current is None or row.get("admittime", "") > current.get("admittime", ""):
            latest[subject_id] = row

    lookup = {
        (row["icd_code"].strip(), str(row["icd_version"]).strip()): row["long_title"].strip()
        for row in _rows(_require(root, "d_icd_diagnoses"))
    }
    diagnoses: dict[str, list[tuple[int, str]]] = {}
    for row in _rows(_require(root, "diagnoses_icd")):
        subject_id = row["subject_id"].strip()
        admission = latest.get(subject_id)
        if admission is None or row["hadm_id"].strip() != admission["hadm_id"].strip():
            continue
        title = lookup.get((row["icd_code"].strip(), str(row["icd_version"]).strip()))
        if not title:
            continue
        try:
            seq = int(row.get("seq_num") or 0)
        except ValueError:
            seq = 0
        diagnoses.setdefault(subject_id, []).append((seq, title))

    cards: list[PatientSummary] = []
    for subject_id in sorted(people):
        admission = latest.get(subject_id)
        if admission is None:
            continue
        patient = people[subject_id]
        age_raw = patient.get("anchor_age", "").strip()
        titles: list[str] = []
        for _, title in sorted(diagnoses.get(subject_id, [])):
            if title not in titles:
                titles.append(title)
            if len(titles) >= diagnosis_limit:
                break
        cards.append(
            PatientSummary(
                subject_id=subject_id,
                hadm_id=admission["hadm_id"].strip(),
                age=int(age_raw) if age_raw.isdigit() else None,
                sex=_sex(patient.get("gender")),
                admission_type=(admission.get("admission_type") or "").strip() or None,
                diagnoses=titles,
            )
        )
    return cards


def build_card(root: Path, subject_id: str) -> PatientCard:
    for name in _TABLES:
        _require(root, name)
    patient = _patient_row(root, subject_id)
    admission = _latest_admission(root, subject_id)
    hadm_id = admission["hadm_id"].strip()
    age_raw = patient.get("anchor_age", "").strip()
    return PatientCard(
        subject_id=subject_id,
        hadm_id=hadm_id,
        age=int(age_raw) if age_raw.isdigit() else None,
        sex=_sex(patient.get("gender")),
        admission_type=(admission.get("admission_type") or "").strip() or None,
        diagnoses=_diagnoses_for_admission(root, subject_id, hadm_id),
        drugs=_drugs_for_admission(root, subject_id, hadm_id),
        abnormal_labs=_abnormal_labs(root, subject_id, hadm_id),
    )
