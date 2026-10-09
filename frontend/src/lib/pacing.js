// Paced reveal of live negotiation lines. Cosmetic: the backend finishes in a flash in scripted mode, so each
// live line gets a short "thinking" beat, then stays on screen long enough to read. History and past deals are
// never delayed.
export const LIVE_WINDOW_S = 120; // safety cap: a line this old is shown at once even if it was created after load
export const GAP_MS = 450; // a beat between one speech bubble ending and the next line landing

// Live means created after this page loaded (so a reload never replays history) and not stale.
export const isLive = (ts, nowS, loadedAtS = 0) => ts >= loadedAtS && nowS - ts < LIVE_WINDOW_S;

// Longer lines "take longer to think about"; a backlog speeds up so the chat never trails far behind.
export function thinkMs(text, backlog) {
  const base = 650 + Math.min(String(text ?? "").length * 9, 800);
  return backlog > 4 ? Math.round(base / 2.5) : base;
}

// How long a speech bubble stays over the ghost: reading time grows with the text (about 40ms a character on top
// of 1.2s), never less than 1.6s or more than 5.5s. Not shortened under a backlog: scripted mode delivers every line
// at once, and the bubbles must stay readable anyway.
export function speakMs(text) {
  return Math.min(5500, Math.max(1600, 1200 + String(text ?? "").length * 40));
}

// Whose turn it is while we wait for the backend: Max opens with his question, then they alternate.
// Nobody once the haggle is over.
export function nextSpeaker(visibleChat, negotiating) {
  if (!negotiating) return null;
  return visibleChat[visibleChat.length - 1]?.data.speaker === "max" ? "viktor" : "max";
}

// How many leading lines are plain history (shown at once when a deal is opened).
export function leadingHistory(chat, nowS, loadedAtS = 0) {
  let n = 0;
  while (n < chat.length && !isLive(chat[n].ts, nowS, loadedAtS)) n += 1;
  return n;
}
