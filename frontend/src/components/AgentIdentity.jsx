import { tada } from "../lib/formatters.js";

const WHO = {
  max: { name: "Max", role: "Buyer agent" },
  viktor: { name: "Viktor", role: "Seller agent" },
};

const ACTION_STATE = { counter: "Countering", accept: "Accepted", walk: "Walked away", open: "Opened" };

export default function AgentIdentity({ who, view }) {
  const w = WHO[who];
  const lines = view.chat.filter((e) => e.data.speaker === who);
  const lastLine = lines[lines.length - 1];
  const speaking = view.stages.negotiate === "active" && view.chat[view.chat.length - 1]?.data.speaker === who;
  const state = lastLine ? ACTION_STATE[lastLine.data.action] ?? lastLine.data.action : "Waiting";

  return (
    <div className={`identity identity-${who}`}>
      <span className={`avatar ${speaking ? "is-speaking" : ""}`} aria-hidden="true">{w.name[0]}</span>
      <div className="identity-text">
        <div className="identity-name"><strong>{w.name}</strong><span>{w.role}{lastLine?.provenance === "scripted" ? " · Scripted" : ""}</span></div>
        <div className="identity-meta">
          <span className="num offer">{tada(view.prices[who], 1)}</span>
          <span className="identity-state">{speaking ? "Speaking" : state}</span>
        </div>
      </div>
    </div>
  );
}
