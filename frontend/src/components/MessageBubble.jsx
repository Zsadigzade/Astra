import { PROVENANCE } from "../lib/eventLabels.js";
import { clock, usd } from "../lib/formatters.js";

const NAME = { max: "Max", viktor: "Viktor" };
const ACTION = { counter: "Counter", accept: "Accepted", walk: "Walked away", open: "Asks" };

// What writes each agent is shown once beside the ghosts. A line only carries a tag when it is exceptional:
// the model call failed (scripted fallback) or the wallet guard spoke.
const EXCEPTIONAL = new Set(["fallback", "guard"]);

// A flat message row: avatar, name and time, the text, and the price as one quiet line. No box around it.
export default function MessageBubble({ e, round }) {
  const who = e.data.speaker === "max" ? "max" : "viktor";
  const note = EXCEPTIONAL.has(e.provenance) ? PROVENANCE[e.provenance] : null;
  const price = e.data.price > 0;
  return (
    <li className={`msg msg-${who}`}>
      <span className="msg-avatar" aria-hidden="true">{NAME[who][0]}</span>
      <article className="msg-body" aria-label={`${NAME[who]}, round ${round}`}>
        <header className="msg-head">
          <b>{NAME[who]}</b>
          <span>R{round}</span>
          <time dateTime={new Date(e.ts * 1000).toISOString()}>{clock(e.ts)}</time>
          {note && <span className={`prov prov-${note.tone}`} title={note.hint}>{note.label}</span>}
        </header>
        <p className="msg-text">{e.data.text}</p>
        {(price || e.data.action === "walk") && (
          <p className="msg-quote">{ACTION[e.data.action] ?? e.data.action}{price && <b className="num">{usd(e.data.price, 1)}</b>}</p>
        )}
      </article>
    </li>
  );
}
