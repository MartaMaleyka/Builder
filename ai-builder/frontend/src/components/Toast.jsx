import { useEffect } from "react";

export default function Toast({ toasts, remove }) {
  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex flex-col items-end gap-2">
      {toasts.map((t) => (
        <ToastItem key={t.id} toast={t} onClose={() => remove(t.id)} />
      ))}
    </div>
  );
}

function ToastItem({ toast, onClose }) {
  useEffect(() => {
    const timer = setTimeout(onClose, toast.duration ?? 5000);
    return () => clearTimeout(timer);
  }, [toast.id, onClose]);

  const base =
    "pointer-events-auto flex max-w-xs items-start gap-3 rounded-lg px-4 py-3 text-sm shadow-lg";
  const styles = {
    error: `${base} bg-error text-white`,
    success: `${base} bg-success text-white`,
    info: `${base} border border-border bg-surface text-primary`,
  };

  return (
    <div className={styles[toast.type] ?? styles.info}>
      <span className="flex-1 leading-snug">{toast.message}</span>
      <button
        type="button"
        onClick={onClose}
        className="mt-0.5 shrink-0 opacity-70 hover:opacity-100"
      >
        ✕
      </button>
    </div>
  );
}
