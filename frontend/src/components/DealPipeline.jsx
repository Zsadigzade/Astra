import { STAGES } from "../lib/eventReducer.js";
import Icon from "./Icons.jsx";

const STATE = {
  idle: { text: "Pending", icon: null },
  active: { text: "In progress", icon: "refresh" },
  wait: { text: "Waiting for a human", icon: "clock" },
  done: { text: "Completed", icon: "check" },
  fail: { text: "Failed or blocked", icon: "x" },
};

export default function DealPipeline({ stages }) {
  return (
    <ol className="pipeline" aria-label="Deal pipeline">
      {STAGES.map(([key, name, hint]) => {
        const st = stages[key];
        const s = STATE[st];
        return (
          <li key={key} className={`pstep pstep-${st}`} aria-current={st === "active" || st === "wait" ? "step" : undefined} title={`${name}: ${hint}`}>
            <span className="pstep-dot" aria-hidden="true">
              {s.icon ? <Icon name={s.icon} size={13} className={st === "active" ? "spin" : ""} /> : <i />}
            </span>
            <span className="pstep-text">
              <span className="pstep-name">{name}</span>
              <span className="pstep-state">{st === "wait" && key === "settle" ? "Awaiting settlement" : s.text}</span>
            </span>
          </li>
        );
      })}
    </ol>
  );
}
