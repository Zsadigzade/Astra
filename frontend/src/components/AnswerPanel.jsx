import { useState } from "react";
import { SOURCE_LABEL } from "../lib/eventLabels.js";
import CopyButton from "./CopyButton.jsx";
import Icon from "./Icons.jsx";
import StatusBadge from "./StatusBadge.jsx";

const VERDICT = { offered: ["clock", "Offered"], accepted: ["check", "Accepted by Max"], rejected: ["x", "Rejected by Max"] };

const safe = (u) => { try { return new URL(u).protocol === "https:"; } catch { return false; } };
const host = (u) => { try { return new URL(u).hostname.replace(/^www\./, ""); } catch { return u; } };

// One finding: the whole card is the link. The photo is the page's own preview image, loaded by the browser
// without a referrer; if it is missing or fails, a plain tile with the site's initial stands in.
function FindingCard({ item, index, animate }) {
  const [broken, setBroken] = useState(false);
  const site = host(item.url);
  const showImage = item.image && safe(item.image) && !broken;
  return (
    <a className={`finding ${animate ? "finding-in" : ""}`} style={animate ? { animationDelay: `${index * 90}ms` } : undefined}
       href={item.url} target="_blank" rel="noopener noreferrer nofollow">
      <span className="finding-photo" aria-hidden="true">
        {showImage
          ? <img src={item.image} alt="" loading="lazy" referrerPolicy="no-referrer" onError={() => setBroken(true)} />
          : <span className="finding-initial">{site.charAt(0).toUpperCase()}</span>}
      </span>
      <span className="finding-body">
        <span className="finding-title">{item.title}</span>
        {item.detail && <span className="finding-detail">{item.detail}</span>}
        <span className="finding-site">{site}<Icon name="external" size={11} /></span>
      </span>
    </a>
  );
}

// A delivered answer (a general request). It fades in, then Max's verdict follows from the rule checks.
// The answer is plain text from a model: it is shown as text only, never as markup.
export default function AnswerPanel({ view, animate = false }) {
  const result = view.delivery?.result;
  const answer = result?.answer ?? "";
  const items = (result?.items ?? []).filter((i) => safe(i.url));
  const shown = new Set(items.map((i) => i.url));
  const sources = (result?.sources ?? []).filter((u) => safe(u) && !shown.has(u));
  const src = SOURCE_LABEL[view.delivery?.source];
  const verdict = view.verified == null ? "offered" : view.verified.ok ? "accepted" : "rejected";
  const [icon, label] = VERDICT[verdict];
  if (!answer) return <p className="tab-empty">The answer appears here once Viktor delivers.</p>;
  return (
    <article className={`answer ${animate ? "answer-in" : ""}`} aria-label="Delivered answer">
      <header className="answer-bar">
        <span className={`verdict verdict-${verdict} ${animate && verdict !== "offered" ? "verdict-in" : ""}`} style={animate ? { animationDelay: "700ms" } : undefined}>
          <Icon name={icon} size={12} />{label}
        </span>
        {src && <StatusBadge tone={src.tone} icon={null} title={src.hint}>{src.label}</StatusBadge>}
        <span className="answer-meta num">{items.length > 0 ? `${items.length} finding${items.length > 1 ? "s" : ""}` : `${answer.length.toLocaleString("en-US")} characters`}</span>
        <CopyButton text={answer} label="Copy answer" showLabel />
      </header>
      <div className="answer-text">{answer}</div>
      {items.length > 0 && (
        <section className="findings" aria-label="Findings">
          {items.map((item, i) => <FindingCard key={item.url} item={item} index={i} animate={animate} />)}
        </section>
      )}
      {sources.length > 0 && (
        <section className="answer-sources" aria-label="Sources">
          <h4>{items.length > 0 ? "More sources" : "Sources"}</h4>
          <ul>{sources.map((u) => <li key={u}><a href={u} target="_blank" rel="noopener noreferrer nofollow">{host(u)}<span>{u}</span></a></li>)}</ul>
        </section>
      )}
      <p className="answer-note">Checked by rules (present, sensible length, not a placeholder, https links). Not fact-checked: open a finding to confirm.</p>
    </article>
  );
}
