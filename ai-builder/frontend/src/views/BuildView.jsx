import { useState } from "react";
import { downloadZip } from "../api/client";
import ModuleProgress from "../components/ModuleProgress";
import { useToast } from "../context/ToastContext";
import { useGeneration } from "../hooks/useGeneration";

export default function BuildView({ sessionId, onBackToPRD }) {
  const { result, error, starting, progress, retry } = useGeneration(sessionId);
  const [downloading, setDownloading] = useState(false);
  const { show: showToast } = useToast();

  const status = result?.status;
  const modules = result?.modules ?? [];
  const allFailed = status === "failed";
  const isComplete = status === "complete";
  const isRunning = status === "in_progress" || starting;

  const handleDownload = async () => {
    setDownloading(true);
    try {
      await downloadZip(sessionId);
    } catch (err) {
      showToast(err.message || "Error descargando el proyecto", "error");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl px-4 py-6">
      <header className="mb-6 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Generación de código</h1>
          <p className="text-sm text-secondary">
            {starting ? "Iniciando generación..." : "Progreso en tiempo real por módulo."}
          </p>
        </div>

        {onBackToPRD && (
          <button
            type="button"
            onClick={onBackToPRD}
            className="flex shrink-0 items-center gap-1 rounded-lg border border-border px-3 py-2 text-xs text-secondary hover:border-accent hover:text-accent transition-colors"
          >
            ← Volver al PRD
          </button>
        )}
      </header>

      <div className="mb-6">
        <div className="mb-2 flex justify-between text-xs text-secondary">
          <span>Progreso global</span>
          <span>{progress}%</span>
        </div>
        <div className="h-2 overflow-hidden rounded-lg bg-surface">
          <div
            className="h-full rounded-lg bg-accent transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      <div className="space-y-2">
        {modules.map((mod) => (
          <ModuleProgress key={mod.module_name} module={mod} />
        ))}
        {!modules.length && (
          <p className="text-center text-sm text-secondary">Esperando estado...</p>
        )}
      </div>

      {error && <p className="mt-4 text-center text-sm text-error">{error}</p>}

      <div className="mt-8 flex flex-col gap-3">
        {isComplete && (
          <button
            type="button"
            onClick={handleDownload}
            disabled={downloading}
            className="w-full rounded-lg bg-success py-4 text-base font-semibold text-white hover:opacity-90 disabled:opacity-50"
          >
            {downloading ? "Descargando..." : "Descargar proyecto ZIP"}
          </button>
        )}

        {allFailed && (
          <button
            type="button"
            onClick={retry}
            className="w-full rounded-lg border border-accent py-3 text-sm font-medium text-accent hover:bg-accent/10"
          >
            Reintentar generación
          </button>
        )}

        {onBackToPRD && (isComplete || allFailed) && (
          <button
            type="button"
            onClick={onBackToPRD}
            className="w-full rounded-lg border border-border py-3 text-sm text-secondary hover:border-accent hover:text-accent transition-colors"
          >
            ← Volver al PRD
          </button>
        )}
      </div>
    </div>
  );
}
