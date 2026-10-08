import { RECOVERY_COMMAND, SCENARIO_LIST } from "../lib/formatters.js";
import CopyButton from "./CopyButton.jsx";
import Icon from "./Icons.jsx";

export default function ScenarioSelector({ selected, onSelect }) {
  const chosen = SCENARIO_LIST.find((s) => s.mode === selected);
  const terminalOnly = chosen?.terminalOnly;

  return (
    <section className="card" aria-labelledby="scenarios-h">
      <h2 id="scenarios-h" className="card-title">Mode</h2>

      <div className="scenario-list" role="radiogroup" aria-label="Mode">
        {SCENARIO_LIST.map((s) => (
          <button key={s.mode} type="button" role="radio" aria-checked={selected === s.mode}
            className={`scenario ${selected === s.mode ? "is-selected" : ""}`} onClick={() => onSelect(s.mode)}>
            <span className="scenario-n">{s.n}</span>
            <span className="scenario-text">
              <span className="scenario-name">{s.name}{s.staged && <em className="staged-tag">Staged</em>}</span>
              <span className="scenario-purpose">{s.purpose}</span>
            </span>
            {selected === s.mode && <Icon name="check" size={16} className="scenario-check" />}
          </button>
        ))}
      </div>

      {terminalOnly ? (
        <div className="terminal-note">
          <p><Icon name="terminal" size={14} /> Recovery needs the buyer to crash, so it starts from a terminal:</p>
          <div className="cmd"><code>{RECOVERY_COMMAND}</code><CopyButton text={RECOVERY_COMMAND} label="Copy command" /></div>
          <p className="muted">Then run a normal request here and watch the buyer restart without paying twice.</p>
        </div>
      ) : null}
    </section>
  );
}
