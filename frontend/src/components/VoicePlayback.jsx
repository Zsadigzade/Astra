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

  const note = `${message}${state.queued > 0 ? ` ${state.queued} queued.` : ""}${state.skipped > 0 ? ` ${state.skipped} clip${state.skipped > 1 ? "s" : ""} unavailable, skipped.` : ""}`;
  return (
    <div className="voice" role="group" aria-label="Conversation audio" title={note}>
      <button type="button" className="icon-btn" onClick={() => queue.current?.play()} disabled={state.enabled && !state.muted}
        aria-label="Play voices" title="Play voices"><Icon name="play" size={14} /></button>
      <button type="button" className="icon-btn" onClick={() => queue.current?.stop()} aria-label="Stop voices" title="Stop"><Icon name="stop" size={14} /></button>
      <button type="button" className="icon-btn" aria-pressed={state.muted} onClick={() => queue.current?.setMuted(!state.muted)}
        aria-label={state.muted ? "Unmute" : "Mute"} title={state.muted ? "Unmute" : "Mute"}><Icon name={state.muted ? "volume-off" : "volume"} size={14} /></button>
      {state.skipped > 0 && <span className="voice-warn">{state.skipped} skipped</span>}
      <span className="sr-only" role="status">{note}</span>
    </div>
  );
}
