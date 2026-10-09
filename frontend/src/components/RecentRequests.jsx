import { tada } from "../lib/formatters.js";

const TONE = { released: "success", refunded: "warning", blocked: "danger", walked: "neutral", error: "danger", running: "info" };
const LABEL = { released: "Released", refunded: "Refunded", blocked: "Blocked", walked: "Ended", error: "Failed", running: "Running" };

// The last few requests, newest first. Click one to open that deal; the newest opens the live view again.
export default function RecentRequests({ deals, currentId, onOpen }) {
  if (!deals.length) return null;
  return (
    <section className="card" aria-labelledby="recent-h">
      <h2 id="recent-h" className="card-title">Recent</h2>
      <ul className="recent">
        {deals.slice(0, 5).map((d) => (
          <li key={d.dealId}>
            <button type="button" className={`recent-row ${d.dealId === currentId ? "is-on" : ""}`} aria-current={d.dealId === currentId ? "true" : undefined}
              title={`${LABEL[d.outcome]}${d.price != null ? ` at ${tada(d.price, 1)}` : ""}`}
              onClick={() => onOpen(d.dealId === deals[0].dealId ? null : d.dealId)}>
              <i className={`dot dot-${TONE[d.outcome]}`} aria-hidden="true" />
              <span className="recent-text">{d.text ?? "Request"}</span>
              <span className="recent-price num">{d.price != null ? tada(d.price, 1) : ""}</span>
              <span className="sr-only">{LABEL[d.outcome]}</span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
