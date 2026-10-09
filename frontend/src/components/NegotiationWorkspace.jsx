import { useState } from "react";
import { API_TOKEN, BUYER } from "../api.js";
import { eventKey } from "../eventIdentity.js";
import ApprovalCard from "./ApprovalCard.jsx";
import DealHeader from "./DealHeader.jsx";
import DealsPanel from "./DealsPanel.jsx";
import EventTimeline from "./EventTimeline.jsx";
import GhostStage from "./GhostStage.jsx";
import ResultsBoard from "./ResultsBoard.jsx";
import Tabs from "./Tabs.jsx";
import VoicePlayback from "./VoicePlayback.jsx";
import WalletGuardCard from "./WalletGuardCard.jsx";

// Centre of the dashboard. The ghosts talk above the tabs; the transcript itself lives in the right rail.
// `paced` is the chat as it is being revealed (shared with the rail); `live` says the reveal animation is on.
export default function NegotiationWorkspace({ view, events, controls, selected, onSelect, trackEyes = false, paced, live }) {
  const [tab, setTab] = useState("results");
  const flats = view.delivery?.result?.kind === "general" ? (view.delivery.result.answer ? 1 : 0) : view.delivery?.result?.flats?.length ?? 0;
  const tabs = [
    { id: "results", label: "Results", count: flats },
    { id: "wallet", label: "Wallet" },
    { id: "timeline", label: "Timeline" },
    { id: "deals", label: "Deals", count: view.deals.length },
  ];
  const panel = {
    results: <ResultsBoard view={view} paced={paced} live={live} />,
    wallet: <div className="wallet-tab"><WalletGuardCard view={view} controls={controls} /></div>,
    timeline: <EventTimeline rows={view.timeline} />,
    deals: <DealsPanel view={view} selected={selected} onSelect={(id) => { onSelect(id); setTab("results"); }} />,
  }[tab];

  return (
    <div className="workspace">
      <DealHeader view={view} onLatest={() => onSelect(null)} />
      {view.approval && view.isLatest && <ApprovalCard key={eventKey(view.approval)} approval={view.approval} controls={controls} />}
      <GhostStage chat={paced.chat} thinking={paced.thinking} speaking={paced.speaking} caughtUp={paced.caughtUp}
        agreed={view.agreed} modes={controls?.modes} trackEyes={trackEyes} />
      <Tabs tabs={tabs} value={tab} onChange={setTab} extra={<VoicePlayback events={events} buyerUrl={BUYER} token={API_TOKEN} dealId={view.dealId} />} />
      <div className="tabpanel" role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>{panel}</div>
    </div>
  );
}
