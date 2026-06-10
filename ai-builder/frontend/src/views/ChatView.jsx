import { useState } from "react";
import { generatePRD } from "../api/client";
import ChatBubble from "../components/ChatBubble";
import { useChat } from "../hooks/useChat";

export default function ChatView({ sessionId, onPRDReady }) {
  const { messages, loading, readyForPRD, error, submit } = useChat(sessionId);
  const [input, setInput] = useState("");
  const [generatingPRD, setGeneratingPRD] = useState(false);

  const handleSend = () => {
    if (!input.trim()) return;
    submit(input);
    setInput("");
  };

  const handleGeneratePRD = async () => {
    setGeneratingPRD(true);
    try {
      const prd = await generatePRD(sessionId);
      onPRDReady(prd);
    } catch (err) {
      alert(err.message);
    } finally {
      setGeneratingPRD(false);
    }
  };

  return (
    <div className="mx-auto flex h-screen max-w-3xl flex-col px-4 py-6">
      <header className="mb-6">
        <h1 className="text-xl font-semibold">Clarify Agent</h1>
        <p className="text-sm text-secondary">
          Describe tu idea de software y responde las preguntas del agente.
        </p>
      </header>

      <div className="flex-1 space-y-4 overflow-y-auto pb-4">
        {messages.length === 0 && (
          <p className="text-center text-sm text-secondary">
            Ej: &quot;Quiero una app web para gestionar tareas de equipo&quot;
          </p>
        )}
        {messages.map((msg, i) => (
          <ChatBubble key={i} role={msg.role} content={msg.content} />
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="flex items-center gap-2 rounded-lg border border-border bg-surface px-4 py-3 text-sm text-secondary">
              <Spinner /> Pensando...
            </div>
          </div>
        )}
        {error && <p className="text-center text-sm text-error">{error}</p>}
      </div>

      {readyForPRD && (
        <button
          type="button"
          onClick={handleGeneratePRD}
          disabled={generatingPRD}
          className="mb-4 w-full rounded-lg bg-accent py-3 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
        >
          {generatingPRD ? "Generando PRD..." : "Generar PRD →"}
        </button>
      )}

      <div className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
          placeholder="Escribe tu mensaje..."
          disabled={loading}
          className="flex-1 rounded-lg border border-border bg-surface px-4 py-3 text-sm outline-none focus:border-accent"
        />
        <button
          type="button"
          onClick={handleSend}
          disabled={loading || !input.trim()}
          className="rounded-lg bg-accent px-5 py-3 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
        >
          Enviar
        </button>
      </div>
    </div>
  );
}

function Spinner() {
  return (
    <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-accent border-t-transparent" />
  );
}
