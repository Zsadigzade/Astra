import { RECOVERY_COMMAND, SCENARIOS } from "../lib/formatters.js";
import CopyButton from "./CopyButton.jsx";
import Ghost from "./Ghost.jsx";
import Icon from "./Icons.jsx";
import StatusBadge from "./StatusBadge.jsx";

// Before a request is given the ghosts watch your cursor. Once you press Run they stop and start to think.
function Side({ who, busy, tracking, name, role }) {
  return (
    <div className={`ghost-side ghost-side-${who}`}>
      <div className="ghost-above" />
      <Ghost who={who} mood={busy ? "thinking" : "idle"} tracking={tracking && !busy} />
      <div className="ghost-name"><b>{name}</b><span>{role}</span></div>
    </div>
  );
}

export default function EmptyDealState({ tracking = true, scenario, text, onText, parse, onRun, launching, disabledReason }) {
  const s = SCENARIOS[scenario] ?? SCENARIOS.honest;
  const { parsed, checking, error } = parse;
  const blocked = launching || !!disabledReason || checking || !parsed?.ok;
  // Say something only when there is something to say: a refused request, or the buyer being offline.
  const problem = !text.trim() ? null : error ? "The buyer service is offline." : parsed && !checking && !parsed.ok ? parsed.summary : null;
  return (
    <section className="empty-page" aria-labelledby="empty-h">
      <div className="stage stage-hero">
        <Side who="max" busy={launching} tracking={tracking} name="Max" role="buyer" />
        <div className="stage-mid hero-mid">
          <span className="guard-ico"><Icon name="shield-check" size={20} /></span>
          <h2 id="empty-h">Run a request</h2>
          <p className="empty-lead">Max negotiates. The guard pays. Viktor delivers.</p>
          {s.staged && <StatusBadge tone="warning" icon={null} title={s.explain}>{s.name.toUpperCase()} · STAGED</StatusBadge>}
          {s.terminalOnly && <div className="cmd"><code>{RECOVERY_COMMAND}</code><CopyButton text={RECOVERY_COMMAND} label="Copy command" showLabel /></div>}
        </div>
        <Side who="viktor" busy={launching} tracking={tracking} name="Viktor" role="seller" />
      </div>

      {!s.terminalOnly && (
        <form className="hero-ask" onSubmit={(ev) => { ev.preventDefault(); if (!blocked) onRun(); }}>
          <label htmlFor="hero-text" className="sr-only">What should Max buy?</label>
          <textarea id="hero-text" className="hero-text" rows={4} maxLength={500} autoFocus value={text}
            placeholder="What should Max buy?" onChange={(ev) => onText(ev.target.value)}
            onKeyDown={(ev) => { if (ev.key === "Enter" && !ev.shiftKey && !ev.nativeEvent.isComposing) { ev.preventDefault(); if (!blocked) onRun(); } }} />
          <button type="submit" className="btn btn-primary hero-run" disabled={blocked}>
            {launching ? <><Icon name="refresh" size={16} className="spin" /> Starting</> : <><Icon name="play" size={16} /> Run request</>}
          </button>
          {(problem || (disabledReason && text.trim())) && <p className="hint hero-hint" role="status">{problem ?? disabledReason}</p>}
        </form>
      )}
    </section>
  );
}
