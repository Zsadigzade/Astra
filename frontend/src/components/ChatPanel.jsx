import { useEffect, useRef } from "react";
import { eventKey } from "../eventIdentity.js";
import GhostStage from "./GhostStage.jsx";
import Icon from "./Icons.jsx";
import MessageBubble from "./MessageBubble.jsx";

const NEAR_BOTTOM_PX = 96;

export default function ChatPanel({ view, paced, modes }) {
  const feed = useRef(null);
  const stick = useRef(true); // follow new messages only while the reader is at the bottom
  const onScroll = () => {
    const el = feed.current;
    if (el) stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < NEAR_BOTTOM_PX;
  };
  useEffect(() => {
    stick.current = true;
  }, [view.dealId]);
  useEffect(() => {
    const el = feed.current;
    if (el && stick.current) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [paced.chat.length, view.dealId]);

  let round = 0;
  return (
    <div className="chat">
      <GhostStage chat={paced.chat} thinking={paced.thinking} speaking={paced.speaking} caughtUp={paced.caughtUp}
        agreed={view.agreed} modes={modes} />
      <div className="feed" ref={feed} onScroll={onScroll} role="log" aria-live="polite" aria-label="Negotiation" tabIndex={0}>
        {paced.chat.length === 0 ? (
          <p className="feed-wait">{view.outcome === "running" ? <><Icon name="refresh" size={14} className="spin" /> Waiting for Viktor</> : "No messages"}</p>
        ) : (
          <ol className="thread">
            {paced.chat.map((e) => {
              if (e.data.speaker === "viktor") round += 1; // a round starts with the seller's ask or counter
              return <MessageBubble key={eventKey(e)} e={e} round={Math.max(round, 1)} />;
            })}
          </ol>
        )}
      </div>
    </div>
  );
}
