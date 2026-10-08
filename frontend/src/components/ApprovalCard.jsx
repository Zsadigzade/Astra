import { useState } from "react";
import { api } from "../api.js";
import { tada } from "../lib/formatters.js";
import Icon from "./Icons.jsx";

export default function ApprovalCard({ approval, controls }) {
  const [busy, setBusy] = useState(null); // "approve" | "decline" | null
  const [sent, setSent] = useState(null); // decision already submitted for this approval id
  const [err, setErr] = useState(null);
  const price = approval.data.price;
  const decided = sent?.id === approval.id;

  const decide = async (ok) => {
    if (busy || decided) return;
    setBusy(ok ? "approve" : "decline");
    setErr(null);
    try {
      await api.decide(approval.deal_id, ok);
      setSent({ id: approval.id, ok });
    } catch (e) {
      setErr(e.message);
    } finally { setBusy(null); }
  };

  return (
    <section className="approval" role="alertdialog" aria-labelledby="approval-h" aria-describedby="approval-d">
      <div className="approval-icon"><Icon name="shield-clock" size={22} /></div>
      <div className="approval-body">
        <h2 id="approval-h">Viktor requests {tada(price, 1)}</h2>
        <p id="approval-d">This price is above the automatic approval line, so the wallet guard will pay only with a human decision.</p>
        <dl className="approval-facts">
          <div><dt>Automatic approval up to</dt><dd className="num">{controls ? tada(controls.guard.approval_over, 1) : "-"}</dd></div>
          <div><dt>Hard spending limit</dt><dd className="num">{controls ? tada(controls.guard.cap, 1) : "-"}</dd></div>
        </dl>
        <p className="muted">{approval.data.reason}. No answer within 5 minutes declines the deal.</p>
        {err && <p className="note note-danger" role="alert">{err}</p>}
        {decided && <p className="note note-info" role="status">{sent.ok ? "Approval sent. Waiting for the guard..." : "Decline sent."}</p>}
        <div className="row">
          <button type="button" className="btn btn-primary" onClick={() => decide(true)} disabled={!!busy || decided}>
            {busy === "approve" ? "Approving..." : `Approve ${tada(price, 1)}`}
          </button>
          <button type="button" className="btn" onClick={() => decide(false)} disabled={!!busy || decided}>
            {busy === "decline" ? "Declining..." : "Decline"}
          </button>
        </div>
      </div>
    </section>
  );
}
