import { useMemo, useState } from "react";
import { SOURCE_LABEL } from "../lib/eventLabels.js";
import { safeUrl } from "../lib/formatters.js";
import { sortFlats, toCsv } from "../lib/csv.js";
import Icon from "./Icons.jsx";
import StatusBadge from "./StatusBadge.jsx";

function download(name, text) {
  const url = URL.createObjectURL(new Blob(["﻿" + text], { type: "text/csv;charset=utf-8" }));
  const a = Object.assign(document.createElement("a"), { href: url, download: name });
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

const COLS = [["title", "Listing"], ["district", "Area"], ["price_czk", "Rent (CZK)"]];
const STEP_MS = 70; // rows fade in one after another
const CAP_MS = 1400; // however many rows, the reveal takes at most this long

// verdict: what Max decided about this delivery. offered -> accepted (verification passed) | rejected (it failed).
function verdictOf(view) {
  if (view.verified == null) return "offered";
  return view.verified.ok ? "accepted" : "rejected";
}
const VERDICT = { offered: "Offered", accepted: "Accepted", rejected: "Rejected" };

// `animate`: the rows are arriving live, so they fade in one by one and the "Accepted" marks follow.
// History and past deals pass animate=false and render at once.
export default function DeliveryPanel({ view, animate = false }) {
  const [sort, setSort] = useState({ key: "price_czk", dir: "asc" });
  const [q, setQ] = useState("");
  const flats = view.delivery?.result?.flats ?? [];
  const src = view.delivery?.source && SOURCE_LABEL[view.delivery.source];
  const verdict = verdictOf(view);
  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const shown = needle ? flats.filter((f) => `${f.title} ${f.district}`.toLowerCase().includes(needle)) : flats;
    return sortFlats(shown, sort.key, sort.dir);
  }, [flats, sort, q]);

  if (!flats.length) return <p className="tab-empty">Listings appear here once Viktor delivers.</p>;

  const toggle = (key) => setSort((s) => (s.key === key ? { key, dir: s.dir === "asc" ? "desc" : "asc" } : { key, dir: "asc" }));
  const avg = Math.round(flats.reduce((n, f) => n + f.price_czk, 0) / flats.length);
  const delay = (i) => (animate ? { animationDelay: `${Math.min(i * STEP_MS, CAP_MS)}ms` } : undefined);
  const markDelay = (i) => (animate ? { animationDelay: `${Math.min(i * STEP_MS, CAP_MS) + 500}ms` } : undefined);

  return (
    <div className="delivery">
      <div className="delivery-bar">
        <input type="search" className="search" placeholder="Filter" aria-label="Filter listings" value={q} onChange={(e) => setQ(e.target.value)} />
        <span className="delivery-stats num">{rows.length}/{flats.length} · avg {avg.toLocaleString("en-US")} CZK</span>
        {src && <StatusBadge tone={src.tone} icon={null} title={src.hint}>{src.label}</StatusBadge>}
        <button type="button" className="btn btn-sm" onClick={() => download(`flats-${view.dealId}.csv`, toCsv(flats))}>
          <Icon name="copy" size={13} /> CSV
        </button>
      </div>
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th scope="col" className="num-col">#</th>
              {COLS.map(([key, label]) => (
                <th key={key} scope="col" aria-sort={sort.key === key ? (sort.dir === "asc" ? "ascending" : "descending") : "none"} className={key === "price_czk" ? "num-col" : ""}>
                  <button type="button" onClick={() => toggle(key)}>{label}{sort.key === key && <span aria-hidden="true">{sort.dir === "asc" ? " ↑" : " ↓"}</span>}</button>
                </th>
              ))}
              <th scope="col" className="verdict-col">Max</th>
              <th scope="col"><span className="sr-only">Link</span></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((f, i) => {
              const url = safeUrl(f.url);
              const real = url && !new URL(url).hostname.endsWith(".invalid");
              return (
                <tr key={f.url || i} className={animate ? "row-in" : ""} style={delay(i)}>
                  <td className="num-col num muted">{i + 1}</td>
                  <td className="cell-title">{f.title}</td>
                  <td className="muted">{f.district.replace(/^.*?[—-]\s*/, "")}</td>
                  <td className="num-col num">{f.price_czk.toLocaleString("en-US")}</td>
                  <td className="verdict-col">
                    <span className={`verdict verdict-${verdict} ${animate && verdict !== "offered" ? "verdict-in" : ""}`} style={markDelay(i)}>
                      <Icon name={verdict === "accepted" ? "check" : verdict === "rejected" ? "x" : "clock"} size={12} />{VERDICT[verdict]}
                    </span>
                  </td>
                  <td className="link-col">{real ? <a href={url} target="_blank" rel="noreferrer" aria-label={`Open ${f.title}`}><Icon name="external" size={13} /></a> : <span className="muted">sample</span>}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
