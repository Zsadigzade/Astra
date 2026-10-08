import { useEffect, useState } from "react";
import { api } from "../api.js";
import Icon from "./Icons.jsx";

function Range({ id, label, value, min, max, step, unit = "", onChange, hint }) {
  return (
    <div className="field">
      <label htmlFor={id}><span>{label}</span><output htmlFor={id} className="num">{value}{unit}</output></label>
      <input id={id} type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(Number(e.target.value))} />
      {hint && <small>{hint}</small>}
    </div>
  );
}

// Run options for the next task plus runtime guard limits (tighten-only; the server enforces the ceiling).
export default function AgentLimits({ controls, options, onOptions, onChanged }) {
  const [draft, setDraft] = useState(null);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);

  const server = controls && { cap: controls.guard.cap, approval: controls.guard.approval_over, rounds: controls.max_rounds };
  const dirty = !!(draft && server && (draft.cap !== server.cap || draft.approval !== server.approval || draft.rounds !== server.rounds));
  useEffect(() => { if (server && !dirty) setDraft(server); }, [controls]); // eslint-disable-line react-hooks/exhaustive-deps

  const save = async () => {
    setSaving(true);
    setMsg(null);
    try {
      await api.updateControls({ guard_cap: draft.cap, guard_approval_over: draft.approval, max_rounds: draft.rounds });
      await onChanged();
      setMsg({ tone: "success", text: "Limits applied to new deals." });
    } catch (e) {
      setMsg({ tone: "danger", text: e.message });
    } finally { setSaving(false); }
  };

  const set = (patch) => onOptions({ ...options, ...patch });
  const ceiling = controls?.guard.cap_ceiling;

  return (
    <details className="card disclosure">
      <summary><span className="card-title">Run options and limits</span><Icon name="chevron" size={14} className="chev" /></summary>

      <div className="grid2">
        <div className="field"><label htmlFor="opt-budget">Task budget (tADA)</label>
          <input id="opt-budget" type="number" min="1" step="1" value={options.budget}
            onChange={(e) => set({ budget: Math.max(1, Number(e.target.value) || 1) })} /></div>
        <div className="field"><label htmlFor="opt-count">Flats wanted</label>
          <input id="opt-count" type="number" min="1" max="50" value={options.count}
            onChange={(e) => set({ count: Math.max(1, Number(e.target.value) || 1) })} /></div>
        <div className="field span2"><label htmlFor="opt-rent">Max rent (CZK / month)</label>
          <input id="opt-rent" type="number" min="1000" step="500" value={options.maxRent}
            onChange={(e) => set({ maxRent: Math.max(1000, Number(e.target.value) || 1000) })} /></div>
      </div>

      {!controls || !draft ? <p className="hint">Guard limits load once the buyer is online.</p> : (
        <>
          <Range id="lim-cap" label="Hard spending cap" unit=" tADA" min={0.5} max={ceiling} step={0.5} value={draft.cap}
            onChange={(cap) => setDraft((d) => ({ ...d, cap, approval: Math.min(d.approval, cap) }))}
            hint={`Above this, payment is blocked. The server ceiling is ${ceiling} tADA; the dashboard can only tighten it.`} />
          <Range id="lim-approval" label="Automatic approval up to" unit=" tADA" min={0.5} max={draft.cap} step={0.5}
            value={Math.min(draft.approval, draft.cap)} onChange={(approval) => setDraft((d) => ({ ...d, approval }))}
            hint="Above this a human must approve. No answer in 5 minutes declines." />
          <Range id="lim-rounds" label="Max negotiation rounds" min={1} max={controls.max_rounds_ceiling} step={1} value={draft.rounds}
            onChange={(rounds) => setDraft((d) => ({ ...d, rounds }))} />
          <div className="row">
            <button type="button" className="btn btn-sm btn-primary" onClick={save} disabled={!dirty || saving}>{saving ? "Applying..." : "Apply limits"}</button>
            <button type="button" className="btn btn-sm" onClick={() => setDraft(server)} disabled={!dirty || saving}>Reset</button>
          </div>
          {msg && <p className={`note note-${msg.tone}`} role="status">{msg.text}</p>}
        </>
      )}
    </details>
  );
}
