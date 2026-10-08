// Deal control room. Contract: memory/INTERFACES.md
// (SSE /events, POST /tasks, POST /approvals/{deal_id}, GET|PUT /controls).
import { useEffect, useRef, useState } from "react";
import { SELLER, api } from "./api.js";
import AgentLimits from "./components/AgentLimits.jsx";
import AppHeader from "./components/AppHeader.jsx";
import ConnectionAlert from "./components/ConnectionAlert.jsx";
import DealDetails from "./components/DealDetails.jsx";
import EmptyDealState from "./components/EmptyDealState.jsx";
import EventTimeline from "./components/EventTimeline.jsx";
import NegotiationWorkspace from "./components/NegotiationWorkspace.jsx";
import ScenarioSelector from "./components/ScenarioSelector.jsx";
import UsageSummary from "./components/UsageSummary.jsx";
import WalletGuardCard from "./components/WalletGuardCard.jsx";
import useControls from "./hooks/useControls.js";
import useDealState from "./hooks/useDealState.js";
import useEventStream from "./hooks/useEventStream.js";
import useServiceHealth from "./hooks/useServiceHealth.js";
import useTheme from "./hooks/useTheme.js";

export default function App() {
  const { theme, toggle } = useTheme();
  const { events, status, retry } = useEventStream();
  const { controls, refresh } = useControls(events, status);
  const sellerState = useServiceHealth(SELLER);
  const view = useDealState(events);

  const [scenario, setScenario] = useState("honest");
  const [options, setOptions] = useState({ budget: 20, count: 20, maxRent: 25000 });
  const [launching, setLaunching] = useState(false);
  const [launchError, setLaunchError] = useState(null);
  const [pauseBusy, setPauseBusy] = useState(false);

  const offline = status !== "live";
  const disabledReason = offline ? "Connect to the buyer service to run a scenario."
    : controls?.paused ? "Agents are paused. Resume them to run a scenario."
    : null;

  // Stay "launching" until the buyer's task_created event for this launch arrives, so a double click
  // cannot start two deals. A timer releases the button if that event never comes.
  const baseline = useRef(0);
  useEffect(() => {
    if (launching && events.slice(baseline.current).some((e) => e.type === "task_created")) setLaunching(false);
  }, [events, launching]);

  const run = async () => {
    if (launching || disabledReason) return;
    baseline.current = events.length;
    setLaunching(true);
    setLaunchError(null);
    try {
      await api.startTask({
        demo_mode: scenario, budget: options.budget,
        job: { count: options.count, district: "Praha 7", max_price_czk: options.maxRent },
        text: `Find me ${options.count} flats in Prague 7 under ${options.maxRent.toLocaleString("en-US")} CZK`,
      });
      setTimeout(() => setLaunching(false), 6000);
    } catch (e) {
      setLaunchError(e.message);
      setLaunching(false);
    }
  };

  const togglePause = async () => {
    setPauseBusy(true);
    try { await api.updateControls({ paused: !controls.paused }); await refresh(); } finally { setPauseBusy(false); }
  };

  return (
    <div className="app">
      <AppHeader stream={status} sellerState={sellerState} controls={controls} view={view} theme={theme}
        onToggleTheme={toggle} onTogglePause={togglePause} pauseBusy={pauseBusy} />
      <ConnectionAlert status={status} onRetry={retry} />
      {launchError && <div className="alert alert-danger" role="alert"><div className="alert-body"><strong>Could not start the scenario</strong><span>{launchError}</span></div></div>}

      <main className="layout">
          <aside className="rail rail-left" aria-label="Scenarios and usage">
            <ScenarioSelector selected={scenario} onSelect={setScenario} onRun={run} launching={launching} disabledReason={disabledReason} />
            <UsageSummary view={view} budget={view.task?.budget ?? options.budget} />
            <AgentLimits controls={controls} options={options} onOptions={setOptions} onChanged={refresh} />
          </aside>

          <div className="center">
            {view.dealId
              ? <NegotiationWorkspace view={view} events={events} controls={controls} />
              : <EmptyDealState scenario={scenario} onRun={run} launching={launching} disabledReason={disabledReason} />}
          </div>

          <aside className="rail rail-right" aria-label="Deal safety">
            <WalletGuardCard view={view} controls={controls} />
            <DealDetails view={view} />
            <EventTimeline rows={view.timeline} />
          </aside>
      </main>
    </div>
  );
}
