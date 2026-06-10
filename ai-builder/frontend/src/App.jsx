import { useMemo, useState } from "react";
import { v4 as uuidv4 } from "uuid";
import BuildView from "./views/BuildView";
import ChatView from "./views/ChatView";
import PRDView from "./views/PRDView";

const VIEWS = { chat: "chat", prd: "prd", build: "build" };

export default function App() {
  const sessionId = useMemo(() => uuidv4(), []);
  const [view, setView] = useState(VIEWS.chat);
  const [prd, setPrd] = useState(null);

  return (
    <div className="min-h-screen bg-bg">
      <nav className="border-b border-border px-4 py-3">
        <div className="mx-auto flex max-w-4xl items-center gap-4">
          <span className="text-sm font-semibold text-accent">AI Architect Builder</span>
          <ViewTab label="Chat" active={view === VIEWS.chat} onClick={() => setView(VIEWS.chat)} />
          <ViewTab label="PRD" active={view === VIEWS.prd} disabled={!prd} onClick={() => prd && setView(VIEWS.prd)} />
          <ViewTab label="Build" active={view === VIEWS.build} disabled={view !== VIEWS.build} onClick={() => view === VIEWS.build && setView(VIEWS.build)} />
        </div>
      </nav>

      {view === VIEWS.chat && (
        <ChatView sessionId={sessionId} onPRDReady={(doc) => { setPrd(doc); setView(VIEWS.prd); }} />
      )}
      {view === VIEWS.prd && prd && (
        <PRDView
          sessionId={sessionId}
          prd={prd}
          onApprove={() => setView(VIEWS.build)}
          onReject={() => setView(VIEWS.chat)}
        />
      )}
      {view === VIEWS.build && <BuildView sessionId={sessionId} />}
    </div>
  );
}

function ViewTab({ label, active, disabled, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`text-xs font-medium ${active ? "text-primary" : "text-secondary"} disabled:opacity-30`}
    >
      {label}
    </button>
  );
}
