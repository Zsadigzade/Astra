import ConnectionStatus from "./ConnectionStatus.jsx";
import Icon from "./Icons.jsx";
import StatusBadge from "./StatusBadge.jsx";
import ThemeToggle from "./ThemeToggle.jsx";

function BrandMark() {
  // Two speech bubbles that overlap: the buyer (blue) and the seller (violet) meeting at one agreed spot (white).
  return (
    <svg className="brand-mark" width="32" height="32" viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="9" fill="#000" />
      <rect x=".5" y=".5" width="31" height="31" rx="8.5" fill="none" stroke="rgba(255,255,255,.14)" />
      <rect x="4" y="4.5" width="16" height="12.5" rx="4" fill="#38bdf8" />
      <path d="M8 16.5 V21.5 L13.5 16.5 Z" fill="#38bdf8" />
      <rect x="12" y="12" width="16" height="12.5" rx="4" fill="#a78bfa" />
      <path d="M24 24 V28.5 L18.5 24 Z" fill="#a78bfa" />
      <rect x="12" y="12" width="8" height="5" rx="1.6" fill="#fff" />
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
          {(controls?.modes.simulated ?? view.simulated) && <StatusBadge tone="warning" icon="info" title="Money is a local ledger, not on-chain">SIMULATED MONEY</StatusBadge>}
        </div>

        <div className="header-actions">
          {stream === "live" && controls && (
            <button type="button" className={`btn btn-sm ${paused ? "btn-danger-solid" : ""}`} onClick={onTogglePause}
              disabled={pauseBusy} aria-pressed={!!paused}
              title="Pausing stops new tasks from starting. Deals already in flight finish safely.">
              <Icon name={paused ? "play" : "pause"} size={14} />
              {paused ? "Resume" : "Pause"}
            </button>
          )}
          <ThemeToggle theme={theme} onToggle={onToggleTheme} />
        </div>
      </div>
    </header>
  );
}
