import { useEffect, useState } from "react";

// Reachability probe for a service that sends no CORS headers: a no-cors request resolves
// (opaque) when the server answers and rejects when nothing is listening. Says nothing about health.
export default function useServiceHealth(url, intervalMs = 5000) {
  const [state, setState] = useState("unknown"); // unknown | online | offline
  useEffect(() => {
    let stop = false;
    const probe = async () => {
      try {
        await fetch(`${url}/health`, { mode: "no-cors", cache: "no-store" });
        if (!stop) setState("online");
      } catch {
        if (!stop) setState("offline");
      }
    };
    probe();
    const t = setInterval(probe, intervalMs);
    return () => { stop = true; clearInterval(t); };
  }, [url, intervalMs]);
  return state;
}
