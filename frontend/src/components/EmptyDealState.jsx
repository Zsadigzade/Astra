import { RECOVERY_COMMAND, SCENARIOS } from "../lib/formatters.js";
import CopyButton from "./CopyButton.jsx";
import Ghost from "./Ghost.jsx";
import Icon from "./Icons.jsx";
import StatusBadge from "./StatusBadge.jsx";

// Before a request is given the ghosts watch your cursor. Once you press Run they stop and start to think.
function Hero({ busy, tracking }) {
  const mood = busy ? "thinking" : "idle";
  return (
    <div className="hero" role="group" aria-label="Max the buyer and Viktor the seller, with the wallet guard between them">
      <div className="hero-side">
        <Ghost who="max" mood={mood} tracking={tracking && !busy} />
        <b>Max</b><span>buyer</span>
      </div>
      <div className="hero-guard">
        <span className="guard-ico"><Icon name="shield-check" size={20} /></span>
        <b>Guard</b><span>plain code</span>
      </div>
      <div className="hero-side">
        <Ghost who="viktor" mood={mood} tracking={tracking && !busy} />
        <b>Viktor</b><span>seller</span>
      </div>
    </div>
  );
}

export default function EmptyDealState({ tracking = true, scenario, summary, onRun, launching, disabledReason }) {
  const s = SCENARIOS[scenario] ?? SCENARIOS.honest;
  return (
    <section className="card empty" aria-labelledby="empty-h">
      <h2 id="empty-h">Run a request</h2>
      <p className="empty-lead">Max negotiates. The guard pays. Viktor delivers.</p>
      <Hero busy={launching} tracking={tracking} />
      {summary && <p className="empty-request"><Icon name="check" size={13} /> {summary}</p>}
      {s.staged && <StatusBadge tone="warning" icon={null} title={s.explain}>{s.name.toUpperCase()} · STAGED</StatusBadge>}
      {s.terminalOnly ? (
        <div className="cmd"><code>{RECOVERY_COMMAND}</code><CopyButton text={RECOVERY_COMMAND} label="Copy command" showLabel /></div>
      ) : (
        <div className="empty-actions">
          <button type="button" className="btn btn-primary" onClick={onRun} disabled={launching || !!disabledReason}>
            {launching ? <><Icon name="refresh" size={14} className="spin" /> Starting</> : <><Icon name="play" size={14} /> Run request</>}
          </button>
          {disabledReason && <span className="hint">{disabledReason}</span>}
        </div>
      )}
      <p className="empty-note"><Icon name="shield" size={14} /> The AI can agree to any price. Only the guard can pay.</p>
    </section>
  );
}
