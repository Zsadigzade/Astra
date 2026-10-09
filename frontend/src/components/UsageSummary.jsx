import { usd } from "../lib/formatters.js";

// Plain aligned label/value rows. Task figures first; the rest are totals across every deal in the ledger.
export default function UsageSummary({ view, budget }) {
  const u = view.usage;
  return (
    <section className="card" aria-labelledby="usage-h">
      <h2 id="usage-h" className="card-title">Usage</h2>
      <dl className="rows">
        <div><dt>Budget</dt><dd className="num">{usd(budget, 1)}</dd></div>
        <div><dt>Agreed</dt><dd className="num">{usd(view.agreed, 1)}</dd></div>
        <div><dt>Released</dt><dd className="num">{usd(u.released, 1)}</dd></div>
        <div><dt>In escrow</dt><dd className="num">{usd(u.locked, 1)}</dd></div>
        {u.scheduled > 0 && <div><dt>Release scheduled</dt><dd className="num">{usd(u.scheduled, 1)}</dd></div>}
        <div><dt>Refunded</dt><dd className="num">{usd(u.refunded, 1)}</dd></div>
      </dl>
      <p className="hint">Totals cover all deals.</p>
    </section>
  );
}
