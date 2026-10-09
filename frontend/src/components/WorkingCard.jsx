import Icon from "./Icons.jsx";

const STEPS = [["planning", "Planning"], ["searching", "Searching"], ["reading", "Reading"], ["writing", "Writing"]];

// Shown in the Results area between "escrow locked" and "delivered": what Viktor has really done so far.
// Every number comes from the seller's own progress report; nothing here is estimated or animated on a timer.
export default function WorkingCard({ progress }) {
  const stage = progress?.stage ?? "starting";
  const at = Math.max(0, STEPS.findIndex(([k]) => k === stage));
  const line = !progress ? "Viktor is pulling your result together."
    : stage === "searching" ? `${progress.pages_done} of ${progress.pages_total} searches back${progress.results_seen ? ` · ${progress.results_seen} results so far` : ""}`
    : stage === "reading" ? `${progress.pages_read} of ${progress.reads_total} pages read`
    : stage === "writing" ? "Putting the best matches together"
    : "Deciding what to search for";
  return (
    <section className="working" aria-live="polite" aria-label="Viktor is working">
      <p className="working-title"><Icon name="refresh" size={15} className="spin" /> Viktor is working on it</p>
      {progress && (
        <ol className="working-steps">
          {STEPS.map(([k, label], i) => <li key={k} className={i < at ? "is-done" : i === at ? "is-now" : ""}>{label}</li>)}
        </ol>
      )}
      <p className="working-line num">{line}</p>
      {progress?.sites?.length > 0 && <p className="working-sites">{progress.sites.map((s) => <span key={s} className="query-chip">{s}</span>)}</p>}
      {progress?.queries?.length > 0 && <p className="working-sites muted">{progress.queries.map((q) => <span key={q} className="query-chip">{q}</span>)}</p>}
    </section>
  );
}
