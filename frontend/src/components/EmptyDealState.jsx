import { RECOVERY_COMMAND, SCENARIOS } from "../lib/formatters.js";
import CopyButton from "./CopyButton.jsx";
import Icon from "./Icons.jsx";
import StatusBadge from "./StatusBadge.jsx";

function Diagram() {
  return (
    <div className="flow" aria-label="Max, the buyer agent, negotiates with Viktor, the seller agent. The wallet guard controls payment.">
      <div className="flow-node flow-max"><span className="avatar avatar-sm" aria-hidden="true">M</span><strong>Max</strong><small>buyer</small></div>
      <Icon name="arrow" size={18} className="flow-arrow" />
      <div className="flow-node flow-guard"><span className="guard-ico"><Icon name="shield-check" size={18} /></span><strong>Guard</strong><small>plain code</small></div>
      <Icon name="arrow" size={18} className="flow-arrow" />
      <div className="flow-node flow-viktor"><span className="avatar avatar-sm" aria-hidden="true">V</span><strong>Viktor</strong><small>seller</small></div>
    </div>
  );
}

export default function EmptyDealState({ scenario, summary, onRun, launching, disabledReason }) {
  const s = SCENARIOS[scenario] ?? SCENARIOS.honest;
  return (
    <section className="card empty" aria-labelledby="empty-h">
      <h2 id="empty-h">Run a request</h2>
      <p className="empty-lead">Max negotiates. The guard pays. Viktor delivers.</p>
      <Diagram />
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
