import { SOURCE_LABEL } from "../lib/eventLabels.js";
import { safeUrl, tada } from "../lib/formatters.js";
import CopyButton from "./CopyButton.jsx";
import Icon from "./Icons.jsx";
import StatusBadge from "./StatusBadge.jsx";

// Escrow, delivery and verifier facts for the current deal. Renders only what the events carried.
export default function DealDetails({ view }) {
  const { escrow, delivery, verified, release } = view;
  if (!escrow && !delivery && !verified) return null;
  const src = delivery?.source && SOURCE_LABEL[delivery.source];
  const tx = safeUrl(escrow?.tx_url);
  const checks = verified?.checks ? Object.entries(verified.checks) : [];

  return (
    <section className="card" aria-labelledby="details-h">
      <h2 id="details-h" className="card-title">Escrow and delivery</h2>

      {escrow && (
        <div className="block">
          <div className="block-head">
            <strong>Escrow</strong>
            {escrow.resumed && <StatusBadge tone="info" icon={null} title="The buyer restarted and found this deal already paid">Not paid twice</StatusBadge>}
          </div>
          <p>{tada(escrow.price, 1)} locked{escrow.on_chain_state ? ` · ${escrow.on_chain_state}` : ""}</p>
          {escrow.ref && (
            <p className="idline"><code title={String(escrow.ref)}>{String(escrow.ref).slice(0, 26)}{String(escrow.ref).length > 26 ? "…" : ""}</code>
              <CopyButton text={String(escrow.ref)} label="Copy transaction ID" /></p>
          )}
          {tx && <a className="ext" href={tx} target="_blank" rel="noreferrer">View on explorer <Icon name="external" size={12} /></a>}
          {release?.release === "scheduled" && (
            <p className="note note-warning">Release is scheduled{release.settles_at ? ` for ${release.settles_at}` : ""}. It has not settled on-chain yet.</p>
          )}
        </div>
      )}

      {delivery && (
        <div className="block">
          <div className="block-head"><strong>Delivery</strong>{src && <StatusBadge tone={src.tone} icon={null} title={src.hint}>{src.label}</StatusBadge>}</div>
          <p>{delivery.items} listings received{delivery.result?.fetched_at ? ` · fetched ${delivery.result.fetched_at}` : ""}</p>
        </div>
      )}

      {checks.length > 0 && (
        <div className="block">
          <div className="block-head"><strong>Verification</strong>
            <StatusBadge tone={verified.ok ? "success" : "danger"}>{verified.ok ? "Passed" : "Failed"}</StatusBadge></div>
          <ul className="checks">
            {checks.map(([k, ok]) => (
              <li key={k} className={ok ? "ok" : "no"}><Icon name={ok ? "check" : "x"} size={13} /> {k.replaceAll("_", " ")}
                <span className="sr-only">{ok ? " passed" : " failed"}</span></li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
