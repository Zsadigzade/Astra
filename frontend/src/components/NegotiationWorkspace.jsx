import { useState } from "react";
import { BUYER } from "../api.js";
import { eventKey } from "../eventIdentity.js";
import ApprovalCard from "./ApprovalCard.jsx";
import ChatPanel from "./ChatPanel.jsx";
import DealHeader from "./DealHeader.jsx";
import DealsPanel from "./DealsPanel.jsx";
import DeliveryPanel from "./DeliveryPanel.jsx";
import EventTimeline from "./EventTimeline.jsx";
import Tabs from "./Tabs.jsx";
import usePacedChat from "../hooks/usePacedChat.js";
import VoicePlayback from "./VoicePlayback.jsx";

export default function NegotiationWorkspace({ view, events, controls, selected, onSelect }) {
  const [tab, setTab] = useState("chat");
  // Live lines get a short thinking beat; past deals and reduced motion show everything at once.
  const reduced = typeof window !== "undefined" && !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  const paced = usePacedChat(view.chat, view.dealId, view.stages.negotiate === "active", view.isLatest && !reduced);
  const flats = view.delivery?.result?.flats?.length ?? 0;
  const tabs = [
    { id: "chat", label: "Chat", count: paced.chat.length },
    { id: "delivery", label: "Delivery", count: flats },
    { id: "timeline", label: "Timeline" },
    { id: "deals", label: "Deals", count: view.deals.length },
  ];
  const panel = { chat: <ChatPanel view={view} paced={paced} modes={controls?.modes} />, delivery: <DeliveryPanel view={view} />,
    timeline: <EventTimeline rows={view.timeline} />,
    deals: <DealsPanel view={view} selected={selected} onSelect={(id) => { onSelect(id); setTab("chat"); }} /> }[tab];

  return (
    <div className="workspace">
      <DealHeader view={view} onLatest={() => onSelect(null)} />
      {view.approval && view.isLatest && <ApprovalCard key={eventKey(view.approval)} approval={view.approval} controls={controls} />}
      <Tabs tabs={tabs} value={tab} onChange={setTab} extra={<VoicePlayback events={events} buyerUrl={BUYER} dealId={view.dealId} />} />
      <div className="tabpanel" role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>{panel}</div>
    </div>
  );
}
