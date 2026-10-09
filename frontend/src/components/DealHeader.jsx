import { SOURCE_LABEL } from "../lib/eventLabels.js";
import { SCENARIOS, shortId } from "../lib/formatters.js";
import CopyButton from "./CopyButton.jsx";
import DealPipeline from "./DealPipeline.jsx";
import Icon from "./Icons.jsx";
import StatusBadge from "./StatusBadge.jsx";

const STATUS = {
  running: ["info", "Running"], released: ["success", "Complete"], refunded: ["warning", "Refunded"],
  blocked: ["danger", "Blocked"], walked: ["neutral", "Ended"], error: ["danger", "Failed"],
};
const RESULT_ICON = { success: "shield-check", warning: "refresh", danger: "shield-alert", neutral: "info" };

export default function DealHeader({ view, onLatest }) {
  const scenario = SCENARIOS[view.scenario];
  const [tone, status] = STATUS[view.outcome];
  const src = view.delivery?.source && SOURCE_LABEL[view.delivery.source];
  return (
    <section className="card deal-head" aria-labelledby="deal-h">
      <div className="deal-head-top">
        <div className="deal-title">
          <h2 id="deal-h">{view.task?.text ?? scenario?.name ?? "Deal"}</h2>
          <div className="deal-sub">
            <span>{scenario?.name}</span>
            <span className="sep" aria-hidden="true" />
            <span>Round <b className="num">{view.round}</b></span>
            <span className="sep" aria-hidden="true" />
            <span className="id"><code>{shortId(view.dealId)}</code><CopyButton text={view.dealId} label="Copy deal ID" /></span>
          </div>
        </div>
        <div className="deal-badges">
          {!view.isLatest && <button type="button" className="btn btn-sm" onClick={onLatest}>Back to latest</button>}
          <StatusBadge tone={tone} icon={view.outcome === "running" ? "clock" : undefined}>{status}</StatusBadge>
          {view.staged && <StatusBadge tone="warning" icon={null}>STAGED</StatusBadge>}
          {src && <StatusBadge tone={src.tone} icon={null} title={src.hint}>{src.label}</StatusBadge>}
        </div>
      </div>
      <DealPipeline stages={view.stages} />
      {view.terminal && (
        <p className={`result-line result-${view.terminal.tone}`} role="status">
          <Icon name={RESULT_ICON[view.terminal.tone]} size={15} /> <b>{view.terminal.title}.</b> {view.terminal.description}
        </p>
      )}
    </section>
  );
}
