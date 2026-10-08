import { useEffect, useRef, useState } from "react";
import { AudioQueue } from "../audioQueue";
import Icon from "./Icons.jsx";

// Mount once next to the negotiation transcript. Do not add parallel audio players.
export default function VoicePlayback({ events, buyerUrl, dealId }) {
  const queue = useRef(null);
  const [state, setState] = useState({ playing: false, queued: 0, enabled: false,
    muted: false, blocked: false, skipped: 0, speed: 1, replayable: [] });
  const [selected, setSelected] = useState("");

  useEffect(() => {
    const instance = new AudioQueue({ buyerUrl, onChange: setState });
    queue.current = instance;
    setState(instance.snapshot());
    setSelected("");
    return () => { instance.destroy(); queue.current = null; };
  }, [buyerUrl, dealId]);

  useEffect(() => { queue.current?.ingest(events.filter((event) => event.deal_id === dealId)); }, [events, buyerUrl, dealId]);

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
        <label>Speed <select aria-label="Voice playback speed" value={state.speed}
          onChange={(event) => queue.current?.setSpeed(Number(event.target.value))}>
          {[0.75, 1, 1.25, 1.5, 2].map((speed) => <option key={speed} value={speed}>{speed}×</option>)}
        </select></label>
      </div>
      {state.replayable.length > 0 && <div className="row">
        <select aria-label="Voice line to replay" value={selected} style={{ maxWidth: "16rem" }}
          onChange={(event) => setSelected(event.target.value)}>
          <option value="">Choose a voice line</option>
          {state.replayable.map((line, index) => <option key={line.key} value={line.key}>
            {index + 1}. {line.speaker}: {line.text.slice(0, 72)}
          </option>)}
        </select>
        <button type="button" className="btn btn-sm" disabled={!selected || state.muted}
          onClick={() => queue.current?.replay(selected)}>Replay line</button>
      </div>}
      <p role="status" className="voice-state">{message}
        {state.queued > 0 && ` ${state.queued} queued.`}
        {state.skipped > 0 && ` ${state.skipped} clip${state.skipped > 1 ? "s" : ""} unavailable, skipped.`}</p>
    </div>
  );
}
