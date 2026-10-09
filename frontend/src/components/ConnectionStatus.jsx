import { useEffect, useRef, useState } from "react";
import Icon from "./Icons.jsx";

const STATE = {
  online: { text: "Online", tone: "success" },
  degraded: { text: "Degraded", tone: "warning" },
  connecting: { text: "Connecting", tone: "warning" },
  reconnecting: { text: "Reconnecting", tone: "warning" },
  offline: { text: "Offline", tone: "danger" },
  unknown: { text: "Unknown", tone: "neutral" },
};
const RANK = { danger: 3, warning: 2, neutral: 1, success: 0 };

// One compact status for Buyer, Seller and Payments. The dot summarises the worst state; details open on click.
export default function ConnectionStatus({ items }) {
  const [open, setOpen] = useState(false);
  const box = useRef(null);
  const rows = items.map((i) => ({ ...i, ...(STATE[i.state] ?? STATE.unknown) }));
  const worst = rows.reduce((a, b) => (RANK[b.tone] > RANK[a.tone] ? b : a), rows[0]);
  const summary = worst.tone === "success" ? "All systems online" : `${worst.name} ${worst.text.toLowerCase()}`;

  useEffect(() => {
    if (!open) return undefined;
    const close = (e) => { if (e.type === "keydown" ? e.key === "Escape" : !box.current?.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => { document.removeEventListener("mousedown", close); document.removeEventListener("keydown", close); };
  }, [open]);

  return (
    <div className="sys" ref={box}>
      <button type="button" className={`sys-btn sys-${worst.tone}`} aria-expanded={open} aria-haspopup="true" onClick={() => setOpen((o) => !o)}>
        <i className="sys-dot" aria-hidden="true" />
        <span>{summary}</span>
        <Icon name="chevron" size={12} className={open ? "flip" : ""} />
      </button>
      {open && (
        <ul className="sys-pop" aria-label="Service status">
          {rows.map((r) => (
            <li key={r.name} className={`sys-row sys-${r.tone}`}>
              <i className="sys-dot" aria-hidden="true" />
              <span className="sys-name">{r.name}</span>
              <span className="sys-state">{r.detail ?? r.text}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
