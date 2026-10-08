import { RECOVERY_COMMAND, SCENARIOS } from "../lib/formatters.js";
import CopyButton from "./CopyButton.jsx";
import Icon from "./Icons.jsx";
import StatusBadge from "./StatusBadge.jsx";

function Diagram() {
  return (
    <div className="flow" aria-label="Max, the buyer agent, negotiates with Viktor, the seller agent. The wallet guard sits between them and controls payment.">
      <div className="flow-node flow-max"><span className="avatar avatar-sm" aria-hidden="true">M</span><strong>Max</strong><small>Buyer agent</small></div>
      <Icon name="arrow" size={18} className="flow-arrow" />
      <div className="flow-node flow-guard"><span className="guard-ico"><Icon name="shield-check" size={18} /></span><strong>Wallet guard</strong><small>Plain code, no AI</small></div>
      <Icon name="arrow" size={18} className="flow-arrow" />
      <div className="flow-node flow-viktor"><span className="avatar avatar-sm" aria-hidden="true">V</span><strong>Viktor</strong><small>Seller agent</small></div>
    </div>
  );
}

export default function EmptyDealState({ scenario, summary, onRun, launching, disabledReason }) {
  const s = SCENARIOS[scenario] ?? SCENARIOS.honest;
  const terminalOnly = s.terminalOnly;
  return (
    <section className="card empty" aria-labelledby="empty-h">
      <h2 id="empty-h">Start a negotiation</h2>
      <p className="empty-lead">Type a request in plain words, for example "10 flats in Praha 2 under 30,000 CZK". Two agents haggle over the price and a deterministic guard decides whether money may move.</p>

      <Diagram />

      {summary && <p className="empty-request"><Icon name="check" size={13} /> Ready to run: <b>{summary}</b></p>}

      <div className="empty-scenario">
        <div className="empty-scenario-head">
          <span className="scenario-n">{s.n}</span>
          <strong>{s.name}</strong>
          {s.staged && <StatusBadge tone="warning" icon={null} title="Seller behaviour is forced for this demo">STAGED SCENARIO</StatusBadge>}
        </div>
        <p>{s.explain}</p>
      </div>

      {terminalOnly ? (
        <div className="cmd"><code>{RECOVERY_COMMAND}</code><CopyButton text={RECOVERY_COMMAND} label="Copy command" showLabel /></div>
      ) : (
        <div className="empty-actions">
          <button type="button" className="btn btn-primary" onClick={onRun} disabled={launching || !!disabledReason}>
            {launching ? <><Icon name="refresh" size={14} className="spin" /> Starting...</> : <><Icon name="play" size={14} /> Run request</>}
          </button>
          {disabledReason && <span className="hint">{disabledReason}</span>}
        </div>
      )}

      <p className="empty-note"><Icon name="shield" size={14} /> The AI can agree to any price, but it cannot pay. Only the wallet guard can move money.</p>
    </section>
  );
}
