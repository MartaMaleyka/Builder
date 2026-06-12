import { useCallback, useEffect, useRef, useState } from "react";
import { getCodeStatus, startCodeGen } from "../api/client";

const POLL_SAFETY_MAX = 200; // stop polling after ~10 min as a safety valve

export function useGeneration(sessionId) {
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [starting, setStarting] = useState(false);
  const startedRef = useRef(false);
  const pollCountRef = useRef(0);

  const kickoff = useCallback(async () => {
    if (startedRef.current) return;
    startedRef.current = true;
    pollCountRef.current = 0;
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

  // Adaptive polling via setTimeout: fast at start, backs off over time.
  // Re-schedules on every result change so it stops automatically when
  // status leaves "in_progress".
  useEffect(() => {
    if (!startedRef.current || !result || result.status !== "in_progress") return;
    if (pollCountRef.current >= POLL_SAFETY_MAX) return;

    const count = pollCountRef.current;
    const delay = count < 4 ? 1000 : count < 12 ? 2000 : 3500;

    const id = setTimeout(async () => {
      pollCountRef.current += 1;
      try {
        const data = await getCodeStatus(sessionId);
        setResult(data);
      } catch (err) {
        setError(err.message);
      }
    }, delay);

    return () => clearTimeout(id);
  }, [sessionId, result]);

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
