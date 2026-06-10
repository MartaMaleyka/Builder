import { EditableText } from "../components/PRDSection";

export function UserStoriesTable({ stories, onChange }) {
  const update = (index, field, value) => {
    const next = stories.map((s, i) => (i === index ? { ...s, [field]: value } : s));
    onChange(next);
  };

  return (
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
          <tr key={i} className="border-b border-border/60">
            {["role", "action", "benefit"].map((field) => (
              <td key={field} className="py-2 pr-3 align-top">
                <EditableText
                  value={story[field]}
                  onChange={(v) => update(i, field, v)}
                />
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
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
          <tr key={i} className="border-b border-border/60">
            <td className="py-2 pr-3">
              <EditableText value={entity.name} onChange={(v) => update(i, "name", v)} />
            </td>
            <td className="py-2 pr-3">
              <EditableText
                value={entity.fields.join(", ")}
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

  return (
    <table className="w-full text-left text-sm">
      <thead>
        <tr className="border-b border-border text-xs text-secondary">
          <th className="py-2 pr-2">Method</th>
          <th className="py-2 pr-2">Path</th>
          <th className="py-2 pr-2">Description</th>
          <th className="py-2">Auth</th>
        </tr>
      </thead>
      <tbody>
        {endpoints.map((ep, i) => (
          <tr key={i} className="border-b border-border/60">
            <td className="py-2 pr-2"><EditableText value={ep.method} onChange={(v) => update(i, "method", v)} /></td>
            <td className="py-2 pr-2"><EditableText value={ep.path} onChange={(v) => update(i, "path", v)} /></td>
            <td className="py-2 pr-2"><EditableText value={ep.description} onChange={(v) => update(i, "description", v)} /></td>
            <td className="py-2">
              <EditableText
                value={String(ep.auth_required)}
                onChange={(v) => update(i, "auth_required", v)}
              />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
