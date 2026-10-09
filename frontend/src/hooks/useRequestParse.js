import { useEffect, useState } from "react";
import { api } from "../api.js";

const RETRY_MS = 1500;

// Live preview of what the buyer would do with the typed request. Debounced; stale answers are dropped.
// A failed check (buyer still starting, brief network blip) retries by itself instead of sticking.
export default function useRequestParse(text, enabled) {
  const [state, setState] = useState({ parsed: null, checking: false, error: null });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!enabled) { setState({ parsed: null, checking: false, error: "offline" }); return undefined; }
    let stale = false;
    let retry;
    setState((s) => ({ ...s, checking: true }));
    const t = setTimeout(() => {
      api.parseRequest(text)
        .then((parsed) => { if (!stale) setState({ parsed, checking: false, error: null }); })
        .catch((e) => {
          if (stale) return;
          setState({ parsed: null, checking: false, error: e.message });
          retry = setTimeout(() => setAttempt((n) => n + 1), RETRY_MS);
        });
    }, 350);
    return () => { stale = true; clearTimeout(t); clearTimeout(retry); };
  }, [text, enabled, attempt]);

  return state;
}
