// Thin stub (owner: mais). Wire-up is real; the look is yours.
// Contract: buyer SSE GET /events, POST /tasks, POST /approvals/{deal_id} (see memory/INTERFACES.md).
import { useEffect, useState } from "react";
import VoicePlayback from "./VoicePlayback.jsx";
import { appendEvent, eventKey } from "./eventIdentity.js";

const BUYER = import.meta.env.VITE_BUYER_URL ?? "http://localhost:8000";

const ACTS = [
  ["honest", "Act 1 - The deal"],
  ["con", "Act 2 - The con (STAGED)"],
  ["junk", "Act 4 - The refund (STAGED)"],
];

export default function App() {
  const [events, setEvents] = useState([]);

  useEffect(() => {
    const es = new EventSource(`${BUYER}/events`);
    es.onmessage = (m) => {
      const ev = JSON.parse(m.data);
      setEvents((prev) => appendEvent(prev, ev));
    };
    return () => es.close();
  }, []);

  const start = (demo_mode) =>
    fetch(`${BUYER}/tasks`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ demo_mode }),
    });

  const decide = (dealId, approve) =>
    fetch(`${BUYER}/approvals/${dealId}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ approve }),
    });

  const chat = events.filter((e) => e.type === "negotiation");
  const balances = [...events].reverse().find((e) => e.type === "balances")?.data;
  const pending = events.filter(
    (e) => e.type === "needs_approval" && !events.some((x) => x.deal_id === e.deal_id && ["approved", "blocked"].includes(x.type) && x.id > e.id),
  );
  const simulated = events.some((e) => e.simulated);

  return (
    <main style={{ fontFamily: "system-ui", maxWidth: 960, margin: "0 auto", padding: 16 }}>
      <h1>The Haggle {simulated && <span style={{ background: "#f5a623", padding: "2px 8px", fontSize: 14 }}>SIMULATED MONEY</span>}</h1>
      <p>
        {ACTS.map(([mode, label]) => (
          <button key={mode} onClick={() => start(mode)} style={{ marginRight: 8 }}>{label}</button>
        ))}
      </p>
      <VoicePlayback events={events} buyerUrl={BUYER} />
      {balances && <p>Max: {balances.buyer} tADA · Viktor: {balances.seller} tADA · Escrow: {balances.escrow} tADA</p>}
      {pending.map((e) => (
        <p key={eventKey(e)} style={{ background: "#fff3cd", padding: 8 }}>
          Approve {e.data.price} tADA? ({e.data.reason}){" "}
          <button onClick={() => decide(e.deal_id, true)}>Approve</button>{" "}
          <button onClick={() => decide(e.deal_id, false)}>Decline</button>
        </p>
      ))}
      <section>
        {chat.map((e) => (
          <p key={eventKey(e)} style={{ textAlign: e.data.speaker === "max" ? "left" : "right" }}>
            <b>{e.data.speaker === "max" ? "Max" : "Viktor"}</b>: {e.data.text} {e.staged && <em>(staged)</em>}
            {e.data.backend === "mock" && <small> (scripted{e.data.fallback_reason ? " fallback" : ""})</small>}
          </p>
        ))}
      </section>
      {events.filter((e) => e.type === "delivered" && e.data.source).map((e) => (
        <p key={eventKey(e)}>
          Data: {e.data.source === "apify_cached" ? "CACHED APIFY" : e.data.source === "apify" ? "LIVE APIFY" : "SAMPLE"}
          {e.data.result?.fetched_at && <> · fetched {e.data.result.fetched_at}</>}
        </p>
      ))}
      <h2>Log</h2>
      <ul>
        {events.filter((e) => e.type !== "negotiation").map((e) => (
          <li key={eventKey(e)} style={{ color: e.type === "blocked" ? "red" : undefined, fontWeight: e.type === "blocked" ? 700 : 400 }}>
            {e.type.toUpperCase()} {e.deal_id} {JSON.stringify(e.data).slice(0, 140)}
          </li>
        ))}
      </ul>
    </main>
  );
}
