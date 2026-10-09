import Icon from "./Icons.jsx";

// One big box and one button. Nothing runs until you press Run (or Enter); it only speaks up when a request is refused.
export default function RequestComposer({ text, onText, parse, onRun, launching, disabledReason }) {
  const { parsed, checking, error } = parse;
  const ok = parsed?.ok && !checking;
  const blocked = launching || !!disabledReason || !ok;

  return (
    <section className="card" aria-labelledby="request-h">
      <h2 id="request-h" className="card-title">Request</h2>

      <label htmlFor="request-text" className="sr-only">What should Max buy?</label>
      <textarea id="request-text" className="request-text" rows={9} maxLength={500} value={text}
        placeholder="What should Max buy?" onChange={(e) => onText(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); if (!blocked) onRun(); } }} />

      {text.trim() && (error || (parsed && !checking && !parsed.ok)) && (
        <p className="understood is-bad" role="status" aria-live="polite"><Icon name="alert" size={13} /> {error ? "Buyer offline" : parsed.summary}</p>
      )}

      <button type="button" className="btn btn-primary btn-block" onClick={onRun} disabled={blocked} title={disabledReason ?? "Enter"}>
        {launching ? <><Icon name="refresh" size={14} className="spin" /> Starting</> : <><Icon name="play" size={14} /> Run request</>}
      </button>
      {disabledReason && !launching && <p className="hint">{disabledReason}</p>}
    </section>
  );
}
