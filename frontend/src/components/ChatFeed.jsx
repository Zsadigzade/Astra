import { useEffect, useRef } from "react";
import { eventKey } from "../eventIdentity.js";
import Icon from "./Icons.jsx";
import MessageBubble from "./MessageBubble.jsx";

const NEAR_BOTTOM_PX = 96;

// The transcript, in the right rail. It scrolls on its own and only follows new messages while you are at the bottom.
export default function ChatFeed({ view, paced }) {
  const feed = useRef(null);
  const stick = useRef(true);
  const onScroll = () => {
    const el = feed.current;
    if (el) stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < NEAR_BOTTOM_PX;
  };
  useEffect(() => { stick.current = true; }, [view.dealId]);
  useEffect(() => {
    const el = feed.current;
    if (el && stick.current) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [paced.chat.length, view.dealId]);

  let round = 0;
  return (
    <section className="card chat-card" aria-labelledby="chat-h">
      <h2 id="chat-h" className="card-title">Chat</h2>
      <div className="feed" ref={feed} onScroll={onScroll} role="log" aria-live="polite" aria-label="Negotiation transcript" tabIndex={0}>
        {paced.chat.length === 0 ? (
          <p className="feed-wait">{view.dealId && view.outcome === "running"
            ? <><Icon name="refresh" size={14} className="spin" /> Max is about to ask</> : "No messages yet"}</p>
        ) : (
          <ol className="thread">
            {paced.chat.map((e) => {
              if (e.data.speaker === "viktor") round += 1; // a round starts with the seller's ask or counter
              return <MessageBubble key={eventKey(e)} e={e} round={Math.max(round, 1)} />;
            })}
          </ol>
        )}
      </div>
    </section>
  );
}
