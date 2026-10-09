import { useEffect, useRef, useState } from "react";
import { GAP_MS, isLive, leadingHistory, nextSpeaker, speakMs, thinkMs } from "../lib/pacing.js";

// Reveals live lines one at a time. Each line gets a thinking beat, then its speech bubble stays up long enough
// to read (longer text, longer bubble) before the next line may land. `enabled` is false for past deals and
// reduced motion, where everything shows at once. Returns the lines to show, who is thinking, who is speaking.
export default function usePacedChat(chat, dealId, negotiating, enabled) {
  const [shown, setShown] = useState(0);
  const [speaking, setSpeaking] = useState(null);
  const lastDeal = useRef(null);
  const speechEnds = useRef(0); // epoch ms when the current speech bubble should disappear
  const loadedAt = useRef(Date.now() / 1000); // lines older than the page are history and never replay

  // A different deal: lines that are already history appear immediately, only the fresh tail is paced.
  useEffect(() => {
    if (lastDeal.current === dealId) return;
    lastDeal.current = dealId;
    speechEnds.current = 0;
    setSpeaking(null);
    setShown(enabled ? leadingHistory(chat, Date.now() / 1000, loadedAt.current) : chat.length);
  }, [dealId, chat, enabled]);

  useEffect(() => {
    if (lastDeal.current !== dealId || shown >= chat.length) return undefined;
    const next = chat[shown];
    if (!enabled || !isLive(next.ts, Date.now() / 1000, loadedAt.current)) { setShown(shown + 1); return undefined; }
    const backlog = chat.length - shown;
    // The next agent may start thinking while the previous one is still talking, but its line waits for that bubble.
    const wait = Math.max(thinkMs(next.data.text, backlog), speechEnds.current - Date.now() + GAP_MS);
    const t = setTimeout(() => {
      const ms = speakMs(next.data.text);
      speechEnds.current = Date.now() + ms;
      setShown(shown + 1);
      setSpeaking({ who: next.data.speaker, text: next.data.text, id: next.id, ms });
    }, wait);
    return () => clearTimeout(t);
  }, [shown, chat, dealId, enabled]);

  useEffect(() => {
    if (!speaking) return undefined;
    const t = setTimeout(() => setSpeaking(null), speaking.ms);
    return () => clearTimeout(t);
  }, [speaking]);

  const count = Math.min(shown, chat.length);
  const visible = chat.slice(0, count);
  const caughtUp = count >= chat.length;
  const thinking = caughtUp ? nextSpeaker(visible, negotiating) : chat[count].data.speaker;
  return { chat: visible, thinking: enabled ? thinking : null, speaking, caughtUp, loadedAt: loadedAt.current };
}
