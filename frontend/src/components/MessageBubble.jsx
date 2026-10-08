import { PROVENANCE } from "../lib/eventLabels.js";
import { clock, tada } from "../lib/formatters.js";
import StatusBadge from "./StatusBadge.jsx";

const NAME = { max: "Max", viktor: "Viktor" };
const ACTION = { counter: "Counter", accept: "Accept", walk: "Walk away", open: "Opening ask" };

export default function MessageBubble({ e, round }) {
  const who = e.data.speaker === "max" ? "max" : "viktor";
  const prov = e.provenance && PROVENANCE[e.provenance];
  return (
    <article className={`msg msg-${who}`} aria-label={`${NAME[who]}, round ${round}`}>
      <div className="msg-card">
        <header className="msg-meta">
          <strong>{NAME[who]}</strong>
          <span>Round {round}</span>
          <time dateTime={new Date(e.ts * 1000).toISOString()}>{clock(e.ts)}</time>
          {prov && e.provenance !== "scripted" && <StatusBadge tone={prov.tone} icon={null} title={prov.hint}>{prov.label}</StatusBadge>}
        </header>
        <p>{e.data.text}</p>
        {(e.data.price > 0 || e.data.action) && (
          <footer className="msg-foot">
            <span className="msg-action">{ACTION[e.data.action] ?? e.data.action}</span>
            {e.data.price > 0 && <span className="price-chip num">{tada(e.data.price, 1)}</span>}
          </footer>
        )}
      </div>
    </article>
  );
}
