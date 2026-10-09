import { SOURCE_LABEL } from "../lib/eventLabels.js";
import { safeUrl } from "../lib/formatters.js";
import CopyButton from "./CopyButton.jsx";
import Icon from "./Icons.jsx";
import StatusBadge from "./StatusBadge.jsx";

// One section: what was delivered, the escrow reference, and the verifier's checks. Only what the events carried.
// The released amount and the final state live in the deal header, not here.
export default function DealDetails({ view }) {
  const { escrow, delivery, verified, release } = view;
  if (!escrow && !delivery && !verified) return null;
  const src = delivery?.source && SOURCE_LABEL[delivery.source];
  const tx = safeUrl(escrow?.tx_url);
  const checks = verified?.checks ? Object.entries(verified.checks) : [];
  const ref = escrow?.ref ? String(escrow.ref) : null;

  return (
    <section className="card" aria-labelledby="details-h">
      <h2 id="details-h" className="card-title">Delivery and verification</h2>

      {delivery && (
        <div className="detail-line">
          <span>{delivery.items} listings{delivery.result?.fetched_at ? <small className="muted"> · fetched {delivery.result.fetched_at.slice(0, 16).replace("T", " ")}</small> : null}</span>
          {src && <StatusBadge tone={src.tone} icon={null} title={src.hint}>{src.label}</StatusBadge>}
        </div>
      )}

      {checks.length > 0 && (
        <ul className="checks">
          {checks.map(([k, ok]) => (
            <li key={k} className={ok ? "ok" : "no"}><Icon name={ok ? "check" : "x"} size={13} /> {k.replaceAll("_", " ")}
              <span className="sr-only">{ok ? " passed" : " failed"}</span></li>
          ))}
        </ul>
      )}

      {ref && (
        <div className="detail-line">
          <span className="idline"><span className="muted">Escrow</span> <code title={ref}>{ref.slice(0, 22)}{ref.length > 22 ? "…" : ""}</code>
            <CopyButton text={ref} label="Copy escrow ID" /></span>
          {escrow.resumed && <StatusBadge tone="info" icon={null} title="The buyer restarted and found this deal already paid">Not paid twice</StatusBadge>}
        </div>
      )}
      {tx && <a className="ext" href={tx} target="_blank" rel="noreferrer">View on explorer <Icon name="external" size={12} /></a>}
      {release?.release === "scheduled" && (
        <p className="note note-warning">Release scheduled{release.settles_at ? ` for ${release.settles_at}` : ""}. Not settled on-chain yet.</p>
      )}
    </section>
  );
}
