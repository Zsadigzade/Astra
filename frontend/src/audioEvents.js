import { eventKey } from "./eventIdentity.js";

export const validAudioUrl = (url) => typeof url === "string" && /^\/audio\/[a-zA-Z0-9_-]+\.mp3$/.test(url);

// Original event identity includes timestamp and deal because reset reuses IDs.
export function audioLines(events) {
  const updates = new Map();
  for (const event of events) {
    if (event.type !== "audio_ready") continue;
    const data = event.data ?? {};
    const key = eventKey({ id: data.message_id, ts: data.message_ts, deal_id: event.deal_id });
    if (!updates.has(key)) updates.set(key, event);
  }
  return events.filter((e) => e.type === "negotiation").map((event) => {
    const update = updates.get(eventKey(event));
    const data = update && update.task_id === event.task_id ? update.data : event.data;
    const url = validAudioUrl(data?.audio_url) ? data.audio_url : null;
    return { ...event, data: { ...event.data, audio_url: url,
      audio_status: url ? "ready" : data?.audio_status === "pending" ? "pending" : "unavailable" } };
  });
}
