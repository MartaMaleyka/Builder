import { useCallback, useState } from "react";
import { sendMessage } from "../api/client";

export function useChat(sessionId) {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [readyForPRD, setReadyForPRD] = useState(false);
  const [error, setError] = useState(null);

  const submit = useCallback(
    async (text) => {
      const trimmed = text.trim();
      if (!trimmed || loading) return;

      setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
      setLoading(true);
      setError(null);

      try {
        const res = await sendMessage(sessionId, trimmed);
        const assistantText = res.needs_more_info
          ? res.questions.join("\n")
          : "Contexto listo. Ya tengo suficiente información para generar el PRD.";

        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: assistantText },
        ]);
        setReadyForPRD(!res.needs_more_info);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    },
    [sessionId, loading]
  );

  return { messages, loading, readyForPRD, error, submit };
}
