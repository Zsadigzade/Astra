import { useEffect, useRef, useState } from "react";
import { SPEAK_MS, isLive, leadingHistory, nextSpeaker, thinkMs } from "../lib/pacing.js";

// Reveals live lines one at a time with a thinking beat. `enabled` is false for past deals and reduced motion,
// where everything shows at once. Returns the lines to show, who is thinking, and who is speaking right now.
export default function usePacedChat(chat, dealId, negotiating, enabled) {
  const [shown, setShown] = useState(0);
  const [speaking, setSpeaking] = useState(null);
  const lastDeal = useRef(null);

  // A different deal: lines that are already history appear immediately, only the fresh tail is paced.
  useEffect(() => {
    if (lastDeal.current === dealId) return;
    lastDeal.current = dealId;
    setSpeaking(null);
    setShown(enabled ? leadingHistory(chat, Date.now() / 1000) : chat.length);
  }, [dealId, chat, enabled]);

  useEffect(() => {
    if (lastDeal.current !== dealId || shown >= chat.length) return undefined;
    const next = chat[shown];
    if (!enabled || !isLive(next.ts, Date.now() / 1000)) { setShown(shown + 1); return undefined; }
    const t = setTimeout(() => {
      setShown(shown + 1);
      setSpeaking({ who: next.data.speaker, text: next.data.text, id: next.id });
    }, thinkMs(next.data.text, chat.length - shown));
    return () => clearTimeout(t);
  }, [shown, chat, dealId, enabled]);

  useEffect(() => {
    if (!speaking) return undefined;
    const t = setTimeout(() => setSpeaking(null), SPEAK_MS);
    return () => clearTimeout(t);
  }, [speaking]);

  const count = Math.min(shown, chat.length);
  const visible = chat.slice(0, count);
  const caughtUp = count >= chat.length;
  const thinking = caughtUp ? nextSpeaker(visible, negotiating) : chat[count].data.speaker;
  return { chat: visible, thinking: enabled ? thinking : null, speaking, caughtUp };
}
