import { useMemo, useState } from "react";
import { v4 as uuidv4 } from "uuid";
import { ToastProvider } from "./context/ToastContext";
import BuildView from "./views/BuildView";
import ChatView from "./views/ChatView";
import PRDView from "./views/PRDView";

const VIEWS = { chat: "chat", prd: "prd", build: "build" };

// Stage controls which tabs are reachable:
// 0 = only Chat | 1 = Chat + PRD | 2 = Chat + PRD + Build
const STAGES = { chat: 0, prd: 1, build: 2 };

export default function App() {
  const sessionId = useMemo(() => uuidv4(), []);
  const [view, setView] = useState(VIEWS.chat);
  const [prd, setPrd] = useState(null);
  const [stage, setStage] = useState(0);

  const goTo = (v) => setView(v);

  const handlePRDReady = (doc) => {
    setPrd(doc);
    setStage((s) => Math.max(s, STAGES.prd));
    setView(VIEWS.prd);
  };

  const handleApprove = () => {
    setStage((s) => Math.max(s, STAGES.build));
    setView(VIEWS.build);
  };

  return (
    <ToastProvider>
      <div className="flex h-screen flex-col bg-bg">
        <nav className="shrink-0 border-b border-border px-4 py-3">
          <div className="mx-auto flex max-w-4xl items-center gap-4">
            <span className="text-sm font-semibold text-accent">AI Architect Builder</span>

            <ViewTab
              label="1. Chat"
              active={view === VIEWS.chat}
              disabled={false}
              onClick={() => goTo(VIEWS.chat)}
            />
            <ViewTab
              label="2. PRD"
              active={view === VIEWS.prd}
              disabled={stage < STAGES.prd}
              onClick={() => stage >= STAGES.prd && goTo(VIEWS.prd)}
            />
            <ViewTab
              label="3. Build"
              active={view === VIEWS.build}
              disabled={stage < STAGES.build}
              onClick={() => stage >= STAGES.build && goTo(VIEWS.build)}
            />
          </div>
        </nav>

        <div className="flex-1 overflow-hidden">
          {view === VIEWS.chat && (
            <ChatView sessionId={sessionId} onPRDReady={handlePRDReady} />
          )}
          {view === VIEWS.prd && prd && (
            <div className="h-full overflow-y-auto">
              <PRDView
                sessionId={sessionId}
                prd={prd}
                onApprove={handleApprove}
                onReject={() => goTo(VIEWS.chat)}
                onBackToChat={() => goTo(VIEWS.chat)}
              />
            </div>
          )}
          {view === VIEWS.build && (
            <div className="h-full overflow-y-auto">
              <BuildView
                sessionId={sessionId}
                onBackToPRD={stage >= STAGES.prd ? () => goTo(VIEWS.prd) : null}
              />
            </div>
          )}
        </div>
      </div>
    </ToastProvider>
  );
}

function ViewTab({ label, active, disabled, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`text-xs font-medium transition-colors ${
        active
          ? "text-accent underline underline-offset-4"
          : "text-secondary hover:text-primary"
      } disabled:cursor-not-allowed disabled:opacity-30`}
    >
      {label}
    </button>
  );
}
