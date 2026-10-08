import { tada } from "../lib/formatters.js";
import StatusBadge from "./StatusBadge.jsx";

export default function UsageSummary({ view, budget }) {
  const u = view.usage;
  const spent = u.released + u.locked;
  const pct = budget > 0 ? Math.min(100, (spent / budget) * 100) : 0;

  return (
    <section className="card" aria-labelledby="usage-h">
      <h2 id="usage-h" className="card-title">Usage</h2>

      <div className="progress-head">
        <span>Committed</span>
        <strong className="num">{tada(spent, 1)} <small>of {tada(budget, 1)}</small></strong>
      </div>
      <div className="progress" role="progressbar" aria-label="Budget committed" aria-valuemin={0} aria-valuemax={budget} aria-valuenow={spent}>
        <div className={`progress-fill ${spent > budget ? "is-over" : ""}`} style={{ width: `${pct}%` }} />
      </div>

      <dl className="rows">
        <div><dt>Task budget</dt><dd className="num">{tada(budget, 1)}</dd></div>
        <div><dt>Agreed amount</dt><dd className="num">{tada(view.agreed, 1)}</dd></div>
        <div><dt>Released</dt><dd className="num">{tada(u.released, 1)}</dd></div>
        <div><dt>In escrow</dt><dd className="num">{tada(u.locked, 1)}</dd></div>
        <div><dt>Refunded</dt><dd className="num">{tada(u.refunded, 1)}</dd></div>
      </dl>

      {u.lines > 0 && (
        <div className="usage-agents">
          <span className="muted">Max</span>
          {u.codex > 0 && <StatusBadge tone="info" icon={null}>{u.codex} Codex subscription</StatusBadge>}
          {u.scripted - u.fallback > 0 && <StatusBadge icon={null}>{u.scripted - u.fallback} scripted</StatusBadge>}
          {u.fallback > 0 && <StatusBadge tone="warning" icon={null} title="The model call failed; a scripted line was used">{u.fallback} fallback</StatusBadge>}
          {u.voice > 0 && <StatusBadge icon={null}>{u.voice} voiced</StatusBadge>}
        </div>
      )}
    </section>
  );
}
