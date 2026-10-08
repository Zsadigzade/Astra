import { useEffect, useState } from "react";
import { api } from "../api.js";

// Live preview of what the buyer would do with the typed request. Debounced; stale answers are dropped.
export default function useRequestParse(text, enabled) {
  const [state, setState] = useState({ parsed: null, checking: false, error: null });

  useEffect(() => {
    if (!enabled) { setState({ parsed: null, checking: false, error: "offline" }); return undefined; }
    let stale = false;
    setState((s) => ({ ...s, checking: true }));
    const t = setTimeout(() => {
      api.parseRequest(text)
        .then((parsed) => { if (!stale) setState({ parsed, checking: false, error: null }); })
        .catch((e) => { if (!stale) setState({ parsed: null, checking: false, error: e.message }); });
    }, 350);
    return () => { stale = true; clearTimeout(t); };
  }, [text, enabled]);

  return state;
}
