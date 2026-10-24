export interface PatientSummary {
  subject_id: string;
  hadm_id: string;
  age: number | null;
  sex: string | null;
  admission_type: string | null;
  diagnoses: string[];
}

export interface Passage {
  id: string;
  title: string;
  content: string;
  source: "pubmed" | "nice" | "statpearls";
  pmid: string | null;
  url: string;
}

export interface PatientCard {
  subject_id: string;
  hadm_id: string;
  age: number | null;
  sex: string | null;
  admission_type: string | null;
  diagnoses: string[];
  drugs: string[];
  abnormal_labs: string[];
  unmatched_drugs?: string[];
}

export interface Claim {
  text: string;
  citation_ids: string[];
  support: "supported" | "unsupported";
  flag: string | null;
}

export interface Interaction {
  drug_a: string;
  drug_b: string;
  relation: string;
  via: string;
}

export interface Source {
  id: string;
  title: string;
  url: string;
}

export interface ConsultResponse {
  notice: string;
  recommendation: string;
  claims: Claim[];
  interactions: Interaction[];
  sources: Source[];
  patient: PatientCard | null;
  graph_context: string[];
}

export interface ConsultRequest {
  question: string | null;
  subject_id: string | null;
  k?: number;
}
