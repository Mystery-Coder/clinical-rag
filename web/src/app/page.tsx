"use client";

import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "cmdk";
import type { ConsultResponse, PatientSummary } from "@/lib/types";
import { Search } from "lucide-react";

const NOTICE = "This is decision support for a clinician. It is not a diagnosis or a treatment order.";

export default function Home() {
  const [patients, setPatients] = useState<PatientSummary[]>([]);
  const [filter, setFilter] = useState("");
  const [selectedPatient, setSelectedPatient] = useState<PatientSummary | null>(null);
  const [question, setQuestion] = useState("treatment considerations in sepsis with kidney injury");
  const [k, setK] = useState(5);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ConsultResponse | null>(null);

  useEffect(() => {
    fetch("/api/patients")
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data?.patients)) {
          setPatients(data.patients);
        } else if (Array.isArray(data)) {
          setPatients(data);
        }
      })
      .catch(() => {
        // ignore
      });
  }, []);

  const filtered = useMemo(() => {
    const term = filter.toLowerCase();
    if (!term) return patients;
    return patients.filter((p) => {
      const diag = (p.diagnoses || []).join(" ").toLowerCase();
      return p.subject_id.toLowerCase().includes(term) || diag.includes(term);
    });
  }, [patients, filter]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setResult(null);
    if (!question.trim() && !selectedPatient?.subject_id) {
      setError("Provide a question or a MIMIC demo subject_id.");
      return;
    }
    setLoading(true);
    try {
      const res = await fetch("/api/consult", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: question.trim() || null,
          subject_id: selectedPatient?.subject_id || null,
          k,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data?.detail || "Request failed.");
        return;
      }
      setResult(data);
    } catch (err: any) {
      setError(err?.message || "Request failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="mx-auto max-w-6xl px-4 py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold">Clinical decision support</h1>
        <p className="text-sm text-[var(--muted)]">{NOTICE}</p>
      </header>

      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Patient search</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="relative">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-[var(--muted)]" />
                <Input
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                  placeholder="Filter by subject id or diagnosis"
                  className="pl-8"
                />
              </div>
              <div className="max-h-[420px] overflow-auto rounded-md border border-[var(--line)]">
                {filtered.length === 0 && (
                  <div className="p-3 text-sm text-[var(--muted)]">No patients found.</div>
                )}
                {filtered.map((p) => (
                  <button
                    key={p.subject_id}
                    type="button"
                    onClick={() => setSelectedPatient(p)}
                    className={`w-full text-left p-3 border-b border-[var(--line)] last:border-0 hover:bg-white/60 ${
                      selectedPatient?.subject_id === p.subject_id ? "bg-white" : ""
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="font-medium">{p.subject_id}</div>
                      <div className="text-xs text-[var(--muted)]">
                        {p.age ? `${p.age}y` : ""} {p.sex || ""}
                      </div>
                    </div>
                    <div className="text-xs text-[var(--muted)]">{p.admission_type || ""}</div>
                    <div className="text-xs mt-1">{(p.diagnoses || []).slice(0, 3).join("; ")}</div>
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Consult</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={submit} className="space-y-3">
                <div>
                  <label className="text-sm text-[var(--muted)]">Question</label>
                  <Textarea
                    rows={3}
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="Treatment considerations in sepsis with kidney injury"
                  />
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-32">
                    <label className="text-sm text-[var(--muted)]">Top-k</label>
                    <Input type="number" min={1} max={20} value={k} onChange={(e) => setK(Number(e.target.value))} />
                  </div>
                  <div className="flex-1 text-sm text-[var(--muted)]">
                    {selectedPatient
                      ? `Using chart: ${selectedPatient.subject_id} (${selectedPatient.hadm_id})`
                      : "No chart selected"}
                  </div>
                </div>
                <Button type="submit" disabled={loading}>
                  {loading ? "Running retrieval, graph lookup, and the support check." : "Consult"}
                </Button>
              </form>
              <p className="text-xs text-[var(--muted)] mt-2">
                Empty state: provide a question or a chart. The consult may take a moment on first run.
              </p>
            </CardContent>
          </Card>

          {error && (
            <Alert>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {loading && (
            <Card>
              <CardContent className="space-y-3">
                <Skeleton className="h-6 w-1/3" />
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-20 w-full" />
              </CardContent>
            </Card>
          )}

          {result && !loading && (
            <div className="space-y-4">
              {result.patient && (
                <Card>
                  <CardHeader>
                    <CardTitle>Patient context</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2 text-sm">
                    <div>
                      Age {result.patient.age}, {result.patient.sex}, {result.patient.admission_type}. Admission {result.patient.hadm_id}.
                    </div>
                    <div>
                      <span className="text-[var(--muted)]">Diagnoses:</span>{" "}
                      {(result.patient.diagnoses || []).join("; ")}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {(result.patient.drugs || []).map((d) => (
                        <Badge key={d} variant="outline">
                          {d}
                        </Badge>
                      ))}
                    </div>
                    {(result.patient.abnormal_labs || []).length > 0 && (
                      <div>
                        <span className="text-[var(--muted)]">Abnormal labs:</span>{" "}
                        {(result.patient.abnormal_labs || []).join("; ")}
                      </div>
                    )}
                    {(result.patient.unmatched_drugs || []).length > 0 && (
                      <div className="text-[var(--flag)]">
                        Unmatched drug names: {(result.patient.unmatched_drugs || []).join(", ")}
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              <Card>
                <CardHeader>
                  <CardTitle>Recommendation</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="font-serif leading-relaxed whitespace-pre-wrap">{result.recommendation}</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Claims</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {(result.claims || []).map((claim, idx) => (
                    <div key={idx} className="text-sm leading-relaxed">
                      <span>{claim.text} </span>
                      {(claim.citation_ids || []).map((cid) => (
                        <a
                          key={cid}
                          href={`#src-${cid}`}
                          className="text-[var(--ix)] underline ml-1"
                        >
                          {cid}
                        </a>
                      ))}
                      {claim.flag ? (
                        <span className="ml-1 px-1 bg-[var(--flag-bg)] text-[var(--flag)]">{claim.flag}</span>
                      ) : (
                        <span className="ml-1 text-[var(--ok)]">supported</span>
                      )}
                    </div>
                  ))}
                  {(result.claims || []).length === 0 && <div>No claims.</div>}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Drug interaction chain</CardTitle>
                </CardHeader>
                <CardContent>
                  {(result.interactions || []).length === 0 ? (
                    <p>No drug pair or contraindication was returned for the matched nodes.</p>
                  ) : (
                    <ul className="space-y-2 text-sm">
                      {(result.interactions || []).map((ix, idx) => (
                        <li key={idx} className="border-l-4 border-[var(--ix)] pl-3">
                          <div className="font-medium">
                            {ix.drug_a} + {ix.drug_b}
                          </div>
                          <div>{ix.relation}</div>
                          <div className="text-[var(--muted)]">{ix.via}</div>
                        </li>
                      ))}
                    </ul>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Sources</CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2 text-sm">
                    {(result.sources || []).map((src) => (
                      <li key={src.id} id={`src-${src.id}`}>
                        <a href={src.url} target="_blank" rel="noreferrer" className="text-[var(--ix)] underline">
                          {src.id}
                        </a>{" "}
                        — {src.title}
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>

              {(result.graph_context || []).length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>Graph context</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <Collapsible>
                      <CollapsibleTrigger>
                        <span>Show graph context</span>
                      </CollapsibleTrigger>
                      <CollapsibleContent>
                        <ul className="space-y-1 text-sm">
                          {(result.graph_context || []).map((g, idx) => (
                            <li key={idx}>{g}</li>
                          ))}
                        </ul>
                      </CollapsibleContent>
                    </Collapsible>
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
