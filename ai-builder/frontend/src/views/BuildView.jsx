import { useState } from "react";
import { downloadZip } from "../api/client";
import ModuleProgress from "../components/ModuleProgress";
import { useGeneration } from "../hooks/useGeneration";

export default function BuildView({ sessionId }) {
  const { result, error, starting, progress, retry } = useGeneration(sessionId);
  const [downloading, setDownloading] = useState(false);

  const status = result?.status;
  const modules = result?.modules ?? [];
  const allFailed = status === "failed";
  const isComplete = status === "complete";

  const handleDownload = async () => {
    setDownloading(true);
    try {
      await downloadZip(sessionId);
    } catch (err) {
      alert(err.message);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl px-4 py-6">
      <header className="mb-6">
        <h1 className="text-xl font-semibold">Generación de código</h1>
        <p className="text-sm text-secondary">
          {starting ? "Iniciando generación..." : "Progreso en tiempo real por módulo."}
        </p>
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

      {isComplete && (
        <button
          type="button"
          onClick={handleDownload}
          disabled={downloading}
          className="mt-8 w-full rounded-lg bg-success py-4 text-base font-semibold text-white hover:opacity-90 disabled:opacity-50"
        >
          {downloading ? "Descargando..." : "Descargar proyecto ZIP"}
        </button>
      )}

      {allFailed && (
        <button
          type="button"
          onClick={retry}
          className="mt-8 w-full rounded-lg border border-accent py-3 text-sm font-medium text-accent hover:bg-accent/10"
        >
          Reintentar
        </button>
      )}
    </div>
  );
}
