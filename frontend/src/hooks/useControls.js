import { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";

// Operator controls from GET /controls, refreshed when another client changes them or the buyer reconnects.
export default function useControls(events, status) {
  const [controls, setControls] = useState(null);
  const [error, setError] = useState(null);
  const lastChange = [...events].reverse().find((e) => e.type === "controls_updated")?.id ?? 0;

  const refresh = useCallback(
    () => api.controls().then((c) => { setControls(c); setError(null); }).catch((e) => setError(e.message)),
    [],
  );
  useEffect(() => { if (status === "live") refresh(); }, [refresh, lastChange, status]);
  return { controls, error, refresh };
}
