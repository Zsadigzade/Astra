import { useEffect, useRef, useState } from "react";
import { AudioQueue } from "./audioQueue";

// Mount once next to the negotiation transcript. Do not add parallel audio players.
export default function VoicePlayback({ events, buyerUrl }) {
  const queue = useRef(null);
  const [state, setState] = useState({ playing: false, queued: 0, enabled: false,
    muted: false, blocked: false, skipped: 0 });

  useEffect(() => {
    const instance = new AudioQueue({ buyerUrl, onChange: setState });
    queue.current = instance;
    return () => { instance.destroy(); queue.current = null; };
  }, [buyerUrl]);

  useEffect(() => { queue.current?.ingest(events); }, [events, buyerUrl]);

  const message = state.muted ? "Muted; new lines stay text only."
    : state.blocked ? "Browser paused audio. Press Play voices to continue."
    : state.playing ? "Playing voices in conversation order."
    : state.enabled ? "Ready for the next voice line."
    : "Press Play voices to enable audio. Text is always available.";

  return (
    <section aria-label="Conversation audio">
      <button type="button" onClick={() => queue.current?.play()}
        disabled={state.enabled && !state.muted}>Play voices</button>{" "}
      <button type="button" onClick={() => queue.current?.stop()}>Stop</button>{" "}
      <button type="button" aria-pressed={state.muted}
        onClick={() => queue.current?.setMuted(!state.muted)}>{state.muted ? "Unmute" : "Mute"}</button>
      <p role="status">{message} {state.queued > 0 && `${state.queued} queued.`}
        {state.skipped > 0 && ` ${state.skipped} unavailable clip(s) skipped.`}</p>
    </section>
  );
}
