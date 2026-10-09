import { useEffect, useRef, useState } from "react";
import { AudioQueue } from "../audioQueue";
import Icon from "./Icons.jsx";

// Mount once next to the negotiation transcript. Do not add parallel audio players.
export default function VoicePlayback({ events, buyerUrl, token = "", dealId }) {
  const queue = useRef(null);
  const [state, setState] = useState({ playing: false, queued: 0, enabled: false,
    muted: false, blocked: false, skipped: 0, speed: 1, replayable: [] });
  const [selected, setSelected] = useState("");

  useEffect(() => {
    const instance = new AudioQueue({ buyerUrl, token, onChange: setState });
    queue.current = instance;
    setState(instance.snapshot());
    setSelected("");
    return () => { instance.destroy(); queue.current = null; };
  }, [buyerUrl, token, dealId]);

  useEffect(() => { queue.current?.ingest(events.filter((event) => event.deal_id === dealId)); }, [events, buyerUrl, dealId]);

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
      <select className="voice-select" aria-label="Voice playback speed" title="Playback speed" value={state.speed}
        onChange={(event) => queue.current?.setSpeed(Number(event.target.value))}>
        {[0.75, 1, 1.25, 1.5, 2].map((speed) => <option key={speed} value={speed}>{speed}×</option>)}
      </select>
      {state.replayable.length > 0 && (
        <>
          <select className="voice-select voice-replay" aria-label="Voice line to replay" title="Pick a line to replay" value={selected}
            onChange={(event) => setSelected(event.target.value)}>
            <option value="">Replay a line</option>
            {state.replayable.map((line, index) => <option key={line.key} value={line.key}>
              {index + 1}. {line.speaker}: {line.text.slice(0, 48)}
            </option>)}
          </select>
          <button type="button" className="icon-btn" disabled={!selected || state.muted} onClick={() => queue.current?.replay(selected)}
            aria-label="Replay selected line" title="Replay line"><Icon name="refresh" size={14} /></button>
        </>
      )}
      {state.skipped > 0 && <span className="voice-warn">{state.skipped} skipped</span>}
      <span className="sr-only" role="status">{note}</span>
    </div>
  );
}
