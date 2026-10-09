import { usd } from "../lib/formatters.js";
import Ghost from "./Ghost.jsx";
import OfferLadder from "./OfferLadder.jsx";

const WHO = { max: { name: "Max", role: "buyer" }, viktor: { name: "Viktor", role: "seller" } };
const clip = (t, n = 130) => (t.length > n ? `${t.slice(0, n - 1).trimEnd()}…` : t);

// What is actually writing this agent's lines. Shown once, beside the agent, instead of on every message.
// Before it has said anything, fall back to the configured mode (the staged con act is scripted regardless).
function provenance(chat, who, modes) {
  const last = [...chat].reverse().find((e) => e.data.speaker === who && e.provenance && e.provenance !== "guard");
  if (last) {
    return { codex: ["Codex subscription", "info"], fallback: ["Scripted · AI fallback", "warning"], scripted: ["Scripted", "neutral"], ai: ["AI", "info"] }[last.provenance] ?? null;
  }
  if (!modes) return null;
  const mode = who === "max" ? modes.llm : modes.seller_llm ?? "mock";
  return mode === "codex" ? ["Codex subscription", "info"] : ["Scripted", "neutral"];
}

function Side({ who, thinking, speaking, offer, prov, track }) {
  const mood = speaking?.who === who ? "speaking" : thinking === who ? "thinking" : "idle";
  return (
    <div className={`ghost-side ghost-side-${who}`}>
      <div className="ghost-above">
        {mood === "thinking" && <span className="thought" aria-label={`${WHO[who].name} is thinking`}><i /><i /><i /></span>}
        {mood === "speaking" && <p className="speech" aria-hidden="true">{clip(speaking.text)}</p>}
      </div>
      <Ghost who={who} mood={mood} tracking={track} />
      <div className="ghost-name"><b>{WHO[who].name}</b><span>{WHO[who].role}</span>
        <span className="num ghost-offer">{offer != null ? usd(offer, 2) : ""}</span></div>
      {prov && <span className={`ghost-prov prov-${prov[1]}`} title="What writes this agent's lines">{prov[0]}</span>}
    </div>
  );
}

// Two ghosts facing each other across the deal. The coin is the price currently on the table.
export default function GhostStage({ chat, thinking, speaking, caughtUp, agreed, modes, trackEyes = false }) {
  const lastOf = (who) => [...chat].reverse().find((e) => e.data.speaker === who && e.data.price > 0)?.data.price ?? null;
  const onTable = [...chat].reverse().find((e) => e.data.price > 0)?.data.price ?? null;
  const settled = caughtUp && agreed != null;
  return (
    <div className="stage" role="group" aria-label="Max and Viktor">
      <Side who="max" thinking={thinking} speaking={speaking} offer={lastOf("max")} prov={provenance(chat, "max", modes)} track={trackEyes} />
      <div className="stage-mid">
        <div className={`coin ${settled ? "is-agreed" : ""}`} aria-label={onTable != null ? `Price on the table: ${usd(onTable, 2)}` : "No price yet"}>
          <span className="coin-face num">{onTable != null ? onTable.toLocaleString("en-US", { maximumFractionDigits: 2 }) : "–"}</span>
          <span className="coin-label">{settled ? "agreed" : "USD"}</span>
        </div>
        <OfferLadder chat={chat} agreed={agreed} caughtUp={caughtUp} />
      </div>
      <Side who="viktor" thinking={thinking} speaking={speaking} offer={lastOf("viktor")} prov={provenance(chat, "viktor", modes)} track={trackEyes} />
    </div>
  );
}
