import { useState } from "react";
import { clock } from "../lib/formatters.js";
import Icon from "./Icons.jsx";

const ICON = { success: "check", danger: "x", warning: "alert", info: "info", neutral: "clock" };

function Row({ row }) {
  const [open, setOpen] = useState(false);
  return (
    <li className={`tl tl-${row.tone}`}>
      <span className="tl-ico"><Icon name={ICON[row.tone]} size={13} /></span>
      <div className="tl-main">
        <div className="tl-top">
          <strong>{row.title}</strong>
          {row.staged && <em className="staged-tag">Staged</em>}
          <time dateTime={new Date(row.ts * 1000).toISOString()}>{clock(row.ts)}</time>
          <button type="button" className="icon-btn" aria-expanded={open} aria-label={`${open ? "Hide" : "Show"} developer details for ${row.title}`}
            onClick={() => setOpen((o) => !o)}><Icon name="chevron" size={14} className={open ? "flip" : ""} /></button>
        </div>
        <p>{row.description}</p>
        {open && (
          <div className="dev">
            <div className="dev-head"><span>Developer details</span></div>
            <pre>{JSON.stringify(row.event, null, 2)}</pre>
          </div>
        )}
      </div>
    </li>
  );
}

export default function EventTimeline({ rows }) {
  const shown = rows.slice(0, 40);
  return (
    <section className="card" aria-labelledby="tl-h">
      <div className="card-head"><h2 id="tl-h" className="card-title">Timeline</h2><span className="muted">{rows.length} events</span></div>
      {shown.length === 0 ? <p className="muted">Events appear here as a deal progresses.</p> : (
        <ol className="timeline">{shown.map((r) => <Row key={r.id} row={r} />)}</ol>
      )}
    </section>
  );
}
