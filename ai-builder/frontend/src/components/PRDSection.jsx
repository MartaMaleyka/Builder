import { useState } from "react";

export function EditableText({ value, onChange, multiline = false, className = "" }) {
  const [editing, setEditing] = useState(false);

  if (editing) {
    const Tag = multiline ? "textarea" : "input";
    return (
      <Tag
        autoFocus
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onBlur={() => setEditing(false)}
        rows={multiline ? 5 : undefined}
        className={`w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-primary outline-none focus:border-accent ${className}`}
      />
    );
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => setEditing(true)}
      onKeyDown={(e) => e.key === "Enter" && setEditing(true)}
      className={`cursor-text rounded-lg border border-transparent px-3 py-2 text-sm hover:border-border ${className}`}
    >
      {value || <span className="text-secondary">Click para editar</span>}
    </div>
  );
}

export function EditableList({ items, onChange, label }) {
  const text = items.join("\n");

  return (
    <div>
      <p className="mb-2 text-xs uppercase tracking-wide text-secondary">{label}</p>
      <EditableText
        multiline
        value={text}
        onChange={(val) => onChange(val.split("\n").filter(Boolean))}
        className="font-mono text-sm"
      />
    </div>
  );
}

export default function PRDSection({ title, children }) {
  return (
    <section className="rounded-lg border border-border bg-surface p-5">
      <h2 className="mb-4 text-base font-semibold text-primary">{title}</h2>
      {children}
    </section>
  );
}
