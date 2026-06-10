import { useState } from "react";
import { approvePRD, rejectPRD } from "../api/client";
import PRDSection, { EditableList, EditableText } from "../components/PRDSection";
import { DataModelTable, EndpointsTable, UserStoriesTable } from "./PRDTables";

export default function PRDView({ sessionId, prd: initialPRD, onApprove, onReject }) {
  const [prd, setPrd] = useState(initialPRD);
  const [saving, setSaving] = useState(false);

  const patch = (field, value) => setPrd((prev) => ({ ...prev, [field]: value }));
  const patchStack = (field, value) =>
    setPrd((prev) => ({ ...prev, proposed_stack: { ...prev.proposed_stack, [field]: value } }));

  const handleApprove = async () => {
    setSaving(true);
    try {
      await approvePRD(sessionId, prd);
      onApprove();
    } catch (err) {
      alert(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleReject = async () => {
    try {
      await rejectPRD(sessionId);
      onReject();
    } catch (err) {
      alert(err.message);
    }
  };

  const stack = prd.proposed_stack;

  return (
    <div className="mx-auto max-w-4xl px-4 py-6">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Product Requirements Document</h1>
          <p className="text-sm text-secondary">Revisa y edita antes de construir.</p>
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={handleReject} className="rounded-lg border border-border px-4 py-2 text-sm text-secondary hover:border-error hover:text-error">
            Rechazar / volver
          </button>
          <button type="button" onClick={handleApprove} disabled={saving} className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50">
            {saving ? "Aprobando..." : "Aprobar y construir →"}
          </button>
        </div>
      </header>

      <div className="space-y-4">
        <PRDSection title="Título y Overview">
          <EditableText value={prd.title} onChange={(v) => patch("title", v)} className="mb-3 text-lg font-semibold" />
          <EditableText multiline value={prd.overview} onChange={(v) => patch("overview", v)} />
        </PRDSection>

        <PRDSection title="Goals">
          <EditableList items={prd.goals} onChange={(v) => patch("goals", v)} label="Objetivos (uno por línea)" />
        </PRDSection>

        <PRDSection title="Out of Scope">
          <EditableList items={prd.out_of_scope} onChange={(v) => patch("out_of_scope", v)} label="Fuera de alcance" />
        </PRDSection>

        <PRDSection title="User Stories">
          <UserStoriesTable stories={prd.user_stories} onChange={(v) => patch("user_stories", v)} />
        </PRDSection>

        <PRDSection title="Proposed Stack">
          <div className="flex flex-wrap gap-2">
            {Object.entries(stack).filter(([k]) => k !== "extras").map(([key, val]) => (
              <span key={key} className="rounded-lg border border-border bg-bg px-3 py-1 text-xs">
                <span className="text-secondary">{key}: </span>
                <EditableText value={val} onChange={(v) => patchStack(key, v)} className="inline px-0 py-0" />
              </span>
            ))}
          </div>
        </PRDSection>

        <PRDSection title="Data Model">
          <DataModelTable entities={prd.data_model} onChange={(v) => patch("data_model", v)} />
        </PRDSection>

        <PRDSection title="API Endpoints">
          <EndpointsTable endpoints={prd.api_endpoints} onChange={(v) => patch("api_endpoints", v)} />
        </PRDSection>

        <PRDSection title="Milestones">
          <div className="grid gap-3 sm:grid-cols-2">
            {prd.milestones.map((ms, i) => (
              <div key={i} className="rounded-lg border border-border bg-bg p-4">
                <p className="text-xs text-secondary">Fase {ms.phase}</p>
                <EditableText value={ms.name} onChange={(v) => {
                  const next = [...prd.milestones];
                  next[i] = { ...ms, name: v };
                  patch("milestones", next);
                }} className="font-medium" />
                <p className="mt-1 text-xs text-secondary">{ms.estimated_weeks} semanas</p>
                <EditableList
                  items={ms.deliverables}
                  onChange={(v) => {
                    const next = [...prd.milestones];
                    next[i] = { ...ms, deliverables: v };
                    patch("milestones", next);
                  }}
                  label="Entregables"
                />
              </div>
            ))}
          </div>
        </PRDSection>
      </div>
    </div>
  );
}
