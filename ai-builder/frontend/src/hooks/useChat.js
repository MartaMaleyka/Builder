import { useCallback, useRef, useState } from "react";
import { sendMessage } from "../api/client";

const WELCOME = {
  id: "welcome",
  role: "assistant",
  content:
    "¡Hola! Soy tu arquitecto de software AI.\n\nCuéntame qué tienes en mente — puede ser algo como \"quiero una app para gestionar el inventario de mi tienda\" o \"necesito un dashboard para mi equipo de ventas\".\n\n¿Qué proyecto quieres construir?",
  ts: Date.now(),
};

export function useChat(sessionId) {
  const [messages, setMessages] = useState([WELCOME]);
  const [loading, setLoading] = useState(false);
  const [readyForPRD, setReadyForPRD] = useState(false);
  const [error, setError] = useState(null);
  const abortRef = useRef(null);

  const submit = useCallback(
    async (text) => {
      const trimmed = text.trim();
      if (!trimmed || loading) return;

      if (abortRef.current) abortRef.current.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: "user", content: trimmed, ts: Date.now() },
      ]);
      setLoading(true);
      setError(null);

      try {
        const res = await sendMessage(sessionId, trimmed, controller.signal);
        const assistantText = res.needs_more_info
          ? res.questions.join("\n")
          : "¡Perfecto! Ya tengo todo el contexto que necesito para armar tu documento de requerimientos.\n\nPuedes generar el PRD cuando quieras.";

        setMessages((prev) => [
          ...prev,
          { id: crypto.randomUUID(), role: "assistant", content: assistantText, ts: Date.now() },
        ]);
        setReadyForPRD(!res.needs_more_info);
      } catch (err) {
        if (err.name === "AbortError") return;
        setError(err.message);
      } finally {
        setLoading(false);
      }
    },
    [sessionId, loading]
  );

  return { messages, loading, readyForPRD, error, submit };
}
