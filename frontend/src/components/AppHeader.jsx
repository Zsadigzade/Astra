import ConnectionStatus from "./ConnectionStatus.jsx";
import Icon from "./Icons.jsx";
import StatusBadge from "./StatusBadge.jsx";
import ThemeToggle from "./ThemeToggle.jsx";

function BrandMark() {
  return (
    <svg className="brand-mark" width="32" height="32" viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="9" fill="var(--accent)" />
      <circle cx="11" cy="16" r="4" fill="#fff" fillOpacity=".95" />
      <circle cx="21" cy="16" r="4" fill="#fff" fillOpacity=".55" />
      <path d="M15 16h2" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export default function AppHeader({ stream, sellerState, controls, view, theme, onToggleTheme, onTogglePause, pauseBusy }) {
  const buyer = { name: "Buyer", state: stream === "live" ? "online" : stream };
  const seller = { name: "Seller", state: sellerState };
  const payments = controls
    ? { name: "Payments", state: "online", detail: controls.modes.simulated ? "Simulated" : "Preprod escrow" }
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
            {controls?.modes.simulated && <StatusBadge tone="warning" icon="info" title="Money is a local ledger, not on-chain">SIMULATED MONEY</StatusBadge>}
            {view.staged && <StatusBadge tone="warning" icon="info" title="This scenario forces seller behaviour for the demo">STAGED SCENARIO</StatusBadge>}
          </div>
        </div>

        <div className="header-actions">
          <button type="button" className={`btn btn-sm ${paused ? "btn-danger-solid" : ""}`} onClick={onTogglePause}
            disabled={!controls || pauseBusy} aria-pressed={!!paused}
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
