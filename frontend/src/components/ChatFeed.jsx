import { Fragment, useEffect, useRef } from "react";
import { eventKey } from "../eventIdentity.js";
import MessageBubble from "./MessageBubble.jsx";

const NEAR_BOTTOM_PX = 96;
const NAME = { max: "Max", viktor: "Viktor" };

// The transcript, in the right rail. It scrolls on its own and only follows new messages while you are at the bottom.
// While an agent is "thinking" (the next line has not landed yet) a quiet typing row shows who is about to speak.
export default function ChatFeed({ view, paced }) {
  const feed = useRef(null);
  const stick = useRef(true);
  const onScroll = () => {
    const el = feed.current;
    if (el) stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < NEAR_BOTTOM_PX;
  };
  useEffect(() => { stick.current = true; }, [view.dealId]);
  const typing = view.dealId && view.isLatest ? paced.thinking : null;
  useEffect(() => {
    const el = feed.current;
    if (el && stick.current) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [paced.chat.length, view.dealId, typing]);

  let round = 0;
  return (
    <section className="card chat-card" aria-labelledby="chat-h">
      <div className="card-head"><h2 id="chat-h" className="card-title">Chat</h2><span className="muted num">{paced.chat.length || ""}</span></div>
      <div className="feed" ref={feed} onScroll={onScroll} role="log" aria-live="polite" aria-label="Negotiation transcript" tabIndex={0}>
        {paced.chat.length === 0 && !typing ? (
          <p className="feed-wait">No messages yet</p>
        ) : (
          <ol className="thread">
            {paced.chat.map((e) => {
              if (e.data.speaker === "viktor") round += 1; // a round starts with the seller's ask or counter
              return <Fragment key={eventKey(e)}><MessageBubble e={e} round={Math.max(round, 1)} /></Fragment>;
            })}
            {typing && (
              <li className={`msg msg-${typing} msg-typing`}>
                <span className="msg-avatar" aria-hidden="true">{NAME[typing][0]}</span>
                <div className="msg-body"><span className="typing" aria-hidden="true"><i /><i /><i /></span>
                  <span className="sr-only" role="status">{NAME[typing]} is thinking</span></div>
              </li>
            )}
          </ol>
        )}
      </div>
    </section>
  );
}
