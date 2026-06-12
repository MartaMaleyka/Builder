import { EditableText } from "../components/PRDSection";

const PRIORITY_COLORS = {
  high: "bg-red-900/40 text-red-300",
  medium: "bg-yellow-900/40 text-yellow-300",
  low: "bg-surface text-secondary",
};

export function UserStoriesTable({ stories, onChange }) {
  const update = (index, field, value) => {
    const next = stories.map((s, i) => (i === index ? { ...s, [field]: value } : s));
    onChange(next);
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-border text-xs text-secondary">
            <th className="py-2 pr-3">Role</th>
            <th className="py-2 pr-3">Action</th>
            <th className="py-2">Benefit</th>
          </tr>
        </thead>
        <tbody>
          {stories.map((story, i) => (
            <tr key={`${story.role}-${i}`} className="border-b border-border/60">
              {["role", "action", "benefit"].map((field) => (
                <td key={field} className="py-2 pr-3 align-top">
                  <EditableText value={story[field]} onChange={(v) => update(i, field, v)} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function RequirementsTable({ requirements, onChange }) {
  const update = (index, field, value) => {
    const next = requirements.map((r, i) => (i === index ? { ...r, [field]: value } : r));
    onChange(next);
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-border text-xs text-secondary">
            <th className="w-20 py-2 pr-3">ID</th>
            <th className="py-2 pr-3">Description</th>
            <th className="w-24 py-2">Priority</th>
          </tr>
        </thead>
        <tbody>
          {requirements.map((req, i) => (
            <tr key={req.id ?? i} className="border-b border-border/60">
              <td className="py-2 pr-3 align-top font-mono text-xs text-secondary">{req.id}</td>
              <td className="py-2 pr-3 align-top">
                <EditableText value={req.description} onChange={(v) => update(i, "description", v)} />
              </td>
              <td className="py-2 align-top">
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${PRIORITY_COLORS[req.priority] ?? PRIORITY_COLORS.low}`}
                >
                  {req.priority}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function DataModelTable({ entities, onChange }) {
  const update = (index, field, value) => {
    const next = entities.map((e, i) =>
      i === index
        ? { ...e, [field]: field === "fields" || field === "relationships" ? value.split(", ") : value }
        : e
    );
    onChange(next);
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-border text-xs text-secondary">
            <th className="py-2 pr-3">Entidad</th>
            <th className="py-2 pr-3">Campos</th>
            <th className="py-2">Relaciones</th>
          </tr>
        </thead>
        <tbody>
          {entities.map((entity, i) => (
            <tr key={entity.name ?? i} className="border-b border-border/60">
              <td className="py-2 pr-3 font-medium">
                <EditableText value={entity.name} onChange={(v) => update(i, "name", v)} />
              </td>
              <td className="py-2 pr-3">
                <EditableText
                  value={entity.fields
                    .map((f) => (typeof f === "string" ? f : `${f.name}:${f.type}`))
                    .join(", ")}
                  onChange={(v) => update(i, "fields", v)}
                />
              </td>
              <td className="py-2">
                <EditableText
                  value={(entity.relationships || []).join(", ")}
                  onChange={(v) => update(i, "relationships", v)}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function EndpointsTable({ endpoints, onChange }) {
  const update = (index, field, value) => {
    const next = endpoints.map((ep, i) =>
      i === index
        ? { ...ep, [field]: field === "auth_required" ? value === "true" : value }
        : ep
    );
    onChange(next);
  };

  const METHOD_COLORS = {
    GET: "text-green-400",
    POST: "text-blue-400",
    PUT: "text-yellow-400",
    PATCH: "text-yellow-400",
    DELETE: "text-red-400",
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-border text-xs text-secondary">
            <th className="w-16 py-2 pr-2">Method</th>
            <th className="py-2 pr-2">Path</th>
            <th className="py-2 pr-2">Description</th>
            <th className="w-12 py-2">Auth</th>
          </tr>
        </thead>
        <tbody>
          {endpoints.map((ep, i) => (
            <tr key={`${ep.method}-${ep.path}-${i}`} className="border-b border-border/60">
              <td className={`py-2 pr-2 font-mono text-xs font-semibold ${METHOD_COLORS[ep.method] ?? "text-secondary"}`}>
                {ep.method}
              </td>
              <td className="py-2 pr-2">
                <EditableText value={ep.path} onChange={(v) => update(i, "path", v)} className="font-mono text-xs" />
              </td>
              <td className="py-2 pr-2">
                <EditableText value={ep.description} onChange={(v) => update(i, "description", v)} />
              </td>
              <td className="py-2">
                <span className={`text-xs ${ep.auth_required ? "text-accent" : "text-secondary"}`}>
                  {ep.auth_required ? "Sí" : "No"}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
