import { RECOVERY_COMMAND, SCENARIO_LIST } from "../lib/formatters.js";
import CopyButton from "./CopyButton.jsx";
import Icon from "./Icons.jsx";

const SHORT = { honest: "Normal", con: "Con", recovery: "Recovery", junk: "Refund" };

// Secondary control: demo modes as a compact segmented switch. The tooltip says what each one demonstrates.
export default function ScenarioSelector({ selected, onSelect }) {
  const chosen = SCENARIO_LIST.find((s) => s.mode === selected);
  return (
    <section className="card card-quiet" aria-labelledby="scenarios-h">
      <h2 id="scenarios-h" className="card-title">Mode</h2>
      <div className="segmented" role="radiogroup" aria-label="Mode">
        {SCENARIO_LIST.map((s) => (
          <button key={s.mode} type="button" role="radio" aria-checked={selected === s.mode} title={`${s.name}: ${s.purpose}`}
            className={`seg ${selected === s.mode ? "is-on" : ""}`} onClick={() => onSelect(s.mode)}>
            {SHORT[s.mode]}{s.staged && <i className="seg-dot" aria-label="staged" />}
          </button>
        ))}
      </div>
      {chosen?.terminalOnly && (
        <div className="terminal-note">
          <p><Icon name="terminal" size={14} /> Starts from a terminal:</p>
          <div className="cmd"><code>{RECOVERY_COMMAND}</code><CopyButton text={RECOVERY_COMMAND} label="Copy command" /></div>
        </div>
      )}
    </section>
  );
}
