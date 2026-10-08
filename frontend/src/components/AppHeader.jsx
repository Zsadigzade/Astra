import ConnectionStatus from "./ConnectionStatus.jsx";
import Icon from "./Icons.jsx";
import StatusBadge from "./StatusBadge.jsx";
import ThemeToggle from "./ThemeToggle.jsx";

function BrandMark() {
  // Two chevrons closing on one point: buyer and seller meeting at a price.
  return (
    <svg className="brand-mark" width="30" height="30" viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="#000" />
      <rect x=".5" y=".5" width="31" height="31" rx="7.5" fill="none" stroke="rgba(255,255,255,.16)" />
      <path d="M8.5 10.5L14 16l-5.5 5.5" fill="none" stroke="#38bdf8" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M23.5 10.5L18 16l5.5 5.5" fill="none" stroke="#a78bfa" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="16" cy="16" r="1.5" fill="#fff" />
    </svg>
  );
}

export default function AppHeader({ stream, sellerState, controls, view, theme, onToggleTheme, onTogglePause, pauseBusy }) {
  const buyer = { name: "Buyer", state: stream === "live" ? "online" : stream };
  const seller = { name: "Seller", state: sellerState };
  const payments = controls
    ? (stream === "live"
      ? { name: "Payments", state: "online", detail: controls.modes.simulated ? "Simulated" : "Preprod escrow" }
      : { name: "Payments", state: "unknown" }) // last known mode would be stale while the buyer is unreachable
    : { name: "Payments", state: "unknown" };
  const paused = controls?.paused;

  return (
    <header className="header">
      <div className="header-inner">
        <div className="brand">
          <BrandMark />
          <div className="brand-text">
            <h1>Astra <span>The Haggle</span></h1>
            <p>Agents negotiate. Code controls the wallet.</p>
          </div>
        </div>

        <div className="header-mid">
          <ConnectionStatus items={[buyer, seller, payments]} />
          <div className="honesty">
            {(controls?.modes.simulated ?? view.simulated) && <StatusBadge tone="warning" icon="info" title="Money is a local ledger, not on-chain">SIMULATED MONEY</StatusBadge>}
            {controls?.modes.llm === "mock" && (controls.modes.seller_llm ?? "mock") === "mock" && <StatusBadge tone="neutral" icon="info" title="Max and Viktor follow scripted personas, not a language model">SCRIPTED AGENTS</StatusBadge>}
            {controls?.modes.llm === "codex" && (controls.modes.seller_llm ?? "mock") === "mock" && <StatusBadge tone="neutral" icon="info" title="Max is written by Codex (ChatGPT subscription). Viktor, the seller, is scripted. The staged con act also uses a scripted Max.">VIKTOR SCRIPTED</StatusBadge>}
            {controls?.modes.llm === "mock" && controls.modes.seller_llm === "codex" && <StatusBadge tone="neutral" icon="info" title="Viktor is written by Codex (ChatGPT subscription). Max follows a scripted persona.">MAX SCRIPTED</StatusBadge>}
            {view.staged && <StatusBadge tone="warning" icon="info" title="This scenario forces seller behaviour for the demo">STAGED SCENARIO</StatusBadge>}
          </div>
        </div>

        <div className="header-actions">
          <button type="button" className={`btn btn-sm ${paused ? "btn-danger-solid" : ""}`} onClick={onTogglePause}
            disabled={!controls || pauseBusy || stream !== "live"} aria-pressed={!!paused}
            title="Pausing stops new tasks from starting. Deals already in flight finish safely.">
            <Icon name={paused ? "play" : "pause"} size={14} />
            {paused ? "Resume agents" : "Pause agents"}
          </button>
          <ThemeToggle theme={theme} onToggle={onToggleTheme} />
        </div>
      </div>
    </header>
  );
}
