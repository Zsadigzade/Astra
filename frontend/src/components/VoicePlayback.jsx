import { useEffect, useRef, useState } from "react";
import { AudioQueue } from "../audioQueue";
import Icon from "./Icons.jsx";

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

  const message = state.muted ? "Muted. New lines stay text only."
    : state.blocked ? "Browser paused audio. Press Play voices to continue."
    : state.playing ? "Playing voices in order."
    : state.enabled ? "Ready for the next voice line."
    : "Voices off. The transcript is always available.";

  return (
    <div className="voice" role="group" aria-label="Conversation audio">
      <div className="row">
        <button type="button" className="btn btn-sm" onClick={() => queue.current?.play()}
          disabled={state.enabled && !state.muted}><Icon name="play" size={13} /> Play voices</button>
        <button type="button" className="btn btn-sm" onClick={() => queue.current?.stop()}><Icon name="stop" size={13} /> Stop</button>
        <button type="button" className="btn btn-sm" aria-pressed={state.muted}
          onClick={() => queue.current?.setMuted(!state.muted)}>
          <Icon name={state.muted ? "volume-off" : "volume"} size={13} /> {state.muted ? "Unmute" : "Mute"}</button>
      </div>
      <p role="status" className="voice-state">{message}
        {state.queued > 0 && ` ${state.queued} queued.`}
        {state.skipped > 0 && ` ${state.skipped} clip${state.skipped > 1 ? "s" : ""} unavailable, skipped.`}</p>
    </div>
  );
}
