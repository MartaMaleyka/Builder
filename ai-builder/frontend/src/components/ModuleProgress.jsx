import { useState } from "react";

const STATUS_STYLES = {
  pending: "border-secondary text-secondary",
  generating: "border-accent text-accent",
  done: "border-success text-success",
  failed: "border-error text-error",
};

export default function ModuleProgress({ module }) {
  const [expanded, setExpanded] = useState(false);
  const { module_name, status, files, error } = module;

  return (
    <div className="rounded-lg border border-border bg-surface px-4 py-3">
      <div className="flex items-center gap-3">
        <StatusIcon status={status} />
        <div className="flex-1">
          <p className="text-sm font-medium capitalize text-primary">
            {module_name.replace(/_/g, " ")}
          </p>
          {status === "done" && (
            <p className="text-xs text-secondary">{files.length} archivos</p>
          )}
        </div>
        {status === "failed" && error && (
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="text-xs text-error hover:underline"
          >
            {expanded ? "Ocultar" : "Ver error"}
          </button>
        )}
      </div>
      {expanded && error && (
        <p className="mt-2 rounded-lg border border-error/30 bg-bg px-3 py-2 text-xs text-error">
          {error}
        </p>
      )}
    </div>
  );
}

function StatusIcon({ status }) {
  const base = `flex h-8 w-8 items-center justify-center rounded-full border-2 ${STATUS_STYLES[status]}`;

  if (status === "generating") {
    return (
      <div className={base}>
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-accent border-t-transparent" />
      </div>
    );
  }
  if (status === "done") {
    return <div className={base}>✓</div>;
  }
  if (status === "failed") {
    return <div className={base}>✕</div>;
  }
  return <div className={`${base} bg-bg`} />;
}
