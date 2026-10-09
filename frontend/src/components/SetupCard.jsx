// What is actually powering the demo right now, straight from the buyer's own settings. Shown while there is no chat yet.
export default function SetupCard({ controls }) {
  const m = controls?.modes;
  const who = (mode) => (mode === "codex" ? "Codex subscription" : "Scripted");
  const rows = m ? [
    ["Max", who(m.llm)],
    ["Viktor", who(m.seller_llm ?? "mock")],
    ["Voice", m.tts === "off" ? "Off (text only)" : "ElevenLabs"],
    ["Anything else", m.answers ? "AI answers on" : "Rentals only"],
    ["Money", m.simulated ? "Simulated" : "Preprod escrow"],
  ] : [];
  return (
    <section className="card" aria-labelledby="setup-h">
      <h2 id="setup-h" className="card-title">Setup</h2>
      {rows.length === 0 ? <p className="hint">Appears once the buyer is online.</p> : (
        <dl className="rows">
          {rows.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}
        </dl>
      )}
    </section>
  );
}
