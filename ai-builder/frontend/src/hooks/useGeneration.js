import { useCallback, useEffect, useRef, useState } from "react";
import { getCodeStatus, startCodeGen } from "../api/client";

export function useGeneration(sessionId) {
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [starting, setStarting] = useState(false);
  const startedRef = useRef(false);

  const kickoff = useCallback(async () => {
    if (startedRef.current) return;
    startedRef.current = true;
    setStarting(true);
    setError(null);
    try {
      await startCodeGen(sessionId);
      const status = await getCodeStatus(sessionId);
      setResult(status);
    } catch (err) {
      startedRef.current = false;
      setError(err.message);
    } finally {
      setStarting(false);
    }
  }, [sessionId]);

  useEffect(() => {
    kickoff();
  }, [kickoff]);

  useEffect(() => {
    if (!startedRef.current || !result || result.status !== "in_progress") return;

    const id = setInterval(async () => {
      try {
        const data = await getCodeStatus(sessionId);
        setResult(data);
      } catch (err) {
        setError(err.message);
      }
    }, 2000);

    return () => clearInterval(id);
  }, [sessionId, result?.status]);

  const retry = useCallback(async () => {
    startedRef.current = false;
    setResult(null);
    setError(null);
    await kickoff();
  }, [kickoff]);

  const doneCount = result?.modules?.filter((m) => m.status === "done").length ?? 0;
  const totalCount = result?.modules?.length ?? 0;
  const progress = totalCount ? Math.round((doneCount / totalCount) * 100) : 0;

  return { result, error, starting, progress, retry };
}
