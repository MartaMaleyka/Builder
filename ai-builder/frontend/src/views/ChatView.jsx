import { useEffect, useRef, useState } from "react";
import { generatePRD } from "../api/client";
import ChatBubble, { AgentAvatar } from "../components/ChatBubble";
import { useToast } from "../context/ToastContext";
import { useChat } from "../hooks/useChat";

const SUGGESTIONS = [
  "App de inventario para una tienda física",
  "CRM para seguimiento de clientes y ventas",
  "Dashboard administrativo para un restaurante",
  "API REST para una plataforma de cursos",
];

export default function ChatView({ sessionId, onPRDReady }) {
  const { messages, loading, readyForPRD, error, submit } = useChat(sessionId);
  const [input, setInput] = useState("");
  const [generatingPRD, setGeneratingPRD] = useState(false);
  const prdAbortRef = useRef(null);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  const { show: showToast } = useToast();

  // Scroll to bottom on every new message or typing indicator change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Auto-resize textarea up to ~160px
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [input]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || loading || readyForPRD) return;
    submit(trimmed);
    setInput("");
  };

  const handleSuggestion = (text) => {
    setInput(text);
    textareaRef.current?.focus();
  };

  const handleGeneratePRD = async () => {
    setGeneratingPRD(true);
    prdAbortRef.current = new AbortController();
    try {
      const prd = await generatePRD(sessionId, prdAbortRef.current.signal);
      onPRDReady(prd);
    } catch (err) {
      if (err.name === "AbortError") return;
      showToast(err.message || "Error generando el PRD", "error");
    } finally {
      setGeneratingPRD(false);
    }
  };

  // Show suggestion chips only while just the welcome message is visible
  const showSuggestions = messages.length === 1 && !loading;

  return (
    <div className="flex h-full flex-col">
      {/* ── Messages ───────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-2xl space-y-5 px-4 py-6">
          {messages.map((msg) => (
            <ChatBubble key={msg.id} role={msg.role} content={msg.content} ts={msg.ts} />
          ))}

          {/* Suggestion chips appear below the welcome message */}
          {showSuggestions && (
            <div className="flex flex-wrap gap-2 pl-10">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => handleSuggestion(s)}
                  className="rounded-full border border-border px-3 py-1.5 text-xs text-secondary transition-colors hover:border-accent hover:text-accent"
                >
                  {s}
                </button>
              ))}
            </div>
          )}

          {/* Typing indicator */}
          {loading && (
            <div className="flex items-start gap-3">
              <AgentAvatar />
              <div className="rounded-2xl rounded-tl-sm border border-border bg-surface px-4 py-3.5">
                <TypingDots />
              </div>
            </div>
          )}

          {error && (
            <p className="text-center text-xs text-error">{error}</p>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* ── Bottom bar ─────────────────────────────────── */}
      <div className="shrink-0 border-t border-border bg-bg">
        <div className="mx-auto max-w-2xl px-4 py-4">
          {readyForPRD ? (
            <ReadyBanner onGenerate={handleGeneratePRD} generating={generatingPRD} />
          ) : (
            <InputRow
              textareaRef={textareaRef}
              input={input}
              setInput={setInput}
              loading={loading}
              onSend={handleSend}
            />
          )}
          <p className="mt-2 text-center text-[10px] text-secondary">
            Enter para enviar · Shift+Enter para nueva línea
          </p>
        </div>
      </div>
    </div>
  );
}

/* ── Sub-components ──────────────────────────────────── */

function ReadyBanner({ onGenerate, generating }) {
  return (
    <div className="rounded-xl border border-accent/30 bg-accent/5 p-4">
      <p className="mb-0.5 text-sm font-semibold text-primary">
        Contexto completo
      </p>
      <p className="mb-3 text-xs text-secondary">
        El agente tiene todo lo necesario para generar el PRD. Puedes revisarlo
        y editarlo antes de construir.
      </p>
      <button
        type="button"
        onClick={onGenerate}
        disabled={generating}
        className="w-full rounded-lg bg-accent py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
      >
        {generating ? (
          <span className="flex items-center justify-center gap-2">
            <Spinner /> Generando PRD...
          </span>
        ) : (
          "Generar PRD →"
        )}
      </button>
    </div>
  );
}

function InputRow({ textareaRef, input, setInput, loading, onSend }) {
  return (
    <div className="flex items-end gap-2 rounded-xl border border-border bg-surface px-3 py-2 transition-colors focus-within:border-accent">
      <textarea
        ref={textareaRef}
        rows={1}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            onSend();
          }
        }}
        placeholder="Describe tu idea o responde la pregunta..."
        disabled={loading}
        className="flex-1 resize-none bg-transparent py-1 text-sm text-primary outline-none placeholder:text-secondary"
      />
      <button
        type="button"
        onClick={onSend}
        disabled={loading || !input.trim()}
        className="mb-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent text-white transition-opacity hover:opacity-90 disabled:opacity-40"
        aria-label="Enviar"
      >
        <SendIcon />
      </button>
    </div>
  );
}

function TypingDots() {
  return (
    <div className="flex items-center gap-1.5">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-2 w-2 rounded-full bg-secondary animate-bounce"
          style={{ animationDelay: `${i * 0.18}s` }}
        />
      ))}
    </div>
  );
}

function Spinner() {
  return (
    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
  );
}

function SendIcon() {
  return (
    <svg
      width="15"
      height="15"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="22" y1="2" x2="11" y2="13" />
      <polygon points="22 2 15 22 11 13 2 9 22 2" />
    </svg>
  );
}
