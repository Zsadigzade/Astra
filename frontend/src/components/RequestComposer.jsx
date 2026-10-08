import { EXAMPLES } from "../lib/formatters.js";
import Icon from "./Icons.jsx";

// Plain-language request box with a live "here is what I understood" preview. Nothing runs until you press Run.
export default function RequestComposer({ text, onText, parse, onRun, launching, disabledReason }) {
  const { parsed, checking, error } = parse;
  const ok = parsed?.ok && !checking;
  const blocked = launching || !!disabledReason || !ok;
  const why = disabledReason ?? (!ok && !checking ? (parsed?.summary ?? null) : null);
  const examples = parsed?.examples ?? EXAMPLES;

  return (
    <section className="card" aria-labelledby="request-h">
      <h2 id="request-h" className="card-title">Request</h2>

      <div className="field">
        <label htmlFor="request-text" className="sr-only">What should Max buy?</label>
        <textarea id="request-text" className="request-text" rows={3} maxLength={500} value={text}
          placeholder="What should Max buy? For example: 10 flats in Praha 2 under 30,000 CZK"
          onChange={(e) => onText(e.target.value)}
          onKeyDown={(e) => { if ((e.ctrlKey || e.metaKey) && e.key === "Enter" && !blocked) onRun(); }} />
      </div>

      <div className="chips" aria-label="Examples">
        {examples.map((ex) => (
          <button key={ex} type="button" className="chip-btn" onClick={() => onText(ex)} title={ex}>{ex}</button>
        ))}
      </div>

      <div className={`understood ${ok ? "is-ok" : parsed && !checking ? "is-bad" : ""}`} role="status" aria-live="polite">
        {checking ? (
          <p className="muted"><Icon name="refresh" size={13} className="spin" /> Checking the request...</p>
        ) : error ? (
          <p className="muted"><Icon name="alert" size={13} /> Cannot check the request while the buyer is offline.</p>
        ) : parsed?.ok ? (
          <>
            <p><Icon name="check" size={13} /> <b>Max will buy:</b> {parsed.summary}</p>
            {parsed.notes.map((n) => <p key={n} className="hint">{n}</p>)}
          </>
        ) : parsed ? (
          <p><Icon name="alert" size={13} /> {parsed.summary}</p>
        ) : null}
      </div>

      <button type="button" className="btn btn-primary btn-block" onClick={onRun} disabled={blocked}
        aria-describedby={why ? "run-why" : undefined}>
        {launching ? <><Icon name="refresh" size={14} className="spin" /> Starting...</> : <><Icon name="play" size={14} /> Run request</>}
      </button>
      {why && !launching && <p id="run-why" className="hint">{disabledReason ?? "Fix the request above to run it."}</p>}
    </section>
  );
}
