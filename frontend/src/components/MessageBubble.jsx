import { PROVENANCE } from "../lib/eventLabels.js";
import { clock, tada } from "../lib/formatters.js";

const NAME = { max: "Max", viktor: "Viktor" };
const ACTION = { counter: "Counter", accept: "Accepted", walk: "Walked away", open: "Ask" };

// What writes each agent is shown once beside the ghosts. A line only carries a tag when it is exceptional:
// the model call failed (scripted fallback) or the wallet guard spoke.
const EXCEPTIONAL = new Set(["fallback", "guard"]);

export default function MessageBubble({ e, round }) {
  const who = e.data.speaker === "max" ? "max" : "viktor";
  const note = EXCEPTIONAL.has(e.provenance) ? PROVENANCE[e.provenance] : null;
  const price = e.data.price > 0;
  return (
    <li className={`bubble-row ${who}`}>
      <article className="bubble" aria-label={`${NAME[who]}, round ${round}`}>
        <p>{e.data.text}</p>
        <footer className="bubble-foot">
          {(price || e.data.action === "walk") && (
            <span className="bubble-quote">{ACTION[e.data.action] ?? e.data.action}{price && <b className="num"> {tada(e.data.price, 1)}</b>}</span>
          )}
          {note && <span className={`prov prov-${note.tone}`} title={note.hint}>{note.label}</span>}
          <span className="bubble-meta">
            {NAME[who]} · R{round} · <time dateTime={new Date(e.ts * 1000).toISOString()}>{clock(e.ts)}</time>
          </span>
        </footer>
      </article>
    </li>
  );
}
