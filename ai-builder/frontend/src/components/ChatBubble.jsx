import { useEffect, useState } from "react";

export default function ChatBubble({ role, content, ts }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Double-rAF so the initial opacity-0 is painted before we flip to opacity-100
    const id = requestAnimationFrame(() => requestAnimationFrame(() => setVisible(true)));
    return () => cancelAnimationFrame(id);
  }, []);

  const time = ts
    ? new Date(ts).toLocaleTimeString("es", { hour: "2-digit", minute: "2-digit" })
    : null;

  const enter = visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-2";

  if (role === "user") {
    return (
      <div className={`flex justify-end transition-all duration-300 ${enter}`}>
        <div className="group flex max-w-[78%] flex-col items-end gap-1">
          <div className="rounded-2xl rounded-tr-sm bg-accent px-4 py-2.5 text-sm leading-relaxed text-white">
            {content.split("\n").map((line, i) => (
              <p key={i} className={i > 0 ? "mt-1" : ""}>{line || <br />}</p>
            ))}
          </div>
          {time && (
            <span className="px-1 text-[10px] text-secondary opacity-0 transition-opacity group-hover:opacity-100">
              {time}
            </span>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className={`flex items-start gap-3 transition-all duration-300 ${enter}`}>
      <AgentAvatar />
      <div className="group flex flex-col gap-1">
        <div className="max-w-[85%] rounded-2xl rounded-tl-sm border border-border bg-surface px-4 py-3 text-sm leading-relaxed text-primary">
          {content.split("\n").map((line, i) => (
            <p key={i} className={i > 0 ? "mt-2" : ""}>{line || <br />}</p>
          ))}
        </div>
        {time && (
          <span className="px-1 text-[10px] text-secondary opacity-0 transition-opacity group-hover:opacity-100">
            {time}
          </span>
        )}
      </div>
    </div>
  );
}

export function AgentAvatar() {
  return (
    <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent/20 text-[10px] font-bold text-accent">
      AI
    </div>
  );
}
