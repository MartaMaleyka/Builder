import { useRef, useState } from "react";
import { approvePRD, rejectPRD } from "../api/client";
import PRDSection, { EditableList, EditableText } from "../components/PRDSection";
import { useToast } from "../context/ToastContext";
import { DataModelTable, EndpointsTable, RequirementsTable, UserStoriesTable } from "./PRDTables";

export default function PRDView({ sessionId, prd: initialPRD, onApprove, onReject, onBackToChat }) {
  const [prd, setPrd] = useState(initialPRD);
  const [saving, setSaving] = useState(false);
  const [rejecting, setRejecting] = useState(false);
  const approveAbortRef = useRef(null);
  const { show: showToast } = useToast();

  const patch = (field, value) => setPrd((prev) => ({ ...prev, [field]: value }));
  const patchStack = (field, value) =>
    setPrd((prev) => ({ ...prev, proposed_stack: { ...prev.proposed_stack, [field]: value } }));

  const handleApprove = async () => {
    setSaving(true);
    approveAbortRef.current = new AbortController();
    try {
      await approvePRD(sessionId, prd, approveAbortRef.current.signal);
      showToast("PRD aprobado, iniciando construcción...", "success");
      onApprove();
    } catch (err) {
      if (err.name === "AbortError") return;
      showToast(err.message || "Error al aprobar el PRD", "error");
    } finally {
      setSaving(false);
    }
  };

  const handleReject = async () => {
    setRejecting(true);
    try {
      await rejectPRD(sessionId);
      onReject();
    } catch (err) {
      showToast(err.message || "Error al rechazar el PRD", "error");
    } finally {
      setRejecting(false);
    }
  };

  const stack = prd.proposed_stack;

  return (
    <div className="mx-auto max-w-4xl px-4 py-6">
      <header className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Product Requirements Document</h1>
          <p className="text-sm text-secondary">
            Haz clic en cualquier campo para editarlo antes de construir.
          </p>
          {onBackToChat && (
            <button
              type="button"
              onClick={onBackToChat}
              className="mt-2 flex items-center gap-1 text-xs text-secondary hover:text-accent transition-colors"
            >
              ← Volver al Chat
            </button>
          )}
        </div>
        <div className="flex shrink-0 gap-2">
          <button
            type="button"
            onClick={handleReject}
            disabled={rejecting || saving}
            className="rounded-lg border border-border px-4 py-2 text-sm text-secondary hover:border-error hover:text-error disabled:opacity-40"
          >
            {rejecting ? "Rechazando..." : "Rechazar PRD"}
          </button>
          <button
            type="button"
            onClick={handleApprove}
            disabled={saving || rejecting}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
          >
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

        <PRDSection title="Functional Requirements">
          <RequirementsTable
            requirements={prd.functional_requirements}
            onChange={(v) => patch("functional_requirements", v)}
          />
        </PRDSection>

        <PRDSection title="Non-Functional Requirements">
          <RequirementsTable
            requirements={prd.non_functional_requirements}
            onChange={(v) => patch("non_functional_requirements", v)}
          />
        </PRDSection>

        <PRDSection title="Proposed Stack">
          <div className="flex flex-wrap gap-2">
            {Object.entries(stack)
              .filter(([k]) => k !== "extras")
              .map(([key, val]) => (
                <span key={key} className="rounded-lg border border-border bg-bg px-3 py-1 text-xs">
                  <span className="text-secondary">{key}: </span>
                  <EditableText value={val} onChange={(v) => patchStack(key, v)} className="inline px-0 py-0" />
                </span>
              ))}
          </div>
          {stack.extras?.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {stack.extras.map((extra, i) => (
                <span key={i} className="rounded-full bg-surface px-2 py-0.5 text-xs text-secondary">
                  {extra}
                </span>
              ))}
            </div>
          )}
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
              <div key={ms.phase} className="rounded-lg border border-border bg-bg p-4">
                <p className="text-xs text-secondary">Fase {ms.phase}</p>
                <EditableText
                  value={ms.name}
                  onChange={(v) => {
                    const next = [...prd.milestones];
                    next[i] = { ...ms, name: v };
                    patch("milestones", next);
                  }}
                  className="font-medium"
                />
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

      <div className="mt-8 flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-2">
          {onBackToChat && (
            <button
              type="button"
              onClick={onBackToChat}
              className="rounded-lg border border-border px-4 py-2 text-sm text-secondary hover:border-accent hover:text-accent transition-colors"
            >
              ← Volver al Chat
            </button>
          )}
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleReject}
            disabled={rejecting || saving}
            className="rounded-lg border border-border px-4 py-2 text-sm text-secondary hover:border-error hover:text-error disabled:opacity-40"
          >
            {rejecting ? "Rechazando..." : "Rechazar PRD"}
          </button>
          <button
            type="button"
            onClick={handleApprove}
            disabled={saving || rejecting}
            className="rounded-lg bg-accent px-6 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
          >
            {saving ? "Aprobando..." : "Aprobar y construir →"}
          </button>
        </div>
      </div>
    </div>
  );
}
