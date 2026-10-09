import { SCENARIOS, tada } from "../lib/formatters.js";
import { clock } from "../lib/formatters.js";
import StatusBadge from "./StatusBadge.jsx";

const OUTCOME = {
  released: ["success", "Released"], refunded: ["warning", "Refunded"], blocked: ["danger", "Blocked"],
  walked: ["neutral", "Ended"], error: ["danger", "Failed"], running: ["info", "Running"],
};

// Every deal in the ledger. Click one to inspect it in all tabs; "Latest" returns to the live one.
export default function DealsPanel({ view, selected, onSelect }) {
  if (!view.deals.length) return <p className="tab-empty">Deals appear here.</p>;
  return (
    <div className="deals">
      <ul className="deal-list">
        {view.deals.map((d) => {
          const [tone, label] = OUTCOME[d.outcome];
          const on = d.dealId === view.dealId;
          return (
            <li key={d.dealId}>
              <button type="button" className={`deal-row ${on ? "is-on" : ""}`} aria-current={on ? "true" : undefined}
                onClick={() => onSelect(d.dealId === view.deals[0].dealId ? null : d.dealId)}>
                <span className="deal-main">
                  <span className="deal-text">{d.text ?? "Request"}</span>
                  <span className="deal-meta">{clock(d.ts)} · {SCENARIOS[d.scenario]?.name ?? d.scenario}{d.items != null ? (d.kind === "general" ? " · AI answer" : ` · ${d.items} listings`) : ""}</span>
                </span>
                <span className="deal-price num">{d.price != null ? tada(d.price, 1) : ""}</span>
                <StatusBadge tone={tone} icon={null}>{label}</StatusBadge>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
