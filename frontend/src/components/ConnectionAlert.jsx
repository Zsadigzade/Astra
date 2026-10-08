import { useState } from "react";
import { BACKEND_COMMAND } from "../lib/formatters.js";
import CopyButton from "./CopyButton.jsx";
import Icon from "./Icons.jsx";

// Compact alert under the header. Offline: explains and offers retry. Reconnecting: a calm status line.
export default function ConnectionAlert({ status, onRetry }) {
  const [open, setOpen] = useState(false);
  if (status === "live") return null;

  if (status === "connecting" || status === "reconnecting") {
    return (
      <div className="alert alert-info" role="status">
        <Icon name="refresh" size={16} className="spin" />
        <div className="alert-body">
          <strong>{status === "connecting" ? "Connecting to the buyer service..." : "Connection lost. Reconnecting..."}</strong>
          {status === "reconnecting" && <span>Deal history is kept and will resync when the stream is back.</span>}
        </div>
      </div>
    );
  }

  return (
    <div className="alert alert-danger" role="alert">
      <Icon name="alert" size={16} />
      <div className="alert-body">
        <strong>Buyer service is offline</strong>
        <span>The dashboard cannot start or monitor deals.</span>
        <button type="button" className="link-btn" aria-expanded={open} aria-controls="setup-details" onClick={() => setOpen((o) => !o)}>
          Setup details <Icon name="chevron" size={12} className={open ? "flip" : ""} />
        </button>
        {open && (
          <div id="setup-details" className="setup">
            <p>Start both agent services from the project root:</p>
            <div className="cmd"><code>{BACKEND_COMMAND}</code><CopyButton text={BACKEND_COMMAND} label="Copy command" showLabel /></div>
            <p>The buyer listens on <code>:8000</code> and the seller on <code>:8001</code>.</p>
          </div>
        )}
      </div>
      <button type="button" className="btn btn-sm btn-primary" onClick={onRetry}>
        <Icon name="refresh" size={14} /> Retry connection
      </button>
    </div>
  );
}
