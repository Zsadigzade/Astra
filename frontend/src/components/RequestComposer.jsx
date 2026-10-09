import { EXAMPLES } from "../lib/formatters.js";
import Icon from "./Icons.jsx";

const brief = (job) => `${job.count} flat${job.count === 1 ? "" : "s"} · ${job.district} · up to ${job.max_price_czk.toLocaleString("en-US")} CZK`;

// Plain-language request with a one-line "understood" preview. Nothing runs until you press Run (or Ctrl+Enter).
export default function RequestComposer({ text, onText, parse, onRun, launching, disabledReason }) {
  const { parsed, checking, error } = parse;
  const ok = parsed?.ok && !checking;
  const blocked = launching || !!disabledReason || !ok;
  const examples = parsed?.examples ?? EXAMPLES;

  return (
    <section className="card" aria-labelledby="request-h">
      <h2 id="request-h" className="card-title">Request</h2>

      <label htmlFor="request-text" className="sr-only">What should Max buy?</label>
      <textarea id="request-text" className="request-text" rows={5} maxLength={500} value={text}
        placeholder="10 flats in Praha 2 under 30,000 CZK" onChange={(e) => onText(e.target.value)}
        onKeyDown={(e) => { if ((e.ctrlKey || e.metaKey) && e.key === "Enter" && !blocked) onRun(); }} />

      <div className="chips" aria-label="Examples">
        {examples.map((ex) => <button key={ex} type="button" className="chip-btn" onClick={() => onText(ex)} title={ex}>{ex}</button>)}
      </div>

      <div className={`understood ${ok ? "is-ok" : parsed && !checking ? "is-bad" : ""}`} role="status" aria-live="polite">
        {checking ? <p className="muted"><Icon name="refresh" size={13} className="spin" /> Checking</p>
          : error ? <p className="muted"><Icon name="alert" size={13} /> Buyer offline</p>
          : parsed?.ok ? (
            <p><Icon name="check" size={13} /> {brief(parsed.job)}
              {parsed.notes.length > 0 && <span className="defaults" title={parsed.notes.join(" ")}> · {parsed.notes.length} default{parsed.notes.length > 1 ? "s" : ""}</span>}</p>
          ) : parsed ? <p><Icon name="alert" size={13} /> {parsed.summary}</p> : null}
      </div>

      <button type="button" className="btn btn-primary btn-block" onClick={onRun} disabled={blocked} title={disabledReason ?? "Ctrl+Enter"}>
        {launching ? <><Icon name="refresh" size={14} className="spin" /> Starting</> : <><Icon name="play" size={14} /> Run request</>}
      </button>
      {disabledReason && !launching && <p className="hint">{disabledReason}</p>}
    </section>
  );
}
