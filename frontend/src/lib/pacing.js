// Paced reveal of live negotiation lines. Cosmetic: the backend finishes in a flash in scripted mode, so each
// live line gets a short "thinking" beat before it appears. History and past deals are never delayed.
export const LIVE_WINDOW_S = 8; // a line older than this is history; it also caps how far the reveal can lag
export const SPEAK_MS = 1100;

export const isLive = (ts, nowS) => nowS - ts < LIVE_WINDOW_S;

// Longer lines "take longer to think about"; a backlog speeds up so the chat never trails far behind.
export function thinkMs(text, backlog) {
  const base = 650 + Math.min(String(text ?? "").length * 9, 800);
  return backlog > 4 ? Math.round(base / 2.5) : base;
}

// Whose turn is it while we wait for the backend: Viktor opens, then they alternate. Nobody once the haggle is over.
export function nextSpeaker(visibleChat, negotiating) {
  if (!negotiating) return null;
  return visibleChat[visibleChat.length - 1]?.data.speaker === "viktor" ? "max" : "viktor";
}

// How many leading lines are plain history (shown at once when a deal is opened).
export function leadingHistory(chat, nowS) {
  let n = 0;
  while (n < chat.length && !isLive(chat[n].ts, nowS)) n += 1;
  return n;
}
