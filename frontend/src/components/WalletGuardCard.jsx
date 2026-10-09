import { usd } from "../lib/formatters.js";
import Icon from "./Icons.jsx";

const ICON = {
  ready: "shield", checking: "shield-clock", safe: "shield-check", approval: "shield-clock", blocked: "shield-alert",
  escrow: "shield-check", verify_failed: "shield-alert", release_scheduled: "shield-check", released: "shield-check",
  refunded: "refresh", no_payment: "shield",
};

function Tip({ text, children }) {
  return (
    <span className="tip" tabIndex={0}>
      {children}
      <span role="tooltip" className="tip-body">{text}</span>
    </span>
  );
}

// Where the price sits against the approval line and the hard cap. Real values only.
function PriceRail({ price, approval, cap }) {
  if (cap == null || approval == null) return null;
  const max = Math.max(cap * 1.25, (price ?? 0) * 1.08, 1);
  const pos = (v) => `${Math.min(100, (v / max) * 100)}%`;
  const zone = price == null ? "none" : price > cap ? "over" : price > approval ? "approval" : "auto";
  return (
    <div className="price-rail" role="img"
      aria-label={price == null ? `Approval line $${approval}, hard cap $${cap}` : `Price $${price} against approval line $${approval} and hard cap $${cap}`}>
      <div className="rail-track">
        <span className="rail-zone rail-auto" style={{ width: pos(approval) }} />
        <span className="rail-zone rail-approval" style={{ left: pos(approval), width: `calc(${pos(cap)} - ${pos(approval)})` }} />
        <span className="rail-zone rail-over" style={{ left: pos(cap), right: 0 }} />
        {price != null && <span className={`rail-dot rail-dot-${zone}`} style={{ left: pos(price) }} />}
      </div>
      <div className="rail-legend">
        <span>Auto to <b className="num">{approval}</b></span>
        <span>Human to <b className="num">{cap}</b></span>
        <span>Blocked above</span>
      </div>
    </div>
  );
}

// Two sections: Wallet policy (what the guard enforces and its current verdict) and Balances.
// The verdict sentence is left to the deal header once a deal has ended, so the same result is not said twice.
export default function WalletGuardCard({ view, controls, only = "all" }) {
  const g = view.guard;
  const cap = controls?.guard.cap;
  const approval = controls?.guard.approval_over;
  const b = view.balances;
  const price = view.agreed ?? view.prices.current;

  const showPolicy = only === "all" || only === "policy";
  const showBalances = only === "all" || only === "balances";
  return (
    <>
      {showPolicy && <section className="card guard" aria-labelledby="guard-h">
        <h2 id="guard-h" className="card-title">Wallet policy</h2>
        <div className={`guard-status guard-${g.tone}`} role="status">
          <span className="guard-ico"><Icon name={ICON[g.status]} size={18} /></span>
          <div>
            <strong>{g.title}</strong>
            {!view.terminal && <p>{g.message}</p>}
          </div>
        </div>
        <PriceRail price={price} approval={approval} cap={cap} />
        <dl className="rows">
          <div><dt><Tip text="No price above this is ever paid, whatever the AI agreed to. Enforced in code.">Hard cap</Tip></dt><dd className="num">{usd(cap, 1)}</dd></div>
          <div><dt><Tip text="Prices up to this amount are paid without asking a human.">Auto-approve to</Tip></dt><dd className="num">{usd(approval, 1)}</dd></div>
          <div><dt>Task budget</dt><dd className="num">{usd(view.task?.budget, 1)}</dd></div>
        </dl>
      </section>}

      {showBalances && <section className="card" aria-labelledby="bal-h">
        <h2 id="bal-h" className="card-title">Balances</h2>
        {b ? (
          <dl className="rows">
            <div><dt>Max</dt><dd className="num">{usd(b.buyer, 1)}</dd></div>
            <div><dt><Tip text="Funds locked until the delivery is verified.">Escrow</Tip></dt><dd className="num">{usd(b.escrow, 1)}</dd></div>
            <div><dt>Viktor</dt><dd className="num">{usd(b.seller, 1)}</dd></div>
          </dl>
        ) : <p className="hint">Appear after the first payment step.</p>}
      </section>}
    </>
  );
}
