import { useEffect, useMemo, useRef } from "react";
import { BUYER } from "../api.js";
import { eventKey } from "../eventIdentity.js";
import { SOURCE_LABEL } from "../lib/eventLabels.js";
import { SCENARIOS, shortId } from "../lib/formatters.js";
import AgentIdentity from "./AgentIdentity.jsx";
import ApprovalCard from "./ApprovalCard.jsx";
import CopyButton from "./CopyButton.jsx";
import DealPipeline from "./DealPipeline.jsx";
import Icon from "./Icons.jsx";
import MessageBubble from "./MessageBubble.jsx";
import StatusBadge from "./StatusBadge.jsx";
import VoicePlayback from "./VoicePlayback.jsx";

const NEAR_BOTTOM_PX = 96;
const STATUS = {
  running: ["info", "In progress"],
  released: ["success", "Completed"],
  refunded: ["warning", "Refunded"],
  blocked: ["danger", "Blocked"],
  walked: ["neutral", "Ended"],
  error: ["danger", "Failed"],
};

export default function NegotiationWorkspace({ view, events, controls }) {
  const feed = useRef(null);
  const stick = useRef(true); // follow new messages only while the reader is at the bottom

  const rounds = useMemo(() => {
    let r = 0;
    return view.chat.map((e) => (e.data.speaker === "viktor" ? ++r : Math.max(r, 1)));
  }, [view.chat]);

  const onScroll = () => {
    const el = feed.current;
    if (el) stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < NEAR_BOTTOM_PX;
  };
  useEffect(() => {
    const el = feed.current;
    if (el && stick.current) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [view.chat.length]);

  const scenario = SCENARIOS[view.scenario];
  const [tone, status] = view.guard.status === "release_scheduled" ? ["info", "Release scheduled"] : STATUS[view.outcome];
  const src = view.delivery?.source && SOURCE_LABEL[view.delivery.source];

  return (
    <div className="workspace">
      <section className="card deal-head" aria-labelledby="deal-h">
        <div className="deal-head-top">
          <div>
            <h2 id="deal-h">{scenario ? scenario.name : "Current deal"}</h2>
            {view.task?.text && <p className="deal-request">“{view.task.text}”</p>}
            <div className="deal-sub">
              <span>Round <b className="num">{view.round}</b></span>
              <span className="sep" aria-hidden="true" />
              <span className="id">Deal <code>{shortId(view.dealId)}</code>
                <CopyButton text={view.dealId} label="Copy deal ID" /></span>
            </div>
          </div>
          <div className="deal-badges">
            <StatusBadge tone={tone} icon={view.outcome === "running" ? "clock" : undefined}>{status}</StatusBadge>
            {view.staged && <StatusBadge tone="warning" icon={null}>STAGED SCENARIO</StatusBadge>}
            {src && <StatusBadge tone={src.tone} icon={null} title={src.hint}>{src.label}</StatusBadge>}
          </div>
        </div>
        <DealPipeline stages={view.stages} />
      </section>

      {view.approval && <ApprovalCard key={eventKey(view.approval)} approval={view.approval} controls={controls} />}

      <section className="card conversation" aria-labelledby="conv-h">
        <div className="conv-head">
          <h2 id="conv-h" className="card-title">Negotiation</h2>
          <VoicePlayback events={events} buyerUrl={BUYER} />
        </div>
        <div className="parties">
          <AgentIdentity who="max" view={view} />
          <Icon name="arrow" size={16} className="parties-arrow" />
          <AgentIdentity who="viktor" view={view} />
        </div>

        <div className="feed" ref={feed} onScroll={onScroll} role="log" aria-live="polite" aria-label="Negotiation transcript" tabIndex={0}>
          {view.chat.length === 0 && <p className="muted feed-wait"><Icon name="refresh" size={14} className="spin" /> Waiting for Viktor's opening ask...</p>}
          {view.chat.map((e, i) => <MessageBubble key={eventKey(e)} e={e} round={rounds[i]} />)}
        </div>

        {view.terminal && (
          <div className={`result result-${view.terminal.tone}`} role="status">
            <Icon name={{ success: "shield-check", warning: "refresh", danger: "shield-alert", neutral: "info" }[view.terminal.tone]} size={18} />
            <div><strong>{view.terminal.title}</strong><p>{view.terminal.description}</p></div>
          </div>
        )}
      </section>
    </div>
  );
}
