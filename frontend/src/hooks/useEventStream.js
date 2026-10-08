import { useCallback, useEffect, useRef, useState } from "react";
import { BUYER } from "../api.js";
import { appendEvent } from "../eventIdentity.js";

const GIVE_UP_AFTER = 3; // consecutive failed reconnects before the UI calls the buyer offline

// status: connecting | live | reconnecting | offline. The buyer replays its full history on every
// (re)connect, so events are de-duplicated by (id, ts, deal_id) and nothing is lost across a drop.
export default function useEventStream() {
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState("connecting");
  const [attempt, setAttempt] = useState(0);
  const everLive = useRef(false);

  useEffect(() => {
    let failures = 0;
    const es = new EventSource(`${BUYER}/events`);
    es.onopen = () => { failures = 0; everLive.current = true; setStatus("live"); };
    es.onerror = () => {
      failures += 1;
      setStatus(everLive.current && failures < GIVE_UP_AFTER ? "reconnecting" : "offline");
    };
    es.onmessage = (m) => {
      let ev;
      try { ev = JSON.parse(m.data); } catch { return; }
      setEvents((prev) => appendEvent(prev, ev));
    };
    return () => es.close();
  }, [attempt]);

  const retry = useCallback(() => { setStatus("connecting"); setAttempt((a) => a + 1); }, []);
  return { events, status, retry };
}
