// Deal control room. Contract: memory/INTERFACES.md
// (SSE /events, POST /tasks, POST /approvals/{deal_id}, GET|PUT /controls).
import { useEffect, useRef, useState } from "react";
import { SELLER, api } from "./api.js";
import AgentLimits from "./components/AgentLimits.jsx";
import AppHeader from "./components/AppHeader.jsx";
import ConnectionAlert from "./components/ConnectionAlert.jsx";
import DealDetails from "./components/DealDetails.jsx";
import EmptyDealState from "./components/EmptyDealState.jsx";
import ChatFeed from "./components/ChatFeed.jsx";
import NegotiationWorkspace from "./components/NegotiationWorkspace.jsx";
import RequestComposer from "./components/RequestComposer.jsx";
import ScenarioSelector from "./components/ScenarioSelector.jsx";
import UsageSummary from "./components/UsageSummary.jsx";
import WalletGuardCard from "./components/WalletGuardCard.jsx";
import useControls from "./hooks/useControls.js";
import useDealState from "./hooks/useDealState.js";
import useEventStream from "./hooks/useEventStream.js";
import usePacedChat from "./hooks/usePacedChat.js";
import useRequestParse from "./hooks/useRequestParse.js";
import useServiceHealth from "./hooks/useServiceHealth.js";
import useTheme from "./hooks/useTheme.js";
import { EXAMPLES, SCENARIOS } from "./lib/formatters.js";

export default function App() {
  const { theme, toggle } = useTheme();
  const { events, status, retry } = useEventStream();
  const { controls, refresh } = useControls(events, status);
  const sellerState = useServiceHealth(SELLER);
  const [selectedDeal, setSelectedDeal] = useState(null);
  // The ghosts' eyes follow the cursor from page load until a request is given in this session.
  const [armed, setArmed] = useState(true);
  const [syncTick, setSyncTick] = useState(0);
  const selectDeal = (id) => { setSelectedDeal(id); setSyncTick((t) => t + 1); };
  const view = useDealState(events, selectedDeal);
  // Live lines get a thinking beat and a readable speech bubble; past deals and reduced motion show everything at once.
  const reduced = typeof window !== "undefined" && !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  const live = view.isLatest && !reduced;
  const paced = usePacedChat(view.chat, view.dealId, view.stages.negotiate === "active", live);

  const [scenario, setScenario] = useState("honest");
  const [options, setOptions] = useState({ budget: 20 });
  const [requestText, setRequestText] = useState(EXAMPLES[0]);
  const [launching, setLaunching] = useState(false);
  const [launchError, setLaunchError] = useState(null);
  const [pauseBusy, setPauseBusy] = useState(false);
  const [pauseError, setPauseError] = useState(null);

  // The request and mode shown on the left always describe the deal on screen: opening a past deal (or loading the
  // page with history) loads that deal's request. Typing afterwards edits a new request without touching the deal.
  useEffect(() => {
    if (view.task?.text) setRequestText(view.task.text);
    if (view.scenario && SCENARIOS[view.scenario]) setScenario(view.scenario);
  }, [view.dealId, syncTick]); // eslint-disable-line react-hooks/exhaustive-deps

  const offline = status !== "live";
  const parse = useRequestParse(requestText, !offline);
  const disabledReason = offline ? "Connect to the buyer service to run a request."
    : controls?.paused ? "Agents are paused. Resume them to run a request."
    : SCENARIOS[scenario]?.terminalOnly ? "Recovery starts from a terminal; see the command under Mode."
    : null;

  // Stay "launching" until the buyer's task_created event for this launch arrives, so a double click
  // cannot start two deals. A timer releases the button if that event never comes.
  const baseline = useRef(0);
  useEffect(() => {
    if (launching && events.slice(baseline.current).some((e) => e.type === "task_created")) setLaunching(false);
  }, [events, launching]);

  const run = async () => {
    if (launching || disabledReason || !parse.parsed?.ok) return;
    baseline.current = events.length;
    setSelectedDeal(null); // follow the new deal
    setArmed(false);
    setLaunching(true);
    setLaunchError(null);
    try {
      await api.startTask({
        demo_mode: scenario, budget: options.budget,
        job: parse.parsed.job,
        text: requestText.trim(),
      });
      setTimeout(() => setLaunching(false), 6000);
    } catch (e) {
      setLaunchError(e.message);
      setLaunching(false);
    }
  };

  const togglePause = async () => {
    if (offline || !controls || pauseBusy) return;
    setPauseBusy(true);
    setPauseError(null);
    try {
      await api.updateControls({ paused: !controls.paused });
      await refresh();
    } catch (e) {
      setPauseError(e.message);
    } finally { setPauseBusy(false); }
  };

  return (
    <div className="app">
      <AppHeader stream={status} sellerState={sellerState} controls={controls} view={view} theme={theme}
        onToggleTheme={toggle} onTogglePause={togglePause} pauseBusy={pauseBusy} />
      <ConnectionAlert status={status} onRetry={retry} />
      {pauseError && <div className="alert alert-danger" role="alert"><div className="alert-body"><strong>Could not change agent pause state</strong><span>{pauseError}</span></div></div>}
      {launchError && <div className="alert alert-danger" role="alert"><div className="alert-body"><strong>Could not start the scenario</strong><span>{launchError}</span></div></div>}

      <main className="layout">
          <aside className="rail rail-left" aria-label="Scenarios and usage">
            <RequestComposer text={requestText} onText={setRequestText} parse={parse} onRun={run}
              launching={launching} disabledReason={disabledReason} />
            <ScenarioSelector selected={scenario} onSelect={setScenario} />
            <UsageSummary view={view} budget={view.task?.budget ?? options.budget} />
            <AgentLimits controls={controls} options={options} onOptions={setOptions} onChanged={refresh} />
          </aside>

          <div className="center">
            {view.dealId
              ? <NegotiationWorkspace view={view} events={events} controls={controls} selected={selectedDeal} onSelect={selectDeal} trackEyes={armed}
                  paced={paced} live={live} />
              : <EmptyDealState tracking={armed} scenario={scenario} summary={parse.parsed?.ok ? parse.parsed.summary : null} onRun={run} launching={launching} disabledReason={disabledReason || (!parse.parsed?.ok ? "Fix the request first." : null)} />}
          </div>

          <aside className="rail rail-right" aria-label="Deal safety">
            <ChatFeed view={view} paced={paced} />
            <WalletGuardCard view={view} controls={controls} only="balances" />
            <DealDetails view={view} />
          </aside>
      </main>
    </div>
  );
}
